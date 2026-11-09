"""Task-driven update decisions. No model calls, new budgets, schedules or self-issued grants."""
import json

from .store import canonical, digest
from .release import apply_release, stop_trial


def advance_update(store, bundle, authority):
    """Advance one scoped candidate as far as available trusted evidence permits.

    The host obtains evaluation/authorization using its existing task allowance.
    This function selects transitions; it never fabricates missing attestations.
    """
    if not isinstance(bundle, dict): raise ValueError("update bundle must be an object")
    bundle = json.loads(canonical(bundle))
    with store.release_lock():
        active = store.reconcile_active()
        selected = store._selection()
        evaluation_envelope = bundle.get('evaluation', {})
        if not isinstance(evaluation_envelope, dict): raise ValueError('evaluation envelope must be an object')
        body = evaluation_envelope.get('signed', {})
        if not isinstance(body, dict): raise ValueError('signed evaluation body must be an object')
        identity = {key: body.get(key) for key in ('baseline', 'candidate', 'flavour')}
        evidence_blob = store.blob(canonical(bundle).encode())

        def record(decision, reason, result=None):
            value = {**identity, 'decision': decision, 'reason': reason,
                     'evidence_blob': evidence_blob, 'model_attempts_started': 0,
                     'background_task_started': False}
            if result is not None: value['release'] = result
            with store.transaction(): store.event('update_decision', value)
            return value

        # A selected trial can be stopped even if its earlier evaluation has expired.
        # stop_trial checks the current trusted policy and exact signed trial identity.
        if selected and selected['authorization'].get('kind') == 'signed-trial' and 'trial' in bundle:
            details = selected['authorization']
            matching = {'baseline': details['baseline'], 'candidate': selected['release'],
                        'flavour': details['flavour'], 'digest': details['evaluation_sha256']}
            observed = authority.trial_identity(bundle['trial'], matching, selected)
            if (type(observed.get('critical_violations')) is int and observed['critical_violations'] > 0
                    or 'fail' in observed.get('checks', {}).values()):
                identity.update({key: matching[key] for key in identity})
                result = stop_trial(store, bundle['trial'], authority)
                return record('rolled_back', 'Signed trial failure restored the original baseline', result)

        evaluation = authority.evaluation(store, bundle['evaluation'])
        if selected and active == evaluation['candidate']:
            details = selected['authorization']
            if details.get('evaluation_sha256') != evaluation['digest']:
                return record('deferred', 'Selected candidate has a different evaluation; reconcile the baseline first')
            if selected['behavior_verified'] and details.get('kind') == 'signed-verified-release':
                return record('already_current', 'This exact evaluated candidate is already verified')
            if details.get('kind') != 'signed-trial':
                return record('deferred', 'Selected candidate is not the matching policy-authorized trial')
            if 'trial' not in bundle:
                return record('deferred', 'Continue observing the current trial within its authorized task scope')
            # Failed signatures/identities are errors. Valid but insufficient observations are a deferral.
            authority.trial_identity(bundle['trial'], evaluation, selected)
            try:
                authority.trial(bundle['trial'], evaluation, selected)
            except ValueError as error:
                return record('deferred', str(error))
            phase = 'promote'
        elif active == evaluation['baseline']:
            phase = 'trial'
        else:
            return record('deferred', 'Active baseline changed; rebase and reevaluate the candidate')
        if 'authorization' not in bundle:
            return record('deferred', 'Obtain a signed ' + phase + ' grant from the configured policy service; no new owner approval is required within policy')
        # Check before preparing; the normal release gate rechecks before publication.
        authority.grant(bundle['authorization'], evaluation, phase, active)
        store.prepare_release(evaluation['baseline'])
        store.prepare_release(evaluation['candidate'])
        result = apply_release(store, bundle, authority, phase)
        return record('trial_started' if phase == 'trial' else 'promoted',
                      'Available signed evidence satisfied the configured ' + phase + ' gate', result)
