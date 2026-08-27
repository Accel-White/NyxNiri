"""Contract tests for the preset mechanism (§3.2).

Covers §14 shapes: the four src-selection branches, dest-missing reset with
upstream-removed warning, state file read/write, and __custom__ preservation
across preset switches (regression guard for the copytree ignore change).
"""

import os
import shutil
import stat
import tempfile
import unittest
from contextlib import contextmanager
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
        state = preset.read_active_preset_state("kitty")
        self.assertIs(state.status, preset.ActivePresetStatus.MISSING)
        self.assertEqual(state.selected, "default")
        self.assertEqual(preset.read_active_preset("kitty"), "default")

    def test_write_then_read(self):
        preset.write_active_preset("kitty", "transparent")
        state = preset.read_active_preset_state("kitty")
        self.assertIs(state.status, preset.ActivePresetStatus.VALID)
        self.assertEqual(state.selected, "transparent")
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")

    def test_write_creates_presets_dir(self):
        # presets_dir does not exist initially; write must create it.
        self.assertFalse(self._ctx.env.presets_dir.exists())
        preset.write_active_preset("kitty", "compact")
        self.assertTrue(self._ctx.env.presets_dir.is_dir())

    def test_present_malformed_active_is_invalid(self):
        self._ctx.env.presets_dir.mkdir(parents=True, exist_ok=True)
        active = self._ctx.env.presets_dir / "kitty.active"

        for raw in (b"", b"   \n", b"\xff\xfe", b"../outside", b"default\n"):
            with self.subTest(raw=raw):
                active.write_bytes(raw)
                state = preset.read_active_preset_state("kitty")
                self.assertIs(state.status, preset.ActivePresetStatus.INVALID)
                self.assertIsNone(state.selected)
                with self.assertRaises(preset.InvalidActivePresetError) as caught:
                    preset.read_active_preset("kitty")
                self.assertEqual(str(caught.exception), "invalid active preset state")

    def test_predictable_legacy_temp_symlink_is_never_followed(self):
        self._ctx.env.presets_dir.mkdir(parents=True, exist_ok=True)
        outside = self._ctx.home / "outside-active"
        outside.write_text("keep")
        active = self._ctx.env.presets_dir / "kitty.active"
        legacy_tmp = active.with_suffix(f".{active.suffix}.tmp.{os.getpid()}")
        legacy_tmp.symlink_to(outside)

        preset.write_active_preset("kitty", "transparent")

        self.assertEqual(outside.read_text(), "keep")
        self.assertTrue(legacy_tmp.is_symlink())
        self.assertFalse(active.is_symlink())
        self.assertEqual(active.read_text(), "transparent")

    def test_active_temp_collision_symlink_is_skipped(self):
        self._ctx.env.presets_dir.mkdir(parents=True, exist_ok=True)
        outside = self._ctx.home / "outside-active"
        outside.write_text("keep")
        collision = ".active-tmp.collision"
        safe = ".active-tmp.safe"
        (self._ctx.env.presets_dir / collision).symlink_to(outside)

        with patch(
            "nyxniri.deploy.preset._random_leaf",
            side_effect=[collision, safe],
        ):
            preset.write_active_preset("kitty", "transparent")

        self.assertEqual(outside.read_text(), "keep")
        self.assertTrue((self._ctx.env.presets_dir / collision).is_symlink())
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")


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

    def test_verified_active_publish_with_dir_fsync_failure_reports_success(self):
        real_fsync = os.fsync
        failed = False

        def fail_presets_dir(fd):
            nonlocal failed
            current = os.fstat(fd)
            presets = os.stat(self.env.presets_dir)
            if (current.st_dev, current.st_ino) == (presets.st_dev, presets.st_ino):
                failed = True
                raise OSError("injected directory fsync failure")
            return real_fsync(fd)

        with patch("nyxniri.deploy.preset.os.fsync", side_effect=fail_presets_dir), \
             patch("sys.stdout", new_callable=StringIO) as output:
            ok = preset.apply_preset("kitty", "transparent")

        self.assertTrue(failed)
        self.assertTrue(ok)
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")
        self.assertIn("could not confirm the active state was persisted", output.getvalue())

    def test_apply_then_write_timing_atomic_fail_leaves_active(self):
        # B2 (§14): if atomic_replace fails, active must NOT be written.
        preset.write_active_preset("kitty", "default")
        with patch(
            "nyxniri.deploy.atomic.atomic_replace_item_transaction",
            side_effect=OSError("injected publish failure"),
        ):
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

    def test_save_succeeds_when_old_backup_cleanup_fails(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("new")
        old = self.env.presets_dir / "kitty" / "mine"
        old.mkdir(parents=True)
        (old / "kitty.conf").write_text("old")
        real_remove = preset._remove_entry_at

        def retain_backup(parent_fd, name):
            if name.startswith(".preset-old."):
                raise OSError("injected cleanup failure")
            return real_remove(parent_fd, name)

        with patch.object(preset, "_remove_entry_at", side_effect=retain_backup):
            self.assertTrue(preset.save_preset("kitty", "mine"))

        self.assertEqual((old / "kitty.conf").read_text(), "new")
        backups = list(old.parent.glob(".preset-old.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "kitty.conf").read_text(), "old")

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


class TestPresetPathBoundary(unittest.TestCase):
    """Preset identifiers stay inside their app-owned filesystem roots."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.env.configs_src = self._ctx.home / "repo-configs"
        self.app_root = self.env.configs_src / "kitty"
        self.app_root.mkdir(parents=True)
        (self.app_root / "kitty.conf").write_text("# default")
        official = self.app_root / "presets" / "transparent"
        official.mkdir(parents=True)
        (official / "kitty.conf").write_text("# transparent")

        self.dest = self.env.config_dir / "kitty"
        self.dest.mkdir(parents=True)
        (self.dest / "kitty.conf").write_text("# current")
        self.user_root = self.env.presets_dir / "kitty"
        self.user_root.mkdir(parents=True)

    def tearDown(self):
        self._ctx.__exit__()

    def _outside_dir(self, name="outside"):
        outside = self._ctx.home / name
        outside.mkdir()
        (outside / "sentinel").write_text("keep")
        return outside

    def test_component_policy_preserves_safe_unicode_names(self):
        for name in (
            "my-nord.v2",
            ".hidden",
            "中文 主题",
            "主题\u00a0浅色",
            "主题\u2009浅色",
            "主题\u3000浅色",
            "字\u200d形",
        ):
            with self.subTest(name=name):
                self.assertTrue(preset._is_safe_component(name))
                self.assertTrue(preset.save_preset("kitty", name))
                self.assertTrue((self.user_root / name / "kitty.conf").is_file())

        for name in ("", ".", "..", "../outside", "/tmp/outside", " edge", "edge ", "bad\nname", "bad\0name"):
            with self.subTest(name=name):
                self.assertFalse(preset._is_safe_component(name))

    def test_save_and_delete_reject_traversal_before_touching_outside(self):
        for operation in (preset.save_preset, preset.delete_preset):
            for name in ("../../outside", str(self._ctx.home / "outside")):
                with self.subTest(operation=operation.__name__, name=name):
                    outside = self._ctx.home / "outside"
                    outside.mkdir(exist_ok=True)
                    sentinel = outside / "sentinel"
                    sentinel.write_text("keep")

                    self.assertFalse(operation("kitty", name))
                    self.assertEqual(sentinel.read_text(), "keep")

    def test_apply_rejects_app_and_name_escape_before_atomic_replace(self):
        invalid_apps = ("", ".", "..", "../kitty", str(self._ctx.home), "missing")
        invalid_names = ("../../outside", str(self._ctx.home / "outside"), "bad\nname")

        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic:
            for app in invalid_apps:
                with self.subTest(app=app):
                    self.assertFalse(preset.apply_preset(app, "default"))
            for name in invalid_names:
                with self.subTest(name=name):
                    self.assertFalse(preset.apply_preset("kitty", name))
        atomic.assert_not_called()

    def test_edit_rejects_escape_without_starting_editor(self):
        outside = self._outside_dir()
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.deploy.preset.subprocess.run") as run:
            self.assertFalse(preset.edit_preset("kitty", "../../outside"))
            self.assertFalse(preset.edit_preset("kitty", str(outside)))
        run.assert_not_called()
        self.assertEqual((outside / "sentinel").read_text(), "keep")

    def test_active_app_escape_is_rejected_before_write(self):
        escaped = self.env.config_dir / "escaped.active"
        preset.write_active_preset("kitty", "default")

        with self.assertRaises(ValueError):
            preset.write_active_preset("../../escaped", "chosen")
        with self.assertRaises(ValueError):
            preset.write_active_preset("kitty", "../chosen")

        self.assertFalse(escaped.exists())
        self.assertEqual(preset.read_active_preset("kitty"), "default")

    def test_invalid_active_freezes_deploy_without_echoing_value(self):
        active = self.env.presets_dir / "kitty.active"
        active.write_text("../../outside\n")

        state = preset.read_active_preset_state("kitty")
        result = preset.resolve_preset_src("kitty", state, self.dest)

        self.assertIs(state.status, preset.ActivePresetStatus.INVALID)
        self.assertIsNone(result.src)
        self.assertIsNone(result.reset_active)
        self.assertTrue(result.warnings)
        self.assertNotIn("../../outside", "".join(result.warnings))
        with patch("nyxniri.deploy.deploy.atomic_replace_item") as atomic, \
             patch("nyxniri.deploy.deploy.log_msg") as log:
            from nyxniri.deploy.deploy import _phase_atomic_deployment
            self.assertEqual(_phase_atomic_deployment(["kitty"]), ["kitty"])
        atomic.assert_not_called()
        self.assertNotIn("../../outside", "".join(str(call) for call in log.call_args_list))

    def test_blank_and_invalid_utf8_active_never_deploy_default(self):
        active = self.env.presets_dir / "kitty.active"
        sentinel = self.dest / "sentinel"
        sentinel.write_text("keep")

        for raw in (b"   \n", b"\xff\xfe"):
            with self.subTest(raw=raw), \
                 patch("nyxniri.deploy.deploy.atomic_replace_item") as atomic:
                active.write_bytes(raw)
                from nyxniri.deploy.deploy import _phase_atomic_deployment
                self.assertEqual(_phase_atomic_deployment(["kitty"]), ["kitty"])
                atomic.assert_not_called()
                self.assertEqual(sentinel.read_text(), "keep")

    def test_invalid_niri_active_does_not_create_effects_symlink(self):
        niri_src = self.env.configs_src / "niri"
        niri_src.mkdir()
        (niri_src / "config.kdl").write_text("default")
        niri_dest = self.env.config_dir / "niri"
        niri_dest.mkdir()
        (niri_dest / "effects_normal.kdl").write_text("normal")
        (self.env.presets_dir / "niri.active").write_bytes(b"\xff\xfe")

        from nyxniri.deploy.deploy import _phase_atomic_deployment

        self.assertEqual(_phase_atomic_deployment(["niri"]), ["niri"])
        self.assertFalse((niri_dest / "effects.kdl").exists())

    def test_active_symlink_escape_is_rejected_before_read_or_write(self):
        outside = self._ctx.home / "outside-active"
        outside.write_text("keep")
        active = self.env.presets_dir / "kitty.active"
        active.symlink_to(outside)

        state = preset.read_active_preset_state("kitty")
        self.assertIs(state.status, preset.ActivePresetStatus.INVALID)
        with self.assertRaises(preset.InvalidActivePresetError):
            preset.read_active_preset("kitty")
        with self.assertRaises((OSError, ValueError)):
            preset.write_active_preset("kitty", "transparent")

        self.assertEqual(outside.read_text(), "keep")

    def test_apply_repairs_malformed_regular_active_file(self):
        active = self.env.presets_dir / "kitty.active"
        active.write_bytes(b"\xff\xfe")

        self.assertTrue(preset.apply_preset("kitty", "transparent"))

        self.assertEqual(preset.read_active_preset("kitty"), "transparent")
        self.assertEqual((self.dest / "kitty.conf").read_text(), "# transparent")

    def test_directory_active_slot_is_rejected_before_deploy(self):
        active = self.env.presets_dir / "kitty.active"
        active.mkdir()

        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic:
            self.assertFalse(preset.apply_preset("kitty", "transparent"))

        atomic.assert_not_called()
        self.assertEqual((self.dest / "kitty.conf").read_text(), "# current")

    def test_active_fifo_is_invalid_and_rejected(self):
        active = self.env.presets_dir / "kitty.active"
        os.mkfifo(active)

        state = preset.read_active_preset_state("kitty")
        self.assertIs(state.status, preset.ActivePresetStatus.INVALID)
        with self.assertRaises(OSError):
            preset.write_active_preset("kitty", "transparent")
        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic:
            self.assertFalse(preset.apply_preset("kitty", "transparent"))

        atomic.assert_not_called()
        self.assertTrue(stat.S_ISFIFO(active.lstat().st_mode))

    def test_presets_root_symlink_rejects_every_preset_sink(self):
        shutil.rmtree(self.env.presets_dir)
        outside = self._ctx.home / "outside-presets"
        outside_preset = outside / "kitty" / "mine"
        outside_preset.mkdir(parents=True)
        sentinel = outside_preset / "sentinel"
        sentinel.write_text("keep")
        self.env.presets_dir.symlink_to(outside, target_is_directory=True)

        state = preset.read_active_preset_state("kitty")
        self.assertIs(state.status, preset.ActivePresetStatus.INVALID)
        with self.assertRaises(OSError):
            preset.write_active_preset("kitty", "transparent")
        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic, \
             patch("nyxniri.deploy.preset.shutil.copytree") as copytree, \
             patch("nyxniri.deploy.preset.subprocess.run") as run:
            self.assertFalse(preset.apply_preset("kitty", "default"))
            self.assertFalse(preset.save_preset("kitty", "mine"))
            self.assertFalse(preset.delete_preset("kitty", "mine"))
            self.assertFalse(preset.edit_preset("kitty", "mine"))

        atomic.assert_not_called()
        copytree.assert_not_called()
        run.assert_not_called()
        self.assertIsNone(preset.list_presets("kitty"))
        self.assertEqual(sentinel.read_text(), "keep")

    def test_official_preset_ignores_unsafe_user_shadow(self):
        outside = self._outside_dir("outside-shadow")
        (self.user_root / "transparent").symlink_to(
            outside,
            target_is_directory=True,
        )
        preset.write_active_preset("kitty", "transparent")

        from nyxniri.deploy.deploy import _phase_atomic_deployment

        self.assertEqual(_phase_atomic_deployment(["kitty"]), [])
        self.assertEqual((self.dest / "kitty.conf").read_text(), "# transparent")
        self.assertEqual((outside / "sentinel").read_text(), "keep")

    def test_non_directory_user_preset_root_fails_closed(self):
        self.user_root.rmdir()
        self.user_root.write_text("not a directory")

        self.assertEqual(preset.collect_presets("kitty"), [])
        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic:
            self.assertFalse(preset.apply_preset("kitty", "default"))
            self.assertFalse(preset.save_preset("kitty", "mine"))
        atomic.assert_not_called()

    def test_nyx_root_symlink_rejects_every_preset_sink(self):
        shutil.rmtree(self.env.nyx_dir)
        outside = self._ctx.home / "outside-nyx"
        outside_preset = outside / "presets" / "kitty" / "mine"
        outside_preset.mkdir(parents=True)
        sentinel = outside_preset / "sentinel"
        sentinel.write_text("keep")
        self.env.nyx_dir.symlink_to(outside, target_is_directory=True)

        state = preset.read_active_preset_state("kitty")
        self.assertIs(state.status, preset.ActivePresetStatus.INVALID)
        with self.assertRaises((OSError, ValueError)):
            preset.write_active_preset("kitty", "transparent")

        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic, \
             patch("nyxniri.deploy.preset.shutil.copytree") as copytree, \
             patch("nyxniri.deploy.preset.subprocess.run") as run:
            self.assertFalse(preset.apply_preset("kitty", "default"))
            self.assertFalse(preset.save_preset("kitty", "mine"))
            self.assertFalse(preset.delete_preset("kitty", "mine"))
            self.assertFalse(preset.edit_preset("kitty", "mine"))
        atomic.assert_not_called()
        copytree.assert_not_called()
        run.assert_not_called()
        self.assertIsNone(preset.list_presets("kitty"))
        self.assertEqual(sentinel.read_text(), "keep")

    def test_apply_binds_user_source_before_parent_is_swapped(self):
        mine = self.user_root / "mine"
        mine.mkdir()
        (mine / "kitty.conf").write_text("safe")
        outside_user = self._outside_dir("outside-user")
        outside_mine = outside_user / "mine"
        outside_mine.mkdir()
        (outside_mine / "kitty.conf").write_text("outside")
        stash = self.env.presets_dir / "kitty-stash"
        swapped = False

        from nyxniri.deploy.atomic import atomic_replace_item_transaction

        def swap_then_apply(*args, **kwargs):
            nonlocal swapped
            self.user_root.rename(stash)
            self.user_root.symlink_to(outside_user, target_is_directory=True)
            swapped = True
            return atomic_replace_item_transaction(*args, **kwargs)

        with patch(
            "nyxniri.deploy.atomic.atomic_replace_item_transaction",
            side_effect=swap_then_apply,
        ):
            self.assertTrue(preset.apply_preset("kitty", "mine"))

        self.assertTrue(swapped)
        self.assertEqual((self.dest / "kitty.conf").read_text(), "safe")
        self.assertEqual((outside_user / "sentinel").read_text(), "keep")

    def test_full_deploy_binds_user_source_before_parent_is_swapped(self):
        mine = self.user_root / "mine"
        mine.mkdir()
        (mine / "kitty.conf").write_text("safe")
        preset.write_active_preset("kitty", "mine")
        outside_user = self._outside_dir("outside-user")
        outside_mine = outside_user / "mine"
        outside_mine.mkdir()
        (outside_mine / "kitty.conf").write_text("outside")
        stash = self.env.presets_dir / "kitty-stash"
        swapped = False

        from nyxniri.deploy.atomic import atomic_replace_item_transaction

        def swap_then_deploy(*args, **kwargs):
            nonlocal swapped
            self.user_root.rename(stash)
            self.user_root.symlink_to(outside_user, target_is_directory=True)
            swapped = True
            return atomic_replace_item_transaction(*args, **kwargs)

        with patch(
            "nyxniri.deploy.deploy.atomic_replace_item_transaction",
            side_effect=swap_then_deploy,
        ):
            from nyxniri.deploy.deploy import _phase_atomic_deployment
            self.assertEqual(_phase_atomic_deployment(["kitty"]), [])

        self.assertTrue(swapped)
        self.assertEqual((self.dest / "kitty.conf").read_text(), "safe")
        self.assertEqual((outside_user / "sentinel").read_text(), "keep")

    def test_apply_keeps_bound_config_root_after_parent_swap(self):
        config_root = self.env.config_dir
        stash = self._ctx.home / "config-stash"
        outside = self._outside_dir("outside-config")
        swapped = False

        from nyxniri.deploy.atomic import atomic_replace_item_transaction

        def swap_then_deploy(*args, **kwargs):
            nonlocal swapped
            config_root.rename(stash)
            config_root.symlink_to(outside, target_is_directory=True)
            swapped = True
            return atomic_replace_item_transaction(*args, **kwargs)

        with patch(
            "nyxniri.deploy.atomic.atomic_replace_item_transaction",
            side_effect=swap_then_deploy,
        ):
            self.assertTrue(preset.apply_preset("kitty", "transparent"))

        self.assertTrue(swapped)
        self.assertEqual((stash / "kitty" / "kitty.conf").read_text(), "# transparent")
        self.assertEqual((outside / "sentinel").read_text(), "keep")
        self.assertFalse((outside / "kitty").exists())

    def test_apply_uses_one_config_root_across_nested_contexts(self):
        config_root = self.env.config_dir
        stash = self._ctx.home / "config-stash"
        outside = self._outside_dir("outside-config")
        real_open = preset._opened_presets_dir_at
        swapped = False

        @contextmanager
        def swap_then_open(config_fd, *, create=False):
            nonlocal swapped
            config_root.rename(stash)
            config_root.symlink_to(outside, target_is_directory=True)
            swapped = True
            with real_open(config_fd, create=create) as presets_fd:
                yield presets_fd

        with patch(
            "nyxniri.deploy.preset._opened_presets_dir_at",
            side_effect=swap_then_open,
        ):
            self.assertTrue(preset.apply_preset("kitty", "transparent"))

        self.assertTrue(swapped)
        self.assertEqual((stash / "kitty" / "kitty.conf").read_text(), "# transparent")
        self.assertEqual((outside / "sentinel").read_text(), "keep")
        self.assertFalse((outside / "kitty").exists())

    def test_template_render_uses_bound_published_app(self):
        niri_src = self.env.configs_src / "niri"
        niri_src.mkdir()
        (niri_src / "config.kdl").write_text("spawn /home/user/tool")
        niri_dest = self.env.config_dir / "niri"
        niri_dest.mkdir()
        (niri_dest / "config.kdl").write_text("old")
        outside = self._outside_dir("outside-niri")
        (outside / "config.kdl").write_text("outside")
        stash = self.env.config_dir / "niri-stash"
        from nyxniri.deploy.templates import _phase_render_templates as real_render
        swapped = False

        def swap_then_render(*args, **kwargs):
            nonlocal swapped
            niri_dest.rename(stash)
            niri_dest.symlink_to(outside, target_is_directory=True)
            swapped = True
            try:
                return real_render(*args, **kwargs)
            finally:
                niri_dest.unlink()
                stash.rename(niri_dest)

        with patch(
            "nyxniri.deploy.templates._phase_render_templates",
            side_effect=swap_then_render,
        ):
            self.assertTrue(preset.apply_preset("niri", "default"))

        self.assertTrue(swapped)
        self.assertIn(str(self.env.home), (niri_dest / "config.kdl").read_text())
        self.assertEqual((outside / "config.kdl").read_text(), "outside")

    def test_save_cancels_if_bound_user_parent_is_swapped(self):
        outside_user = self._outside_dir("outside-user")
        outside_mine = outside_user / "mine"
        outside_mine.mkdir()
        sentinel = outside_mine / "sentinel"
        sentinel.write_text("keep")
        stash = self.env.presets_dir / "kitty-stash"
        real_copytree = shutil.copytree
        swapped = False

        def swap_then_copy(*args, **kwargs):
            nonlocal swapped
            self.user_root.rename(stash)
            self.user_root.symlink_to(outside_user, target_is_directory=True)
            swapped = True
            return real_copytree(*args, **kwargs)

        with patch("nyxniri.deploy.preset.shutil.copytree", side_effect=swap_then_copy):
            self.assertFalse(preset.save_preset("kitty", "mine"))

        self.assertTrue(swapped)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_save_cancels_if_config_root_is_swapped_after_binding(self):
        config_root = self.env.config_dir
        stash = self._ctx.home / "config-stash"
        outside = self._outside_dir("outside-config")
        real_copytree = shutil.copytree
        swapped = False

        def swap_then_copy(*args, **kwargs):
            nonlocal swapped
            config_root.rename(stash)
            config_root.symlink_to(outside, target_is_directory=True)
            swapped = True
            return real_copytree(*args, **kwargs)

        with patch("nyxniri.deploy.preset.shutil.copytree", side_effect=swap_then_copy):
            self.assertFalse(preset.save_preset("kitty", "mine"))

        self.assertTrue(swapped)
        self.assertEqual((outside / "sentinel").read_text(), "keep")
        self.assertFalse((outside / "NyxNiri").exists())

    def test_file_app_random_stage_skips_symlink_collision(self):
        file_src = self.env.configs_src / "starship.toml"
        file_src.write_text("safe")
        outside = self._ctx.home / "outside-file"
        outside.write_text("keep")
        collision = self.env.config_dir / ".starship.toml.new.collision"
        safe_stage = self.env.config_dir / ".starship.toml.new.safe"
        collision.symlink_to(outside)

        with patch(
            "nyxniri.deploy.atomic._random_sibling",
            side_effect=[collision, safe_stage],
        ):
            self.assertTrue(preset.apply_preset("starship.toml", "default"))

        self.assertEqual(outside.read_text(), "keep")
        self.assertTrue(collision.is_symlink())
        self.assertEqual((self.env.config_dir / "starship.toml").read_text(), "safe")

    def test_delete_cancels_if_bound_user_parent_is_swapped(self):
        mine = self.user_root / "mine"
        mine.mkdir()
        (mine / "sentinel").write_text("original")
        outside_user = self._outside_dir("outside-user")
        outside_mine = outside_user / "mine"
        outside_mine.mkdir()
        outside_sentinel = outside_mine / "sentinel"
        outside_sentinel.write_text("keep")
        stash = self.env.presets_dir / "kitty-stash"
        real_remove = preset._remove_tree_at
        swapped = False

        def swap_then_remove(parent_fd, name, *, parent_path=None):
            nonlocal swapped
            self.user_root.rename(stash)
            self.user_root.symlink_to(outside_user, target_is_directory=True)
            swapped = True
            return real_remove(parent_fd, name, parent_path=parent_path)

        with patch("nyxniri.deploy.preset._remove_tree_at", side_effect=swap_then_remove):
            self.assertFalse(preset.delete_preset("kitty", "mine"))

        self.assertTrue(swapped)
        self.assertEqual(outside_sentinel.read_text(), "keep")
        self.assertEqual((stash / "mine" / "sentinel").read_text(), "original")

    def test_reset_write_failure_stops_before_default_deploy(self):
        preset.write_active_preset("kitty", "transparent")
        shutil.rmtree(self.dest)

        with patch("nyxniri.deploy.deploy._write_active_at", side_effect=OSError("full")), \
             patch("nyxniri.deploy.deploy.atomic_replace_item") as atomic:
            from nyxniri.deploy.deploy import _phase_atomic_deployment
            failed = _phase_atomic_deployment(["kitty"])

        self.assertEqual(failed, ["kitty"])
        atomic.assert_not_called()
        self.assertFalse(self.dest.exists())
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")

    def test_user_preset_symlink_escape_is_not_listed_or_operable(self):
        outside = self._outside_dir()
        escaped = self.user_root / "escaped"
        escaped.symlink_to(outside, target_is_directory=True)

        self.assertNotIn("escaped", [name for name, _, _ in preset.collect_presets("kitty")])
        info = preset.get_preset_info("kitty", "escaped")
        self.assertFalse(info.is_editable)
        self.assertEqual(info.files, [])
        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic, \
             patch("nyxniri.deploy.preset.subprocess.run") as run:
            self.assertFalse(preset.apply_preset("kitty", "escaped"))
            self.assertFalse(preset.delete_preset("kitty", "escaped"))
            self.assertFalse(preset.edit_preset("kitty", "escaped"))
        atomic.assert_not_called()
        run.assert_not_called()
        self.assertEqual((outside / "sentinel").read_text(), "keep")

    def test_user_app_symlink_escape_rejects_all_operations(self):
        self.user_root.rmdir()
        outside = self._outside_dir()
        self.user_root.symlink_to(outside, target_is_directory=True)

        self.assertEqual(preset.collect_presets("kitty"), [])
        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic, \
             patch("nyxniri.deploy.preset.subprocess.run") as run:
            self.assertFalse(preset.apply_preset("kitty", "default"))
            self.assertFalse(preset.save_preset("kitty", "mine"))
            self.assertFalse(preset.delete_preset("kitty", "mine"))
            self.assertFalse(preset.edit_preset("kitty", "mine"))
        atomic.assert_not_called()
        run.assert_not_called()
        self.assertEqual((outside / "sentinel").read_text(), "keep")

    def test_app_source_and_destination_symlinks_are_rejected(self):
        outside_source = self._outside_dir("outside-source")
        (outside_source / "config").write_text("outside")
        linked_source = self.env.configs_src / "linked"
        linked_source.symlink_to(outside_source, target_is_directory=True)

        with patch("nyxniri.deploy.atomic.atomic_replace_item") as atomic:
            self.assertFalse(preset.apply_preset("linked", "default"))

            import shutil
            shutil.rmtree(self.dest)
            outside_dest = self._outside_dir("outside-dest")
            self.dest.symlink_to(outside_dest, target_is_directory=True)
            self.assertFalse(preset.apply_preset("kitty", "default"))
        atomic.assert_not_called()
        self.assertEqual((outside_dest / "sentinel").read_text(), "keep")


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
    """Preset Switcher interactive tests via a mocked key stream."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _run_keys(self, switcher, keys):
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.tui.read_key", side_effect=keys), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def test_enter_returns_app_and_preset(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False)])
        # RIGHT → expand kitty & land on default; DOWN → transparent; ENTER
        self.assertEqual(self._run_keys(sw, ["RIGHT", "DOWN", "ENTER"]), ("kitty", "transparent"))

    def test_pane_switch_keeps_app_cursor(self):
        apps = ["fastfetch", "kitty"]
        presets_kitty = [("default", True), ("transparent", False)]
        sw = PresetSwitcher(apps, lambda a: presets_kitty if a == "kitty" else [("default", True)])
        # DOWN→app kitty; RIGHT→expand; LEFT→back to app kitty; RIGHT→focus presets; DOWN; ENTER
        self.assertEqual(
            self._run_keys(sw, ["DOWN", "RIGHT", "LEFT", "RIGHT", "DOWN", "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_up_down_cycles_in_pane(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False), ("compact", False)])
        # RIGHT; DOWN; DOWN; ENTER
        self.assertEqual(self._run_keys(sw, ["RIGHT", "DOWN", "DOWN", "ENTER"]), ("kitty", "compact"))

    def test_app_switch_lands_cursor_on_active_preset(self):
        apps = ["fastfetch", "kitty"]
        presets_kitty = [("default", False), ("transparent", True)]  # transparent is active
        sw = PresetSwitcher(apps, lambda a: presets_kitty if a == "kitty" else [("default", True)])
        # DOWN→kitty; RIGHT→expand kitty; ENTER applies active transparent directly
        self.assertEqual(self._run_keys(sw, ["DOWN", "RIGHT", "ENTER"]), ("kitty", "transparent"))

    def test_cancel_returns_none(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        self.assertIsNone(self._run_keys(sw, ["q"]))

    def test_no_tty_returns_none(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        with patch("sys.stdin.isatty", return_value=False):
            self.assertIsNone(sw.run())

    def test_invalid_state_is_not_displayed_as_default(self):
        from nyxniri.i18n import msg

        sw = PresetSwitcher(
            ["kitty"],
            lambda _app: [("default", "official", False)],
            on_action=lambda *_args: None,
            active_for=lambda _app: None,
        )
        output = StringIO()
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.tui.read_key", side_effect=["ENTER", "q"]), \
             patch("sys.stdout", output):
            self.assertIsNone(sw.run())
        self.assertIn(msg("preset_status_invalid"), output.getvalue())


class TestPresetSwitcherMouse(unittest.TestCase):
    """Mouse interaction: click selects/expands, wheel scrolls."""

    def _run_keys(self, switcher, keys):
        import os
        import nyxniri.tui as tui
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

    def test_click_app_applies_active_preset_in_standalone_mode(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False)])
        # Click kitty at row 15 -> returns ("kitty", "default")
        self.assertEqual(self._run_keys(sw, [self._click(10, 14)]), ("kitty", "default"))

    def test_wheel_down_cycles_app(self):
        sw = PresetSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", True)] if a == "fastfetch" else [("transparent", True)],
        )
        # wheel-down -> fastfetch to kitty; Enter applies kitty/transparent.
        self.assertEqual(
            self._run_keys(sw, [self._wheel("WHEEL_DOWN"), "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_wheel_up_cycles_backwards(self):
        sw = PresetSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", True)] if a == "fastfetch" else [("transparent", True)],
        )
        # DOWN to kitty first, then WHEEL_UP back to fastfetch, Enter -> fastfetch/default.
        self.assertEqual(
            self._run_keys(sw, ["DOWN", self._wheel("WHEEL_UP"), "ENTER"]),
            ("fastfetch", "default"),
        )

    def test_click_on_header_row_is_ignored(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        self.assertEqual(self._run_keys(sw, [self._click(40, 12), "ENTER"]), ("kitty", "default"))


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
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][0], "myed")
        self.assertTrue(args[0][1].startswith("/proc/self/fd/"))
        self.assertFalse(kwargs["check"])
        self.assertEqual(len(kwargs["pass_fds"]), 1)


class TestPresetStudioInspection(unittest.TestCase):
    """Tests for preset metadata inspection (get_preset_info)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_default_preset_info(self):
        info = preset.get_preset_info("kitty", "default")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "default")
        self.assertEqual(info.source, "official")
        self.assertFalse(info.is_editable)
        self.assertFalse(info.is_deletable)
        self.assertEqual(info.path, "configs/kitty")

    def test_official_preset_info(self):
        info = preset.get_preset_info("kitty", "transparent")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "transparent")
        self.assertEqual(info.source, "official")
        self.assertFalse(info.is_editable)
        self.assertFalse(info.is_deletable)
        self.assertEqual(info.path, "configs/kitty/presets/transparent")

    def test_user_preset_info(self):
        user_dir = self.env.presets_dir / "kitty" / "my-nord"
        user_dir.mkdir(parents=True)
        (user_dir / "kitty.conf").write_text("# my theme")

        info = preset.get_preset_info("kitty", "my-nord")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "my-nord")
        self.assertEqual(info.source, "user")
        self.assertTrue(info.is_editable)
        self.assertTrue(info.is_deletable)
        self.assertIn("kitty.conf", info.files)


class TestPresetStudioActions(unittest.TestCase):
    """Tests for Preset Studio interactive actions via on_action callback."""

    def _run_keys(self, switcher, keys):
        fake_size = os.terminal_size((80, 24))
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.tui.read_key", side_effect=keys), \
             patch("shutil.get_terminal_size", return_value=fake_size), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def test_apply_action_triggered(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Applied {name}"

        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("default", "official", True), ("transparent", "official", False)],
            on_action=on_action,
        )
        # RIGHT -> move to presets, DOWN -> transparent, ENTER -> apply, q -> quit
        self._run_keys(sw, ["RIGHT", "DOWN", "ENTER", "q"])
        self.assertEqual(actions, [("apply", "kitty", "transparent")])

    def test_save_action_triggered(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Saved {name}"

        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("default", "official", True)],
            on_action=on_action,
        )
        # 's' triggers save prompt -> type 'm', 'i', 'n', 'e', ENTER -> q to quit
        self._run_keys(sw, ["s", "m", "i", "n", "e", "ENTER", "q"])
        self.assertEqual(actions, [("save", "kitty", "mine")])

    def test_delete_action_with_confirmation(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Deleted {name}"

        info_map = {
            ("kitty", "my-nord"): preset.PresetInfo(
                app="kitty", name="my-nord", source="user", is_active=False,
                path="~/.config/NyxNiri/presets/kitty/my-nord", files=[], preserve=[],
                is_editable=True, is_deletable=True
            )
        }

        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("my-nord", "user", False)],
            info_for=lambda a, n: info_map.get((a, n)),
            on_action=on_action,
        )
        # RIGHT -> presets, 'd' -> delete, 'y' -> confirm, 'q' -> quit
        self._run_keys(sw, ["RIGHT", "d", "y", "q"])
        self.assertEqual(actions, [("delete", "kitty", "my-nord")])

    def test_delete_action_cancelled(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Deleted {name}"

        info_map = {
            ("kitty", "my-nord"): preset.PresetInfo(
                app="kitty", name="my-nord", source="user", is_active=False,
                path="~/.config/NyxNiri/presets/kitty/my-nord", files=[], preserve=[],
                is_editable=True, is_deletable=True
            )
        }

        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("my-nord", "user", False)],
            info_for=lambda a, n: info_map.get((a, n)),
            on_action=on_action,
        )
        # RIGHT -> presets, 'd' -> delete, 'n' -> cancel, 'q' -> quit
        self._run_keys(sw, ["RIGHT", "d", "n", "q"])
        self.assertEqual(actions, [])

    def test_tab_toggles_details(self):
        info_map = {
            ("kitty", "default"): preset.PresetInfo(
                app="kitty", name="default", source="official", is_active=True,
                path="configs/kitty", files=["kitty.conf"], preserve=["monitor.kdl"],
                is_editable=False, is_deletable=False
            )
        }
        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("default", "official", True)],
            info_for=lambda a, n: info_map.get((a, n)),
        )
        # TAB expands, TAB collapses, q quits cleanly
        result = self._run_keys(sw, ["TAB", "TAB", "q"])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
