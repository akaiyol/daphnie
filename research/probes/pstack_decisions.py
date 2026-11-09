#!/usr/bin/env python3
"""Diagnose the reviewed decisions with real code and synthetic evidence.

No live model calls or production writes. Exit 0 means the diagnostic completed,
not that the system is defect-free. Findings appear explicitly in JSON output.
Uses disposable test_release fixtures and requires OpenSSL Ed25519 support.
"""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch


def fixture_case(fixture_type, probe):
    fixture = fixture_type()
    fixture.setUp()
    try:
        return probe(fixture)
    finally:
        fixture.tearDown()


def procedure_identity(f):
    from control.release import apply_release
    from evaluate import review
    library = f.source / 'libraries/assistant'
    manifest = library / 'manifest.json'
    baseline = {'flavour': 'assistant', 'library_version': '1.0.0',
                'skills': [{'id': 'procedure', 'path': 'procedure.md', 'version': '1.0.0'}]}
    manifest.write_text(json.dumps(baseline))
    (library / 'procedure.md').write_text('Original active procedure')
    (library / 'alternate.md').write_text('Different active procedure')
    f.baseline = f.store.capture('source')['snapshot']
    f.store.prepare_release(f.baseline)
    f.store.activate(f.baseline, f.baseline, 'Synthetic identity baseline')
    candidate = json.loads(json.dumps(baseline))
    candidate['library_version'] = '1.0.1'
    candidate['skills'][0]['path'] = 'alternate.md'
    manifest.write_text(json.dumps(candidate))
    f.candidate = f.store.capture('source')['snapshot']
    f.store.prepare_release(f.candidate)
    f.evaluated.update(baseline=f.baseline, candidate=f.candidate)
    f.evaluated['input']['candidate_id'] = f.candidate
    f.evaluated['report'] = review(f.evaluated['input'])
    try:
        trial = apply_release(f.store, f.bundle(), f.authority, 'trial')
    except ValueError as error:
        if str(error) != 'changed procedure version must increase':
            raise
        preserved = f.store.reconcile_active() == f.baseline
        return {'probe': 'procedure_identity', 'expected': 'reject changed procedure without a version increase',
                'rejected': True, 'reason': str(error), 'baseline_preserved': preserved,
                'observed_defect': not preserved}
    final = apply_release(f.store, f.bundle('promote', f.trial_evidence()), f.authority, 'promote')
    selected = json.loads((f.store.home / 'current/libraries/assistant/manifest.json').read_text())['skills'][0]
    text = (f.store.home / 'current/libraries/assistant' / selected['path']).read_text()
    return {'probe': 'procedure_identity', 'expected': 'reject changed procedure without a version increase',
            'before': baseline['skills'][0], 'after': selected, 'selected_text': text,
            'trial': trial['state'], 'promotion': final['state'], 'control_verification_label': final['behavior_verified'],
            'observed_defect': selected['version'] == '1.0.0' and text != 'Original active procedure'}


def malformed_input(f):
    from control import cli, release
    policy = f.base / 'policy.json'
    policy.write_text(json.dumps(f.policy))
    policy.chmod(0o400)
    cases = []
    for evaluation in ([], None):
        bundle = f.base / 'malformed.json'
        bundle.write_text(json.dumps({'evaluation': evaluation}))
        stderr = io.StringIO()
        result = {'input': evaluation, 'return_code': None, 'escaped_exception': None}
        with patch.object(release, 'HOST_POLICY', policy), contextlib.redirect_stderr(stderr):
            try:
                result['return_code'] = cli.main(['--state', str(f.store.home), 'advance-update', '--bundle', str(bundle)])
            except Exception as error:
                result['escaped_exception'] = type(error).__name__
        result['stderr'] = stderr.getvalue()
        cases.append(result)
    return {'probe': 'malformed_input', 'expected': 'return 2 and a validation message without an escaping exception',
            'cases': cases, 'baseline_preserved': f.store.reconcile_active() == f.baseline,
            'observed_defect': any(case['escaped_exception'] is not None or case['return_code'] != 2
                                   or not case['stderr'].startswith('ERROR: ') for case in cases)}


def quality_only_gate():
    from evaluate import review, CHECKS
    data = {'candidate_id': 'synthetic-efficiency-candidate', 'flavour': 'assistant', 'change_type': 'skill',
            'policy': {'min_families': 3, 'min_improvement': 0.05, 'max_regression': 0.02, 'max_cost_ratio': 1.2},
            'checks': dict.fromkeys(CHECKS, 'pass'),
            'runs': [{'family': f'{kind}-{i}', 'suite': kind, 'split': 'acceptance',
                      'baseline': 1.0, 'candidate': 1.0, 'baseline_cost': 1.0, 'candidate_cost': 0.5}
                     for kind in ('target', 'regression') for i in range(3)]}
    report = review(data)
    return {'probe': 'quality_only_gate', 'decision': report['decision'],
            'quality_delta': report['mean_target_improvement'], 'supplied_cost_ratio': report['worst_family_cost_ratio'],
            'reasons': report['reasons'], 'observed_defect': False,
            'interpretation': 'Current quality-only profile cannot approve an efficiency-only change. Synthetic supplied costs are not a performance measurement.'}


def final_authorization(f):
    from control.release import apply_release
    bundle = f.bundle()
    grant = bundle['authorization']['signed']
    grant['expires_at'] = grant['issued_at'] + 10
    bundle['authorization'] = f.sign(grant, 'approver')
    clock = [time.time()]
    staged = [False]
    f.authority.clock = lambda: clock[0]
    original = f.store._create_deployment

    def expire_after_staging(*args, **kwargs):
        result = original(*args, **kwargs)
        staged[0] = True
        clock[0] = bundle['authorization']['signed']['expires_at'] + 1
        return result

    rejected = False
    with patch.object(f.store, '_create_deployment', side_effect=expire_after_staging):
        try:
            apply_release(f.store, bundle, f.authority, 'trial')
        except ValueError:
            rejected = True
    preserved = f.store.reconcile_active() == f.baseline
    return {'probe': 'final_authorization', 'staged_before_expiry': staged[0], 'expired_grant_rejected': rejected, 'baseline_preserved': preserved,
            'observed_defect': not (staged[0] and rejected and preserved),
            'interpretation': 'Final validation crosses a time-of-use boundary and must not be removed as duplicate checking.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path[:0] = [str(root / 'scripts'), str(root / 'tests')]
    from test_release import ReleaseTests
    ReleaseTests.setUpClass()
    try:
        results = [fixture_case(ReleaseTests, procedure_identity), fixture_case(ReleaseTests, malformed_input),
                   quality_only_gate(), fixture_case(ReleaseTests, final_authorization)]
        print(json.dumps({'synthetic_control_probes': True, 'live_model_calls': 0, 'production_writes': False,
                          'results': results}, indent=2))
    finally:
        ReleaseTests.tearDownClass()


if __name__ == '__main__':
    main()
