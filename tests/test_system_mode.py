"""Contract tests for system mode (§5, §14 C2).

Covers: .system-install marker detection (first), repo/standalone fallbacks,
PATH occlusion warning, safe_git_pull system branch, and ensure_nyxniri_symlink
no-op in system mode.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nyxniri.core as core
from tests.utils import TempEnv


class TestDetectRunMode(unittest.TestCase):
    """§14 C2: branch coverage for the marker-first mode detection."""

    def test_system_marker_wins_over_repo_signature(self):
        # A root with .system-install AND configs/+assets/ → system (not repo).
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / ".system-install").touch()
            (root / "configs").mkdir()
            (root / "assets").mkdir()
            cache = Path("/nonexistent/cache")
            mode, label, repo = core._detect_run_mode(root, cache)
            self.assertEqual(mode, "system")
            self.assertEqual(label, "System Package")
            self.assertEqual(repo, root)

    def test_repo_when_configs_and_assets_present(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "configs").mkdir()
            (root / "assets").mkdir()
            cache = Path("/nonexistent/cache")
            mode, label, repo = core._detect_run_mode(root, cache)
            self.assertEqual(mode, "repo")
            self.assertEqual(repo, root)

    def test_standalone_when_root_equals_cache(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            mode, label, repo = core._detect_run_mode(root, root)
            self.assertEqual(mode, "standalone")
            self.assertEqual(repo, root)

    def test_standalone_fallback_when_nothing_matches(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)  # no marker, no configs/assets, not the cache
            cache = Path("/nonexistent/cache")
            mode, label, repo = core._detect_run_mode(root, cache)
            self.assertEqual(mode, "standalone")
            self.assertEqual(repo, cache)


class TestCheckPathOcclusion(unittest.TestCase):
    """§5.3: system mode warns when ~/.local/bin/nyxniri shadows /usr/bin/nyxniri."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_warns_in_system_mode_when_user_link_present(self):
        self._ctx.env.run_mode = "system"
        (self._ctx.env.home / ".local/bin").mkdir(parents=True, exist_ok=True)
        (self._ctx.env.home / ".local/bin" / "nyxniri").symlink_to("/usr/bin/nyxniri")
        with patch("builtins.print"):
            self.assertTrue(core.check_path_occlusion())

    def test_silent_in_system_mode_when_no_user_link(self):
        self._ctx.env.run_mode = "system"
        with patch("builtins.print"):
            self.assertFalse(core.check_path_occlusion())

    def test_silent_outside_system_mode(self):
        self._ctx.env.run_mode = "repo"
        (self._ctx.env.home / ".local/bin").mkdir(parents=True, exist_ok=True)
        (self._ctx.env.home / ".local/bin" / "nyxniri").symlink_to("/usr/bin/foo")
        with patch("builtins.print"):
            self.assertFalse(core.check_path_occlusion())


class TestEnsureSymlinkSystemMode(unittest.TestCase):
    """§5.3: in system mode the package owns the CLI; the user link is untouched."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_system_mode_does_not_create_user_link(self):
        self._ctx.env.run_mode = "system"
        target = self._ctx.env.home / ".local/bin" / "nyxniri"
        core.ensure_nyxniri_symlink()
        self.assertFalse(target.exists(), "system mode must not create a user-territory link")


class TestSafeGitPullSystemBranch(unittest.TestCase):
    """§5.6: system mode refuses git pull, hints pacman."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self._ctx.env.run_mode = "system"
        # safe_git_pull needs a .git dir + git binary to reach the system branch.
        (self._ctx.env.repo_dir / ".git").mkdir(exist_ok=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_system_mode_returns_none_and_skips_pull(self):
        from nyxniri.network import safe_git_pull
        with patch("nyxniri.network.shutil.which", return_value="/usr/bin/git"), \
             patch("builtins.print"):
            result = safe_git_pull(self._ctx.env.repo_dir)
        self.assertIsNone(result, "system mode must skip git pull (return None)")


if __name__ == "__main__":
    unittest.main()
