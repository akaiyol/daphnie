"""Policy-bound release attestations. Signing keys and policy must be outside learner write access."""
import base64
import copy
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from .store import canonical, digest, FLAVOURS, identifier
from evaluate import review, CHECKS, POLICY

HOST_POLICY = Path.home() / '.config/daphnie/release-policy.json'


def sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('expected a SHA-256 digest')
    return value


def number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value < float('inf'):
        raise ValueError('invalid ' + label)
    return value


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('expected a numeric semantic version')
    return tuple(int(n) for n in value.split('.'))


class ReleaseAuthority:
    """Instantiate only in the trusted host. The learner supplies signed bundles, never trust roots."""
    def __init__(self, policy, clock=time.time):
        self.policy = copy.deepcopy(policy)
        self.clock = clock
        identifier(policy['id'])
        if policy.get('schema') != 1 or policy.get('approval_mode') not in ('per_release', 'preauthorized_policy'):
            raise ValueError('unsupported release policy')
        if not policy.get('allowed_flavours') or not set(policy['allowed_flavours']) <= set(FLAVOURS):
            raise ValueError('policy must name permitted flavours')
        if set(policy.get('evaluation_policy', {})) != POLICY:
            raise ValueError('policy must freeze evaluation thresholds')
        if isinstance(policy.get('min_trial_observations'), bool) or not isinstance(policy.get('min_trial_observations'), int) or policy['min_trial_observations'] < 1:
            raise ValueError('policy must require positive trial observations')
        if not 1 <= number(policy.get('max_grant_seconds'), 'grant lifetime') <= 86400:
            raise ValueError('grant lifetime must be at most one day')
        number(policy.get('min_trial_seconds', 0), 'minimum trial duration')
        if not policy['max_grant_seconds'] <= number(policy.get('max_evidence_seconds', policy['max_grant_seconds']), 'evidence lifetime') <= 30*86400:
            raise ValueError('evidence lifetime must be bounded to thirty days')
        for role in ('evaluation', 'authorization', 'trial'):
            ids = policy.get('roles', {}).get(role)
            if not isinstance(ids, list) or not ids or any(key not in policy.get('keys', {}) for key in ids):
                raise ValueError('policy lacks trusted ' + role + ' keys')
        if set(policy['roles']['authorization']) & (set(policy['roles']['evaluation']) | set(policy['roles']['trial'])):
            raise ValueError('authorization keys must be independent of evaluator/trial keys')
        # Validate thresholds through the same evaluator, not a separate permissive interpretation.
        p = policy['evaluation_policy']
        if isinstance(p['min_families'], bool) or not isinstance(p['min_families'], int) or p['min_families'] < 2:
            raise ValueError('policy needs at least two independent families per suite')
        for name in ('min_improvement', 'max_regression'):
            if number(p[name], name) > 1: raise ValueError('invalid quality threshold')
        number(p['max_cost_ratio'], 'cost ratio', 1)
        if len(policy['keys']) > 16: raise ValueError('too many policy keys')
        for keyid, pem in policy['keys'].items():
            if not isinstance(pem, str) or 'PRIVATE KEY' in pem or len(pem) > 2000:
                raise ValueError('only bounded public keys belong in the host policy')
            with tempfile.TemporaryDirectory(prefix='daphnie-policy-key-') as td:
                key = Path(td) / 'public.pem'; key.write_text(pem)
                raw = subprocess.run(['openssl', 'pkey', '-pubin', '-in', str(key), '-outform', 'DER'], capture_output=True, timeout=10)
                described = subprocess.run(['openssl', 'pkey', '-pubin', '-in', str(key), '-text', '-noout'], capture_output=True, timeout=10)
                if raw.returncode or described.returncode or b'ED25519' not in described.stdout or digest(raw.stdout) != keyid:
                    raise ValueError('policy key ID must fingerprint an Ed25519 public key')
        self.policy_digest = digest(canonical(self.policy).encode())
        self._fresh_policy()

    @classmethod
    def from_host_policy(cls):
        path = HOST_POLICY
        if not path.is_file():
            raise ValueError('Release approval is not configured. A trusted operator must approve one policy and independent signer keys; existing skills remain active.')
        if path.is_symlink() or path.stat().st_mode & 0o222 or path.stat().st_uid != os.getuid():
            raise ValueError('Host release policy must be an owner-owned read-only regular file')
        authority = cls(json.loads(path.read_text()))
        authority._policy_path = path
        return authority

    def _fresh_policy(self):
        if getattr(self, '_policy_path', None):
            if digest(canonical(json.loads(self._policy_path.read_text())).encode()) != self.policy_digest:
                raise ValueError('Host policy changed; obtain fresh authorization')
        if number(self.policy.get('expires_at'), 'policy expiry') <= self.clock():
            raise ValueError('release policy has expired')

    def envelope(self, envelope, role, kind):
        self._fresh_policy()
        if not isinstance(envelope, dict) or set(envelope) != {'signed', 'keyid', 'signature'}:
            raise ValueError('signed attestation required')
        body, keyid = envelope['signed'], envelope['keyid']
        if not isinstance(body, dict): raise ValueError('signed attestation body must be an object')
        if keyid not in self.policy['roles'][role] or body.get('type') != kind:
            raise ValueError('attestation role/type not trusted')
        if len(canonical(body).encode()) > 2 * 1024 * 1024:
            raise ValueError('attestation exceeds supported size')
        now = self.clock()
        issued, expiry = number(body.get('issued_at'), 'issued time'), number(body.get('expires_at'), 'expiry')
        if issued > now or expiry <= now or expiry <= issued or expiry - issued > (self.policy['max_grant_seconds'] if role == 'authorization' else self.policy.get('max_evidence_seconds', self.policy['max_grant_seconds'])):
            raise ValueError('attestation is future-dated, expired or exceeds its lifetime')
        pem = self.policy['keys'][keyid]
        if not isinstance(pem, str) or 'PRIVATE KEY' in pem or 'BEGIN PUBLIC KEY' not in pem:
            raise ValueError('policy must contain public verification keys only')
        try: signature = base64.b64decode(envelope['signature'], validate=True)
        except (ValueError, TypeError): raise ValueError('invalid signature encoding')
        if len(signature) != 64: raise ValueError('Ed25519 signature required')
        with tempfile.TemporaryDirectory(prefix='daphnie-attestation-') as td:
            folder = Path(td)
            (folder / 'public.pem').write_text(pem)
            (folder / 'payload.json').write_text(canonical(body))
            (folder / 'signature').write_bytes(signature)
            result = subprocess.run(['openssl', 'pkeyutl', '-verify', '-pubin', '-inkey', str(folder / 'public.pem'),
                                     '-rawin', '-in', str(folder / 'payload.json'), '-sigfile', str(folder / 'signature')],
                                    capture_output=True, timeout=10)
            if result.returncode: raise ValueError('attestation signature does not match trusted key')
        return body

    def evaluation(self, store, envelope):
        body = self.envelope(envelope, 'evaluation', 'daphnie-evaluation-v1')
        baseline, candidate, flavour = sha(body.get('baseline')), sha(body.get('candidate')), body.get('flavour')
        if flavour not in self.policy['allowed_flavours']: raise ValueError('flavour not authorized by policy')
        supplied = body.get('input')
        if not isinstance(supplied, dict) or supplied.get('flavour') != flavour or supplied.get('candidate_id') != candidate:
            raise ValueError('evaluation input identity mismatch')
        p = supplied.get('policy', {}); frozen = self.policy['evaluation_policy']
        if (set(p) != POLICY or p['min_families'] < frozen['min_families'] or p['min_improvement'] < frozen['min_improvement']
                or p['max_regression'] > frozen['max_regression'] or p['max_cost_ratio'] > frozen['max_cost_ratio']):
            raise ValueError('evaluation weakens the approved policy')
        report = review(supplied)
        if report['decision'] != 'eligible_for_trial' or canonical(report) != canonical(body.get('report')):
            raise ValueError('acceptance report is ineligible or does not reproduce')
        if body.get('protected_acceptance') is not True or body.get('actual_skill_loading') is not True:
            raise ValueError('protected acceptance and actual skill loading must be attested')
        for key in ('suite_sha256', 'configuration_sha256', 'artifact_manifest_sha256'): sha(body.get(key))
        before, after = store.snapshot(baseline), store.snapshot(candidate)
        if before['kind'] != 'package' or after['kind'] != 'package' or before['project'] != after['project']:
            raise ValueError('release snapshots must be packages from the same project')
        old = {e['path']: e for e in before['entries']}; new = {e['path']: e for e in after['entries']}
        changed = sorted(p for p in set(old) | set(new) if old.get(p) != new.get(p))
        prefix = 'libraries/' + flavour + '/'
        if not changed or any(not p.startswith(prefix) for p in changed):
            raise ValueError('automatic release may change only the named flavour library')
        manifest_path = prefix + 'manifest.json'
        if manifest_path not in old or manifest_path not in new or manifest_path not in changed:
            raise ValueError('release must version its flavour manifest')
        previous = json.loads(store.read_blob(old[manifest_path]['blob']))
        proposed = json.loads(store.read_blob(new[manifest_path]['blob']))
        if proposed.get('flavour') != flavour or version(proposed.get('library_version')) <= version(previous.get('library_version')):
            raise ValueError('library version must increase in its own flavour')
        old_skills = {s['id']: s for s in previous.get('skills', [])}
        if not set(old_skills) <= {s['id'] for s in proposed.get('skills', [])}:
            raise ValueError('automatic release cannot remove an existing skill')
        for skill in proposed.get('skills', []):
            relative = prefix + skill['path']
            if relative not in new or not relative.startswith(prefix) or '..' in Path(relative).parts:
                raise ValueError('procedure must stay in its library')
            prior = old_skills.get(skill['id'])
            prior_entry = old.get(prefix + prior['path']) if prior else None
            if (prior and (prior['path'] != skill['path'] or prior_entry != new[relative])
                    and version(skill.get('version')) <= version(prior.get('version'))):
                raise ValueError('changed procedure version must increase')
        return {**body, 'changed_files': changed, 'digest': digest(canonical(body).encode()), 'keyid': envelope['keyid']}

    def grant(self, envelope, evaluation, phase, active):
        body = self.envelope(envelope, 'authorization', 'daphnie-release-grant-v1')
        identifier(body.get('id'))
        if (body.get('policy_id') != self.policy['id'] or body.get('policy_sha256') != self.policy_digest
                or body.get('phase') != phase or body.get('expected_active') != active
                or body.get('evaluation_sha256') != evaluation['digest']
                or any(body.get(k) != evaluation[k] for k in ('baseline', 'candidate', 'flavour'))):
            raise ValueError('grant does not authorize this exact release, evaluation and active baseline')
        return body

    def trial_identity(self, envelope, evaluation, selection):
        body = self.envelope(envelope, 'trial', 'daphnie-trial-v1')
        trial = selection['authorization']
        if (trial.get('kind') != 'signed-trial' or body.get('trial_id') != trial['trial_id']
                or any(body.get(k) != evaluation[k] for k in ('baseline', 'candidate', 'flavour'))
                or body.get('evaluation_sha256') != evaluation['digest']):
            raise ValueError('trial evidence does not match the active trial')
        start, end = number(body.get('started_at'), 'trial start'), number(body.get('finished_at'), 'trial finish')
        if start != trial['started_at'] or end < start or end > self.clock() or body['issued_at'] < end:
            raise ValueError('trial interval mismatch or evidence issued before trial completion')
        return {**body, 'digest': digest(canonical(body).encode())}

    def trial(self, envelope, evaluation, selection):
        body = self.trial_identity(envelope, evaluation, selection)
        if (body.get('checks') != {name: 'pass' for name in CHECKS} or type(body.get('critical_violations')) is not int
                or body.get('critical_violations') != 0 or body.get('rollback_tested') is not True
                or body.get('actual_skill_loading') is not True or type(body.get('observations')) is not int
                or body['observations'] < self.policy['min_trial_observations']
                or body['finished_at'] - body['started_at'] < self.policy.get('min_trial_seconds', 0)):
            raise ValueError('trial failed, incomplete or insufficiently observed')
        return body


def apply_release(store, bundle, authority, phase, preview=False):
    bundle = json.loads(canonical(bundle))  # Freeze caller-owned input before verification.
    if phase not in ('trial', 'promote'): raise ValueError('unsupported release phase')
    with store.release_lock():
        store.reconcile_active()
        selected = store._selection()
        active = selected['release'] if selected else None
        evaluation = authority.evaluation(store, bundle['evaluation'])
        grant = authority.grant(bundle['authorization'], evaluation, phase, active)
        expected = evaluation['baseline'] if phase == 'trial' else evaluation['candidate']
        if active != expected: raise ValueError('active release changed; rebase and reevaluate')
        if store.db.execute('SELECT 1 FROM consumed_grants WHERE id=?', (grant['id'],)).fetchone():
            raise ValueError('release grant already consumed')
        details = {'kind': 'signed-trial' if phase == 'trial' else 'signed-verified-release',
                   'policy_id': authority.policy['id'], 'policy_sha256': authority.policy_digest,
                   'grant_id': grant['id'], 'evaluation_sha256': evaluation['digest'],
                   'trial_id': grant['id'] if phase == 'trial' else selected['authorization'].get('trial_id'),
                   'started_at': authority.clock() if phase == 'trial' else selected['authorization'].get('started_at'),
                   'flavour': evaluation['flavour'], 'baseline': evaluation['baseline']}
        if phase == 'promote':
            observed = authority.trial(bundle['trial'], evaluation, selected)
            if grant['issued_at'] < observed['finished_at']:
                raise ValueError('promotion authorization predates completed trial')
            if grant.get('trial_sha256') != observed['digest']: raise ValueError('grant does not authorize the exact trial evidence')
            details['trial_sha256'] = observed['digest']
        if preview:
            return {"candidate": evaluation["candidate"], "baseline": evaluation["baseline"],
                    "flavour": evaluation["flavour"], "changed_files": evaluation["changed_files"],
                    "policy": authority.policy["id"], "approval_mode": authority.policy["approval_mode"],
                    "phase": phase, "release_applied": False, "history_recovery_may_run": True,
                    "message": "Complete signed release bundle checked; no release applied"}
        # Persist signed evidence privately with the intent; IDs and hashes alone are not proof.
        details['attestations'] = bundle
        return store._activate(evaluation['candidate'], evaluation['candidate'],
                               'Policy-approved ' + phase, False, phase == 'promote', details,
                               revalidate=lambda: (authority.evaluation(store, bundle['evaluation']),
                                                   authority.grant(bundle['authorization'], evaluation, phase, active),
                                                   authority.trial(bundle['trial'], evaluation, selected) if phase == 'promote' else None))


def stop_trial(store, envelope, authority):
    """A trusted observer can stop a failing trial and restore only its exact original baseline."""
    envelope = json.loads(canonical(envelope))
    with store.release_lock():
        store.reconcile_active()
        selected = store._selection()
        if not selected or selected['authorization'].get('kind') != 'signed-trial':
            raise ValueError('no policy-authorized trial is active')
        details = selected['authorization']
        evaluation = {'baseline': details['baseline'], 'candidate': selected['release'],
                      'flavour': details['flavour'], 'digest': details['evaluation_sha256']}
        evidence = authority.trial_identity(envelope, evaluation, selected)
        violations = evidence.get('critical_violations')
        if not ((type(violations) is int and violations > 0) or 'fail' in evidence.get('checks', {}).values()):
            raise ValueError('trial stop requires an explicit signed failure; unknown is not a fabricated failure')
        return store._activate(evaluation['baseline'], evaluation['baseline'], 'Signed trial failure; restore baseline',
                               True, False, {'kind': 'signed-trial-rollback', 'trial_id': details['trial_id'],
                                             'failure_sha256': evidence['digest'], 'attestation': envelope},
                               revalidate=lambda: authority.trial_identity(envelope, evaluation, selected))
