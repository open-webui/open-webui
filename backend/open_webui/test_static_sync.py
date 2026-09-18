"""Regression tests for frontend static sync (https://github.com/open-webui/open-webui/issues/29968)."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / 'static_sync.py'


def load_static_sync():
    spec = importlib.util.spec_from_file_location('static_sync', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestSyncFrontendStatic(unittest.TestCase):
    def setUp(self):
        self._module = load_static_sync()
        self.sync = self._module.sync_frontend_static

    def test_missing_frontend_static_dir_preserves_tracked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            static_dir = root / 'package_static'
            static_dir.mkdir()
            kept = static_dir / 'logo.png'
            kept.write_text('tracked-logo')
            (static_dir / 'custom.css').write_text('body{}')

            self.sync(static_dir, root / 'build')

            self.assertTrue(kept.exists())
            self.assertEqual(kept.read_text(), 'tracked-logo')
            self.assertTrue((static_dir / 'custom.css').exists())

    def test_frontend_build_without_static_subdir_preserves_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            static_dir = root / 'package_static'
            static_dir.mkdir()
            kept = static_dir / 'favicon.png'
            kept.write_bytes(b'favicon')
            build_dir = root / 'build'
            build_dir.mkdir()

            self.sync(static_dir, build_dir)

            self.assertTrue(kept.exists())
            self.assertEqual(kept.read_bytes(), b'favicon')

    def test_present_frontend_static_wipes_and_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            static_dir = root / 'package_static'
            static_dir.mkdir()
            (static_dir / 'logo.png').write_text('stale')
            nested_dir = static_dir / 'assets'
            nested_dir.mkdir()
            nested_kept = nested_dir / 'keep.txt'
            nested_kept.write_text('dir-entry-survives-nonrecursive-wipe')

            frontend_static = root / 'build' / 'static'
            frontend_static.mkdir(parents=True)
            (frontend_static / 'logo.png').write_text('fresh-logo')
            (frontend_static / 'favicon.png').write_text('fresh-favicon')
            nested_src = frontend_static / 'assets' / 'app.js'
            nested_src.parent.mkdir()
            nested_src.write_text('bundle')

            self.sync(static_dir, root / 'build')

            self.assertEqual((static_dir / 'logo.png').read_text(), 'fresh-logo')
            self.assertEqual((static_dir / 'favicon.png').read_text(), 'fresh-favicon')
            self.assertEqual((static_dir / 'assets' / 'app.js').read_text(), 'bundle')
            self.assertTrue(nested_kept.exists())

    def test_empty_frontend_static_dir_still_wipes_top_level_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            static_dir = root / 'package_static'
            static_dir.mkdir()
            stale = static_dir / 'loader.js'
            stale.write_text('old')
            (root / 'build' / 'static').mkdir(parents=True)

            self.sync(static_dir, root / 'build')

            self.assertFalse(stale.exists())


if __name__ == '__main__':
    unittest.main()
