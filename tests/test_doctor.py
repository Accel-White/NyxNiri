"""Tests for doctor preset-drift check (§8/§11)."""

import contextlib
import io
import shutil
import unittest

from tests.utils import TempEnv


class TestPresetDrift(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _run_drift(self):
        from nyxniri.doctor import _check_preset_drift
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _check_preset_drift(self._ctx.env)
        return buf.getvalue()

    def test_default_active_no_warn(self):
        # All apps at default → no drift.
        self.assertNotIn("已不在仓库", self._run_drift())

    def test_active_existing_preset_no_warn(self):
        from nyxniri.deploy.preset import write_active_preset
        # 'transparent' exists in the shipped kitty presets → no drift.
        write_active_preset("kitty", "transparent")
        self.assertNotIn("已不在仓库", self._run_drift())

    def test_active_missing_preset_warns(self):
        from nyxniri.deploy.preset import write_active_preset
        write_active_preset("kitty", "ghost")  # not in repo or user presets
        out = self._run_drift()
        self.assertIn("kitty", out)
        self.assertIn("ghost", out)

    def test_invalid_active_warns_without_echoing_untrusted_value(self):
        active = self._ctx.env.presets_dir / "kitty.active"
        active.parent.mkdir(parents=True, exist_ok=True)
        for raw in (b"../../outside\n", b"   \n", b"\xff\xfe"):
            with self.subTest(raw=raw):
                active.write_bytes(raw)
                out = self._run_drift()
                self.assertIn("kitty", out)
                self.assertNotIn("../../outside", out)

    def test_active_symlink_warns(self):
        from nyxniri.i18n import text

        active = self._ctx.env.presets_dir / "kitty.active"
        active.parent.mkdir(parents=True, exist_ok=True)
        outside = self._ctx.home / "outside-active"
        outside.write_text("transparent")
        active.symlink_to(outside)

        out = self._run_drift()

        self.assertIn("kitty", out)
        self.assertIn(text("活动预设状态无效", "active preset state is invalid"), out)

    def test_nyx_root_symlink_warns_without_reading_outside(self):
        from nyxniri.i18n import text

        self._ctx.env.nyx_dir.mkdir(parents=True)
        shutil.rmtree(self._ctx.env.nyx_dir)
        outside = self._ctx.home / "outside-nyx"
        (outside / "presets").mkdir(parents=True)
        (outside / "presets" / "kitty.active").write_text("transparent")
        self._ctx.env.nyx_dir.symlink_to(outside, target_is_directory=True)

        out = self._run_drift()

        self.assertIn("kitty", out)
        self.assertIn(text("活动预设状态无效", "active preset state is invalid"), out)


if __name__ == "__main__":
    unittest.main()
