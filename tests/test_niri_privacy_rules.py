"""Privacy contracts for the public Niri configuration."""

import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_RULES = _REPO / "configs" / "niri" / "rules.kdl"


class TestScreencastPrivacy(unittest.TestCase):
    def test_noctalia_notifications_are_blocked_from_screencasts_only(self):
        src = _RULES.read_text(encoding="utf-8")
        expected = '''layer-rule {
    match namespace="^noctalia-notification$"
    block-out-from "screencast"
}'''

        self.assertIn(expected, src)
        self.assertNotIn('block-out-from "screen-capture"', src)


if __name__ == "__main__":
    unittest.main()
