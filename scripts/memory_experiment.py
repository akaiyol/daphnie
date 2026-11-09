#!/usr/bin/env python3
"""Run synthetic no-memory/scoped-memory pairs. Live runs require an explicit 12-attempt budget."""
import argparse
import json
from pathlib import Path
from control.memory_experiment import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True, help='New private directory outside this repository')
parser.add_argument('--adapter', choices=('command', 'codex'), default='command')
parser.add_argument('--model')
parser.add_argument('--effort')
parser.add_argument('--max-live-attempts', type=int)
args = parser.parse_args()
if args.adapter == 'codex' and (args.max_live_attempts != 12 or not args.model or not args.effort):
    parser.error('live comparison requires --max-live-attempts 12, --model and --effort')
package = Path(__file__).resolve().parents[1]
if args.output.resolve() == package or package in args.output.resolve().parents:
    parser.error('private experiment output must be outside the repository')
print(json.dumps(run(args.output, args.adapter, args.model, args.effort), indent=2))
