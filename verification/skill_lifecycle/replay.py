"""Replay lifecycle model witnesses against the real Store in disposable state."""
import ast
import hashlib
import inspect
from pathlib import Path
import sys
import tempfile
import textwrap
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from control import store as implementation
from control.store import Store


def package(path):
    path.mkdir()
    (path / 'CORE.md').write_text('Synthetic core; never installed')
    (path / 'OPERATING.md').write_text('Synthetic operating contract')
    (path / 'skills/daphnie').mkdir(parents=True)
    (path / 'skills/daphnie/SKILL.md').write_text('Synthetic router')
    (path / 'modes').mkdir()
    for flavour in ('assistant', 'research', 'design', 'think'):
        (path / 'modes' / (flavour + '.md')).write_text(flavour)
        skill = path / 'skills' / ('daphnie-' + flavour)
        skill.mkdir(parents=True); (skill / 'SKILL.md').write_text('Synthetic profile')
        library = path / 'libraries' / flavour
        library.mkdir(parents=True); (library / 'procedure.md').write_text('Synthetic procedure')
        import json
        (library / 'manifest.json').write_text(json.dumps({'flavour': flavour, 'skills': [{'path': 'procedure.md'}]}))


def mutant(mode):
    tree = ast.parse(textwrap.dedent(inspect.getsource(Store._activate)))
    changed = []

    class Mutate(ast.NodeTransformer):
        def visit_If(self, node):
            expression = ast.unparse(node.test)
            if (mode == 'skip_confirmation' and 'confirmation != rid' in expression) or (
                    mode == 'skip_rollback_history' and expression.startswith('rollback and')):
                node.test = ast.Constant(False); changed.append(expression)
            return self.generic_visit(node)

        def visit_Dict(self, node):
            if mode == 'mark_verified':
                for index, key in enumerate(node.keys):
                    if isinstance(key, ast.Constant) and key.value == 'behavior_verified':
                        node.values[index] = ast.Constant(True); changed.append('behavior_verified')
            return self.generic_visit(node)

    tree = ast.fix_missing_locations(Mutate().visit(tree))
    if not changed:
        raise ValueError('Mutation no longer matches implementation; review model coverage')
    namespace = dict(implementation.__dict__)
    exec(compile(tree, '<isolated-lifecycle-mutant>', 'exec'), namespace)
    return namespace['_activate']


def replay():
    results = {}
    with tempfile.TemporaryDirectory(prefix='daphnie-formal-replay-') as td:
        base = Path(td).resolve()
        source = base / 'source'; package(source)
        store = Store(base / 'state')
        try:
            store.register('package', source, 'shared', 'formal-replay')
            first = store.capture('package')['snapshot']
            old = store.prepare_release(first)['release']
            try: store.activate(old, 'wrong', 'Must reject')
            except ValueError: results['wrong_confirmation_rejected'] = True
            else: results['wrong_confirmation_rejected'] = False
            try: store.activate(old, old, 'Never active', rollback=True)
            except ValueError: results['never_active_rollback_rejected'] = True
            else: results['never_active_rollback_rejected'] = False
            results['manual_adoption_reachable'] = store.activate(old, old, 'Temporary test adoption')['active'] == old
            (source / 'CORE.md').write_text('Different synthetic package')
            second = store.capture('package')['snapshot']
            new = store.prepare_release(second)['release']
            # Interruption after the pointer commit, before audit projection finalization.
            finishing = store._finish_activation
            failed = [False]
            def fail_history(receipt):
                if receipt['release'] == new and not failed[0]:
                    failed[0] = True
                    raise OSError('Injected post-publication history interruption')
                return finishing(receipt)
            with patch.object(store, '_finish_activation', side_effect=fail_history):
                result = store.activate(new, new, 'Injected post-publication interruption')
            row = store.db.execute('SELECT release FROM active WHERE slot=1').fetchone()[0]
            selected = store._selection()
            store.reconcile_active()
            results['postpublication_history_recovered'] = (
                result['state'] == 'applied_pending_history_recovery' and row == old
                and selected['release'] == new
                and store.db.execute('SELECT release FROM active WHERE slot=1').fetchone()[0] == new)
            results['rollback_reachable'] = store.activate(old, old, 'Temporary rollback', rollback=True)['active'] == old

            # Repeat the original race: prepared cache changes after its successful precheck.
            checked = store.validate_package
            path = store.home / 'packages' / new / 'CORE.md'
            original = path.read_bytes()
            changed = [False]
            def write_after_validation(sid, destination):
                checked(sid, destination)
                if sid == new and Path(destination) == store.home / 'packages' / new and not changed[0]:
                    changed[0] = True
                    path.write_text('External write after precheck')
            with patch.object(store, 'validate_package', side_effect=write_after_validation):
                outcome = store.activate(new, new, 'Integrity race regression')
            results['prepared_write_cannot_corrupt_deployment'] = (
                changed[0] and outcome['state'] == 'applied'
                and (store.home / 'current/CORE.md').read_bytes() == original
                and store._selection()['release'] == new)
            path.write_bytes(original)

            with patch.object(Store, '_activate', mutant('skip_confirmation')):
                result = store.activate(new, 'wrong', 'Broken confirmation guard')
                results['confirmation_mutant_detected'] = result['active'] == new
            # A fresh prepared release has no activation history.
            (source / 'CORE.md').write_text('Third synthetic package')
            third = store.prepare_release(store.capture('package')['snapshot'])['release']
            with patch.object(Store, '_activate', mutant('skip_rollback_history')):
                results['rollback_mutant_detected'] = store.activate(third, third, 'Broken history guard', rollback=True)['active'] == third
            with patch.object(Store, '_activate', mutant('mark_verified')):
                results['verification_label_mutant_detected'] = store.activate(new, new, 'Broken label')['behavior_verified'] is True
            results['original_function_restored'] = store.activate(new, new, 'Original unverified adoption')['behavior_verified'] is False
            results['ledger_consistent_after_drill'] = store.verify()['status'] == 'consistent'
            results.update(replay_signed_release())
            return results
        finally:
            store.close()


def replay_signed_release():
    # Use independent disposable signer fixtures, never real approval credentials or acceptance data.
    sys.path.insert(0, str(ROOT / 'tests'))
    from test_release import ReleaseTests
    ReleaseTests.setUpClass()
    try:
        for name in ('test_signed_trial_then_verified_release_without_changing_core_or_other_flavours',
                     'test_tampered_or_forged_grants_cannot_apply',
                     'test_promotion_requires_matching_successful_monitored_trial'):
            case = ReleaseTests(name)
            case.setUp()
            try: getattr(case, name)()
            finally: case.tearDown()
        return {'signed_trial_and_verified_release_reachable': True,
                'forged_authorization_rejected': True, 'incomplete_trial_promotion_rejected': True}
    finally:
        ReleaseTests.tearDownClass()


if __name__ == '__main__':
    import json
    value = replay()
    print(json.dumps(value, indent=2))
    raise SystemExit(0 if all(value.values()) else 1)
