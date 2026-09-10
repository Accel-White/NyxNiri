"""Contracts for the shipped Noctalia configuration."""

import unittest
from pathlib import Path


_REPO = Path(__file__).resolve().parent.parent
_NOCTALIA_CONFIG = _REPO / "configs" / "noctalia" / "noctalia-config.toml"


def _section(text: str, name: str) -> str:
    marker = f"[{name}]"
    start = text.index(marker) + len(marker)
    tail = text[start:]
    next_section = tail.find("\n[")
    return tail if next_section == -1 else tail[:next_section]


class TestNoctaliaConfig(unittest.TestCase):
    def test_launched_apps_are_isolated_from_shell_lifecycle(self):
        """Launcher/dock/taskbar apps must not inherit the Noctalia cgroup."""
        text = _NOCTALIA_CONFIG.read_text(encoding="utf-8")
        shell = _section(text, "shell")

        self.assertIn("launch_apps_as_systemd_services = true", shell)
        self.assertNotIn("launch_apps_custom_command", shell)


if __name__ == "__main__":
    unittest.main()
