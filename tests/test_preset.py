"""Contract tests for the preset mechanism (§3.2).

Covers §14 shapes: the four src-selection branches, dest-missing reset with
upstream-removed warning, state file read/write, and __custom__ preservation
across preset switches (regression guard for the copytree ignore change).
"""

import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import nyxniri.deploy.preset as preset
from nyxniri.deploy.atomic import atomic_replace_item
from nyxniri.tui import PresetSwitcher
from tests.utils import TempEnv


class TestActiveStateFile(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_read_default_when_no_file(self):
        self.assertEqual(preset.read_active_preset("kitty"), "default")

    def test_write_then_read(self):
        preset.write_active_preset("kitty", "transparent")
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")

    def test_write_creates_presets_dir(self):
        # presets_dir does not exist initially; write must create it.
        self.assertFalse(self._ctx.env.presets_dir.exists())
        preset.write_active_preset("kitty", "compact")
        self.assertTrue(self._ctx.env.presets_dir.is_dir())

    def test_read_empty_file_treated_as_default(self):
        # An empty (e.g. half-written) active file must not silently switch —
        # read() treats empty/whitespace as "default".
        self._ctx.env.presets_dir.mkdir(parents=True, exist_ok=True)
        (self._ctx.env.presets_dir / "kitty.active").write_text("   \n")
        self.assertEqual(preset.read_active_preset("kitty"), "default")


class TestResolvePresetSrc(unittest.TestCase):
    """The four src branches (§3.2) — parameter-shape contract on src path."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.configs_src = Path(self._sandbox.name)

        self.app = "kitty"
        self.app_root = self.env.configs_src / self.app
        self.app_root.mkdir(parents=True)
        (self.app_root / "kitty.conf").write_text("# default")

        self.official = self.app_root / "presets" / "transparent"
        self.official.mkdir(parents=True)
        (self.official / "kitty.conf").write_text("# transparent")

        self.dest = self.env.config_dir / self.app

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_default_branch(self):
        r = preset.resolve_preset_src(self.app, "default", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertIsNone(r.reset_active)
        self.assertEqual(r.warnings, [])

    def test_official_preset_branch(self):
        self.dest.mkdir(parents=True)
        (self.dest / "old.conf").write_text("x")
        r = preset.resolve_preset_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.official)
        self.assertIsNone(r.reset_active)

    def test_user_preset_branch(self):
        self.dest.mkdir(parents=True)
        user_dir = self.env.presets_dir / self.app / "mine"
        user_dir.mkdir(parents=True)
        r = preset.resolve_preset_src(self.app, "mine", self.dest)
        self.assertEqual(r.src, user_dir)

    def test_official_preferred_over_user_same_name(self):
        # §2.2: official wins on name collision
        self.dest.mkdir(parents=True)
        (self.env.presets_dir / self.app / "transparent").mkdir(parents=True)
        r = preset.resolve_preset_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.official)

    def test_not_found_freezes_dest(self):
        # active = ghost, dest exists → src None (freeze), warning. Do NOT
        # fall back to default (would silently wipe the user's config). §3.2
        self.dest.mkdir(parents=True)
        r = preset.resolve_preset_src(self.app, "ghost", self.dest)
        self.assertIsNone(r.src)
        self.assertTrue(r.warnings)

    def test_dest_missing_resets_to_default(self):
        # dest absent + active=transparent (still upstream) → default, no extra warning
        r = preset.resolve_preset_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertEqual(r.reset_active, "default")
        self.assertEqual(r.warnings, [])

    def test_dest_missing_and_upstream_removed_warns(self):
        # dest absent + active=ghost (gone upstream) → default + extra warning (B1)
        r = preset.resolve_preset_src(self.app, "ghost", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertEqual(r.reset_active, "default")
        self.assertTrue(r.warnings)


class TestCustomSurvivesPresetSwitch(unittest.TestCase):
    """__custom__ files survive preset switches (Dunder + copytree-ignore compat)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.configs_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_custom_file_retained_across_two_presets(self):
        app = "kitty"
        root = self.env.configs_src / app
        root.mkdir(parents=True)
        transparent = root / "presets" / "transparent"
        transparent.mkdir(parents=True)
        (transparent / "kitty.conf").write_text("# transparent")
        compact = root / "presets" / "compact"
        compact.mkdir(parents=True)
        (compact / "kitty.conf").write_text("# compact")

        dest = self.env.config_dir / app
        # First deploy transparent, then add a user __custom__.conf, then switch.
        self.assertTrue(atomic_replace_item(transparent, dest))
        (dest / "__custom__.conf").write_text("# my overrides")
        self.assertTrue(atomic_replace_item(compact, dest))

        # compact's kitty.conf is now in dest, and __custom__.conf survived.
        self.assertEqual((dest / "kitty.conf").read_text(), "# compact")
        self.assertTrue((dest / "__custom__.conf").exists())
        self.assertEqual((dest / "__custom__.conf").read_text(), "# my overrides")

    def test_module_toml_not_shipped_to_dest(self):
        # §10.4 boundary: .module.toml is repo metadata, must not land in dest.
        app = "kitty"
        root = self.env.configs_src / app
        root.mkdir(parents=True)
        (root / "kitty.conf").write_text("# conf")
        (root / ".module.toml").write_text('[packages]\nrepo = ["kitty"]\n')
        dest = self.env.config_dir / app
        atomic_replace_item(root, dest)
        self.assertFalse((dest / ".module.toml").exists())
        # The real kitty.conf did ship.
        self.assertTrue((dest / "kitty.conf").exists())

    def test_presets_subdir_not_shipped_to_dest(self):
        # presets/ stays in repo, not deployed into ~/.config/<app>/presets/
        app = "kitty"
        root = self.env.configs_src / app
        root.mkdir(parents=True)
        (root / "kitty.conf").write_text("# conf")
        (root / "presets" / "transparent").mkdir(parents=True)
        (root / "presets" / "transparent" / "kitty.conf").write_text("# t")
        dest = self.env.config_dir / app
        atomic_replace_item(root, dest)
        self.assertFalse((dest / "presets").exists())


class TestPresetOperations(unittest.TestCase):
    """list/apply/save/delete against the real repo's kitty + transparent demo."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_list_marks_active_default(self):
        entries = preset.list_presets("kitty")
        names = [n for n, _, _ in entries]
        self.assertIn("default", names)
        self.assertIn("transparent", names)  # the shipped demo preset
        active_entry = [e for e in entries if e[2]]
        self.assertEqual(len(active_entry), 1)
        self.assertEqual(active_entry[0][0], "default")  # fresh = default

    def test_apply_transparent_writes_active_and_deploys_variant(self):
        ok = preset.apply_preset("kitty", "transparent")
        self.assertTrue(ok)
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")
        conf = self.env.config_dir / "kitty" / "kitty.conf"
        self.assertTrue(conf.is_file())
        self.assertIn("0.75", conf.read_text())  # the transparent variant

    def test_apply_default_resets(self):
        preset.write_active_preset("kitty", "transparent")
        ok = preset.apply_preset("kitty", "default")
        self.assertTrue(ok)
        self.assertEqual(preset.read_active_preset("kitty"), "default")

    def test_apply_unknown_preset_fails_without_writing(self):
        # Nonexistent preset: fail, do not touch active.
        preset.write_active_preset("kitty", "transparent")
        ok = preset.apply_preset("kitty", "ghost")
        self.assertFalse(ok)
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")

    def test_apply_then_write_timing_atomic_fail_leaves_active(self):
        # B2 (§14): if atomic_replace fails, active must NOT be written.
        preset.write_active_preset("kitty", "default")
        with patch("nyxniri.deploy.atomic.atomic_replace_item", return_value=False):
            ok = preset.apply_preset("kitty", "transparent")
        self.assertFalse(ok)
        # active still default — deploy-then-write held back the write.
        self.assertEqual(preset.read_active_preset("kitty"), "default")

    def test_save_rejects_reserved_default(self):
        # Set up a dest so the rejection is specifically the name, not the empty dest.
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# conf")
        self.assertFalse(preset.save_preset("kitty", "default"))

    def test_save_rejects_official_name_collision(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# conf")
        # 'transparent' is an official preset — collision must be rejected.
        self.assertFalse(preset.save_preset("kitty", "transparent"))

    def test_save_snapshots_tree_minus_custom(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# my conf")
        (dest / "__custom__.conf").write_text("# private")
        custom_dir = dest / "__custom__"
        custom_dir.mkdir()
        (custom_dir / "extra.conf").write_text("# nested custom")

        self.assertTrue(preset.save_preset("kitty", "mine"))
        target = self.env.presets_dir / "kitty" / "mine"
        self.assertTrue((target / "kitty.conf").is_file())
        # __custom__ entries filtered out (both file and dir).
        self.assertFalse((target / "__custom__.conf").exists())
        self.assertFalse((target / "__custom__").exists())

    def test_save_then_apply_user_preset(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# my flavor")
        self.assertTrue(preset.save_preset("kitty", "mine"))
        # Wipe dest, then re-apply the saved user preset.
        import shutil
        shutil.rmtree(dest)
        self.assertTrue(preset.apply_preset("kitty", "mine"))
        self.assertEqual(preset.read_active_preset("kitty"), "mine")
        self.assertEqual((dest / "kitty.conf").read_text(), "# my flavor")

    def test_delete_user_preset(self):
        target = self.env.presets_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        (target / "kitty.conf").write_text("# x")
        self.assertTrue(preset.delete_preset("kitty", "mine"))
        self.assertFalse(target.exists())

    def test_delete_rejects_default_and_official(self):
        self.assertFalse(preset.delete_preset("kitty", "default"))
        self.assertFalse(preset.delete_preset("kitty", "transparent"))


class TestApplyNarrowPath(unittest.TestCase):
    """§9 / §14 U1: apply runs only atomic_replace + render — no hw patches, no services."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_apply_skips_hardware_patches_and_post_install_services(self):
        with patch("nyxniri.deploy.hardware._phase_hardware_patches") as hw, \
             patch("nyxniri.deploy.deploy._phase_post_install_services") as svc:
            ok = preset.apply_preset("kitty", "transparent")
        self.assertTrue(ok)
        hw.assert_not_called()
        svc.assert_not_called()


class TestPresetSwitchPreservesManifestFiles(unittest.TestCase):
    """The narrow deploy path honours the manifest ``preserve`` list.

    Regression guard: applying a preset must not wipe runtime-managed files the
    new variant doesn't ship — specifically niri/effects.kdl (a symlink whose
    target encodes EyeCare on/off) and niri/monitor.kdl (user-generated). Both
    are declared in niri/.module.toml preserve and must survive a switch.
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.niri_dest = self.env.config_dir / "niri"
        # Deploy niri defaults first so monitor.kdl + effects_*.kdl exist.
        from nyxniri.deploy.atomic import atomic_replace_item
        atomic_replace_item(self.env.configs_src / "niri", self.niri_dest)
        # Create the runtime effects.kdl symlink (as deploy.py does on first install).
        effects_normal = self.niri_dest / "effects_normal.kdl"
        self.effects_sym = self.niri_dest / "effects.kdl"
        self.effects_sym.symlink_to(effects_normal)
        # Mark monitor.kdl so we can detect a wipe.
        self.monitor = self.niri_dest / "monitor.kdl"
        with self.monitor.open("a") as f:
            f.write("# USER-MARKER\n")

    def tearDown(self):
        self._ctx.__exit__()

    def test_effects_kdl_symlink_survives_preset_switch(self):
        self.assertTrue(preset.apply_preset("niri", "default"))
        self.assertTrue(self.effects_sym.is_symlink(), "effects.kdl symlink was wiped")
        self.assertIn("effects_normal.kdl", os.readlink(self.effects_sym))

    def test_monitor_kdl_survives_preset_switch(self):
        self.assertTrue(preset.apply_preset("niri", "default"))
        self.assertIn("# USER-MARKER", self.monitor.read_text())


class TestPresetSwitcher(unittest.TestCase):
    """§14 U1: dual-pane focus behavior via a mocked key stream."""

    def _run_keys(self, switcher, keys):
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.tui.read_key", side_effect=keys), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def test_enter_returns_app_and_preset(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False)])
        # RIGHT → right pane; DOWN → transparent; ENTER
        self.assertEqual(self._run_keys(sw, ["RIGHT", "DOWN", "ENTER"]), ("kitty", "transparent"))

    def test_pane_switch_keeps_app_cursor(self):
        apps = ["fastfetch", "kitty"]
        presets_kitty = [("default", True), ("transparent", False)]
        sw = PresetSwitcher(apps, lambda a: presets_kitty if a == "kitty" else [("default", True)])
        # DOWN→app kitty; RIGHT→right; LEFT→back to left (app still kitty); RIGHT; DOWN; ENTER
        self.assertEqual(
            self._run_keys(sw, ["DOWN", "RIGHT", "LEFT", "RIGHT", "DOWN", "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_up_down_cycles_in_pane(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False), ("compact", False)])
        # RIGHT; UP (wrap to last = compact); ENTER
        self.assertEqual(self._run_keys(sw, ["RIGHT", "UP", "ENTER"]), ("kitty", "compact"))

    def test_app_switch_lands_cursor_on_active_preset(self):
        apps = ["fastfetch", "kitty"]
        presets_kitty = [("default", False), ("transparent", True)]  # transparent is active
        sw = PresetSwitcher(apps, lambda a: presets_kitty if a == "kitty" else [("default", True)])
        # DOWN→kitty (right pane auto-lands on 'transparent' active); ENTER applies it directly
        self.assertEqual(self._run_keys(sw, ["DOWN", "RIGHT", "ENTER"]), ("kitty", "transparent"))

    def test_cancel_returns_none(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        self.assertIsNone(self._run_keys(sw, ["q"]))

    def test_no_tty_returns_none(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        with patch("sys.stdin.isatty", return_value=False):
            self.assertIsNone(sw.run())


class TestPresetSwitcherMouse(unittest.TestCase):
    """Mouse interaction: left-click browses, right-click applies, wheel scrolls.

    Row geometry is fixed by the full-size logo (11 newlines) + title + blank +
    1 header row = first data row at terminal row 15. Tests pin the terminal
    size so the layout is deterministic.
    """

    def _run_keys(self, switcher, keys):
        import os
        import nyxniri.tui as tui
        # os.terminal_size is a tuple subclass with .columns/.lines — supports both
        # the `cols, lines = get_terminal_size(...)` unpacking and attribute access.
        fake_size = os.terminal_size((80, 24))
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.tui.read_key", side_effect=keys), \
             patch.object(tui.shutil, "get_terminal_size", return_value=fake_size), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def _click(self, col, row):
        from nyxniri.tui import MouseEvent
        return MouseEvent(kind="PRESS", col=col, row=row)

    def _wheel(self, kind, col=3, row=15):
        from nyxniri.tui import MouseEvent
        return MouseEvent(kind=kind, col=col, row=row)

    def test_right_click_applies_preset_immediately(self):
        # kitty is the focused app (row 1 of data = terminal row 15). Click its
        # 'default' preset in the right pane -> apply and return, no Enter needed.
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False)])
        # RIGHT to enter right pane is NOT required for click-to-apply: a click
        # in the right column applies directly.
        self.assertEqual(self._run_keys(sw, [self._click(40, 15)]), ("kitty", "default"))

    def test_right_click_second_preset_applies_it(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False)])
        # transparent is data row 1 = terminal row 16; right column is col 40.
        self.assertEqual(self._run_keys(sw, [self._click(40, 16)]), ("kitty", "transparent"))

    def test_left_click_browses_app_without_applying(self):
        # Two apps: fastfetch (row 15), kitty (row 16). Click kitty in the left
        # column -> browse (cursor moves to kitty) but does NOT apply; a follow-up
        # Enter applies kitty's active preset, proving the click only browsed.
        sw = PresetSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", True), ("transparent", False)] if a == "kitty" else [("default", True)],
        )
        self.assertEqual(
            self._run_keys(sw, [self._click(3, 16), "ENTER"]),
            ("kitty", "default"),
        )

    def test_left_click_does_not_steal_apply_from_right_column(self):
        # Clicking the left column must never apply. With focus on fastfetch,
        # a left click on fastfetch's row then Enter applies fastfetch/default
        # (not kitty) — proves left click only moved cursor within left pane.
        sw = PresetSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", True)] if a == "fastfetch" else [("transparent", True)],
        )
        self.assertEqual(
            self._run_keys(sw, [self._click(3, 15), "ENTER"]),
            ("fastfetch", "default"),
        )

    def test_wheel_down_on_left_cycles_app(self):
        sw = PresetSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", True)] if a == "fastfetch" else [("transparent", True)],
        )
        # wheel-down in left pane -> fastfetch to kitty; Enter applies kitty/transparent.
        self.assertEqual(
            self._run_keys(sw, [self._wheel("WHEEL_DOWN"), "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_wheel_up_on_left_cycles_backwards(self):
        sw = PresetSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", True)] if a == "fastfetch" else [("transparent", True)],
        )
        # DOWN to kitty first, then WHEEL_UP back to fastfetch, Enter -> fastfetch/default.
        self.assertEqual(
            self._run_keys(sw, ["DOWN", self._wheel("WHEEL_UP"), "ENTER"]),
            ("fastfetch", "default"),
        )

    def test_wheel_on_right_moves_preset_cursor(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False)])
        # RIGHT to right pane, WHEEL_DOWN to transparent, Enter applies it.
        self.assertEqual(
            self._run_keys(sw, ["RIGHT", self._wheel("WHEEL_DOWN", col=40), "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_click_on_header_row_is_ignored(self):
        # Row 13 = the blank line between title and header (no data). A click
        # there must not apply; follow-up Enter applies the focused default,
        # proving the click was ignored.
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        self.assertEqual(self._run_keys(sw, [self._click(40, 13), "ENTER"]), ("kitty", "default"))


class TestEditPreset(unittest.TestCase):
    """edit_preset: rejects default/official/missing; opens editor on a user preset."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_rejects_default(self):
        self.assertFalse(preset.edit_preset("kitty", "default"))

    def test_rejects_official(self):
        # 'transparent' is a shipped official preset — read-only.
        self.assertFalse(preset.edit_preset("kitty", "transparent"))

    def test_rejects_missing(self):
        self.assertFalse(preset.edit_preset("kitty", "ghost"))

    def test_non_tty_hints_path(self):
        target = self.env.presets_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            self.assertFalse(preset.edit_preset("kitty", "mine"))

    def test_opens_editor_on_user_preset(self):
        target = self.env.presets_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        (target / "kitty.conf").write_text("# mine")
        with patch("sys.stdin.isatty", return_value=True), \
             patch.dict("os.environ", {"EDITOR": "myed"}), \
             patch.object(preset.subprocess, "run") as mock_run:
            self.assertTrue(preset.edit_preset("kitty", "mine"))
        mock_run.assert_called_once_with(["myed", str(target)], check=False)


if __name__ == "__main__":
    unittest.main()
