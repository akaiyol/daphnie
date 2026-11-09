"""Experimental scoped files/SQLite memory. Scope checks are not OS access control."""
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

from .store import FLAVOURS, canonical, identifier, reject_obvious_credentials


class IndexBudgetError(ValueError):
    pass


def timestamp(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('dates must be ISO strings with a timezone')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('dates must include a timezone')
    return parsed.astimezone(dt.timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, home, flavour, project, owner, index_budget=5000, clock=None):
        if flavour not in FLAVOURS:
            raise ValueError('invalid flavour')
        for value in (project, owner):
            identifier(value)
        if isinstance(index_budget, bool) or not isinstance(index_budget, int) or not 256 <= index_budget <= 20000:
            raise ValueError('index budget must be 256–20000 UTF-8 bytes')
        self.home = Path(home).expanduser().resolve()
        package = Path(__file__).resolve().parents[2]
        if self.home == Path.home() or self.home == Path(self.home.anchor) or self.home == package or package in self.home.parents:
            raise ValueError('memory needs a dedicated private directory outside the package')
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.home.chmod(0o700)
        for name in ('memory.lock', 'memory.sqlite', 'notes'):
            if (self.home / name).is_symlink():
                raise ValueError('managed memory paths must not be symlinks')
        self.lock = (self.home / 'memory.lock').open('a')
        try:
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.notes = self.home / 'notes'
            self.notes.mkdir(mode=0o700, exist_ok=True)
            self.db = sqlite3.connect(str(self.home / 'memory.sqlite'))
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA secure_delete=ON')
            self.db.execute('PRAGMA journal_mode=DELETE')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''
              CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY, family TEXT NOT NULL, key TEXT, revision INTEGER NOT NULL,
                title TEXT, kind TEXT, attribution TEXT, source TEXT, source_date TEXT,
                created TEXT NOT NULL, expires TEXT, status TEXT NOT NULL,
                value_json TEXT, body_hash TEXT, supersedes TEXT);
              CREATE UNIQUE INDEX IF NOT EXISTS active_keys ON records(key) WHERE status='active';
              CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL, record TEXT NOT NULL);
            ''')
            self.scope = {'flavour': flavour, 'project': project, 'owner': owner}
            self.budget = index_budget
            self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc).isoformat())
            expected = {'scope': self.scope, 'index_budget_bytes': index_budget, 'schema': 1}
            row = self.db.execute('SELECT data FROM settings WHERE id=1').fetchone()
            if row and json.loads(row[0]) != expected:
                raise ValueError('store scope or budget mismatch; no records may be retrieved')
            if not row:
                with self.db:
                    self.db.execute('INSERT INTO settings VALUES (1,?)', (canonical(expected),))
            self._cleanup()
        except BaseException:
            self.close()
            raise

    def close(self):
        if getattr(self, 'db', None):
            self.db.close()
            self.db = None
        if getattr(self, 'lock', None):
            self.lock.close()
            self.lock = None

    def _now(self):
        return timestamp(self.clock())

    def _cleanup(self):
        # Recover interrupted creates/deletes. Committed tombstones deny retrieval before physical cleanup.
        keep = {r[0] + '.md' for r in self.db.execute("SELECT id FROM records WHERE kind='note' AND status!='deleted'")}
        for path in self.notes.iterdir():
            if path.name not in keep:
                if path.is_dir() and not path.is_symlink():
                    raise ValueError('unexpected directory in private note storage')
                path.unlink()

    def _rows(self):
        return self.db.execute("SELECT * FROM records WHERE status='active' AND (expires IS NULL OR expires>?) ORDER BY key", (self._now(),)).fetchall()

    def index(self):
        entries = [{k: row[k] for k in ('id', 'key', 'title', 'kind', 'attribution', 'source_date', 'expires')}
                   for row in self._rows() if row['attribution'] != 'inferred']
        value = {'scope': self.scope, 'authority': 'context_only', 'entries': entries,
                 'index_bytes': 0, 'budget_bytes': self.budget}
        for _ in range(4):
            value['index_bytes'] = len(canonical(value).encode())
        size = len(canonical(value).encode())
        if size > self.budget:
            raise IndexBudgetError('memory index exceeds byte budget; explicitly shorten titles or forget obsolete records; no automatic deletion')
        return value

    def put(self, key, title, kind, content, source, source_date, attribution='explicit_user', expires=None, supersedes=None):
        identifier(key)
        if not isinstance(title, str) or not 1 <= len(title) <= 120 or not isinstance(source, str) or not 1 <= len(source) <= 1000:
            raise ValueError('nonempty bounded title and source required')
        if kind not in ('note', 'fact', 'preference') or attribution not in ('explicit_user', 'sourced', 'inferred'):
            raise ValueError('invalid kind or attribution')
        if kind == 'note' and not isinstance(content, str):
            raise ValueError('notes must be text')
        if kind != 'note' and not isinstance(content, dict):
            raise ValueError('facts/preferences require a structured JSON object')
        raw = (content if kind == 'note' else canonical(content)).encode()
        if not raw or len(raw) > 3000:
            raise ValueError('memory content must contain 1–3000 UTF-8 bytes')
        reject_obvious_credentials(raw + title.encode() + source.encode())
        dated, expiry = timestamp(source_date), timestamp(expires)
        if not dated:
            raise ValueError('source date required')
        previous = self.db.execute("SELECT * FROM records WHERE key=? AND status='active'", (key,)).fetchone()
        if (previous is not None and supersedes != previous['id']) or (previous is None and supersedes is not None):
            raise ValueError('correction must name the exact current record; silent overwrite refused')
        rid = uuid.uuid4().hex
        family, revision = (previous['family'], previous['revision'] + 1) if previous else (rid, 1)
        path = self.notes / (rid + '.md')
        if kind == 'note':
            with path.open('xb') as output:
                output.write(raw); output.flush(); os.fsync(output.fileno())
            path.chmod(0o600)
        try:
            with self.db:
                if previous:
                    self.db.execute("UPDATE records SET status='superseded' WHERE id=?", (previous['id'],))
                self.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                (rid, family, key, revision, title, kind, attribution, source, dated, self._now(), expiry,
                                 'active', raw.decode() if kind != 'note' else None,
                                 hashlib.sha256(raw).hexdigest(), supersedes))
                self.index()  # Fail the write atomically instead of silently discarding index entries.
                self.db.execute('INSERT INTO events(at,action,record) VALUES (?,?,?)',
                                (self._now(), 'corrected' if previous else 'created', rid))
        except BaseException:
            if path.exists():
                path.unlink()
            raise
        return {'id': rid, 'key': key, 'revision': revision, 'status': 'active', 'authority': 'context_only'}

    def _content(self, row):
        if row['kind'] == 'note':
            path = self.notes / (row['id'] + '.md')
            if path.is_symlink():
                raise ValueError('linked memory body refused')
            if path.stat().st_size > 3000:
                raise ValueError('memory body exceeds supported size')
            raw = path.read_bytes()
        else:
            raw = row['value_json'].encode()
        if len(raw) > 3000:
            raise ValueError('memory body exceeds supported size')
        if hashlib.sha256(raw).hexdigest() != row['body_hash']:
            raise ValueError('memory body integrity mismatch')
        return raw.decode() if row['kind'] == 'note' else json.loads(raw)

    def get(self, key):
        identifier(key)
        row = next((r for r in self._rows() if r['key'] == key and r['attribution'] != 'inferred'), None)
        if row is None:
            return None
        return {**{k: row[k] for k in ('id', 'key', 'revision', 'kind', 'title', 'attribution', 'source', 'source_date', 'expires')},
                'content': self._content(row), 'authority': 'context_only', 'scope': self.scope}

    def recall(self, query, limit=5, budget=12000):
        if not isinstance(query, str) or not query.strip() or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError('query and limit of 1–20 required')
        if not isinstance(budget, int) or not 256 <= budget <= 20000:
            raise ValueError('retrieval byte budget must be 256–20000')
        terms = set(re.findall(r'\w+', query.lower()))
        ranked = []
        for entry in self.index()['entries']:
            text = (entry['key'] + ' ' + entry['title']).lower()
            matches = len(terms & set(re.findall(r'\w+', text)))
            if matches:
                ranked.append((-matches, entry['key']))
        records = []
        value = {'scope': self.scope, 'authority': 'context_only', 'records': records}
        if len(canonical(value).encode()) > budget:
            raise IndexBudgetError('scope envelope exceeds retrieval byte budget')
        for _, key in sorted(ranked)[:limit]:
            candidate = self.get(key)
            if candidate is None:  # A record may expire between index creation and retrieval.
                continue
            proposed = {**value, 'records': records + [candidate]}
            if len(canonical(proposed).encode()) > budget:
                raise IndexBudgetError('retrieved context exceeds byte budget; narrow the query or reduce the limit')
            records.append(candidate)
        return value

    def forget(self, key, confirmation):
        identifier(key)
        row = self.db.execute("SELECT id,family FROM records WHERE key=? AND status='active'", (key,)).fetchone()
        if not row or confirmation != row['id']:
            raise ValueError('forget requires the exact current record ID')
        with self.db:
            self.db.execute("UPDATE records SET key=NULL,title=NULL,kind=NULL,attribution=NULL,source=NULL,source_date=NULL,expires=NULL,value_json=NULL,body_hash=NULL,status='deleted' WHERE family=?", (row['family'],))
            self.db.execute('INSERT INTO events(at,action,record) VALUES (?,?,?)', (self._now(), 'forgotten', row['id']))
        self._cleanup()
        return {'forgotten': row['id'], 'all_revisions_removed': True,
                'limit': 'Current store only; exported contexts, backups and prior model sessions are not erased'}

    def verify(self):
        for row in self.db.execute("SELECT * FROM records WHERE status!='deleted'"):
            self._content(row)
        self.index()
        return {'status': 'consistent', 'scope': self.scope, 'host_isolation': 'unverified'}
