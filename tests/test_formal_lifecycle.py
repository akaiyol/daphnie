"""Concrete formal-model witnesses and coverage drift. TLC runs separately; no model API calls."""
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'verification/skill_lifecycle'
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location('daphnie_formal_runner', DIRECTORY / 'run.py')
formal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(formal)


class FormalLifecycleTests(unittest.TestCase):
    def test_concrete_counterexample_progress_and_mutations(self):
        before = formal.source_fingerprints()
        self.assertEqual(formal.check_sources(), before)
        results = formal.replay()
        for name, passed in results.items():
            with self.subTest(witness=name): self.assertTrue(passed)
        self.assertEqual(formal.source_fingerprints(), before)

    def test_covered_source_change_demands_review_before_repinning(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            for relative in formal.SOURCES:
                destination = base / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, destination)
            path = base / 'scripts/control/store.py'
            text = path.read_text()
            self.assertIn("'behavior_verified': False", text)
            path.write_text(text.replace("'behavior_verified': False", "'behavior_verified': True", 1))
            with patch.object(formal, 'ROOT', base):
                with self.assertRaisesRegex(ValueError, 'Covered implementation changed'):
                    formal.check_sources()


if __name__ == '__main__':
    unittest.main()
