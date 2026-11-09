#!/usr/bin/env python3
"""Explicit experimental memory operations; no automatic skill or personality changes."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from control.memory import MemoryStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--flavour', choices=('assistant', 'research', 'think', 'design'), required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--index-budget', type=int, default=5000, help='UTF-8 bytes, not model tokens')
    actions = parser.add_subparsers(dest='action', required=True)
    for name in ('init', 'index', 'verify'):
        actions.add_parser(name)
    put = actions.add_parser('put')
    put.add_argument('--record', type=Path, required=True, help='Private JSON record; source_date must include timezone')
    get = actions.add_parser('get'); get.add_argument('key')
    recall = actions.add_parser('recall'); recall.add_argument('query')
    recall.add_argument('--limit', type=int, default=5); recall.add_argument('--budget', type=int, default=12000)
    forget = actions.add_parser('forget'); forget.add_argument('key'); forget.add_argument('--confirm-record', required=True)
    args = parser.parse_args(argv)
    store = None
    try:
        store = MemoryStore(args.state, args.flavour, args.project, args.owner, args.index_budget)
        if args.action == 'init':
            result = {'scope': store.scope, 'background_tasks': False, 'host_isolation': 'unverified'}
        elif args.action == 'put':
            result = store.put(**json.loads(args.record.read_text()))
        elif args.action == 'get':
            result = store.get(args.key)
        elif args.action == 'recall':
            result = store.recall(args.query, args.limit, args.budget)
        elif args.action == 'forget':
            result = store.forget(args.key, args.confirm_record)
        elif args.action == 'verify':
            result = store.verify()
        else:
            result = store.index()
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, TypeError, OSError, sqlite3.Error) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 2
    finally:
        if store:
            store.close()


if __name__ == '__main__':
    raise SystemExit(main())
