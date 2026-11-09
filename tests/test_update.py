"""Automatic decisions over synthetic signed evidence; no live learning claim."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from control.update import advance_update
import test_release as fixtures


class UpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): fixtures.ReleaseTests.setUpClass()
    @classmethod
    def tearDownClass(cls): fixtures.ReleaseTests.tearDownClass()
    def setUp(self):
        self.f = fixtures.ReleaseTests(); self.f.setUp()
    def tearDown(self): self.f.tearDown()
    def advance(self, bundle): return advance_update(self.f.store, bundle, self.f.authority)

    def test_selects_trial_then_promotion_then_noop(self):
        self.assertEqual(self.advance(self.f.bundle())['decision'], 'trial_started')
        trial = self.f.trial_evidence(); bundle = self.f.bundle('promote', trial)
        self.assertEqual(self.advance(bundle)['decision'], 'promoted')
        self.assertEqual(self.advance(bundle)['decision'], 'already_current')
        self.assertTrue(self.f.store._selection()['behavior_verified'])
        self.f.store.verify()

    def test_without_grant_defers_without_consumption_or_selection_change(self):
        bundle = self.f.bundle(); del bundle['authorization']
        value = self.advance(bundle)
        self.assertEqual(value['decision'], 'deferred')
        self.assertEqual(value['model_attempts_started'], 0)
        self.assertFalse(value['background_task_started'])
        self.assertEqual(self.f.store.reconcile_active(), self.f.baseline)
        self.assertEqual(self.f.store.db.execute('SELECT count(*) FROM consumed_grants').fetchone()[0], 0)
        self.assertEqual(json.loads(self.f.store.read_blob(value['evidence_blob'])), bundle)

    def test_missing_or_insufficient_observations_defer(self):
        self.advance(self.f.bundle())
        self.assertEqual(self.advance(self.f.bundle())['decision'], 'deferred')
        trial = self.f.trial_evidence(); trial['observations'] = 0
        value = self.advance(self.f.bundle('promote', trial))
        self.assertEqual(value['decision'], 'deferred')
        self.assertFalse(self.f.store._selection()['behavior_verified'])

    def test_signed_failure_automatically_restores_baseline(self):
        self.advance(self.f.bundle())
        trial = self.f.trial_evidence(); trial['checks']['privacy'] = 'fail'
        result = self.advance({'trial': self.f.sign(trial)})
        self.assertEqual(result['decision'], 'rolled_back')
        self.assertEqual(self.f.store.reconcile_active(), self.f.baseline)

    def test_unknown_does_not_promote_or_trigger_false_rollback(self):
        self.advance(self.f.bundle())
        trial = self.f.trial_evidence(); trial['checks']['privacy'] = 'unknown'
        self.assertEqual(self.advance(self.f.bundle('promote', trial))['decision'], 'deferred')
        self.assertEqual(self.f.store.reconcile_active(), self.f.candidate)

    def test_forged_evidence_errors_without_changing_selection(self):
        bundle = self.f.bundle(); bundle['evaluation']['signed']['actual_skill_loading'] = False
        with self.assertRaises(ValueError): self.advance(bundle)
        self.assertEqual(self.f.store.reconcile_active(), self.f.baseline)

    def test_prepares_unprepared_candidate_automatically_after_grant_validation(self):
        import shutil
        with self.f.store.transaction():
            self.f.store.db.execute('DELETE FROM releases WHERE id=?', (self.f.candidate,))
        shutil.rmtree(self.f.store.home / 'packages' / self.f.candidate)
        self.assertEqual(self.advance(self.f.bundle())['decision'], 'trial_started')
        self.assertEqual(self.f.store.reconcile_active(), self.f.candidate)

    def test_malformed_bundle_is_rejected(self):
        for bundle in ([], {'evaluation': []}, {'evaluation': None}, {'evaluation': {'signed': []}}):
            with self.assertRaises(ValueError): self.advance(bundle)
        self.assertEqual(self.f.store.reconcile_active(), self.f.baseline)

    def test_cli_reports_malformed_evaluation_without_escaping_exception(self):
        from control import cli, release
        from contextlib import redirect_stderr
        import io
        policy = self.f.base / 'policy.json'
        policy.write_text(json.dumps(self.f.policy))
        policy.chmod(0o400)
        bundle = self.f.base / 'malformed.json'
        for evaluation in ([], None):
            with self.subTest(evaluation=evaluation):
                bundle.write_text(json.dumps({'evaluation': evaluation}))
                output = io.StringIO()
                with patch.object(release, 'HOST_POLICY', policy), redirect_stderr(output):
                    code = cli.main(['--state', str(self.f.store.home), 'advance-update', '--bundle', str(bundle)])
                self.assertEqual(code, 2)
                self.assertTrue(output.getvalue().startswith('ERROR: '))
        self.assertEqual(self.f.store.reconcile_active(), self.f.baseline)

    def test_cli_chooses_phase_without_owner_phase_selection(self):
        from control import cli
        from contextlib import redirect_stdout
        import io
        path = self.f.base / 'bundle.json'; path.write_text(json.dumps(self.f.bundle()))
        with patch.object(cli.ReleaseAuthority, 'from_host_policy', return_value=self.f.authority):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(['--state', str(self.f.store.home), 'advance-update', '--bundle', str(path)]), 0)
            self.assertEqual(json.loads(output.getvalue())['decision'], 'trial_started')
