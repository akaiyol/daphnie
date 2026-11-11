"""Two-checkout handoffs and data-loss boundaries, using local bare remotes."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import handoff


class HandoffTests(unittest.TestCase):
    def git(self, folder, *args):
        result = subprocess.run(['git', '-C', str(folder), *args], check=True,
                                text=True, capture_output=True)
        return result.stdout.strip()

    def identity(self, folder):
        self.git(folder, 'config', 'user.name', 'Synthetic test')
        self.git(folder, 'config', 'user.email', 'test@example.invalid')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        self.git(self.source, 'init', '-b', 'main')
        self.identity(self.source)
        (self.source / 'CORE.md').write_text('Synthetic package\n')
        self.git(self.source, 'add', '.')
        self.git(self.source, 'commit', '-m', 'Initial package')
        self.code_remote = self.base / 'code.git'
        self.git(self.base, 'clone', '--bare', str(self.source), str(self.code_remote))
        self.git(self.source, 'remote', 'add', 'origin', str(self.code_remote))
        self.memory = self.base / 'memory'
        # Supply identity without creating files in the new memory directory.
        with patch.dict('os.environ', {'GIT_AUTHOR_NAME': 'Synthetic test',
                        'GIT_AUTHOR_EMAIL': 'test@example.invalid',
                        'GIT_COMMITTER_NAME': 'Synthetic test',
                        'GIT_COMMITTER_EMAIL': 'test@example.invalid'}):
            handoff.initialize(self.memory, self.source, 'alpha')
        self.identity(self.memory)
        self.remote = self.base / 'memory.git'
        self.git(self.base, 'clone', '--bare', str(self.memory), str(self.remote))
        self.git(self.memory, 'remote', 'add', 'origin', str(self.remote))
        self.other = self.base / 'pc-memory'
        self.pc = self.base / 'pc-source'
        self.git(self.base, 'clone', str(self.remote), str(self.other))
        self.git(self.base, 'clone', str(self.code_remote), str(self.pc))
        self.identity(self.other)
        self.identity(self.pc)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)
        self.temp.cleanup()

    def test_round_trip_notes_code_and_deletion(self):
        handoff.start(self.memory, self.source, 'laptop')
        (self.memory / 'notes/CURRENT.md').write_text('Decision: synthetic checkpoint\n')
        (self.source / 'CORE.md').write_text('Synthetic package revision two\n')
        self.git(self.source, 'commit', '-am', 'Update package')
        self.git(self.source, 'push', 'origin', 'main')
        head = self.git(self.source, 'rev-parse', 'HEAD')
        handoff.finish(self.memory, self.source, 'laptop')
        handoff.start(self.other, self.pc, 'pc')
        self.assertEqual(self.git(self.pc, 'rev-parse', 'HEAD'), head)
        self.assertIn('checkpoint', (self.other / 'notes/CURRENT.md').read_text())
        (self.other / 'notes/INDEX.md').unlink()
        handoff.finish(self.other, self.pc, 'pc')
        handoff.start(self.memory, self.source, 'laptop')
        self.assertFalse((self.memory / 'notes/INDEX.md').exists())

    def test_second_device_cannot_take_active_handoff(self):
        handoff.start(self.memory, self.source, 'laptop')
        with self.assertRaisesRegex(ValueError, 'already checked out'):
            handoff.start(self.other, self.pc, 'pc')

    def test_racing_start_push_cannot_overwrite_winner(self):
        # Pause the first device after its commit, before the remote push.
        with patch.object(handoff, 'publish'):
            handoff.start(self.memory, self.source, 'laptop')
        handoff.start(self.other, self.pc, 'pc')
        with self.assertRaisesRegex(ValueError, 'push'):
            handoff.publish(self.memory)
        remote_state = json.loads(self.git(self.remote, 'show', 'main:HANDOFF.json'))
        self.assertEqual(remote_state['active_device'], 'pc')
        self.assertEqual(handoff.validate_memory(self.memory)['active_device'], 'laptop')

    def test_finish_requires_checkpoint(self):
        handoff.start(self.memory, self.source, 'laptop')
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            handoff.finish(self.memory, self.source, 'laptop')
        self.assertEqual(handoff.validate_memory(self.memory)['active_device'], 'laptop')

    def test_dirty_package_is_preserved(self):
        (self.pc / 'CORE.md').write_text('Uncommitted work\n')
        with self.assertRaisesRegex(ValueError, 'uncommitted'):
            handoff.start(self.other, self.pc, 'pc')
        self.assertEqual((self.pc / 'CORE.md').read_text(), 'Uncommitted work\n')

    def test_finish_rejects_wrong_device_and_unpublished_code(self):
        handoff.start(self.memory, self.source, 'laptop')
        (self.memory / 'notes/CURRENT.md').write_text('Checkpoint\n')
        with self.assertRaisesRegex(ValueError, 'does not own'):
            handoff.finish(self.memory, self.source, 'pc')
        (self.source / 'CORE.md').write_text('Local only\n')
        self.git(self.source, 'commit', '-am', 'Local only')
        with self.assertRaisesRegex(ValueError, 'not on origin'):
            handoff.finish(self.memory, self.source, 'laptop')
        self.assertEqual(handoff.validate_memory(self.memory)['active_device'], 'laptop')

    def test_database_symlink_and_credential_rejected(self):
        database = self.memory / 'notes/memory.sqlite'
        database.write_bytes(b'SQLite format 3\x00')
        with self.assertRaises(ValueError):
            handoff.validate_memory(self.memory)
        database.unlink()
        link = self.memory / 'notes/link.md'
        link.symlink_to(self.source / 'CORE.md')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            handoff.validate_memory(self.memory)
        link.unlink()
        link.write_text('ghp_' + 'A' * 30)
        with self.assertRaisesRegex(ValueError, 'credential'):
            handoff.validate_memory(self.memory)

    def test_memory_divergence_is_not_merged(self):
        (self.memory / 'notes/local.md').write_text('Unpublished memory\n')
        handoff.commit(self.memory, 'Unpublished memory')
        with self.assertRaisesRegex(ValueError, 'unpublished or divergent'):
            handoff.start(self.memory, self.source, 'laptop')
        self.assertTrue((self.memory / 'notes/local.md').exists())

    def test_different_push_url_rejected_before_publication(self):
        self.git(self.memory, 'remote', 'set-url', '--push', 'origin', str(self.code_remote))
        with self.assertRaisesRegex(ValueError, 'different push URL'):
            handoff.private_remote(self.memory)

    def test_public_or_unverified_github_remote_rejected(self):
        self.git(self.memory, 'remote', 'set-url', 'origin', 'https://github.com/example/public.git')
        real = subprocess.run
        with patch.object(handoff.subprocess, 'run') as mock:
            def dispatch(args, **kwargs):
                if args[0] == 'gh':
                    return subprocess.CompletedProcess(args, 0, stdout='false\n', stderr='')
                return real(args, **kwargs)
            mock.side_effect = dispatch
            with self.assertRaisesRegex(ValueError, 'private GitHub'):
                handoff.private_remote(self.memory)

    def test_failed_push_preserves_checkpoint_and_requires_recovery(self):
        handoff.start(self.memory, self.source, 'laptop')
        (self.memory / 'notes/CURRENT.md').write_text('Checkpoint survives failed push\n')
        with patch.object(handoff, 'publish', side_effect=ValueError('offline')):
            with self.assertRaisesRegex(ValueError, 'offline'):
                handoff.finish(self.memory, self.source, 'laptop')
        self.assertEqual(self.git(self.memory, 'status', '--porcelain'), '')
        with self.assertRaisesRegex(ValueError, 'unpublished or divergent'):
            handoff.start(self.memory, self.source, 'laptop')
        self.git(self.memory, 'push', 'origin', 'main')
        handoff.start(self.other, self.pc, 'pc')
        self.assertIn('survives', (self.other / 'notes/CURRENT.md').read_text())

    def test_connect_is_idempotent_and_preserves_other_project(self):
        index = self.base / 'config/INDEX.md'
        index.parent.mkdir()
        index.write_text('# Existing configuration\nOther project pointer.\n')
        handoff.connect(self.memory, index)
        first = index.read_text()
        handoff.connect(self.memory, index)
        self.assertEqual(index.read_text(), first)
        self.assertIn('Other project pointer.', first)
        self.assertIn(str(self.memory / 'INDEX.md'), first)


if __name__ == '__main__':
    unittest.main()
