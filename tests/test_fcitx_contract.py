"""The Fcitx regression contract must be runnable against an arbitrary checkout."""

import io
import subprocess
import sys
import tarfile
import tempfile
import unittest
from tests.utils import TempEnv


class TestFcitxThemeHotReloadContract(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_contract_accepts_this_checkout(self):
        repo = self._ctx.env.repo_dir
        contract = repo / "contracts" / "fcitx_theme_hot_reload.py"
        result = subprocess.run(
            [sys.executable, str(contract), str(repo)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("contract passed", result.stdout)

    def test_contract_rejects_pure_v304(self):
        repo = self._ctx.env.repo_dir
        contract = repo / "contracts" / "fcitx_theme_hot_reload.py"
        try:
            archive = subprocess.run(
                ["git", "archive", "5ea801dc17d687e89dd344294c6738a910a1f4e6"],
                cwd=repo,
                capture_output=True,
                check=False,
            )
        except OSError:
            self.skipTest("git is unavailable in this source export")
        if archive.returncode != 0:
            self.skipTest("v3.0.4 source is unavailable in this checkout")
        with tempfile.TemporaryDirectory() as raw_checkout:
            with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as contents:
                contents.extractall(raw_checkout)
            result = subprocess.run(
                [sys.executable, str(contract), raw_checkout],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
