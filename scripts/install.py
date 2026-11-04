#!/usr/bin/env python3
"""Link skills from this canonical checkout without replacing existing entries."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('daphnie', 'daphnie-design', 'daphnie-think', 'daphnie-assistant', 'daphnie-research')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=Path.home() / '.codex/skills')
    args = parser.parse_args()
    destination = args.destination.expanduser().absolute()
    plans = []
    conflicts = []
    for name in NAMES:
        source = ROOT / 'skills' / name
        target = destination / name
        if not (source / 'SKILL.md').is_file():
            conflicts.append(f'missing source: {source}')
            continue
        if os.path.lexists(target):
            if target.is_symlink() and target.resolve() == source.resolve():
                continue
            conflicts.append(f'refusing existing entry: {target}')
        else:
            plans.append((source, target))
    if conflicts:
        print('\n'.join(conflicts), file=sys.stderr)
        return 1
    destination.mkdir(parents=True, exist_ok=True)
    for source, target in plans:
        # symlink creation also refuses a path created after preflight.
        try:
            target.symlink_to(source, target_is_directory=True)
        except OSError as error:
            print(f'installation stopped: {error}; existing entries preserved', file=sys.stderr)
            return 1
        print(f'linked {target.name}')
    print('Installation complete; no environments, dependencies or models were installed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
