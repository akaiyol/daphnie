"""Signed release controls with synthetic independent signers; not real behavioral acceptance."""
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from control.store import Store, canonical, digest
from control.release import ReleaseAuthority, apply_release, stop_trial
from evaluate import review, CHECKS
from test_controller import package


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = tempfile.TemporaryDirectory(prefix='daphnie-signers-')
        cls.signers = {}
        for role in ('reviewer', 'approver'):
            private = Path(cls.keys.name) / (role + '.pem')
            subprocess.run(['openssl', 'genpkey', '-algorithm', 'ED25519', '-out', str(private)], check=True, capture_output=True)
            private.chmod(0o600)
            public = subprocess.check_output(['openssl', 'pkey', '-in', str(private), '-pubout'], text=True)
            raw = subprocess.check_output(['openssl', 'pkey', '-in', str(private), '-pubout', '-outform', 'DER'])
            cls.signers[role] = {'private': private, 'public': public, 'id': digest(raw)}

    @classmethod
    def tearDownClass(cls): cls.keys.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='daphnie-release-')
        self.base = Path(self.temp.name).resolve()
        self.source = package(self.base / 'source')
        for flavour in ('assistant', 'research', 'think', 'design'):
            p = self.source / 'libraries' / flavour / 'manifest.json'
            p.write_text(json.dumps({'flavour': flavour, 'library_version': '1.0.0',
                                    'skills': [{'id': 'procedure', 'path': 'procedure.md', 'version': '1.0.0'}]}))
        self.store = Store(self.base / 'state'); self.store.register('source', self.source, 'shared', 'project')
        self.baseline = self.store.capture('source')['snapshot']
        self.store.prepare_release(self.baseline); self.store.activate(self.baseline, self.baseline, 'Synthetic baseline')
        (self.source / 'libraries/assistant/procedure.md').write_text('Changed synthetic assistant procedure')
        manifest = self.source / 'libraries/assistant/manifest.json'
        data = json.loads(manifest.read_text()); data['library_version'] = '1.0.1'; data['skills'][0]['version'] = '1.0.1'
        manifest.write_text(json.dumps(data))
        self.candidate = self.store.capture('source')['snapshot']; self.store.prepare_release(self.candidate)
        self.now = time.time()
        reviewer, approver = self.signers['reviewer'], self.signers['approver']
        self.policy = {'schema': 1, 'id': 'synthetic-approved-policy', 'approval_mode': 'preauthorized_policy',
                       'expires_at': self.now + 3600, 'max_grant_seconds': 600,
                       'allowed_flavours': ['assistant'], 'min_trial_observations': 3,
                       'evaluation_policy': {'min_families': 3, 'min_improvement': 0.05, 'max_regression': 0.02, 'max_cost_ratio': 1.2},
                       'keys': {reviewer['id']: reviewer['public'], approver['id']: approver['public']},
                       'roles': {'evaluation': [reviewer['id']], 'trial': [reviewer['id']], 'authorization': [approver['id']]}}
        self.authority = ReleaseAuthority(self.policy)
        supplied = {'candidate_id': self.candidate, 'flavour': 'assistant', 'change_type': 'skill',
                    'policy': self.policy['evaluation_policy'], 'checks': {name: 'pass' for name in CHECKS},
                    'runs': [{'family': f'{kind}-{i}', 'suite': kind, 'split': 'acceptance',
                              'baseline': 0.5, 'candidate': 0.8 if kind == 'target' else 0.5,
                              'baseline_cost': 1, 'candidate_cost': 1} for kind in ('target', 'regression') for i in range(3)]}
        self.evaluated = {'type': 'daphnie-evaluation-v1', 'baseline': self.baseline, 'candidate': self.candidate,
                          'flavour': 'assistant', 'input': supplied, 'report': review(supplied),
                          'protected_acceptance': True, 'actual_skill_loading': True,
                          'suite_sha256': 'a'*64, 'configuration_sha256': 'b'*64, 'artifact_manifest_sha256': 'c'*64,
                          'issued_at': self.now-1, 'expires_at': self.now+500}

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def sign(self, body, role='reviewer'):
        folder = self.base / uuid.uuid4().hex; folder.mkdir(mode=0o700)
        payload = folder / 'payload'; payload.write_text(canonical(body))
        signature = subprocess.check_output(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', str(self.signers[role]['private']), '-in', str(payload)])
        return {'signed': copy.deepcopy(body), 'keyid': self.signers[role]['id'], 'signature': base64.b64encode(signature).decode()}

    def bundle(self, phase='trial', trial=None):
        grant = {'type': 'daphnie-release-grant-v1', 'id': uuid.uuid4().hex,
                 'policy_id': self.policy['id'], 'policy_sha256': self.authority.policy_digest,
                 'phase': phase, 'baseline': self.baseline, 'candidate': self.candidate, 'flavour': 'assistant',
                 'expected_active': self.baseline if phase == 'trial' else self.candidate,
                 'evaluation_sha256': digest(canonical(self.evaluated).encode()),
                 'issued_at': time.time(), 'expires_at': self.now+500}
        result = {'evaluation': self.sign(self.evaluated)}
        if trial:
            grant['trial_sha256'] = digest(canonical(trial).encode()); result['trial'] = self.sign(trial)
        result['authorization'] = self.sign(grant, 'approver')
        return result

    def trial_evidence(self):
        selected = self.store._selection()
        return {'type': 'daphnie-trial-v1', 'trial_id': selected['authorization']['trial_id'],
                'baseline': self.baseline, 'candidate': self.candidate, 'flavour': 'assistant',
                'evaluation_sha256': digest(canonical(self.evaluated).encode()),
                'checks': {name: 'pass' for name in CHECKS}, 'critical_violations': 0,
                'rollback_tested': True, 'actual_skill_loading': True, 'observations': 3,
                'started_at': selected['authorization']['started_at'], 'finished_at': time.time(),
                'issued_at': time.time(), 'expires_at': self.now+500}

    def test_signed_trial_then_verified_release_without_changing_core_or_other_flavours(self):
        first = apply_release(self.store, self.bundle(), self.authority, 'trial')
        self.assertFalse(first['behavior_verified'])
        trial = self.trial_evidence()
        final = apply_release(self.store, self.bundle('promote', trial), self.authority, 'promote')
        self.assertTrue(final['behavior_verified'])
        self.assertEqual(final['state'], 'applied')
        self.assertEqual(self.store._selection()['authorization']['kind'], 'signed-verified-release')
        self.assertEqual((self.store.home/'current/CORE.md').read_text(), 'Shared core')
        self.assertEqual((self.store.home/'current/libraries/research/procedure.md').read_text(), 'Procedure')
        self.assertFalse((self.store.home/'current/CORE.md').stat().st_mode & 0o222)

    def test_tampered_or_forged_grants_cannot_apply(self):
        bundle = self.bundle(); bundle['authorization']['signed']['candidate'] = 'f'*64
        with self.assertRaises(ValueError): apply_release(self.store, bundle, self.authority, 'trial')
        bundle = self.bundle(); bundle['authorization'] = self.sign(bundle['authorization']['signed'], 'reviewer')
        with self.assertRaises(ValueError): apply_release(self.store, bundle, self.authority, 'trial')
        self.assertEqual(self.store.reconcile_active(), self.baseline)

    def test_redirected_procedure_requires_version_increase_before_trial_and_promotion(self):
        library = self.source / 'libraries/assistant'
        manifest_path = library / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['library_version'] = '1.0.0'
        manifest['skills'][0]['version'] = '1.0.0'
        manifest_path.write_text(json.dumps(manifest))
        (library / 'alternate.md').write_text('Different active procedure')
        self.baseline = self.store.capture('source')['snapshot']
        self.store.prepare_release(self.baseline)
        self.store.activate(self.baseline, self.baseline, 'Synthetic path baseline')
        manifest['library_version'] = '1.0.1'
        manifest['skills'][0]['path'] = 'alternate.md'
        manifest_path.write_text(json.dumps(manifest))
        self.candidate = self.store.capture('source')['snapshot']
        self.store.prepare_release(self.candidate)
        self.evaluated.update(baseline=self.baseline, candidate=self.candidate)
        self.evaluated['input']['candidate_id'] = self.candidate
        self.evaluated['report'] = review(self.evaluated['input'])
        with self.assertRaisesRegex(ValueError, 'changed procedure version must increase'):
            apply_release(self.store, self.bundle(), self.authority, 'trial')
        self.assertEqual(self.store.reconcile_active(), self.baseline)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM consumed_grants').fetchone()[0], 0)
        manifest['skills'][0]['version'] = '1.0.1'
        manifest_path.write_text(json.dumps(manifest))
        self.candidate = self.store.capture('source')['snapshot']
        self.store.prepare_release(self.candidate)
        self.evaluated['candidate'] = self.candidate
        self.evaluated['input']['candidate_id'] = self.candidate
        self.evaluated['report'] = review(self.evaluated['input'])
        apply_release(self.store, self.bundle(), self.authority, 'trial')
        result = apply_release(self.store, self.bundle('promote', self.trial_evidence()), self.authority, 'promote')
        self.assertTrue(result['behavior_verified'])
        self.assertEqual((self.store.home / 'current/libraries/assistant/alternate.md').read_text(), 'Different active procedure')

    def test_authorization_expiring_after_staging_cannot_publish(self):
        bundle = self.bundle()
        grant = bundle['authorization']['signed']
        grant['expires_at'] = grant['issued_at'] + 10
        bundle['authorization'] = self.sign(grant, 'approver')
        clock, staged = [time.time()], [False]
        self.authority.clock = lambda: clock[0]
        original = self.store._create_deployment
        def expire_after_staging(*args, **kwargs):
            result = original(*args, **kwargs)
            staged[0] = True
            clock[0] = grant['expires_at'] + 1
            return result
        with patch.object(self.store, '_create_deployment', side_effect=expire_after_staging):
            with self.assertRaisesRegex(ValueError, 'expired'):
                apply_release(self.store, bundle, self.authority, 'trial')
        self.assertTrue(staged[0])
        self.assertEqual(self.store.reconcile_active(), self.baseline)

    def test_expired_unknown_and_development_evidence_cannot_apply(self):
        for mutate in (lambda e:e.update(expires_at=self.now-1),
                       lambda e:e.update(protected_acceptance=False),
                       lambda e:e.update(actual_skill_loading=False),
                       lambda e:e['input']['checks'].update(privacy='unknown'),
                       lambda e:e['input']['runs'][0].update(split='development')):
            saved = copy.deepcopy(self.evaluated); mutate(self.evaluated)
            with self.assertRaises(ValueError): apply_release(self.store, self.bundle(), self.authority, 'trial')
            self.evaluated = saved
        self.assertEqual(self.store.reconcile_active(), self.baseline)

    def test_policy_weakened_or_changed_core_is_rejected(self):
        self.evaluated['input']['policy'] = dict(self.policy['evaluation_policy'], min_families=2)
        self.evaluated['report'] = review(self.evaluated['input'])
        with self.assertRaises(ValueError): apply_release(self.store, self.bundle(), self.authority, 'trial')
        (self.source/'CORE.md').write_text('Unauthorized core edit')
        self.evaluated['candidate'] = self.store.capture('source')['snapshot']
        self.evaluated['input']['candidate_id'] = self.evaluated['candidate']
        self.evaluated['input']['policy'] = self.policy['evaluation_policy']; self.evaluated['report'] = review(self.evaluated['input'])
        with self.assertRaises(ValueError): self.authority.evaluation(self.store, self.sign(self.evaluated))

    def test_grant_replay_and_stale_baseline_are_rejected(self):
        bundle = self.bundle(); apply_release(self.store, bundle, self.authority, 'trial')
        with self.assertRaises(ValueError): apply_release(self.store, bundle, self.authority, 'trial')
        self.store.activate(self.baseline, self.baseline, 'Return to baseline', rollback=True)
        with self.assertRaises(ValueError): apply_release(self.store, bundle, self.authority, 'trial')

    def test_promotion_requires_matching_successful_monitored_trial(self):
        with self.assertRaises((ValueError, KeyError)): apply_release(self.store, self.bundle('promote'), self.authority, 'promote')
        apply_release(self.store, self.bundle(), self.authority, 'trial')
        for name, value in [('observations', 0), ('critical_violations', 1), ('rollback_tested', False), ('trial_id', 'other')]:
            trial = self.trial_evidence(); trial[name] = value
            with self.assertRaises(ValueError): apply_release(self.store, self.bundle('promote', trial), self.authority, 'promote')
        self.assertFalse(self.store._selection()['behavior_verified'])

    def test_mutation_of_prepared_package_after_precheck_cannot_change_deployed_bytes(self):
        original = self.store.validate_package; changed = [False]
        def mutate(sid, destination):
            original(sid, destination)
            if sid == self.candidate and not changed[0]:
                (self.store.home/'packages'/sid/'CORE.md').write_text('External write')
                changed[0] = True
        with patch.object(self.store, 'validate_package', side_effect=mutate):
            result = self.store.activate(self.candidate, self.candidate, 'Snapshot deployment')
        self.assertEqual(result['state'], 'applied')
        self.assertEqual((self.store.home/'current/CORE.md').read_text(), 'Shared core')
        self.assertEqual(self.store._selection()['release'], self.candidate)

    def test_pointer_failure_preserves_previous_active_and_does_not_replay_unpublished_intent(self):
        with patch.object(self.store, '_switch_pointer', side_effect=OSError('Injected before publish')):
            with self.assertRaises(OSError): self.store.activate(self.candidate, self.candidate, 'Failure drill')
        self.assertEqual(self.store.reconcile_active(), self.baseline)
        self.assertEqual(self.store.db.execute('SELECT release FROM active').fetchone()[0], self.baseline)

    def test_post_pointer_history_failure_is_recovered_once_and_reported_as_applied(self):
        original = self.store._finish_activation
        count = [0]
        def fail_candidate(receipt):
            if receipt['release'] == self.candidate:
                count[0] += 1
                if count[0] == 1: raise OSError('Injected history failure')
            return original(receipt)
        with patch.object(self.store, '_finish_activation', side_effect=fail_candidate):
            result = self.store.activate(self.candidate, self.candidate, 'Recovery drill')
        self.assertEqual(result['state'], 'applied_pending_history_recovery')
        self.assertEqual((self.store.home/'current/VERSION.txt').read_text(), '0')
        self.assertEqual(self.store.reconcile_active(), self.candidate)
        before = self.store.db.execute('SELECT count(*) FROM activations').fetchone()[0]
        self.store.reconcile_active()
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM activations').fetchone()[0], before)

    def test_signed_trial_failure_restores_exact_baseline_without_new_owner_prompt(self):
        apply_release(self.store, self.bundle(), self.authority, 'trial')
        failure = self.trial_evidence(); failure['critical_violations'] = 1
        result = stop_trial(self.store, self.sign(failure), self.authority)
        self.assertEqual(result['active'], self.baseline)
        self.assertFalse(result['behavior_verified'])
        self.assertEqual(self.store._selection()['authorization']['kind'], 'signed-trial-rollback')

    def test_unknown_trial_is_blocked_and_cannot_be_relabelled_a_failure(self):
        apply_release(self.store, self.bundle(), self.authority, 'trial')
        trial = self.trial_evidence(); trial['checks']['privacy'] = 'unknown'
        with self.assertRaises(ValueError): stop_trial(self.store, self.sign(trial), self.authority)
        with self.assertRaises(ValueError): apply_release(self.store, self.bundle('promote', trial), self.authority, 'promote')

    def test_preview_checks_full_bundle_without_consuming_authorization(self):
        bundle = self.bundle()
        result = apply_release(self.store, bundle, self.authority, 'trial', preview=True)
        self.assertFalse(result['release_applied'])
        self.assertEqual(self.store.reconcile_active(), self.baseline)
        apply_release(self.store, bundle, self.authority, 'trial')
        with self.assertRaises(KeyError):
            apply_release(self.store, self.bundle('promote'), self.authority, 'promote', preview=True)
        result = apply_release(self.store, self.bundle('promote', self.trial_evidence()), self.authority, 'promote', preview=True)
        self.assertFalse(result['release_applied'])
        self.assertFalse(self.store._selection()['behavior_verified'])
        with self.assertRaises(ValueError):
            apply_release(self.store, bundle, self.authority, 'unknown', preview=True)

    def test_host_policy_requires_read_only_owner_file_and_cli_reports_setup(self):
        from control import cli, release
        from contextlib import redirect_stdout
        import io
        path = self.base / 'policy.json'
        with patch.object(release, 'HOST_POLICY', path):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(['--state', str(self.store.home), 'release-status']), 0)
            self.assertFalse(json.loads(output.getvalue())['policy']['configured'])
            path.write_text(json.dumps(self.policy)); path.chmod(0o600)
            with self.assertRaises(ValueError): ReleaseAuthority.from_host_policy()
            path.chmod(0o400)
            self.assertEqual(ReleaseAuthority.from_host_policy().policy['id'], self.policy['id'])
            bundle = self.base / 'bundle.json'; bundle.write_text(json.dumps(self.bundle()))
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(['--state', str(self.store.home), 'release-preview', '--bundle', str(bundle)]), 0)
            self.assertFalse(json.loads(output.getvalue())['release_applied'])

    def test_approval_keys_must_be_distinct_from_reviewers(self):
        policy = copy.deepcopy(self.policy); policy['roles']['authorization'] = policy['roles']['evaluation']
        with self.assertRaises(ValueError): ReleaseAuthority(policy)


if __name__ == '__main__': unittest.main()
