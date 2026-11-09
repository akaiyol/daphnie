"""Explicit operator CLI. No schedules, implicit scans or automatic updates."""
import argparse
import fcntl
import html
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from .store import Store, FLAVOURS, canonical
from .bench import freeze_plan, run_plan, summarize
from .release import ReleaseAuthority, apply_release, stop_trial
from .update import advance_update


def render_history(store):
    store.verify()
    rows = []
    for row in store.db.execute('SELECT kind,at,data FROM events ORDER BY seq'):
        rows.append({'kind': row['kind'], 'at': row['at'], 'data': json.loads(row['data'])})
    reports = [store.audited('reports', r[0], 'comparison_recorded') for r in store.db.execute('SELECT id FROM reports ORDER BY rowid')]
    return {'events': rows, 'comparisons': reports,
            'active': store.reconcile_active(), 'coverage': 'Registered roots and controller-run sessions only',
            'background_monitoring': False, 'automatic_activation': False}


def html_report(value):
    # Escape all evidence. This is a local private report, never a public export.
    reports = []
    for report in value['comparisons']:
        flavour_rows = ''.join('<tr><td>' + html.escape(name) + '</td><td>' + html.escape(str(item['outcome']))
                               + '</td><td>' + html.escape(str(item['mean_quality_delta'])) + '</td><td>'
                               + html.escape(str(item['families'])) + '</td></tr>'
                               for name, item in report['flavours'].items())
        reports.append('<section><h2>Comparison ' + html.escape(report['id'][:12])
                       + '</h2><p>Development only · release eligibility blocked</p><table>'
                       + '<tr><th>Flavour</th><th>Outcome</th><th>Quality change</th><th>Families</th></tr>'
                       + flavour_rows + '</table><details><summary>Complete report</summary><pre>'
                       + html.escape(json.dumps(report, indent=2)) + '</pre></details></section>')
    events = ''.join('<details><summary>' + html.escape(e['kind']) + '</summary><pre>'
                     + html.escape(json.dumps(e, indent=2)) + '</pre></details>' for e in value['events'])
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>Daphnie local history</title><style>body{font:16px system-ui;max-width:960px;margin:40px auto;padding:0 20px;'
            'line-height:1.5}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:8px;border-bottom:1px solid #aaa}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere}section{margin:36px 0}summary{padding:8px 0}</style>'
            '<h1>Daphnie local history</h1><p>Private report. Registered roots and controller-run sessions only. '
            'No background monitoring or automatic activation.</p><p>Active release: '
            + html.escape(str(value['active'])) + '</p>' + ''.join(reports) + '<h2>Change and run events</h2>'
            + events + '</html>')


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', type=Path, required=True, help='Dedicated private controller directory, outside registered roots')
    commands = p.add_subparsers(dest='action', required=True)
    commands.add_parser('init')
    r = commands.add_parser('register')
    r.add_argument('name'); r.add_argument('path', type=Path)
    r.add_argument('--flavour', choices=(*FLAVOURS, 'shared'), required=True)
    r.add_argument('--project', required=True); r.add_argument('--kind', choices=('package', 'memory'), default='package')
    scan = commands.add_parser('scan')
    scan.add_argument('root'); scan.add_argument('--reason', default='reconciliation'); scan.add_argument('--actor', default='unknown')
    fetch = commands.add_parser('fetch')
    fetch.add_argument('root'); fetch.add_argument('--branch', default='main')
    revision = commands.add_parser('import-revision')
    revision.add_argument('root'); revision.add_argument('commit')
    note = commands.add_parser('observe')
    note.add_argument('root'); note.add_argument('--flavour', choices=FLAVOURS, required=True)
    note.add_argument('--project', required=True); note.add_argument('--topic', required=True)
    note.add_argument('--text-file', type=Path, required=True, help='Authorized private note; never a credential file')
    group = commands.add_parser('consolidate')
    group.add_argument('root'); group.add_argument('--flavour', choices=FLAVOURS, required=True); group.add_argument('--project', required=True)
    candidate = commands.add_parser('candidate')
    candidate.add_argument('baseline'); candidate.add_argument('--workspace', type=Path, required=True)
    candidate.add_argument('--flavour', choices=FLAVOURS, required=True)
    candidate.add_argument('--reason-file', type=Path, required=True); candidate.add_argument('--bundle')
    plan = commands.add_parser('plan')
    plan.add_argument('--baseline', required=True); plan.add_argument('--candidate', required=True)
    plan.add_argument('--suite', type=Path, required=True); plan.add_argument('--task')
    plan.add_argument('--adapter', choices=('codex', 'command'), required=True)
    plan.add_argument('--command-json', help='Trusted test program argument array; not a shell string')
    plan.add_argument('--model'); plan.add_argument('--effort')
    plan.add_argument('--repetitions', type=int, default=1); plan.add_argument('--max-attempts', type=int, required=True)
    plan.add_argument('--timeout', type=int, default=120); plan.add_argument('--min-families', type=int, default=3)
    plan.add_argument('--min-improvement', type=float, default=0.05); plan.add_argument('--max-regression', type=float, default=0.02)
    plan.add_argument('--equivalence-margin', type=float, default=0.01)
    run = commands.add_parser('run'); run.add_argument('plan')
    report = commands.add_parser('compare'); report.add_argument('plan')
    release = commands.add_parser('prepare-release'); release.add_argument('snapshot')
    for action in ('activate', 'rollback'):
        release = commands.add_parser(action)
        release.add_argument('release'); release.add_argument('--confirm-release', required=True)
        release.add_argument('--reason', required=True)
        release.add_argument('--owner-adopt-unverified', action='store_true', required=True,
                             help='Manual owner adoption, explicitly NOT a verified learned release')
    commands.add_parser('release-status')
    for name in ('release-preview', 'start-trial', 'promote-release', 'stop-trial', 'advance-update'):
        item = commands.add_parser(name)
        item.add_argument('--bundle', type=Path, required=True, help='Signed evidence and policy-bound authorization; no private signing keys')
    commands.add_parser('verify')
    commands.add_parser('status')
    commands.add_parser('recover')
    history = commands.add_parser('history')
    history.add_argument('--html', type=Path, help='Exclusive-create a private read-only HTML report')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    store = lock = None
    try:
        store = Store(args.state)
        # One mutating operator at a time, including whole runs and recovery.
        # SQLite still lets independent read-only tools inspect durable events during a run.
        lock = (store.home / 'operator.lock').open('a')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        action = args.action
        if action == 'init':
            value = {'state': str(store.home), 'background_monitoring': False, 'automatic_activation': False}
        elif action == 'register':
            value = {'root': store.register(args.name, args.path, args.flavour, args.project, args.kind)}
        elif action == 'scan':
            value = store.capture(args.root, args.reason, args.actor)
        elif action == 'fetch':
            value = store.fetch(args.root, args.branch)
        elif action == 'import-revision':
            value = store.import_revision(args.root, args.commit)
        elif action == 'observe':
            value = {'observation': store.observe(args.root, args.flavour, args.project, args.topic, args.text_file.read_text())}
        elif action == 'consolidate':
            value = store.consolidate(args.root, args.flavour, args.project)
        elif action == 'candidate':
            value = store.create_candidate(args.baseline, args.workspace, args.flavour, args.reason_file.read_text(), args.bundle)
        elif action == 'plan':
            value = freeze_plan(store, args.baseline, args.candidate, json.loads(args.suite.read_text()),
                                args.adapter, args.model, args.effort,
                                json.loads(args.command_json) if args.command_json else None,
                                args.repetitions, args.max_attempts, args.timeout, args.min_families,
                                args.min_improvement, args.max_regression, args.equivalence_margin, args.task)
        elif action == 'run':
            value = run_plan(store, args.plan)
        elif action == 'compare':
            existing = store.db.execute('SELECT id FROM reports WHERE plan=?', (args.plan,)).fetchone()
            value = store.audited('reports', existing[0], 'comparison_recorded') if existing else summarize(store, args.plan)
        elif action == 'prepare-release':
            value = store.prepare_release(args.snapshot)
        elif action in ('activate', 'rollback'):
            value = store.activate(args.release, args.confirm_release, args.reason, action == 'rollback')
        elif action == 'release-status':
            active = store.reconcile_active()
            try:
                authority = ReleaseAuthority.from_host_policy()
                policy = {'configured': True, 'id': authority.policy['id'], 'approval_mode': authority.policy['approval_mode']}
            except ValueError as error:
                policy = {'configured': False, 'next_action': str(error)}
            selected = store._selection()
            value = {'active': active, 'behavior_verified': selected.get('behavior_verified', False) if selected else False,
                     'policy': policy, 'background_monitoring': False}
        elif action in ('release-preview', 'start-trial', 'promote-release', 'stop-trial', 'advance-update'):
            if args.bundle.stat().st_size > 2 * 1024 * 1024:
                raise ValueError('release bundle exceeds supported size')
            bundle = json.loads(args.bundle.read_text())
            authority = ReleaseAuthority.from_host_policy()
            if action == 'advance-update':
                value = advance_update(store, bundle, authority)
            elif action == 'release-preview':
                value = apply_release(store, bundle, authority, bundle['authorization']['signed']['phase'], preview=True)
            elif action == 'stop-trial':
                value = stop_trial(store, bundle['trial'], authority)
            else:
                value = apply_release(store, bundle, authority, 'trial' if action == 'start-trial' else 'promote')
        elif action == 'verify':
            value = store.verify()
        elif action == 'status':
            value = {'active': store.reconcile_active(), 'events': store.db.execute('SELECT count(*) FROM events').fetchone()[0],
                     'roots': [dict(r) for r in store.db.execute('SELECT * FROM roots')],
                     'background_monitoring': False, 'automatic_activation': False}
        elif action == 'recover':
            with store.transaction():
                recovered = []
                for row in store.db.execute('SELECT id,data FROM attempts').fetchall():
                    value = json.loads(row['data'])
                    if value['status'] == 'started':
                        value['status'] = 'interrupted'
                        value['score'] = None
                        store.db.execute('UPDATE attempts SET data=? WHERE id=?', (canonical(value), row['id']))
                        store.event('attempt_interrupted', value)
                        recovered.append(row['id'])
            value = {'interrupted_attempts': recovered, 'active': store.reconcile_active(), 'rerun_external_actions': False}
        elif action == 'history':
            value = render_history(store)
            if args.html:
                for row in store.db.execute('SELECT path FROM roots'):
                    root = Path(row[0])
                    if root == args.html.resolve() or root in args.html.resolve().parents:
                        raise ValueError('private history reports must stay outside registered source/memory roots')
                descriptor = os.open(args.html, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'w') as output:
                    output.write(html_report(value))
                value = {'private_report': str(args.html), 'comparisons': len(value['comparisons'])}
        print(json.dumps(value, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 2
    finally:
        if lock:
            lock.close()
        if store:
            store.close()
