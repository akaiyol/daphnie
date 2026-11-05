"""Synthetic gate calibration; not evidence of Daphnie's behavioral effectiveness."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('evaluate', Path(__file__).parents[1] / 'scripts/evaluate.py')
evaluate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate)


def fixture():
    return {'candidate_id': 'synthetic', 'flavour': 'research', 'change_type': 'skill',
            'policy': {'min_families': 3, 'min_improvement': 0.05,
                       'max_regression': 0.02, 'max_cost_ratio': 1.2},
            'checks': {k: 'pass' for k in evaluate.CHECKS},
            'runs': [{'family': f'{suite}-{i}', 'suite': suite, 'split': 'acceptance',
                      'baseline': 0.5, 'candidate': 0.7 if suite == 'target' else 0.5,
                      'baseline_cost': 1, 'candidate_cost': 1}
                     for suite in ('target', 'regression') for i in range(3)]}


class EvaluationTests(unittest.TestCase):
    def test_supported_gain_is_only_trial_eligible(self):
        self.assertEqual(evaluate.review(fixture())['decision'], 'eligible_for_trial')

    def test_critical_failure_overrides_gain(self):
        for check in evaluate.CHECKS:
            data = fixture()
            data['checks'][check] = 'fail'
            self.assertEqual(evaluate.review(data)['decision'], 'reject')

    def test_unknown_blocks_eligibility(self):
        data = fixture()
        data['checks']['privacy'] = 'unknown'
        self.assertEqual(evaluate.review(data)['decision'], 'inconclusive')

    def test_cosmetic_change_is_inconclusive(self):
        data = fixture()
        for run in data['runs']:
            run['candidate'] = run['baseline']
        self.assertEqual(evaluate.review(data)['decision'], 'inconclusive')

    def test_regression_not_hidden_by_target_gain(self):
        data = fixture()
        data['runs'][-1]['candidate'] = 0.2
        self.assertEqual(evaluate.review(data)['decision'], 'reject')

    def test_consistent_target_harm_is_rejected(self):
        data = fixture()
        for run in data['runs'][:3]:
            run['candidate'] = 0.1
        self.assertEqual(evaluate.review(data)['decision'], 'reject')

    def test_cost_failure(self):
        data = fixture()
        data['runs'][0]['candidate_cost'] = 2
        self.assertEqual(evaluate.review(data)['decision'], 'reject')

    def test_repeats_do_not_count_as_families(self):
        data = fixture()
        data['runs'] = [copy.deepcopy(data['runs'][0]) for _ in range(100)] + data['runs'][3:]
        report = evaluate.review(data)
        self.assertEqual(report['family_counts']['target'], 1)
        self.assertEqual(report['decision'], 'inconclusive')

    def test_heterogeneous_gain_needs_uncertainty_check(self):
        data = fixture()
        for run, score in zip(data['runs'], [0, 0.5, 1]):
            run['candidate'] = score
        self.assertEqual(evaluate.review(data)['decision'], 'inconclusive')

    def test_input_order_does_not_change_metrics(self):
        data = fixture()
        old = evaluate.review(data)
        data['runs'].reverse()
        new = evaluate.review(data)
        for key in ('decision', 'target_interval_95', 'mean_target_improvement'):
            self.assertEqual(old[key], new[key])

    def test_malformed_records_fail_closed(self):
        mutations = [lambda d: d['checks'].pop('permissions'),
                     lambda d: d['runs'][0].update(candidate=float('nan')),
                     lambda d: d['runs'][0].update(baseline_cost=0),
                     lambda d: d['runs'][0].update(candidate=True),
                     lambda d: d['runs'][0].update(split='development'),
                     lambda d: d['policy'].update(min_families=True),
                     lambda d: d.update(change_type='knowledge'),
                     lambda d: d['runs'].append(dict(d['runs'][0], suite='regression'))]
        for mutate in mutations:
            data = fixture()
            mutate(data)
            with self.assertRaises(ValueError):
                evaluate.review(data)


if __name__ == '__main__':
    unittest.main()
