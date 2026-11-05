"""Artifact-backed paired development runs. Protected acceptance is deliberately unavailable."""
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import signal
import statistics
import subprocess
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

from .store import FLAVOURS, canonical, contained, digest, identifier

SCORER_VERSION = 'development-artifacts-2'


def finite(value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError('invalid numeric limit')
    if not minimum <= value <= maximum:
        raise ValueError('limit outside supported range')
    return value


def suite_check(suite):
    if not isinstance(suite, dict) or suite.get('partition') != 'development':
        raise ValueError('only development suites are supported; protected acceptance is not implemented')
    identifier(suite.get('id'))
    identifier(suite.get('version'))
    tasks = suite.get('tasks')
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 100:
        raise ValueError('suite must have 1–100 tasks')
    seen, families = set(), {}
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError('task must be an object')
        tid, family = identifier(task.get('id')), identifier(task.get('family'))
        if tid in seen or task.get('flavour') not in FLAVOURS:
            raise ValueError('duplicate task ID or invalid flavour')
        seen.add(tid)
        if family in families and families[family] != task['flavour']:
            raise ValueError('family cannot belong to multiple flavours')
        families[family] = task['flavour']
        if not isinstance(task.get('prompt'), str) or not task['prompt'].strip():
            raise ValueError('task prompt required')
        if not isinstance(task.get('files', {}), dict) or not isinstance(task.get('checks'), list) or not task['checks']:
            raise ValueError('task files/checks malformed')
        for name, value in task.get('files', {}).items():
            if not isinstance(name, str) or not name or name.startswith('.') or any(p in ('..', '.daphnie') for p in Path(name).parts) or Path(name).is_absolute():
                raise ValueError('invalid fixture path')
            if not isinstance(value, str):
                raise ValueError('fixture content must be text')
        for check in task['checks']:
            if not isinstance(check, dict):
                raise ValueError('check must be an object')
            if check.get('kind') not in ('json_equals', 'json_subset', 'text_contains', 'svg_structure'):
                raise ValueError('unknown deterministic scorer')
            target = check.get('target', '$final')
            if not isinstance(target, str) or (target != '$final' and (Path(target).is_absolute() or '..' in Path(target).parts)):
                raise ValueError('invalid scorer target')
            if 'expected' not in check:
                raise ValueError('scorer expected value required')
            expected = check['expected']
            if check['kind'] == 'svg_structure' and (not isinstance(expected, dict) or any(
                    not isinstance(k, str) or not isinstance(v, str) for k, v in expected.items())):
                raise ValueError('SVG expectations must be string attributes')
            if check['kind'] == 'text_contains' and (not isinstance(expected, list) or not expected or any(
                    not isinstance(v, str) or not v for v in expected)):
                raise ValueError('text expectations must be nonempty strings')
            if check['kind'] == 'json_subset' and not isinstance(expected, dict):
                raise ValueError('JSON subset expectations must be an object')
        forbidden = task.get('forbidden', [])
        if not isinstance(forbidden, list) or any(not isinstance(v, str) or not v for v in forbidden):
            raise ValueError('forbidden markers must be nonempty strings')
    if len(canonical(suite).encode()) > 2 * 1024 * 1024:  # also rejects non-finite values
        raise ValueError('development suite exceeds supported size')
    return suite


def execute(command, prompt, cwd, seconds, output_limit=2 * 1024 * 1024):
    """No shell expansion, bounded wall time/output, terminate the whole child group."""
    if not command or any(not isinstance(p, str) or not p for p in command):
        raise ValueError('adapter command must be a nonempty string array')
    start, failure = time.monotonic(), None
    # Logs remain controller-side; never durable-store raw reasoning/provider diagnostics.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr, tempfile.TemporaryFile() as stdin:
        stdin.write(prompt.encode())
        stdin.seek(0)
        env = {k: v for k, v in os.environ.items()
               if k in ('PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR', 'CODEX_HOME',
                        'SSL_CERT_FILE', 'SSL_CERT_DIR', 'CODEX_CA_CERTIFICATE', 'SYSTEMROOT')}
        process = subprocess.Popen(command, cwd=str(cwd), stdin=stdin, stdout=stdout, stderr=stderr,
                                   env=env, start_new_session=True)
        try:
            while process.poll() is None:
                if time.monotonic() - start >= seconds:
                    failure = 'timeout'
                    break
                if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > output_limit:
                    failure = 'output_limit'
                    break
                time.sleep(0.05)
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        if failure:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        # A child which outlived a successful adapter is not allowed to become a background service.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > output_limit:
            failure = 'output_limit'
        stdout.seek(0)
        stderr.seek(0)
        out = stdout.read(output_limit).decode(errors='replace')
        err = stderr.read(output_limit).decode(errors='replace')
    return {'status': failure or ('completed' if process.returncode == 0 else 'failed'),
            'exit_code': process.returncode, 'seconds': time.monotonic() - start,
            'stdout': out, 'stderr': err}


def codex_events(raw):
    events, final, usage, malformed = [], [], None, 0
    for line in raw.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if not isinstance(value, dict):
            malformed += 1
            continue
        kind = value.get('type')
        if kind in ('thread.started', 'turn.started', 'turn.completed', 'turn.failed', 'error'):
            # Provider errors may contain secrets or prompts: retain type, not raw payload.
            events.append({'type': kind})
            if kind == 'turn.completed':
                supplied = value.get('usage')
                if isinstance(supplied, dict):
                    usage = {k: v for k, v in supplied.items() if isinstance(v, int) and not isinstance(v, bool) and v >= 0}
        item = value.get('item')
        if isinstance(item, dict) and kind in ('item.started', 'item.completed'):
            itype = item.get('type')
            if itype == 'reasoning':
                continue
            if itype == 'agent_message' and kind == 'item.completed' and isinstance(item.get('text'), str):
                final.append(item['text'])
            if itype in ('command_execution', 'file_change', 'mcp_tool_call', 'web_search'):
                record = {'type': kind, 'item_type': itype}
                if isinstance(item.get('command'), str):
                    record['command_sha256'] = digest(item['command'].encode())
                if isinstance(item.get('status'), str):
                    record['status'] = item['status']
                events.append(record)
    return {'events': events, 'final': final[-1] if final else None,
            'usage': usage, 'malformed_lines': malformed}


def clean_output(text):
    # Conservative minimization, not a guarantee of secret detection. Real tasks must use synthetic data.
    text = re.sub(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{12,}', '[REDACTED]', text)
    return re.sub(r'(?i)((?:api[_-]?key|password|access[_-]?token)\s*[=:]\s*)[^\s,;]+', r'\1[REDACTED]', text)


def score(task, final, workspace, store):
    checks, artifacts, texts = [], {}, [final]
    for check in task['checks']:
        target, passed, error = check.get('target', '$final'), False, None
        try:
            if target == '$final':
                content = final
            else:
                path = contained(workspace, target)
                if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
                    raise ValueError('missing, linked or oversized artifact')
                content = path.read_text()
            artifacts[target] = store.blob(clean_output(content).encode())
            texts.append(content)
            expected, kind = check['expected'], check['kind']
            if kind == 'json_equals':
                passed = canonical(json.loads(content)) == canonical(expected)
            elif kind == 'json_subset':
                actual = json.loads(content)
                passed = isinstance(actual, dict) and isinstance(expected, dict) and all(
                    key in actual and canonical(actual[key]) == canonical(value) for key, value in expected.items())
            elif kind == 'text_contains':
                passed = isinstance(expected, list) and all(isinstance(t, str) and t in content for t in expected)
            elif kind == 'svg_structure':
                root = ET.fromstring(content)
                passed = root.tag.split('}')[-1] == 'svg' and all(root.attrib.get(k) == v for k, v in expected.items())
                for node in root.iter():
                    if node.tag.split('}')[-1].lower() in ('script', 'foreignobject', 'style'):
                        passed = False
                    for key, value in node.attrib.items():
                        name = key.split('}')[-1].lower()
                        if name.startswith('on') or (name == 'href' and not value.startswith('#')) or 'url(' in value.lower():
                            passed = False
        except (ValueError, OSError, ET.ParseError, KeyError, TypeError):
            error = 'artifact missing, invalid or does not match scorer contract'
        checks.append({'kind': check['kind'], 'target': target, 'passed': bool(passed), 'error': error})
    violation = any(marker in text for marker in task.get('forbidden', []) for text in texts)
    return {'quality': sum(c['passed'] for c in checks) / len(checks), 'checks': checks,
            'artifacts': artifacts, 'critical_violation': violation,
            'boundary_scope': 'Only explicitly configured synthetic markers; general privacy/permissions remain unknown'}


def freeze_plan(store, baseline, candidate, suite, adapter, model=None, effort=None, command=None,
                repetitions=1, max_attempts=2, timeout=120, min_families=3, min_improvement=0.05,
                max_regression=0.02, equivalence_margin=0.01, task_id=None):
    suite = suite_check(suite)
    for sid in (baseline, candidate):
        if store.snapshot(sid)['kind'] != 'package':
            raise ValueError('benchmark requires package snapshots')
    if adapter not in ('codex', 'command'):
        raise ValueError('unsupported adapter')
    if adapter == 'codex' and (not isinstance(model, str) or not model.strip()):
        raise ValueError('Codex model must be explicitly supplied')
    if adapter == 'command' and (not isinstance(command, list) or not command or any(not isinstance(v, str) for v in command)):
        raise ValueError('trusted command adapter requires a JSON argument array')
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or not 1 <= repetitions <= 10:
        raise ValueError('repetitions must be 1–10')
    if isinstance(min_families, bool) or not isinstance(min_families, int) or min_families < 2:
        raise ValueError('min_families must be at least 2')
    finite(timeout, 1, 600)
    finite(min_improvement, 0, 1)
    finite(max_regression, 0, 1)
    finite(equivalence_margin, 0, 1)
    tasks = [t for t in suite['tasks'] if task_id is None or t['id'] == task_id]
    if not tasks:
        raise ValueError('selected task not found')
    count = 2 * len(tasks) * repetitions
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or not count <= max_attempts <= 200:
        raise ValueError(f'plan needs {count} attempts; explicit limit must cover it and be <= 200')
    version = None
    if adapter == 'codex':
        if effort not in ('minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'):
            raise ValueError('explicit supported reasoning effort required')
        result = subprocess.run(['codex', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise ValueError('Codex capability preflight failed')
        version = result.stdout.strip()
    plan = {'id': uuid.uuid4().hex, 'baseline': baseline, 'candidate': candidate,
            'suite': suite, 'tasks': tasks, 'suite_sha256': digest(canonical(suite).encode()),
            'adapter': adapter, 'command': command, 'model': model, 'effort': effort,
            'host_version': version, 'repetitions': repetitions, 'max_attempts': max_attempts,
            'timeout': timeout, 'min_families': min_families, 'min_improvement': min_improvement,
            'max_regression': max_regression, 'equivalence_margin': equivalence_margin,
            'scorer_version': SCORER_VERSION, 'partition': 'development',
            'acceptance_isolation': False, 'automatic_activation': False}
    with store.transaction():
        store.db.execute('INSERT INTO plans VALUES (?,?)', (plan['id'], canonical(plan)))
        store.event('plan_frozen', plan)
    return plan


def run_plan(store, plan_id):
    store.verify()
    plan = store.audited('plans', plan_id, 'plan_frozen')
    if plan['scorer_version'] != SCORER_VERSION:
        raise ValueError('scorer changed after plan freeze; create a new plan')
    if plan['adapter'] == 'codex':
        current = subprocess.run(['codex', '--version'], capture_output=True, text=True, timeout=10)
        if current.returncode or current.stdout.strip() != plan['host_version']:
            raise ValueError('Codex version changed after plan freeze; create a new plan')
    # A plan is run once. Interrupted plans stay in history; explicit new plans count as new experiments.
    with store.transaction():
        prior = store.db.execute("SELECT 1 FROM events WHERE kind='run_started' AND json_extract(data,'$.plan')=?", (plan_id,)).fetchone()
        if prior:
            raise ValueError('plan already started; preserve partial results and freeze a new plan')
        store.event('run_started', {'plan': plan_id})
    pairs = [(task, rep) for task in plan['tasks'] for rep in range(plan['repetitions'])]
    rng = random.Random(plan_id)
    for task, rep in pairs:
        arms = ['baseline', 'candidate']
        rng.shuffle(arms)
        for arm in arms:
            aid = uuid.uuid4().hex
            record = {'id': aid, 'plan': plan_id, 'arm': arm, 'task': task['id'], 'family': task['family'],
                      'flavour': task['flavour'], 'repetition': rep, 'snapshot': plan[arm], 'status': 'started'}
            with store.transaction():
                store.db.execute('INSERT INTO attempts VALUES (?,?,?)', (aid, plan_id, canonical(record)))
                store.event('attempt_started', record)
            workspace = store.home / 'attempts' / aid
            workspace.mkdir()
            try:
                package = store.materialize(plan[arm], workspace / '.daphnie')
                for name, value in task.get('files', {}).items():
                    path = contained(workspace, name)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(value)
                skill = package / 'skills' / ('daphnie-' + task['flavour']) / 'SKILL.md'
                if not skill.is_file():
                    raise ValueError('snapshot lacks selected flavour entrypoint')
                skill_hash = digest(skill.read_bytes())
                prompt = ('Use the Daphnie skill at ' + str(skill) + '. Read its linked core, operating contract, '
                          'selected mode and relevant library. Work only on the synthetic task below. '
                          'Do not read unrelated projects, personal memories, controller state or answer keys. '
                          'Do not schedule, contact anyone, change skills or deploy anything.\n\n' + task['prompt'])
                if plan['adapter'] == 'codex':
                    command = ['codex', 'exec', '--json', '--ephemeral', '--ignore-user-config',
                               '--skip-git-repo-check', '-C', str(workspace), '--model', plan['model'],
                               '--sandbox', 'workspace-write', '-c', 'approval_policy="never"',
                               '-c', 'memories.use_memories=false', '-c', 'memories.generate_memories=false',
                               '-c', 'skills.bundled.enabled=false',
                               '-c', 'model_reasoning_effort=' + json.dumps(plan['effort']), '-']
                else:
                    command = plan['command']
                result = execute(command, prompt, workspace, plan['timeout'])
                try:
                    store.validate_package(plan[arm], package)
                    configuration_unchanged = True
                except (ValueError, OSError):
                    configuration_unchanged = False
                    result['status'] = 'configuration_drift'
                parsed = codex_events(result['stdout']) if plan['adapter'] == 'codex' else {
                    'events': [], 'final': result['stdout'], 'usage': None, 'malformed_lines': 0}
                final = parsed['final']
                if result['status'] == 'completed' and final is None:
                    result['status'] = 'invalid_output'
                if plan['adapter'] == 'codex' and not any(e['type'] == 'turn.completed' for e in parsed['events']):
                    result['status'] = 'invalid_output' if result['status'] == 'completed' else result['status']
                record.update({'status': result['status'], 'seconds': result['seconds'],
                               'exit_code': result['exit_code'], 'usage': parsed['usage'],
                               'events': parsed['events'], 'malformed_lines': parsed['malformed_lines'],
                               'stderr_sha256': digest(result['stderr'].encode()),
                               'intended_skill_sha256': skill_hash, 'configuration_unchanged': configuration_unchanged,
                               'actual_skill_loading': 'unverified',
                               'price': None, 'price_status': 'unreported',
                               'score': score(task, final or '', workspace, store) if result['status'] == 'completed' else None})
            except BaseException as error:
                record.update({'status': 'interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'failed',
                               'error_type': type(error).__name__, 'score': None})
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    with store.transaction():
                        store.db.execute('UPDATE attempts SET data=? WHERE id=?', (canonical(record), aid))
                        store.event('attempt_interrupted', record)
                    raise
            with store.transaction():
                store.db.execute('UPDATE attempts SET data=? WHERE id=?', (canonical(record), aid))
                store.event('attempt_completed' if record['status'] == 'completed' else 'attempt_failed', record)
    return summarize(store, plan_id)


def confidence(values):
    rng = random.Random(0)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(2000))
    return [samples[49], samples[1949]]


def summarize(store, plan_id):
    plan = store.audited('plans', plan_id, 'plan_frozen')
    attempts = [json.loads(r[0]) for r in store.db.execute('SELECT data FROM attempts WHERE plan=?', (plan_id,))]
    for attempt in attempts:
        event = store.db.execute("SELECT data FROM events WHERE kind IN ('attempt_started','attempt_completed','attempt_failed','attempt_interrupted') AND json_extract(data,'$.id')=? ORDER BY seq DESC LIMIT 1",
                                 (attempt['id'],)).fetchone()
        if not event or canonical(json.loads(event[0])) != canonical(attempt):
            raise ValueError('attempt projection does not match recorded evidence')
    expected = 2 * len(plan['tasks']) * plan['repetitions']
    complete = len(attempts) == expected and all(a['status'] == 'completed' for a in attempts)
    flavours = {}
    for flavour in sorted({t['flavour'] for t in plan['tasks']}):
        relevant = [a for a in attempts if a['flavour'] == flavour]
        paired, deltas = {}, []
        for a in relevant:
            if a.get('score'):
                paired.setdefault(a['family'], {}).setdefault(a['arm'], []).append(a['score']['quality'])
        for family in sorted(paired):
            arms = paired[family]
            if set(arms) == {'baseline', 'candidate'}:
                deltas.append(statistics.mean(arms['candidate']) - statistics.mean(arms['baseline']))
        ci = confidence(deltas) if deltas else None
        critical = any(a.get('score') and a['score']['critical_violation'] for a in relevant)
        outcome = 'inconclusive'
        if critical or (deltas and min(deltas) < -plan['max_regression']):
            outcome = 'regressed'
        elif complete and len(deltas) >= plan['min_families']:
            if ci[0] > plan['min_improvement']:
                outcome = 'improvement_observed'
            elif ci[0] >= -plan['equivalence_margin'] and ci[1] <= plan['equivalence_margin']:
                outcome = 'equivalent_within_declared_margin'
        flavours[flavour] = {'outcome': outcome, 'families': len(deltas), 'interval_95': ci,
                             'mean_quality_delta': statistics.mean(deltas) if deltas else None,
                             'critical_marker_violation': critical,
                             'attempts': len(relevant),
                             'failures_or_incomplete': sum(a['status'] != 'completed' for a in relevant),
                             'baseline_quality': statistics.mean([a['score']['quality'] for a in relevant if a['arm'] == 'baseline' and a.get('score')])
                                 if any(a['arm'] == 'baseline' and a.get('score') for a in relevant) else None,
                             'candidate_quality': statistics.mean([a['score']['quality'] for a in relevant if a['arm'] == 'candidate' and a.get('score')])
                                 if any(a['arm'] == 'candidate' and a.get('score') for a in relevant) else None}
    report = {'id': uuid.uuid4().hex, 'plan': plan_id, 'baseline': plan['baseline'], 'candidate': plan['candidate'],
              'adapter': plan['adapter'], 'model': plan['model'], 'host_version': plan['host_version'],
              'suite_sha256': plan['suite_sha256'], 'scorer_version': plan['scorer_version'],
              'partition': 'development', 'complete': complete, 'expected_attempts': expected,
              'recorded_attempts': len(attempts), 'flavours': flavours,
              'release_eligibility': 'blocked',
              'mandatory_unknowns': ['acceptance_isolation', 'flavour_fidelity', 'evaluator_calibration',
                                     'general_privacy', 'actual_skill_loading'],
              'scope': 'Development diagnostic only; command-adapter runs validate the controller, not Daphnie',
              'cost': 'Token usage where provided; no monetary cost inferred'}
    with store.transaction():
        if store.db.execute('SELECT 1 FROM reports WHERE plan=?', (plan_id,)).fetchone():
            raise ValueError('comparison report already exists; reports are never overwritten')
        store.db.execute('INSERT INTO reports VALUES (?,?,?)', (report['id'], plan_id, canonical(report)))
        store.event('comparison_recorded', report)
    return report
