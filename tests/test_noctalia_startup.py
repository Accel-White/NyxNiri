"""Safety contracts for the Noctalia user-session startup wrapper."""

import subprocess
import unittest
from pathlib import Path

from tests.utils import TempEnv

_REPO = Path(__file__).resolve().parent.parent
_START_NOCTALIA = _REPO / "configs" / "niri" / "scripts" / "start-noctalia.sh"


class TestNoctaliaStartup(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.home = self._ctx.home
        self.bin_dir = self.home / "bin"
        self.bin_dir.mkdir()
        self.calls = self.home / "calls"

    def tearDown(self):
        self._ctx.__exit__()

    def _write_command(self, name, body):
        command = self.bin_dir / name
        command.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        command.chmod(0o755)

    def _run_start(self):
        return subprocess.run(
            ["/bin/bash", str(_START_NOCTALIA)],
            capture_output=True,
            text=True,
            timeout=10,
            env={
                "PATH": f"{self.bin_dir}:/usr/bin:/bin",
                "HOME": str(self.home),
                "CALLS": str(self.calls),
            },
        )

    def test_stale_noctalia_scope_is_stopped_before_start(self):
        self._write_command("systemctl", 'printf "systemctl:%s\\n" "$*" >>"$CALLS"')
        self._write_command("noctalia", 'printf "noctalia\\n" >>"$CALLS"')

        proc = self._run_start()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.calls.read_text(encoding="utf-8").splitlines(),
            [
                "systemctl:--user stop app-niri-noctalia-*.scope",
                "noctalia",
            ],
        )

    def test_no_matching_scope_does_not_block_start(self):
        self._write_command("systemctl", "exit 1")
        self._write_command("noctalia", 'printf "noctalia\\n" >"$CALLS"')

        proc = self._run_start()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.calls.read_text(encoding="utf-8"), "noctalia\n")


if __name__ == "__main__":
    unittest.main()
