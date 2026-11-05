#!/usr/bin/env python3
"""Review paired procedural outcomes; never execute an agent or activate a release."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys

FLAVOURS = {'assistant', 'research', 'design', 'think'}
CHECKS = {'evidence_integrity', 'flavour_fidelity', 'permissions', 'privacy',
          'context_isolation', 'transfer', 'evaluator_calibration'}
POLICY = {'min_families', 'min_improvement', 'max_regression', 'max_cost_ratio'}


def number(value, name, low=0, high=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if value < low or (high is not None and value > high) or (positive and value <= 0):
        raise ValueError(f'{name} outside allowed range')
    return value


def interval(values):
    """Family bootstrap, not per-repeat resampling. Fixed seed makes reports reproducible."""
    rng = random.Random(0)
    means = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(2000))
    return [means[49], means[1949]]


def review(data):
    if not isinstance(data, dict):
        raise ValueError('input must be an object')
    if not isinstance(data.get('candidate_id'), str) or not data['candidate_id'].strip():
        raise ValueError('candidate_id required')
    if data.get('flavour') not in FLAVOURS or data.get('change_type') not in {'skill', 'retrieval'}:
        raise ValueError('invalid flavour or procedural change_type')
    policy = data.get('policy')
    if not isinstance(policy, dict) or set(policy) != POLICY:
        raise ValueError('policy must declare all supported thresholds')
    count = policy['min_families']
    if isinstance(count, bool) or not isinstance(count, int) or count < 2:
        raise ValueError('min_families must be an integer >= 2')
    number(policy['min_improvement'], 'min_improvement', high=1)
    number(policy['max_regression'], 'max_regression', high=1)
    number(policy['max_cost_ratio'], 'max_cost_ratio', low=1)
    checks = data.get('checks')
    if not isinstance(checks, dict) or set(checks) != CHECKS:
        raise ValueError('all mandatory checks required; unknown names are invalid')
    if any(v not in ('pass', 'fail', 'unknown') for v in checks.values()):
        raise ValueError('check results must be pass, fail or unknown')
    runs = data.get('runs')
    if not isinstance(runs, list) or not runs:
        raise ValueError('nonempty paired runs required')
    families = {}
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError('run must be an object')
        family = run.get('family')
        if not isinstance(family, str) or not family.strip():
            raise ValueError('family ID required')
        if run.get('split') != 'acceptance' or run.get('suite') not in {'target', 'regression'}:
            raise ValueError('only acceptance target/regression outcomes are eligible')
        baseline = number(run.get('baseline'), 'baseline', high=1)
        candidate = number(run.get('candidate'), 'candidate', high=1)
        old_cost = number(run.get('baseline_cost'), 'baseline_cost', positive=True)
        new_cost = number(run.get('candidate_cost'), 'candidate_cost', positive=True)
        item = families.setdefault(family, {'suite': run['suite'], 'deltas': [], 'costs': []})
        if item['suite'] != run['suite']:
            raise ValueError('a family cannot occur in both suites')
        item['deltas'].append(candidate - baseline)
        ratio = new_cost / old_cost
        number(ratio, 'cost ratio', positive=True)
        item['costs'].append(ratio)
    # Sort IDs so merely reordering submitted runs does not change bootstrap samples.
    grouped = {suite: [statistics.mean(families[k]['deltas']) for k in sorted(families)
                       if families[k]['suite'] == suite] for suite in ('target', 'regression')}
    target, regression = grouped['target'], grouped['regression']
    ci = interval(target) if target else None
    worst_regression = min(regression) if regression else None
    worst_cost = max(statistics.mean(v['costs']) for v in families.values())
    reasons = []
    failed = sorted(k for k, v in checks.items() if v == 'fail')
    unknown = sorted(k for k, v in checks.items() if v == 'unknown')
    decision = 'eligible_for_trial'
    if failed:
        reasons.append('Mandatory failures: ' + ', '.join(failed))
        decision = 'reject'
    if worst_regression is not None and worst_regression < -policy['max_regression']:
        reasons.append('A regression family exceeds the allowed quality loss')
        decision = 'reject'
    if worst_cost > policy['max_cost_ratio']:
        reasons.append('A family exceeds the allowed mean cost ratio')
        decision = 'reject'
    if unknown:
        reasons.append('Unknown mandatory checks: ' + ', '.join(unknown))
        if decision != 'reject':
            decision = 'inconclusive'
    if len(target) < count or len(regression) < count:
        reasons.append('Insufficient independent target or regression families')
        if decision != 'reject':
            decision = 'inconclusive'
    if ci is not None and ci[1] < 0:
        reasons.append('Target outcomes support a quality regression')
        decision = 'reject'
    if ci is None or ci[0] <= policy['min_improvement']:
        reasons.append('Target improvement is not supported above the declared threshold')
        if decision != 'reject':
            decision = 'inconclusive'
    if not reasons:
        reasons.append('Offline criteria met; authorization and limited trial still required')
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return {'evaluator_version': '1.0.0', 'candidate_id': data['candidate_id'],
            'flavour': data['flavour'], 'change_type': data['change_type'],
            'input_sha256': digest, 'policy': policy, 'checks': checks,
            'family_counts': {k: len(v) for k, v in grouped.items()},
            'mean_target_improvement': statistics.mean(target) if target else None,
            'target_interval_95': ci, 'worst_regression_delta': worst_regression,
            'worst_family_cost_ratio': worst_cost, 'decision': decision, 'reasons': reasons,
            'scope': 'Submitted records only; no agent execution, authorization or release'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = review(json.loads(args.input.read_text()))
        # Exclusive creation preserves earlier reports and avoids following existing links.
        with args.output.open('x') as output:
            json.dump(report, output, indent=2, allow_nan=False)
            output.write('\n')
    except (ValueError, OSError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 2
    print(report['decision'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
