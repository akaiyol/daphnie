#!/usr/bin/env python3
"""Package structure checks only; not behavioral or artistic validation."""
from pathlib import Path
import json
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
                target = path.resolve().parent / ref.split('#', 1)[0]
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
    for mode in MODES:
        library = ROOT / 'libraries' / mode
        try:
            manifest = json.loads((library / 'manifest.json').read_text())
            if manifest['flavour'] != mode or not re.fullmatch(r'\d+\.\d+\.\d+', manifest['library_version']):
                raise ValueError('invalid library identity/version')
            ids = set()
            if not manifest['skills']:
                raise ValueError('empty library')
            for skill in manifest['skills']:
                if skill['id'] in ids or not re.fullmatch(r'[a-z0-9-]+', skill['id']):
                    raise ValueError('invalid/duplicate skill ID')
                ids.add(skill['id'])
                if not re.fullmatch(r'\d+\.\d+\.\d+', skill['version']):
                    raise ValueError('invalid skill version')
                target = (library / skill['path']).resolve(strict=True)
                target.relative_to(library.resolve())
                if not target.is_file():
                    raise ValueError('skill path must be a contained file')
                if skill['status'] == 'owner-adopted':
                    baseline = {'assistant': 'task-recovery', 'research': 'evidence-audit',
                                'design': 'reference-review', 'think': 'decision-test'}
                    if (skill['id'] != baseline[mode] or skill['version'] != '1.0.0'
                            or skill['validation'] != 'behavior-unvalidated' or skill['release_record'] is not None):
                        raise ValueError('bootstrap status restricted to original unvalidated baseline')
                elif skill['status'] == 'verified':
                    if skill['validation'] != 'verified' or not skill['release_record']:
                        raise ValueError('verified skill requires release evidence')
                    release = (ROOT / skill['release_record']).resolve(strict=True)
                    release.relative_to(ROOT)
                    if not release.is_file():
                        raise ValueError('release evidence must be a file')
                else:
                    raise ValueError('active library contains unapproved skill')
        except (KeyError, ValueError, OSError, TypeError) as error:
            errors.append(f'invalid {mode} library: {error}')
        for entry, ref in ((f'daphnie-{mode}', 'library'), ('daphnie', f'{mode}-library')):
            link = ROOT / 'skills' / entry / 'references' / ref
            if not link.is_symlink() or link.resolve() != library.resolve():
                errors.append(f'missing/wrong library link: {entry}/{ref}')
    return errors


if __name__ == '__main__':
    failures = check()
    for failure in failures:
        print(f'FAIL: {failure}', file=sys.stderr)
    if failures:
        sys.exit(1)
    print('PASS: five entrypoints, four scoped libraries, metadata and contained references.')
    print('Scope: structural checks only; behavior and quality remain unverified.')
