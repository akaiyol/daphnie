#!/usr/bin/env python3
"""Package structure checks only; not behavioral or artistic validation."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MODES = ('design', 'think', 'assistant', 'research')
NAMES = ('daphnie', *(f'daphnie-{mode}' for mode in MODES))


def check():
    errors = []
    for filename in ('CORE.md', 'OPERATING.md', *(f'modes/{mode}.md' for mode in MODES)):
        if not (ROOT / filename).is_file():
            errors.append(f'missing {filename}')
    for path in ROOT.rglob('*'):
        if path.is_symlink():
            try:
                path.resolve(strict=True).relative_to(ROOT)
            except (ValueError, OSError, RuntimeError):
                errors.append(f'broken or external symlink: {path.relative_to(ROOT)}')
        if path.suffix == '.md' and path.is_file():
            content = path.read_text()
            if re.search(r'\b(?:TODO|TBD|FIXME)\b|\[INSERT\b', content):
                errors.append(f'unfinished content: {path.relative_to(ROOT)}')
            for ref in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
                if '://' in ref or ref.startswith('#'):
                    continue
                target = path.parent / ref.split('#', 1)[0]
                try:
                    target.resolve(strict=True).relative_to(ROOT)
                except (ValueError, OSError, RuntimeError):
                    errors.append(f'missing or external reference: {path.relative_to(ROOT)} -> {ref}')
    for name in NAMES:
        skill = ROOT / 'skills' / name
        path = skill / 'SKILL.md'
        if not path.is_file():
            errors.append(f'missing entrypoint: {name}')
            continue
        match = re.match(r'\A---\n(.*?)\n---\n', path.read_text(), re.S)
        fields = {}
        if match:
            for line in match[1].splitlines():
                key, sep, value = line.partition(':')
                if sep:
                    fields[key.strip()] = value.strip()
        if fields.get('name') != name or not re.fullmatch(r'[a-z0-9-]{1,63}', fields.get('name', '')):
            errors.append(f'invalid name: {name}')
        if not fields.get('description'):
            errors.append(f'missing description: {name}')
        if not (skill / 'references/core.md').is_symlink():
            errors.append(f'core must be linked: {name}')
        refs = ('design', 'think', 'assistant', 'research') if name == 'daphnie' else ('mode',)
        for ref in refs:
            if not (skill / f'references/{ref}.md').is_symlink():
                errors.append(f'missing mode link: {name}/{ref}')
        metadata = skill / 'agents/openai.yaml'
        if not metadata.is_file() or f'${name}' not in metadata.read_text():
            errors.append(f'missing invocation metadata: {name}')
    return errors


if __name__ == '__main__':
    failures = check()
    for failure in failures:
        print(f'FAIL: {failure}', file=sys.stderr)
    if failures:
        sys.exit(1)
    print('PASS: five entrypoints, frontmatter basics, modes, contained links/references and no unfinished placeholders.')
    print('Scope: structural checks only; behavior and quality remain unverified.')
