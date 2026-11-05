"""Observable controller behavior, including real subprocess fixtures; no model-quality claim."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from control.store import Store, canonical
from control.bench import freeze_plan, run_plan, summarize, codex_events, execute, suite_check, score
from control.cli import main, html_report, render_history


def package(path, version='0'):
    path.mkdir()
    (path / 'CORE.md').write_text('Shared core')
    (path / 'OPERATING.md').write_text('Operating contract')
    (path / 'VERSION.txt').write_text(version)
    (path / 'modes').mkdir()
    (path / 'skills/daphnie').mkdir(parents=True)
    (path / 'skills/daphnie/SKILL.md').write_text('Router')
    for flavour in ('assistant', 'research', 'design', 'think'):
        skill = path / 'skills' / ('daphnie-' + flavour)
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('Use this test profile.')
        (path / 'modes' / (flavour + '.md')).write_text(flavour)
        library = path / 'libraries' / flavour
        library.mkdir(parents=True)
        (library / 'procedure.md').write_text('Procedure')
        (library / 'manifest.json').write_text(json.dumps({'flavour': flavour, 'skills': [{'path': 'procedure.md'}]}))
    return path


def suite(flavours=('assistant',), families=3):
    return {'id': 'synthetic', 'version': '1.0.0', 'partition': 'development', 'tasks': [
        {'id': f'{flavour}-{i}', 'family': f'{flavour}-family-{i}', 'flavour': flavour,
         'prompt': 'Use input.txt. Return only JSON with answer.', 'files': {'input.txt': 'fixture'},
         'checks': [{'kind': 'json_equals', 'target': '$final', 'expected': {'answer': 1}}]}
        for flavour in flavours for i in range(families)]}


class ControllerTests(unittest.TestCase):
    def test_svg_scorer_rejects_active_or_external_content(self):
        task = {'checks': [{'kind': 'svg_structure', 'target': 'output.svg', 'expected': {'width': '320'}}]}
        target = self.base / 'output.svg'
        target.write_text('<svg width="320"><text>Daphnie</text></svg>')
        self.assertEqual(score(task, '', self.base, self.store)['quality'], 1)
        for content in ('<script/>', '<foreignObject/>', '<style/>', '<image href="https://example.invalid/x"/>',
                        '<rect onclick="run()"/>', '<rect fill="url(https://example.invalid/x)"/>'):
            target.write_text('<svg width="320">' + content + '</svg>')
            self.assertEqual(score(task, '', self.base, self.store)['quality'], 0)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='daphnie-controller-')
        self.base = Path(self.temp.name)
        self.source = package(self.base / 'source')
        self.store = Store(self.base / 'state')
        self.store.register('code', self.source, 'shared', 'project')
        self.first = self.store.capture('code')['snapshot']
        self.program = self.base / 'adapter.py'
        self.program.write_text('from pathlib import Path\nimport json,sys\n'
                                'prompt=sys.stdin.read()\n'
                                'assert "expected" not in prompt\n'
                                'print(json.dumps({"answer":int(Path(".daphnie/VERSION.txt").read_text())}))\n')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def candidate(self, version='1'):
        (self.source / 'VERSION.txt').write_text(version)
        return self.store.capture('code', 'test candidate', 'operator')['snapshot']

    def plan(self, baseline=None, candidate=None, tasks=None, **options):
        return freeze_plan(self.store, baseline or self.first, candidate or self.candidate(),
                           tasks or suite(), 'command', command=[sys.executable, str(self.program)],
                           max_attempts=100, **options)

    def test_changes_include_deletions_and_reverts_without_duplicate_scan_events(self):
        second = self.candidate()
        self.assertNotEqual(self.first, second)
        (self.source / 'VERSION.txt').write_text('0')
        reverted = self.store.capture('code')
        self.assertEqual(reverted['snapshot'], self.first)
        self.assertTrue(self.store.capture('code')['unchanged'])
        (self.source / 'VERSION.txt').unlink()
        deleted = self.store.capture('code')
        self.assertEqual(deleted['changed'][0]['after'], None)
        self.assertEqual(self.store.verify()['status'], 'consistent')

    def test_snapshots_preserve_contained_links_and_reject_external_links(self):
        (self.source / 'core-link.md').symlink_to('CORE.md')
        sid = self.store.capture('code')['snapshot']
        dest = self.store.materialize(sid, self.base / 'copy')
        self.assertTrue((dest / 'core-link.md').is_symlink())
        self.assertEqual((dest / 'core-link.md').read_text(), 'Shared core')
        (self.source / 'outside').symlink_to('../')
        with self.assertRaises(ValueError):
            self.store.capture('code')

    def test_secret_paths_are_excluded_and_reported(self):
        (self.source / '.env').write_text('never snapshot this')
        capture = self.store.capture('code')
        manifest = self.store.snapshot(capture['snapshot'])
        self.assertIn('.env', manifest['excluded'])
        self.assertNotIn('.env', [e['path'] for e in manifest['entries']])

    def test_state_and_root_cannot_overlap(self):
        with self.assertRaises(ValueError):
            self.store.register('bad', self.base, 'shared', 'project', 'memory')
        with self.assertRaises(ValueError):
            Store(Path.home())

    def test_transaction_rolls_back_event_on_failure(self):
        before = self.store.verify()['events']
        with self.assertRaises(RuntimeError):
            with self.store.transaction():
                self.store.event('uncommitted', {'x': 1})
                raise RuntimeError('injected failure')
        self.assertEqual(self.store.verify()['events'], before)

    def test_process_crash_does_not_commit_partial_event(self):
        before = self.store.verify()['events']
        code = ('import os,signal,sys;from control.store import Store;'
                's=Store(sys.argv[1]);s.db.execute("BEGIN IMMEDIATE");'
                's.event("crash",{});os.kill(os.getpid(),signal.SIGKILL)')
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1] / 'scripts'), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, '-c', code, str(self.store.home)], env=env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.store.verify()['events'], before)

    def test_chain_and_snapshot_corruption_detected(self):
        self.store.db.execute("UPDATE events SET data='{}' WHERE seq=1")
        self.store.db.commit()
        with self.assertRaises(ValueError):
            self.store.verify()

    def test_observations_consolidate_only_in_requested_scope(self):
        self.store.observe('code', 'assistant', 'project', 'recovery', 'first observation')
        self.store.observe('code', 'assistant', 'project', 'recovery', 'contrary observation')
        self.store.observe('code', 'research', 'project', 'recovery', 'unrelated flavour')
        groups = self.store.consolidate('code', 'assistant', 'project')
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]['evidence']), 2)
        self.assertEqual(groups[0]['status'], 'proposed')
        count = self.store.verify()['events']
        self.assertEqual(groups, self.store.consolidate('code', 'assistant', 'project'))
        self.assertEqual(count, self.store.verify()['events'])
        with self.assertRaises(ValueError):
            self.store.consolidate('code', 'assistant', 'other-project')

    def test_evidence_backed_candidate_is_separate_and_stays_inactive(self):
        self.store.observe('code', 'assistant', 'project', 'recovery', 'A failed task requires a narrower procedure')
        bundle = self.store.consolidate('code', 'assistant', 'project')[0]['id']
        candidate = self.store.create_candidate(self.first, self.base / 'candidate', 'assistant', 'Evidence-linked proposal', bundle)
        self.assertFalse(candidate['active'])
        (self.base / 'candidate/VERSION.txt').write_text('1')
        changed = self.store.capture(candidate['root'])
        self.assertNotEqual(changed['snapshot'], self.first)
        self.assertEqual((self.source / 'VERSION.txt').read_text(), '0')
        self.assertFalse((self.store.home / 'current').exists())
        with self.assertRaises(ValueError):
            self.store.create_candidate(self.first, self.base / 'other-candidate', 'research', 'Wrong scope', bundle)

    def test_obvious_credentials_refused_before_persistence(self):
        secret = 'sk-' + 'a' * 32
        with self.assertRaises(ValueError):
            self.store.observe('code', 'assistant', 'project', 'topic', secret)
        (self.source / 'accidental.txt').write_text(secret)
        with self.assertRaises(ValueError):
            self.store.capture('code')

    def test_release_installation_uses_stable_pointer_without_replacing_unknown_entries(self):
        # Include the router expected by the existing five-skill installer.
        router = self.source / 'skills/daphnie'
        router.mkdir(exist_ok=True)
        (router / 'SKILL.md').write_text('Router')
        sid = self.store.capture('code')['snapshot']
        rid = self.store.prepare_release(sid)['release']
        self.store.activate(rid, rid, 'Manual install fixture')
        installer = str(Path(__file__).parents[1] / 'scripts/install.py')
        destination = self.base / 'installed'
        args = [sys.executable, installer, '--destination', str(destination), '--release-state', str(self.store.home)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('/current/', os.readlink(destination / 'daphnie-assistant'))
        rid2 = self.store.prepare_release(self.candidate())['release']
        self.store.activate(rid2, rid2, 'Second manual fixture')
        self.assertEqual((destination / 'daphnie-assistant/SKILL.md').read_text(), 'Use this test profile.')
        self.assertEqual((destination / 'daphnie-assistant').resolve().parents[1], self.store.home / 'packages' / rid2)
        (destination / 'daphnie').unlink()
        (destination / 'daphnie').mkdir()
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)

    def test_manual_release_switch_rollback_and_pointer_recovery(self):
        one = self.store.prepare_release(self.first)['release']
        two = self.store.prepare_release(self.candidate())['release']
        with self.assertRaises(ValueError):
            self.store.activate(one, 'yes', 'not exact')
        with self.assertRaises(ValueError):
            self.store.activate(two, two, 'never active rollback', rollback=True)
        self.store.activate(one, one, 'explicit bootstrap')
        self.store.activate(two, two, 'explicit operator adoption')
        self.assertEqual((self.store.home / 'current/VERSION.txt').read_text(), '1')
        self.store.activate(one, one, 'restore prior package', rollback=True)
        self.assertEqual((self.store.home / 'current/VERSION.txt').read_text(), '0')
        (self.store.home / 'current').unlink()
        self.store.reconcile_active()
        self.assertEqual((self.store.home / 'current/VERSION.txt').read_text(), '0')

    def test_changed_release_cannot_activate(self):
        rid = self.store.prepare_release(self.first)['release']
        (self.store.home / 'packages' / rid / 'extra.txt').write_text('tampering')
        with self.assertRaises(ValueError):
            self.store.activate(rid, rid, 'should fail')

    def test_incomplete_package_cannot_be_prepared_for_release(self):
        (self.source / 'skills/daphnie-research/SKILL.md').unlink()
        sid = self.store.capture('code')['snapshot']
        with self.assertRaises(ValueError):
            self.store.prepare_release(sid)

    def test_real_subprocess_pairs_measure_known_improvement_but_block_release(self):
        report = run_plan(self.store, self.plan()['id'])
        self.assertTrue(report['complete'])
        self.assertEqual(report['flavours']['assistant']['mean_quality_delta'], 1)
        self.assertEqual(report['flavours']['assistant']['outcome'], 'improvement_observed')
        self.assertEqual(report['release_eligibility'], 'blocked')
        self.assertEqual(report['recorded_attempts'], 6)
        self.assertEqual(self.store.verify()['status'], 'consistent')

    def test_noop_and_harmful_changes_are_not_improvements(self):
        good = self.candidate()
        noop = run_plan(self.store, self.plan(good, good)['id'])
        self.assertEqual(noop['flavours']['assistant']['outcome'], 'equivalent_within_declared_margin')
        harm = run_plan(self.store, self.plan(good, self.first)['id'])
        self.assertEqual(harm['flavours']['assistant']['outcome'], 'regressed')

    def test_reports_are_per_flavour_and_runs_cannot_be_replayed_or_overwritten(self):
        plan = self.plan(tasks=suite(('assistant', 'research', 'design', 'think')))
        report = run_plan(self.store, plan['id'])
        self.assertEqual(set(report['flavours']), {'assistant', 'research', 'design', 'think'})
        with self.assertRaises(ValueError):
            run_plan(self.store, plan['id'])
        with self.assertRaises(ValueError):
            summarize(self.store, plan['id'])

    def test_frozen_plan_projection_tampering_is_detected(self):
        plan = self.plan()
        plan['min_improvement'] = 0
        self.store.db.execute('UPDATE plans SET data=? WHERE id=?', (canonical(plan), plan['id']))
        self.store.db.commit()
        with self.assertRaises(ValueError):
            run_plan(self.store, plan['id'])

    def test_changed_scorer_requires_new_plan(self):
        from unittest.mock import patch
        plan = self.plan()
        with patch('control.bench.SCORER_VERSION', 'changed'):
            with self.assertRaises(ValueError):
                run_plan(self.store, plan['id'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 0)

    def test_compare_command_reads_existing_report_without_replacing_it(self):
        plan = self.plan()
        report = run_plan(self.store, plan['id'])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['--state', str(self.store.home), 'compare', plan['id']]), 0)
        self.assertEqual(json.loads(output.getvalue())['id'], report['id'])

    def test_scored_artifact_corruption_is_detected(self):
        run_plan(self.store, self.plan()['id'])
        record = json.loads(self.store.db.execute('SELECT data FROM attempts LIMIT 1').fetchone()[0])
        checksum = next(iter(record['score']['artifacts'].values()))
        path = self.store.home / 'blobs' / checksum
        path.chmod(0o600)
        path.write_text('corrupt')
        with self.assertRaises(ValueError):
            self.store.verify()

    def test_failed_process_is_recorded_and_not_scored_as_success(self):
        self.program.write_text('raise SystemExit(3)')
        report = run_plan(self.store, self.plan()['id'])
        self.assertFalse(report['complete'])
        self.assertEqual(report['flavours']['assistant']['outcome'], 'inconclusive')
        self.assertEqual(report['flavours']['assistant']['failures_or_incomplete'], 6)

    def test_timeout_kills_adapter_and_keeps_failure(self):
        result = execute([sys.executable, '-c', 'import time;time.sleep(10)'], '', self.base, 0.1)
        self.assertEqual(result['status'], 'timeout')
        self.assertLess(result['seconds'], 3)

    def test_output_limit_is_enforced(self):
        result = execute([sys.executable, '-c', 'print("x"*100000)'], '', self.base, 5, output_limit=1024)
        self.assertEqual(result['status'], 'output_limit')

    def test_configuration_changes_by_adapter_invalidate_attempts(self):
        self.program.write_text('from pathlib import Path\nPath(".daphnie/CORE.md").write_text("edited")\nprint("{}")')
        report = run_plan(self.store, self.plan()['id'])
        self.assertFalse(report['complete'])
        rows = [json.loads(r[0]) for r in self.store.db.execute('SELECT data FROM attempts')]
        self.assertTrue(all(r['status'] == 'configuration_drift' for r in rows))

    def test_inadequate_sample_stays_inconclusive(self):
        report = run_plan(self.store, self.plan(tasks=suite(families=1))['id'])
        self.assertEqual(report['flavours']['assistant']['outcome'], 'inconclusive')

    def test_synthetic_boundary_failure_is_not_averaged_away(self):
        tasks = suite()
        tasks['tasks'][0]['forbidden'] = ['answer']
        report = run_plan(self.store, self.plan(tasks=tasks)['id'])
        self.assertEqual(report['flavours']['assistant']['outcome'], 'regressed')

    def test_acceptance_and_path_traversal_rejected_before_execution(self):
        for mutate in (lambda s: s.update(partition='acceptance'),
                       lambda s: s['tasks'][0]['files'].update({'../answer': 'bad'}),
                       lambda s: s['tasks'][0]['checks'][0].update(target='../outside')):
            tasks = suite()
            mutate(tasks)
            with self.assertRaises(ValueError):
                suite_check(tasks)
        with self.assertRaises(ValueError):
            freeze_plan(self.store, self.first, self.first, suite(), 'command',
                        command=[sys.executable], max_attempts=2)

    def test_model_event_parser_excludes_reasoning_and_raw_command_output(self):
        raw = '\n'.join(json.dumps(e) for e in [
            {'type': 'item.completed', 'item': {'type': 'reasoning', 'text': 'private reasoning'}},
            {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'cat key', 'aggregated_output': 'secret'}},
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{"answer":1}'}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 5}},
        ])
        parsed = codex_events(raw)
        self.assertEqual(parsed['final'], '{"answer":1}')
        self.assertEqual(parsed['usage']['input_tokens'], 10)
        self.assertNotIn('private reasoning', canonical(parsed))
        self.assertNotIn('secret', canonical(parsed))

    def test_partial_attempt_recovery_never_replays_external_actions(self):
        plan = self.plan()
        record = {'id': 'partial', 'plan': plan['id'], 'status': 'started', 'flavour': 'assistant',
                  'family': 'partial', 'arm': 'baseline'}
        with self.store.transaction():
            self.store.db.execute('INSERT INTO attempts VALUES (?,?,?)', ('partial', plan['id'], canonical(record)))
            self.store.event('attempt_started', record)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(['--state', str(self.store.home), 'recover'])
        self.assertEqual(status, 0)
        self.assertFalse(json.loads(output.getvalue())['rerun_external_actions'])
        report = summarize(self.store, plan['id'])
        self.assertFalse(report['complete'])

    def test_html_evidence_is_escaped(self):
        self.store.observe('code', 'assistant', 'project', 'topic', '<script>alert(1)</script>')
        data = render_history(self.store)
        data['events'].append({'kind': '<script>bad</script>', 'at': 0, 'data': {}})
        rendered = html_report(data)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_git_import_has_exact_revision_without_checkout_changes(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.source), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git('init', '-b', 'main')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        git('add', '.')
        git('commit', '-m', 'baseline')
        revision = git('rev-parse', 'HEAD')
        (self.source / 'VERSION.txt').write_text('uncommitted')
        imported = self.store.import_revision('code', revision)
        dest = self.store.materialize(imported['snapshot'], self.base / 'imported')
        self.assertEqual((dest / 'VERSION.txt').read_text(), '0')
        self.assertEqual((self.source / 'VERSION.txt').read_text(), 'uncommitted')
        self.assertFalse(imported['activated'])

    def test_fetch_does_not_checkout_or_activate_remote_update(self):
        def git(directory, *args):
            return subprocess.run(['git', '-C', str(directory), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git(self.source, 'init', '-b', 'main')
        git(self.source, 'config', 'user.name', 'Test')
        git(self.source, 'config', 'user.email', 'test@example.invalid')
        git(self.source, 'add', '.')
        git(self.source, 'commit', '-m', 'base')
        remote = self.base / 'remote.git'
        subprocess.run(['git', 'clone', '--bare', str(self.source), str(remote)], check=True, capture_output=True)
        git(self.source, 'remote', 'add', 'origin', str(remote))
        writer = self.base / 'writer'
        subprocess.run(['git', 'clone', str(remote), str(writer)], check=True, capture_output=True)
        git(writer, 'config', 'user.name', 'Test')
        git(writer, 'config', 'user.email', 'test@example.invalid')
        (writer / 'VERSION.txt').write_text('remote-change')
        git(writer, 'add', '.')
        git(writer, 'commit', '-m', 'remote change')
        git(writer, 'push', 'origin', 'main')
        fetched = self.store.fetch('code')
        self.assertEqual(fetched['revision'], git(writer, 'rev-parse', 'HEAD'))
        self.assertEqual((self.source / 'VERSION.txt').read_text(), '0')
        self.assertFalse(fetched['activated'])


if __name__ == '__main__':
    unittest.main()
