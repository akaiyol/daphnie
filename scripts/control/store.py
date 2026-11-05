"""Transactional private ledger, content-addressed snapshots and explicit releases."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time
import uuid

FLAVOURS = ('assistant', 'research', 'design', 'think')
EXCLUDED = {'.git', 'node_modules', '__pycache__', '.pytest_cache', '.DS_Store', 'private'}
SECRET = re.compile(r'(^\.env($|\.)|credentials|secrets|auth\.json|\.(pem|key)$)', re.I)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reject_obvious_credentials(data):
    if re.search(rb'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_\-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----', data):
        raise ValueError('obvious credential material refused; keep credentials outside registered roots/observations')


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}', value):
        raise ValueError('IDs must be simple names of at most 100 characters')
    return value


def contained(base, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('expected a relative path')
    p = base / relative
    p.resolve().relative_to(base.resolve())
    return p


class Store:
    def __init__(self, home):
        self.home = Path(home).expanduser().resolve()
        if self.home == Path(self.home.anchor) or self.home == Path.home().resolve():
            raise ValueError('controller state requires a dedicated directory')
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.home, 0o700)
        for name in ('blobs', 'packages', 'attempts'):
            (self.home / name).mkdir(exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(str(self.home / 'ledger.sqlite'), timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, at REAL NOT NULL,
            kind TEXT NOT NULL, data TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS roots (
            id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, flavour TEXT NOT NULL,
            project TEXT NOT NULL, kind TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS snapshots (
            id TEXT PRIMARY KEY, root TEXT NOT NULL REFERENCES roots(id), manifest TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS root_heads (root TEXT PRIMARY KEY REFERENCES roots(id),
            snapshot TEXT NOT NULL REFERENCES snapshots(id));
          CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY, root TEXT NOT NULL REFERENCES roots(id), flavour TEXT NOT NULL,
            project TEXT NOT NULL, topic TEXT NOT NULL, body TEXT NOT NULL,
            forgotten INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS bundles (id TEXT PRIMARY KEY, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, plan TEXT NOT NULL REFERENCES plans(id),
            data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, plan TEXT UNIQUE NOT NULL REFERENCES plans(id),
            data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS releases (id TEXT PRIMARY KEY, snapshot TEXT NOT NULL REFERENCES snapshots(id),
            data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS active (slot INTEGER PRIMARY KEY CHECK(slot=1), release TEXT REFERENCES releases(id));
          CREATE TABLE IF NOT EXISTS activations (seq INTEGER PRIMARY KEY AUTOINCREMENT, release TEXT NOT NULL,
            previous TEXT, reason TEXT NOT NULL);
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    @contextlib.contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def event(self, kind, data):
        previous = self.db.execute('SELECT hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        previous = previous[0] if previous else ''
        record = {'id': uuid.uuid4().hex, 'at': time.time(), 'kind': kind, 'data': data, 'previous': previous}
        checksum = digest(canonical(record).encode())
        self.db.execute('INSERT INTO events(id,at,kind,data,previous,hash) VALUES (?,?,?,?,?,?)',
                        (record['id'], record['at'], kind, canonical(data), previous, checksum))
        return record['id']

    def blob(self, data):
        checksum = digest(data)
        path = self.home / 'blobs' / checksum
        if path.exists():
            if digest(path.read_bytes()) != checksum:
                raise ValueError('existing artifact is corrupt')
            return checksum
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.pending-')
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, 0o400)
            # No overwrite; concurrent identical artifacts can safely share the content address.
            try:
                os.link(tmp, path)
            except FileExistsError:
                if digest(path.read_bytes()) != checksum:
                    raise ValueError('artifact race found corrupt content')
        finally:
            os.unlink(tmp)
        return checksum

    def read_blob(self, checksum):
        if not re.fullmatch(r'[0-9a-f]{64}', checksum):
            raise ValueError('invalid artifact digest')
        data = (self.home / 'blobs' / checksum).read_bytes()
        if digest(data) != checksum:
            raise ValueError('artifact hash mismatch')
        return data

    def register(self, name, path, flavour, project, kind='package'):
        identifier(name)
        identifier(project)
        if flavour not in (*FLAVOURS, 'shared') or kind not in ('package', 'memory'):
            raise ValueError('invalid root scope')
        path = Path(path).expanduser().resolve(strict=True)
        if not path.is_dir():
            raise ValueError('root must be a directory')
        if path == Path(path.anchor) or path == Path.home().resolve():
            raise ValueError('register a narrow directory, not a filesystem or home root')
        if path == self.home or path in self.home.parents or self.home in path.parents:
            raise ValueError('registered roots cannot contain or be inside controller state')
        if kind == 'package' and not (path / 'CORE.md').is_file():
            raise ValueError('package root must contain CORE.md')
        with self.transaction():
            self.db.execute('INSERT INTO roots VALUES (?,?,?,?,?)', (name, str(path), flavour, project, kind))
            self.event('root_registered', {'root': name, 'path': str(path), 'flavour': flavour,
                                            'project': project, 'kind': kind})
        return name

    def root(self, name):
        row = self.db.execute('SELECT * FROM roots WHERE id=?', (name,)).fetchone()
        if not row:
            raise ValueError('unknown root')
        return dict(row)

    def capture(self, root_id, reason='reconciliation', actor='unknown'):
        root = self.root(root_id)
        source = Path(root['path'])
        entries, excluded, total = [], [], 0
        for directory, dirs, files in os.walk(source, followlinks=False):
            base = Path(directory)
            names = sorted(dirs + files)
            dirs[:] = [d for d in dirs if d not in EXCLUDED and not SECRET.search(d)
                       and not (base / d).is_symlink()]
            for name in names:
                p = base / name
                relative = p.relative_to(source).as_posix()
                if name in EXCLUDED or SECRET.search(name):
                    excluded.append(relative)
                    continue
                if p.is_symlink():
                    # Links to directories are captured as links, never followed by the walk.
                    p.resolve(strict=True).relative_to(source)
                    target = os.readlink(p)
                    if Path(target).is_absolute():
                        raise ValueError('snapshots require portable relative links')
                    entries.append({'path': relative, 'mode': 'link', 'blob': self.blob(target.encode())})
                elif p.is_file():
                    before = p.stat()
                    if before.st_size > 2 * 1024 * 1024:
                        raise ValueError('file exceeds snapshot limit: ' + relative)
                    content = p.read_bytes()
                    reject_obvious_credentials(content)
                    after = p.stat()
                    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                        raise ValueError('source changed during capture; retry')
                    total += len(content)
                    if total > 30 * 1024 * 1024:
                        raise ValueError('registered root exceeds snapshot limit')
                    entries.append({'path': relative, 'mode': 'file', 'blob': self.blob(content),
                                    'executable': bool(before.st_mode & 0o111)})
        entries.sort(key=lambda x: x['path'])
        manifest = {'root': root_id, 'flavour': root['flavour'], 'project': root['project'],
                    'kind': root['kind'], 'entries': entries, 'excluded': sorted(excluded)}
        sid = digest(canonical(manifest).encode())
        with self.transaction():
            old = self.db.execute('SELECT s.id,s.manifest FROM root_heads h JOIN snapshots s ON s.id=h.snapshot WHERE h.root=?',
                                  (root_id,)).fetchone()
            if old and old['id'] == sid:
                return {'snapshot': sid, 'changed': [], 'unchanged': True}
            previous = {x['path']: x for x in json.loads(old['manifest'])['entries']} if old else {}
            current = {x['path']: x for x in entries}
            changed = [{'path': p, 'before': previous.get(p), 'after': current.get(p)}
                       for p in sorted(set(previous) | set(current)) if previous.get(p) != current.get(p)]
            # Reverts have an existing content identity but are new observations in history.
            self.db.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?)', (sid, root_id, canonical(manifest)))
            self.db.execute('INSERT OR REPLACE INTO root_heads VALUES (?,?)', (root_id, sid))
            self.event('change_observed', {'root': root_id, 'snapshot': sid, 'before': old['id'] if old else None,
                                           'actor': actor, 'reason': reason, 'changes': changed,
                                           'excluded': manifest['excluded']})
        return {'snapshot': sid, 'changed': changed, 'unchanged': False}

    def snapshot(self, sid):
        row = self.db.execute('SELECT manifest FROM snapshots WHERE id=?', (sid,)).fetchone()
        if not row:
            raise ValueError('unknown snapshot')
        value = json.loads(row[0])
        if digest(canonical(value).encode()) != sid:
            raise ValueError('snapshot manifest changed')
        return value

    def fetch(self, root_id, branch='main'):
        root = self.root(root_id)
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]{0,150}', branch) or '..' in branch:
            raise ValueError('invalid branch')
        def git(*args):
            return subprocess.run(['git', '-C', root['path'], *args], check=True,
                                  capture_output=True, timeout=60)
        # Fetch updates Git object/ref data only: no checkout, install, code execution or activation.
        git('fetch', '--no-tags', 'origin', branch)
        revision = git('rev-parse', '--verify', 'FETCH_HEAD^{commit}').stdout.decode().strip()
        with self.transaction():
            self.event('update_fetched', {'root': root_id, 'branch': branch, 'revision': revision,
                                          'checkout_changed': False, 'activated': False})
        return {'revision': revision, 'checkout_changed': False, 'activated': False}

    def import_revision(self, root_id, revision):
        root = self.root(root_id)
        if root['kind'] != 'package' or not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise ValueError('import requires a package root and exact 40-character Git commit')
        def git(*args):
            return subprocess.run(['git', '-C', root['path'], *args], check=True,
                                  capture_output=True, timeout=30).stdout
        actual = git('rev-parse', '--verify', revision + '^{commit}').decode().strip()
        if actual != revision:
            raise ValueError('revision did not resolve to the exact requested commit')
        entries, excluded, total = [], [], 0
        for line in git('ls-tree', '-rzl', revision).split(b'\0'):
            if not line:
                continue
            metadata, raw_path = line.split(b'\t', 1)
            mode, kind, sha, raw_size = metadata.decode().split()
            path = raw_path.decode()
            if Path(path).is_absolute() or '..' in Path(path).parts:
                raise ValueError('invalid Git path')
            if any(part in EXCLUDED or SECRET.search(part) for part in Path(path).parts):
                excluded.append(path)
                continue
            if kind != 'blob' or mode not in ('100644', '100755', '120000'):
                raise ValueError('submodules and special modes are not supported')
            size = int(raw_size)
            total += size
            if size > 2 * 1024 * 1024 or total > 30 * 1024 * 1024 or len(entries) >= 10000:
                raise ValueError('Git snapshot exceeds supported limits')
            content = git('cat-file', 'blob', sha)
            reject_obvious_credentials(content)
            entry = {'path': path, 'mode': 'link' if mode == '120000' else 'file', 'blob': self.blob(content)}
            if mode == '120000':
                target = content.decode()
                if Path(target).is_absolute():
                    raise ValueError('absolute Git link')
                # Lexical traversal check is completed against the materialized snapshot as well.
                depth = len(Path(path).parent.parts)
                for part in Path(target).parts:
                    depth += -1 if part == '..' else (0 if part == '.' else 1)
                    if depth < 0:
                        raise ValueError('Git link escapes the snapshot')
            else:
                entry['executable'] = mode == '100755'
            entries.append(entry)
        if not any(e['path'] == 'CORE.md' for e in entries):
            raise ValueError('revision is not a Daphnie package')
        manifest = {'root': root_id, 'flavour': root['flavour'], 'project': root['project'], 'kind': 'package',
                    'entries': sorted(entries, key=lambda e: e['path']), 'excluded': sorted(excluded), 'git_revision': revision}
        sid = digest(canonical(manifest).encode())
        with self.transaction():
            self.db.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?)', (sid, root_id, canonical(manifest)))
            self.event('snapshot_imported', {'root': root_id, 'revision': revision, 'snapshot': sid,
                                             'checkout_changed': False, 'activated': False})
        return {'snapshot': sid, 'revision': revision, 'activated': False}

    def materialize(self, sid, destination):
        manifest = self.snapshot(sid)
        destination = Path(destination)
        if destination.exists():
            raise ValueError('materialization destination must not exist')
        destination.mkdir(parents=True)
        # Files first, links last; no writes through a link supplied by a snapshot.
        for entry in sorted(manifest['entries'], key=lambda e: e['mode'] == 'link'):
            path = contained(destination, entry['path'])
            path.parent.mkdir(parents=True, exist_ok=True)
            content = self.read_blob(entry['blob'])
            if entry['mode'] == 'link':
                target = content.decode()
                if Path(target).is_absolute():
                    raise ValueError('absolute snapshot link')
                (path.parent / target).resolve().relative_to(destination.resolve())
                path.symlink_to(target)
            else:
                path.write_bytes(content)
                path.chmod(0o755 if entry.get('executable') else 0o644)
        return destination

    def observe(self, root, flavour, project, topic, text):
        scope = self.root(root)
        if flavour not in FLAVOURS or project != scope['project'] or scope['flavour'] not in ('shared', flavour):
            raise ValueError('observation does not match registered scope')
        identifier(topic)
        if not text.strip() or len(text) > 12000:
            raise ValueError('observation must contain 1–12000 characters; never include credentials')
        reject_obvious_credentials(text.encode())
        oid, body = uuid.uuid4().hex, self.blob(text.encode())
        with self.transaction():
            self.db.execute('INSERT INTO observations(id,root,flavour,project,topic,body) VALUES (?,?,?,?,?,?)',
                            (oid, root, flavour, project, topic, body))
            self.event('observation_recorded', {'id': oid, 'root': root, 'flavour': flavour,
                                               'project': project, 'topic': topic, 'body': body})
        return oid

    def consolidate(self, root, flavour, project):
        scope = self.root(root)
        if scope['project'] != project or scope['flavour'] not in ('shared', flavour) or flavour not in FLAVOURS:
            raise ValueError('consolidation scope denied')
        groups = {}
        for row in self.db.execute('SELECT * FROM observations WHERE root=? AND flavour=? AND project=? AND forgotten=0 ORDER BY id',
                                   (root, flavour, project)):
            groups.setdefault(row['topic'], []).append({'id': row['id'], 'body': row['body']})
        bundles = []
        with self.transaction():
            for topic, evidence in groups.items():
                data = {'root': root, 'flavour': flavour, 'project': project, 'topic': topic,
                        'evidence': evidence, 'status': 'proposed',
                        'scope': 'Evidence grouping only; no inferred lesson or active update'}
                bid = digest(canonical(data).encode())
                if not self.db.execute('SELECT 1 FROM bundles WHERE id=?', (bid,)).fetchone():
                    self.db.execute('INSERT INTO bundles VALUES (?,?)', (bid, canonical(data)))
                    self.event('bundle_proposed', {'id': bid, **data})
                bundles.append({'id': bid, **data})
        return bundles

    def create_candidate(self, baseline, workspace, flavour, reason, bundle=None):
        if flavour not in FLAVOURS or not reason.strip():
            raise ValueError('candidate requires a flavour and an evidenced reason')
        source = self.snapshot(baseline)
        if source['kind'] != 'package':
            raise ValueError('candidate baseline must be a package')
        workspace = Path(workspace).expanduser().resolve()
        if workspace == self.home or self.home in workspace.parents or workspace in self.home.parents:
            raise ValueError('candidate workspace must be outside controller state')
        for row in self.db.execute('SELECT path FROM roots'):
            existing = Path(row[0])
            if workspace == existing or existing in workspace.parents or workspace in existing.parents:
                raise ValueError('candidate workspace must not overlap a registered root')
        evidence = None
        if bundle:
            row = self.db.execute('SELECT data FROM bundles WHERE id=?', (bundle,)).fetchone()
            if not row:
                raise ValueError('unknown evidence bundle')
            evidence = json.loads(row[0])
            if evidence['flavour'] != flavour or evidence['project'] != source['project']:
                raise ValueError('cross-scope candidate transfer requires separate review')
        cid = 'candidate-' + uuid.uuid4().hex
        self.materialize(baseline, workspace)
        self.register(cid, workspace, flavour, source['project'], 'package')
        data = {'id': cid, 'baseline': baseline, 'root': cid, 'workspace': str(workspace),
                'flavour': flavour, 'project': source['project'], 'reason': reason,
                'bundle': bundle, 'status': 'proposed', 'active': False,
                'next': 'Edit only this workspace, then scan its root to freeze the candidate snapshot'}
        with self.transaction():
            self.db.execute('INSERT INTO candidates VALUES (?,?)', (cid, canonical(data)))
            self.event('candidate_proposed', data)
        return data

    def audited(self, table, record_id, event_kind):
        if table not in ('plans', 'reports'):
            raise ValueError('unsupported audited projection')
        row = self.db.execute('SELECT data FROM ' + table + ' WHERE id=?', (record_id,)).fetchone()
        if not row:
            raise ValueError('unknown ' + table + ' ID')
        event = self.db.execute("SELECT data FROM events WHERE kind=? AND json_extract(data,'$.id')=? ORDER BY seq DESC LIMIT 1",
                                (event_kind, record_id)).fetchone()
        if not event or canonical(json.loads(event[0])) != canonical(json.loads(row[0])):
            raise ValueError('projection does not match its recorded event')
        return json.loads(row[0])

    def verify(self):
        previous, count = '', 0
        for row in self.db.execute('SELECT * FROM events ORDER BY seq'):
            record = {k: row[k] for k in ('id', 'at', 'kind', 'previous')}
            record['data'] = json.loads(row['data'])
            if row['previous'] != previous or digest(canonical(record).encode()) != row['hash']:
                raise ValueError('event chain mismatch at sequence ' + str(row['seq']))
            previous, count = row['hash'], count + 1
        for row in self.db.execute('SELECT id FROM snapshots'):
            for entry in self.snapshot(row[0])['entries']:
                self.read_blob(entry['blob'])
        for row in self.db.execute('SELECT body FROM observations WHERE forgotten=0'):
            self.read_blob(row[0])
        for row in self.db.execute('SELECT data FROM attempts'):
            result = json.loads(row[0]).get('score')
            if result:
                for checksum in result.get('artifacts', {}).values():
                    self.read_blob(checksum)
        return {'events': count, 'head': previous, 'status': 'consistent',
                'limit': 'Detects accidental changes; not tamper-proof against the same OS account'}

    def prepare_release(self, sid):
        if self.snapshot(sid)['kind'] != 'package':
            raise ValueError('only package snapshots can become releases')
        rid = sid
        destination = self.home / 'packages' / rid
        if not destination.exists():
            pending = self.home / 'packages' / ('.pending-' + uuid.uuid4().hex)
            self.materialize(sid, pending)
            os.rename(pending, destination)
        self.validate_package(sid, destination)
        required = ['CORE.md', 'OPERATING.md', 'skills/daphnie/SKILL.md']
        for flavour in FLAVOURS:
            required.extend([f'modes/{flavour}.md', f'skills/daphnie-{flavour}/SKILL.md',
                             f'libraries/{flavour}/manifest.json'])
        for relative in required:
            if not contained(destination, relative).is_file():
                raise ValueError('release lacks required package file: ' + relative)
        for flavour in FLAVOURS:
            library = destination / 'libraries' / flavour
            manifest = json.loads((library / 'manifest.json').read_text())
            if manifest.get('flavour') != flavour or not isinstance(manifest.get('skills'), list) or not manifest['skills']:
                raise ValueError('invalid flavour library in release')
            for skill in manifest['skills']:
                if not contained(library, skill['path']).is_file():
                    raise ValueError('release library procedure missing')
        with self.transaction():
            if not self.db.execute('SELECT 1 FROM releases WHERE id=?', (rid,)).fetchone():
                data = {'id': rid, 'snapshot': sid, 'status': 'prepared', 'behavior_verified': False}
                self.db.execute('INSERT INTO releases VALUES (?,?,?)', (rid, sid, canonical(data)))
                self.event('release_prepared', data)
        return {'release': rid, 'path': str(destination), 'behavior_verified': False}

    def validate_package(self, sid, destination):
        entries = self.snapshot(sid)['entries']
        actual = set()
        for directory, dirs, files in os.walk(destination, followlinks=False):
            base = Path(directory)
            for name in dirs + files:
                p = base / name
                if p.is_symlink() or p.is_file():
                    actual.add(p.relative_to(destination).as_posix())
        if actual != {e['path'] for e in entries}:
            raise ValueError('release package file inventory changed')
        for entry in entries:
            p = contained(destination, entry['path'])
            raw = os.readlink(p).encode() if entry['mode'] == 'link' and p.is_symlink() else (
                p.read_bytes() if entry['mode'] == 'file' and p.is_file() and not p.is_symlink() else None)
            if raw is None or digest(raw) != entry['blob']:
                raise ValueError('release package changed: ' + entry['path'])

    def reconcile_active(self):
        row = self.db.execute('SELECT release FROM active WHERE slot=1').fetchone()
        if not row:
            return None
        rid = row[0]
        self.validate_package(rid, self.home / 'packages' / rid)
        link, pending = self.home / 'current', self.home / ('.current-' + uuid.uuid4().hex)
        if link.exists() and not link.is_symlink():
            raise ValueError('current must be a managed symlink')
        pending.symlink_to('packages/' + rid)
        os.replace(pending, link)
        return rid

    def activate(self, rid, confirmation, reason, rollback=False):
        if confirmation != rid or not reason.strip():
            raise ValueError('operator confirmation must equal the full release ID and include a reason')
        if not self.db.execute('SELECT 1 FROM releases WHERE id=?', (rid,)).fetchone():
            raise ValueError('release not prepared')
        self.validate_package(rid, self.home / 'packages' / rid)
        with self.transaction():
            old = self.db.execute('SELECT release FROM active WHERE slot=1').fetchone()
            previous = old[0] if old else None
            if rollback and not self.db.execute('SELECT 1 FROM activations WHERE release=?', (rid,)).fetchone():
                raise ValueError('rollback target was never active')
            self.db.execute('INSERT OR REPLACE INTO active VALUES (1,?)', (rid,))
            self.db.execute('INSERT INTO activations(release,previous,reason) VALUES (?,?,?)', (rid, previous, reason))
            self.event('rollback_recorded' if rollback else 'activation_recorded',
                       {'release': rid, 'previous': previous, 'reason': reason,
                        'authorization': 'explicit local operator adoption', 'behavior_verified': False})
        # Database is authoritative. A crash here is repaired by the next status/run.
        self.reconcile_active()
        return {'active': rid, 'previous': previous, 'behavior_verified': False,
                'memory_rollback': 'not performed; preserve newer project observations'}
