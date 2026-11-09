#!/usr/bin/env python3
"""Run pinned TLC checks and concrete lifecycle replays. Exit 1 means findings, 2 means tool/source error."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from replay import replay

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JAR_SHA256 = '936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88'
SOURCES = {
    'scripts/control/store.py': ['Store.transaction', 'Store.prepare_release', 'Store.validate_package', 'Store.release_lock', 'Store._create_deployment', 'Store._selection', 'Store._switch_pointer', 'Store._finish_activation', 'Store._activate', 'Store.activate', 'Store.reconcile_active'],
    'scripts/control/release.py': ['ReleaseAuthority.__init__', 'ReleaseAuthority.from_host_policy', 'ReleaseAuthority._fresh_policy', 'ReleaseAuthority.envelope', 'ReleaseAuthority.evaluation', 'ReleaseAuthority.grant', 'ReleaseAuthority.trial_identity', 'ReleaseAuthority.trial', 'apply_release', 'stop_trial'],
    'scripts/control/bench.py': ['summarize'],
    'scripts/evaluate.py': ['review'],
    'scripts/control/cli.py': ['parser', 'main'],
    'scripts/control/update.py': ['advance_update'],
}
CHECKS = {
    'safety': ('invariant_holds', 'Six modeled safety invariants'),
    'content-race': ('invariant_holds', 'Prepared-cache changes cannot alter the fresh sealed snapshot published as active'),
    'manual-progress': ('counterexample', 'Manual unverified adoption is reachable'),
    'rollback-progress': ('counterexample', 'Rollback to a previously active release is reachable'),
    'recovery-progress': ('counterexample', 'Pointer reconciliation is reachable'),
    'verified-progress': ('counterexample', 'Signed eligible evaluation, policy grant and monitored trial can reach a verified release'),
    'mutant-confirmation': ('counterexample', 'Removed confirmation guard is detected'),
    'mutant-rollback': ('counterexample', 'Removed rollback-history guard is detected'),
    'mutant-label': ('counterexample', 'False verification label is detected'),
}


def source_fingerprints():
    pins = {}
    for filename, names in SOURCES.items():
        text = (ROOT / filename).read_text()
        pins[filename + ':<module>'] = hashlib.sha256(text.encode()).hexdigest()
        tree = ast.parse(text)
        for name in names:
            parts = name.split('.')
            nodes = tree.body
            for part in parts:
                node = next(n for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part)
                nodes = node.body
            segment = ast.get_source_segment(text, node)
            pins[filename + ':' + name] = hashlib.sha256(segment.encode()).hexdigest()
    return pins


def check_sources():
    record = json.loads((HERE / 'coverage.json').read_text())
    actual = source_fingerprints()
    if record['functions'] != actual:
        changed = sorted(k for k in set(record['functions']) | set(actual) if record['functions'].get(k) != actual.get(k))
        raise ValueError('Covered implementation changed; review transitions before repinning: ' + ', '.join(changed))
    return actual


def run(jar, output):
    pins = check_sources()
    jar = Path(jar).resolve(strict=True)
    if hashlib.sha256(jar.read_bytes()).hexdigest() != JAR_SHA256:
        raise ValueError('TLC binary checksum mismatch')
    if not shutil.which('java'):
        raise ValueError('Java runtime unavailable')
    output = Path(output).resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('checker outputs require a new private directory outside the repository')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    evidence = {'tool': 'TLC 2.19 / TLA+ tools release v1.7.4', 'workers': 1,
                'java': subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=10).stderr.strip(),
                'jar_sha256': JAR_SHA256, 'functions': pins,
                'model_sha256': hashlib.sha256((HERE / 'SkillLifecycle.tla').read_bytes()).hexdigest(),
                'bounds': 'One baseline, one candidate; finite symbolic content validity, consent, reports, pointer and transaction stages',
                'checks': {}, 'replays': {}, 'findings': [],
                'limits': ['Model-level exhaustive checking, not an unbounded implementation proof',
                           'No OS identity/access proof, arbitrary SQL corruption, hash-collision proof, actual skill loading or task-quality evidence',
                           'Reachability witnesses are not unconditional eventual-progress guarantees; no fairness/liveness property claimed',
                           'External writes to mutable prepared packages remain allowed. Fresh private sealed deployment copies are not writable by ordinary actors; same-account chmod/receipt or database attacks are outside this bound',
                           'Signature validity, protected policy and honest independent review are abstract assumptions, separately exercised with synthetic signer fixtures']}
    for name, (expected, meaning) in CHECKS.items():
        command = ['java', '-Xmx512m', '-XX:+UseParallelGC', '-cp', str(jar), 'tlc2.TLC',
                   '-workers', '1', '-metadir', str(output / ('states-' + name)),
                   str(HERE / 'SkillLifecycle.tla'), '-config', str(HERE / (name + '.cfg'))]
        result = subprocess.run(command, capture_output=True, text=True, timeout=45, cwd=output)
        log = result.stdout + result.stderr
        path = output / (name + '.log'); path.write_text(log); path.chmod(0o600)
        if result.returncode == 0 and 'Model checking completed. No error has been found.' in log:
            status = 'invariant_holds'
        elif result.returncode == 12 and re.search(r'Error: Invariant \w+ is violated', log):
            status = 'counterexample'
        else:
            raise ValueError('TLC did not complete a valid result for ' + name + '; inspect ' + str(path))
        counts = re.search(r'([\d,]+) states generated, ([\d,]+) distinct states found', log)
        trace = re.findall(r'State \d+: <([A-Za-z]\w*) (?:line|predicate)', log)
        evidence['checks'][name] = {'status': status, 'meaning': meaning, 'expected_result_matched': status == expected,
                                   'generated_states': int(counts[1].replace(',', '')) if counts else None,
                                   'distinct_states': int(counts[2].replace(',', '')) if counts else None,
                                   'shortest_action_path': trace,
                                   'config_sha256': hashlib.sha256((HERE / (name + '.cfg')).read_bytes()).hexdigest()}
        print(name + ': ' + status, flush=True)
    evidence['replays'] = replay()
    if evidence['checks']['content-race']['status'] == 'counterexample':
        evidence['findings'].append({
            'id': 'F001', 'status': 'reproduced' if not evidence['replays']['prepared_write_cannot_corrupt_deployment'] else 'model_only',
            'finding': 'Package modification after precheck can commit active DB state before reconciliation rejects it; pointer may retain the prior release.',
            'assumption': 'An external writer can change managed package bytes during activation. The operator lock does not prevent direct file writes.'})
    if evidence['checks']['verified-progress']['status'] == 'invariant_holds':
        evidence['findings'].append({
            'id': 'F002', 'status': 'missing_capability',
            'finding': 'No verified learned-release transition exists. Offline eligibility does not authorize activation; manual adoption stays unverified.'})
    evidence['harness_checks_passed'] = all(v['expected_result_matched'] for v in evidence['checks'].values()) and all(evidence['replays'].values())
    evidence['verification_clean'] = evidence['harness_checks_passed'] and not evidence['findings']
    (output / 'report.json').write_text(json.dumps(evidence, indent=2) + '\n')
    (output / 'report.json').chmod(0o600)
    print(json.dumps({'report': str(output / 'report.json'), 'harness_checks_passed': evidence['harness_checks_passed'],
                      'verification_clean': evidence['verification_clean'], 'findings': evidence['findings']}, indent=2))
    return 0 if evidence['verification_clean'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        raise SystemExit(run(args.jar, args.output))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
