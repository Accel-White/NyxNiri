"""Safety contracts for clean-cache argument modes."""

import os
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path

from tests.utils import TempEnv


class TestCleanCacheDryRun(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.home = self._ctx.home
        self.script = Path(__file__).resolve().parent.parent / "configs" / "fish" / "clean-cache"
        self.fake_bin = self.home / "fake-bin"
        self.fake_bin.mkdir()
        self.marker = self.home / "mutation.log"

        stub = self.fake_bin / "tool-stub"
        stub.write_text(
            """#!/usr/bin/env bash
set -eu
tool=${0##*/}
case "$tool:$*" in
    systemctl:is-active*) exit 1 ;;
    systemctl:start*)
        IFS= read -r answer || exit 88
        printf 'systemctl-input %s\\n' "$answer" >> "$HOME/mutation.log" ;;
    journalctl:--until*) printf 'No entries\\n' ;;
    snap:list*) printf 'Name Version Rev Tracking Publisher Notes\\n' ;;
    pnpm:'store path') printf '%s\\n' "$HOME/.local/share/pnpm" ;;
    cargo:'help -Z gc') exit 0 ;;
    pacman:-Qdtq*) exit 0 ;;
    pacman:'-Rs --print-format'*) exit 0 ;;
    pacdiff:-o*) exit 0 ;;
    paccache:-dk2*) printf 'cache yes\\n' ;;
    *) printf '%s %s\\n' "$tool" "$*" >> "$HOME/mutation.log" ;;
esac
""",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        for name in (
            "bun", "cargo", "ccache", "corepack", "docker", "flatpak", "gem",
            "go", "journalctl", "npm", "paccache", "pacdiff", "pacman", "pamac", "paru",
            "pip", "pnpm", "shelly", "snap", "systemctl", "yarn", "yay",
        ):
            shutil.copy2(stub, self.fake_bin / name)

        self.sandbox_usr = self.home / "sandbox-usr"
        sandbox_bin = self.sandbox_usr / "bin"
        sandbox_bin.mkdir(parents=True)
        shutil.copy2("/usr/bin/true", sandbox_bin / "sudo")
        os.symlink("/mnt/usr/bin/env", sandbox_bin / "env")
        os.symlink("/mnt/usr/bin/bash", sandbox_bin / "bash")
        os.symlink("/mnt/usr/bin/bash", sandbox_bin / "sh")
        os.symlink("/mnt/usr/lib", self.sandbox_usr / "lib")
        os.symlink("/mnt/usr/share", self.sandbox_usr / "share")

        self.root_sandbox_script = self.home / "clean-cache-root-sandbox"
        source = self.script.read_text(encoding="utf-8")
        root_guard = "[[ $EUID -eq 0 ]]"
        self.assertEqual(source.count(root_guard), 1)
        # Namespace uid 0 makes the fake sudo path pass the production trust checks
        # Disable only the root refusal in this isolated copy; all other code stays exact
        self.root_sandbox_script.write_text(
            source.replace(root_guard, "[[ 1 -eq 0 ]]"),
            encoding="utf-8",
        )
        self.root_sandbox_script.chmod(0o755)

        self.protected_paths = []
        for path in (
            ".cache/thumbnails/.keep",
            ".cache/go-build/item",
            ".cache/node/corepack/item",
            ".cache/pip/item",
            ".cache/yarn/item",
            ".cargo/registry/cache/item",
            ".java/deployment/cache/item",
            ".local/share/flatpak/item",
            ".local/share/gem/item",
            ".local/share/pnpm/item",
            ".npm/item",
            ".snap/item",
            "go/pkg/item",
        ):
            target = self.home / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("keep", encoding="utf-8")
            self.protected_paths.append(target)

    def tearDown(self):
        self._ctx.__exit__()

    def _sandbox_command(self, *args, new_session=True):
        if not shutil.which("bwrap"):
            self.skipTest("bubblewrap is required for destructive-command isolation")

        command = [
            "bwrap",
            "--die-with-parent",
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
        ]
        if new_session:
            command.append("--new-session")
        command.extend([
            "--ro-bind", "/", "/",
            "--tmpfs", "/tmp",
            "--tmpfs", "/run",
            "--tmpfs", "/home",
            "--tmpfs", "/var",
            "--proc", "/proc",
            "--dev", "/dev",
            "--ro-bind", str(self.script), "/run/clean-cache",
            "--ro-bind", str(self.fake_bin), "/run/fake-bin",
            "--bind", str(self.home), "/home/test",
            "--setenv", "HOME", "/home/test",
            "--setenv", "XDG_CONFIG_HOME", "/home/test/xdg-config",
            "--setenv", "XDG_CACHE_HOME", "/home/test/.cache",
            "--setenv", "PATH", "/run/fake-bin:/usr/bin",
            "/usr/bin/bash", "/run/clean-cache", *args,
        ])
        return command

    def _auto_sandbox_command(self, auto_option):
        if not shutil.which("bwrap"):
            self.skipTest("bubblewrap is required for destructive-command isolation")

        return [
            "bwrap",
            "--die-with-parent",
            "--unshare-user",
            "--uid", "0",
            "--gid", "0",
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
            "--new-session",
            "--tmpfs", "/",
            "--dir", "/mnt",
            "--ro-bind", "/", "/mnt",
            "--ro-bind", str(self.sandbox_usr), "/usr",
            "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/bin", "/sbin",
            "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib", "/lib64",
            "--ro-bind", "/etc", "/etc",
            "--tmpfs", "/run",
            "--tmpfs", "/tmp",
            "--tmpfs", "/home",
            "--tmpfs", "/var",
            "--proc", "/proc",
            "--dev", "/dev",
            "--ro-bind", str(self.root_sandbox_script), "/run/clean-cache",
            "--ro-bind", str(self.fake_bin), "/run/fake-bin",
            "--bind", str(self.home), "/home/test",
            "--setenv", "HOME", "/home/test",
            "--setenv", "XDG_CONFIG_HOME", "/home/test/xdg-config",
            "--setenv", "XDG_CACHE_HOME", "/home/test/.cache",
            "--setenv", "PATH", "/run/fake-bin:/usr/bin:/mnt/usr/bin",
            "/mnt/usr/bin/bash", "/run/clean-cache", auto_option,
        ]

    def _run(self, *args, extra_env=None):
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        command = self._sandbox_command(*args)
        return subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)

    def _run_interactive(self, *args, replies):
        script_command = shutil.which("script")
        if not script_command:
            self.skipTest("util-linux script is required for pseudo-terminal input")

        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.home),
                "XDG_CONFIG_HOME": str(self.home / "xdg-config"),
                "XDG_CACHE_HOME": str(self.home / ".cache"),
                "PATH": f"{self.fake_bin}:/usr/bin",
            }
        )
        sandbox_command = self._sandbox_command(*args, new_session=False)
        command = [
            script_command,
            "--quiet",
            "--return",
            "--command", shlex.join(sandbox_command),
            "/dev/null",
        ]
        return subprocess.run(
            command,
            input=replies,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

    def test_dry_run_all_scopes_never_invokes_mutating_tools(self):
        modes = (
            ("--dry-run",),
            ("-n",),
            ("-dn",),
            ("-nd",),
            ("--dry-run", "-d"),
            ("-d", "--dry-run"),
        )
        for args in modes:
            with self.subTest(args=args):
                result = self._run(*args)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(
                    self.marker.exists(),
                    self.marker.read_text() if self.marker.exists() else "",
                )
                for protected in self.protected_paths:
                    self.assertTrue(protected.is_file(), protected)
                self.assertFalse((self.home / "xdg-config" / "maclean").exists())
                self.assertIn("[Dry-Run] Would execute:", result.stderr)
                self.assertIn("[Dry-Run] Would remove:", result.stderr)
                self.assertIn(
                    "Dry-run: no user data, packages, services, or caches will be changed",
                    result.stdout,
                )

    def test_interactive_mode_still_executes_real_cleaning(self):
        config = self.home / "xdg-config" / "maclean" / "maclean.conf"
        config.parent.mkdir(parents=True)
        target = self.home / ".adobe"
        target.mkdir()
        (target / "item").write_text("remove", encoding="utf-8")
        config.write_text("_mc_junk_dirs=(\n/home/test/.adobe\n)\n", encoding="utf-8")

        result = self._run_interactive("-j", replies="n\nn\ny\ny\nx")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(target.exists())

    def test_auto_mode_feeds_confirmation_stream_to_mutating_command(self):
        for auto_option in ("-a", "-y", "--auto", "--yes"):
            with self.subTest(auto_option=auto_option):
                if self.marker.exists():
                    self.marker.unlink()
                result = subprocess.run(
                    self._auto_sandbox_command(auto_option),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.marker.exists())
                self.assertIn("systemctl-input y", self.marker.read_text(encoding="utf-8"))

    def test_combined_auto_and_dry_run_is_fail_safe(self):
        result = self._run("-and")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists(), self.marker.read_text() if self.marker.exists() else "")
        self.assertIn("Dry-run:", result.stdout)

    def test_invalid_option_fails_before_creating_config(self):
        result = self._run("--dry-run", "--bogus")

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / "xdg-config" / "maclean").exists())
        self.assertFalse(self.marker.exists())

    def test_help_and_version_validate_all_arguments_before_output(self):
        for args in (("-h", "-z"), ("--help", "--bogus"), ("-v", "extra")):
            with self.subTest(args=args):
                result = self._run(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.home / "xdg-config" / "maclean").exists())

        for args in (("-h",), ("--help",), ("-v",), ("--version",)):
            with self.subTest(args=args):
                result = self._run(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((self.home / "xdg-config" / "maclean").exists())

    def test_ambient_auto_variable_cannot_bypass_confirmation(self):
        config = self.home / "xdg-config" / "maclean" / "maclean.conf"
        config.parent.mkdir(parents=True)
        target = self.home / ".adobe"
        target.mkdir()
        config.write_text("_mc_junk_dirs=(\n/home/test/.adobe\n)\n", encoding="utf-8")

        result = self._run("-j", extra_env={"_mc_auto": "1", "_mc_dryrun": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(target.is_dir())
        self.assertFalse(self.marker.exists())
        self.assertNotIn("[auto]", result.stdout)


if __name__ == "__main__":
    unittest.main()
