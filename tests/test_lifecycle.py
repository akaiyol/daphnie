"""Whole CLI lifecycle with the real package and synthetic effects; no model calls in unit tests."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def exercise(base, adapter='command', model=None, effort=None):
    """Live callers must separately authorize eight attempts. All installations stay under base."""
    base = Path(base).resolve()
    base.mkdir(mode=0o700, parents=True, exist_ok=False)
    source, state, candidate = base / 'source', base / 'state', base / 'candidate'
    shutil.copytree(ROOT, source, symlinks=True,
                    ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache', '.DS_Store'))
    phases = []
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')

    def command(*args, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/daphnie.py'), '--state', str(state),
                                 *map(str, args)], capture_output=True, text=True, env=environment)
        if ok:
            if result.returncode:
                raise AssertionError(result.stderr)
            return json.loads(result.stdout)
        if result.returncode == 0:
            raise AssertionError('Expected rejection: ' + str(args))
        return result.stderr

    def phase(name):
        phases.append(name)
        print('Lifecycle: ' + name, flush=True)

    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], stderr=subprocess.DEVNULL,
                                       text=True).strip()

    command('init')
    command('register', 'source', source, '--flavour', 'shared', '--project', 'lifecycle')
    baseline = command('scan', 'source', '--reason', 'Synthetic lifecycle baseline')['snapshot']
    assert command('scan', 'source')['unchanged']
    phase('baseline captured; repeat scan deduplicated')

    note = base / 'observation.md'
    note.write_text('Synthetic correction: structured task edits must preserve untouched fields and order.\n')
    command('observe', 'source', '--flavour', 'assistant', '--project', 'lifecycle', '--topic', 'preservation', '--text-file', note)
    command('observe', 'source', '--flavour', 'research', '--project', 'lifecycle', '--topic', 'preservation', '--text-file', note)
    groups = command('consolidate', 'source', '--flavour', 'assistant', '--project', 'lifecycle')
    assert len(groups) == 1 and len(groups[0]['evidence']) == 1 and groups[0]['status'] == 'proposed'
    command('consolidate', 'source', '--flavour', 'assistant', '--project', 'other', ok=False)
    command('candidate', baseline, '--workspace', base / 'wrong-scope', '--flavour', 'research',
            '--reason-file', note, '--bundle', groups[0]['id'], ok=False)
    proposal = command('candidate', baseline, '--workspace', candidate, '--flavour', 'assistant',
                       '--reason-file', note, '--bundle', groups[0]['id'])
    procedure = candidate / 'libraries/assistant/task-recovery.md'
    procedure.write_text(procedure.read_text() + '\nFor structured task edits, preserve original ordering and every field not explicitly authorized to change.\n')
    manifest = candidate / 'libraries/assistant/manifest.json'
    metadata = json.loads(manifest.read_text())
    metadata['library_version'] = '1.0.1'
    metadata['skills'][0]['version'] = '1.0.1'
    manifest.write_text(json.dumps(metadata, indent=2) + '\n')
    capture = command('scan', proposal['root'], '--reason', 'Synthetic preservation procedure candidate')
    changed = capture['snapshot']
    # A candidate's first scan inventories everything: independently compare its files with baseline.
    differences = [str(p.relative_to(candidate)) for p in candidate.rglob('*') if p.is_file()
                   and not p.is_symlink() and p.read_bytes() != (source / p.relative_to(candidate)).read_bytes()]
    assert sorted(differences) == ['libraries/assistant/manifest.json', 'libraries/assistant/task-recovery.md']
    assert command('status')['active'] is None
    phase('scoped correction consolidated; separate assistant-only candidate frozen')

    options = ['--adapter', adapter, '--max-attempts', '8', '--timeout', '120']
    if adapter == 'codex':
        options += ['--model', model, '--effort', effort]
    else:
        program = base / 'fixture.py'
        program.write_text('''import json,sys
from pathlib import Path
sys.stdin.read()
if Path('items.json').exists():
    items=json.loads(Path('items.json').read_text())
    for item in items:
        if item['id']=='a': item['completed']=True
    answer={'items':items}
elif Path('sources.json').exists():
    latest=max(json.loads(Path('sources.json').read_text()),key=lambda x:x['date'])
    answer={'current_policy':latest['policy'],'source':latest['id'],'qualification':'synthetic_source_only'}
elif Path('options.json').exists():
    options=json.loads(Path('options.json').read_text())
    eligible=[x for x in options if x['cost']<=5 and x['latency']<=100]
    answer={'selected':min(eligible,key=lambda x:x['cost'])['id'], 'rejected':sorted(x['id'] for x in options if x not in eligible)}
else:
    Path('output.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180"><text x="10" y="30">Daphnie</text><text x="10" y="80">Continue</text></svg>')
    answer={'written':'output.svg'}
print(json.dumps(answer))
''')
        options += ['--command-json', json.dumps([sys.executable, str(program)])]
    plan = command('plan', '--baseline', baseline, '--candidate', changed,
                   '--suite', ROOT / 'benchmarks/development/core.json', *options)
    phase('eight-attempt development plan frozen; execution starting')
    report = command('run', plan['id'])
    assert report['recorded_attempts'] == 8
    assert report['release_eligibility'] == 'blocked'
    assert set(report['flavours']) == {'assistant', 'research', 'design', 'think'}
    assert all(result['outcome'] in ('inconclusive', 'regressed') for result in report['flavours'].values())
    assert command('compare', plan['id'])['id'] == report['id']
    command('run', plan['id'], ok=False)
    assert command('status')['active'] is None
    phase('all-flavour attempts recorded; verified promotion blocked; replay rejected')

    # Test-only operator adoption exercises mechanics, even when behavioural evidence is insufficient.
    # Both destination and stable skill links are confined to this scratch test directory.
    old = command('prepare-release', baseline)['release']
    new = command('prepare-release', changed)['release']
    command('activate', old, '--confirm-release', 'wrong', '--reason', 'Must reject', '--owner-adopt-unverified', ok=False)
    command('rollback', new, '--confirm-release', new, '--reason', 'Never active', '--owner-adopt-unverified', ok=False)
    adopted = command('activate', old, '--confirm-release', old, '--reason', 'Temporary test baseline', '--owner-adopt-unverified')
    assert adopted['behavior_verified'] is False
    install = subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), '--release-state', str(state),
                              '--destination', str(base / 'skills')], capture_output=True, text=True, env=environment)
    assert install.returncode == 0, install.stderr
    link = base / 'skills/daphnie-assistant'
    stable = os.readlink(link)
    old_hash = hashlib.sha256((link / 'references/library/task-recovery.md').read_bytes()).hexdigest()
    command('activate', new, '--confirm-release', new, '--reason', 'Temporary test candidate; not verified', '--owner-adopt-unverified')
    assert os.readlink(link) == stable
    assert hashlib.sha256((link / 'references/library/task-recovery.md').read_bytes()).hexdigest() != old_hash
    assert len(list((base / 'skills').iterdir())) == 5
    phase('temporary installation follows explicit adoption without relinking')

    command('observe', proposal['root'], '--flavour', 'assistant', '--project', 'lifecycle', '--topic', 'post-trial', '--text-file', note)
    command('rollback', old, '--confirm-release', old, '--reason', 'Temporary rollback drill', '--owner-adopt-unverified')
    assert hashlib.sha256((link / 'references/library/task-recovery.md').read_bytes()).hexdigest() == old_hash
    assert command('consolidate', proposal['root'], '--flavour', 'assistant', '--project', 'lifecycle')
    (state / 'current').unlink()
    recovered = command('recover')
    assert recovered['active'] == old and recovered['rerun_external_actions'] is False
    assert (state / 'current/CORE.md').read_bytes() == (source / 'CORE.md').read_bytes()
    assert not ((state / 'current/CORE.md').stat().st_mode & 0o222)
    phase('rollback restores prior skill bytes; observations retained; missing pointer recovered')

    git('init', '-b', 'main'); git('config', 'user.name', 'Lifecycle test')
    git('config', 'user.email', 'lifecycle@example.invalid'); git('add', '.')
    git('commit', '-m', 'Synthetic lifecycle source')
    revision = git('rev-parse', 'HEAD')
    remote = base / 'remote.git'
    subprocess.run(['git', 'clone', '--bare', str(source), str(remote)], check=True, capture_output=True)
    git('remote', 'add', 'origin', str(remote))
    assert command('fetch', 'source')['revision'] == revision
    imported = command('import-revision', 'source', revision)
    assert imported['activated'] is False and command('status')['active'] == old
    assert git('rev-parse', 'HEAD') == revision
    phase('update fetch/import leave checkout and active release unchanged')

    integrity = command('verify')
    history = command('history')
    export = command('history', '--html', base / 'history.html')
    assert (base / 'history.html').stat().st_mode & 0o777 == 0o600
    assert history['background_monitoring'] is False and history['automatic_activation'] is False
    assert history['comparisons'][0]['id'] == report['id']
    phase('ledger integrity and private report verified')
    summary = {'adapter': adapter, 'phases': phases, 'report': report, 'integrity': integrity,
               'private_report': export['private_report'], 'active_test_release': old,
               'installed_user_skills_changed': False, 'background_tasks_started': False,
               'limitations': ['No production verified learned release exercised', 'No protected acceptance', 'No host-enforced context isolation',
                               'No personality calibration', 'No compatible private-memory rollback']}
    (base / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (base / 'summary.json').chmod(0o600)
    return summary


class LifecycleTests(unittest.TestCase):
    def test_complete_cli_lifecycle_with_real_package_and_synthetic_effects(self):
        with tempfile.TemporaryDirectory(prefix='daphnie-lifecycle-test-') as root:
            summary = exercise(Path(root) / 'run')
            self.assertTrue(summary['report']['complete'])
            self.assertEqual(summary['integrity']['status'], 'consistent')
            self.assertTrue(all(value['baseline_quality'] == value['candidate_quality'] == 1
                                for value in summary['report']['flavours'].values()))


if __name__ == '__main__':
    unittest.main()
