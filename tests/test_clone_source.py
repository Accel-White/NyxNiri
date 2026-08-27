"""Contract tests for NYXNIRI_REPO clone-source override."""

import subprocess
import sys
import unittest


class TestCloneSourceOverride(unittest.TestCase):
    def _registry_with_env(self, env_value=None):
        env_assignment = (
            f"os.environ['NYXNIRI_REPO']={env_value!r};" if env_value is not None else "os.environ.pop('NYXNIRI_REPO', None);"
        )
        code = (
            "import os;" + env_assignment +
            "from nyxniri import constants;"
            "print(constants.REPO_URL);"
            "print(constants.GIT_MIRROR_REGISTRY)"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, check=True,
        )
        lines = res.stdout.strip().splitlines()
        return lines[0], lines[1]

    def test_override_collapses_to_single_custom_mirror(self):
        custom = "https://git.internal/NyxNiri.git"
        repo_url, registry = self._registry_with_env(custom)
        self.assertEqual(registry, f"[('Custom', '{custom}')]")

    def test_display_repo_url_stays_official_even_when_overridden(self):
        repo_url, _ = self._registry_with_env("https://git.internal/NyxNiri.git")
        self.assertTrue(repo_url.endswith("ech678/NyxNiri.git"))

    def test_default_without_env_unchanged(self):
        repo_url, registry = self._registry_with_env(None)
        self.assertIn("gh-proxy.org", registry)
        self.assertIn("Official", registry)


if __name__ == "__main__":
    unittest.main()
