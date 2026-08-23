"""Behavior contracts for network: dirty tree return value, git existence check."""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import make_temp_home, force_repo_mode, reset_env


class TestGitExistenceCheck(unittest.TestCase):
    """safe_git_pull must check git exists before running git commands."""

    def setUp(self):
        self._tmp = make_temp_home()
        reset_env(Path(self._tmp.name))
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_git_missing_returns_false_not_crash(self):
        """If git is not installed, should return False with friendly message, not crash."""
        from nyxniri.network import safe_git_pull

        with patch("shutil.which", return_value=None):
            with patch("builtins.print"):
                result = safe_git_pull(Path("/fake/repo"))

        self.assertFalse(result, "Should return False when git is missing")


class TestDirtyTreeReturnValue(unittest.TestCase):
    """Non-interactive dirty tree must return False (not None), so exit code is non-zero."""

    def setUp(self):
        self._tmp = make_temp_home()
        reset_env(Path(self._tmp.name))
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_non_interactive_dirty_tree_returns_false(self):
        """Non-interactive + dirty tree should return False (not None=skip, not True=ok)."""
        from nyxniri.network import safe_git_pull

        fake_repo = Path(self._tmp.name) / "fake-repo"
        fake_repo.mkdir()
        (fake_repo / ".git").mkdir()

        # Force standalone mode so dirty tree doesn't short-circuit on "repo" mode
        from nyxniri.core import get_env
        get_env().run_mode = "standalone"
        get_env().repo_dir = fake_repo

        # git status --porcelain returns dirty
        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "status" in cmd and "--porcelain" in cmd:
                mock.stdout = " M some-file\n"  # dirty
                mock.returncode = 0
            else:
                mock.stdout = ""
                mock.returncode = 0
            return mock

        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run", side_effect=fake_run):
                with patch("sys.stdin.isatty", return_value=False):
                    with patch("builtins.print"):
                        result = safe_git_pull(fake_repo)

        self.assertEqual(result, False,
                         "Non-interactive dirty tree should return False (non-zero exit), not None (skip)")

    def test_interactive_dirty_tree_cancelled_returns_none(self):
        """Interactive + dirty tree + user says no → None (skip)."""
        from nyxniri.network import safe_git_pull

        fake_repo = Path(self._tmp.name) / "fake-repo"
        fake_repo.mkdir()
        (fake_repo / ".git").mkdir()

        from nyxniri.core import get_env
        get_env().run_mode = "standalone"
        get_env().repo_dir = fake_repo

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "status" in cmd and "--porcelain" in cmd:
                mock.stdout = " M some-file\n"
                mock.returncode = 0
            else:
                mock.stdout = ""
                mock.returncode = 0
            return mock

        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run", side_effect=fake_run):
                with patch("sys.stdin.isatty", return_value=True):
                    with patch("nyxniri.network.prompt_confirm", return_value=False):
                        with patch("builtins.print"):
                            result = safe_git_pull(fake_repo)

        self.assertIsNone(result,
                          "Interactive dirty tree with user cancel should return None (skip)")

    def test_clean_tree_proceeds_to_pull(self):
        """Clean tree should proceed to git pull."""
        from nyxniri.network import safe_git_pull

        fake_repo = Path(self._tmp.name) / "fake-repo"
        fake_repo.mkdir()
        (fake_repo / ".git").mkdir()

        from nyxniri.core import get_env
        get_env().run_mode = "standalone"
        get_env().repo_dir = fake_repo

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "status" in cmd and "--porcelain" in cmd:
                mock.stdout = ""  # clean
                mock.returncode = 0
            elif "pull" in cmd:
                mock.stdout = "Already up to date."
                mock.returncode = 0
            else:
                mock.stdout = ""
                mock.returncode = 0
            return mock

        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("nyxniri.network._run_git_transfer") as mock_transfer:
                mock_transfer.return_value = MagicMock(returncode=0)
                with patch("builtins.print"):
                    result = safe_git_pull(fake_repo)

        self.assertTrue(result, "Clean tree with successful pull should return True")


if __name__ == "__main__":
    unittest.main()
