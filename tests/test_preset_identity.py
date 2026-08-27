"""Identity checks for preset trust roots and active state slots."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import nyxniri.deploy.preset as preset
from nyxniri.deploy.manifest import load_manifest_at
from nyxniri.tui import PresetSwitcher
from tests.utils import TempEnv


class TestBoundTrustRoot(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.base = self._ctx.home / "root-race"
        self.base.mkdir()

    def tearDown(self):
        self._ctx.__exit__()

    def test_resolve_then_parent_symlink_swap_is_rejected(self):
        parent = self.base / "parent"
        root = parent / "config"
        root.mkdir(parents=True)
        outside_parent = self.base / "outside"
        outside_root = outside_parent / "config"
        outside_root.mkdir(parents=True)
        stash = self.base / "parent-stash"
        real_resolve = Path.resolve
        swapped = False

        def resolve_then_swap(path, *args, **kwargs):
            nonlocal swapped
            result = real_resolve(path, *args, **kwargs)
            if path == root and not swapped:
                parent.rename(stash)
                parent.symlink_to(outside_parent, target_is_directory=True)
                swapped = True
            return result

        with patch.object(Path, "resolve", resolve_then_swap):
            with self.assertRaises(OSError):
                with preset._opened_root(root):
                    self.fail("swapped trust root must not be opened")

        self.assertTrue(swapped)
        self.assertTrue(outside_root.is_dir())

    def test_stable_root_symlink_resolves_to_its_target(self):
        target = self.base / "target"
        target.mkdir()
        linked = self.base / "linked"
        linked.symlink_to(target, target_is_directory=True)

        with preset._opened_root(linked) as fd:
            self.assertEqual(os.fstat(fd).st_ino, target.stat().st_ino)


class TestActiveSlotIdentity(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.env.configs_src = self._ctx.home / "repo-configs"
        app = self.env.configs_src / "kitty"
        app.mkdir(parents=True)
        (app / "kitty.conf").write_text("default")

    def tearDown(self):
        self._ctx.__exit__()

    def test_active_snapshot_detects_replacement_and_creation(self):
        with preset._opened_presets_dir(create=True) as presets_fd:
            missing = preset._read_active_at(presets_fd, "kitty")
            self.assertTrue(
                preset._active_state_unchanged_at(presets_fd, "kitty", missing)
            )
            preset._write_active_at(presets_fd, "kitty", "transparent")
            self.assertFalse(
                preset._active_state_unchanged_at(presets_fd, "kitty", missing)
            )

            selected = preset._read_active_at(presets_fd, "kitty")
            self.assertTrue(
                preset._active_state_unchanged_at(presets_fd, "kitty", selected)
            )
            preset._write_active_at(presets_fd, "kitty", "mine")
            self.assertFalse(
                preset._active_state_unchanged_at(presets_fd, "kitty", selected)
            )

    def test_active_temp_inode_swap_is_rejected_without_touching_target(self):
        preset.write_active_preset("kitty", "default")
        outside = self._ctx.home / "outside-active"
        outside.write_text("keep")
        real_stat = os.stat
        swapped = False

        def swap_before_stat(path, *args, **kwargs):
            nonlocal swapped
            dir_fd = kwargs.get("dir_fd")
            if (
                not swapped
                and dir_fd is not None
                and isinstance(path, str)
                and path.startswith(".active-tmp.")
            ):
                os.unlink(path, dir_fd=dir_fd)
                os.symlink(outside, path, dir_fd=dir_fd)
                swapped = True
            return real_stat(path, *args, **kwargs)

        with patch("nyxniri.deploy.preset.os.stat", side_effect=swap_before_stat):
            with self.assertRaises(OSError):
                preset.write_active_preset("kitty", "mine")

        self.assertTrue(swapped)
        self.assertEqual(outside.read_text(), "keep")
        self.assertEqual(preset.read_active_preset("kitty"), "default")


class TestPresetSwitcherCompatibility(unittest.TestCase):
    def test_existing_positional_title_and_hint_arguments_keep_their_slots(self):
        switcher = PresetSwitcher(
            ["kitty"],
            lambda _app: [],
            None,
            None,
            "custom_title",
            "custom_hint",
        )

        self.assertEqual(switcher.title_key, "custom_title")
        self.assertEqual(switcher.hint_key, "custom_hint")
        self.assertIsNone(switcher.active_for)


class TestBoundManifest(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.env.configs_src = self._ctx.home / "repo-configs"
        self.env.configs_src.mkdir()

    def tearDown(self):
        self._ctx.__exit__()

    def test_directory_manifest_is_loaded_below_bound_app(self):
        app = self.env.configs_src / "niri"
        app.mkdir()
        (app / "config.kdl").write_text("config")
        (app / ".module.toml").write_text(
            '[packages]\npreserve = ["monitor.kdl"]\n'
        )

        with preset._opened_repo_app("niri") as bound:
            manifest = load_manifest_at(
                "niri",
                bound.fd,
                bound.info,
                bound.root_fd,
            )

        self.assertEqual(manifest.name, "niri")
        self.assertEqual(manifest.preserve, ["monitor.kdl"])

    def test_file_sidecar_uses_real_app_name_under_bound_configs_root(self):
        app = self.env.configs_src / "starship.toml"
        app.write_text("format = '$all'")
        (self.env.configs_src / "starship.toml.module.toml").write_text(
            '[packages]\nrepo = ["starship"]\n'
        )

        with preset._opened_repo_app("starship.toml") as bound:
            manifest = load_manifest_at(
                "starship.toml",
                bound.fd,
                bound.info,
                bound.root_fd,
            )

        self.assertEqual(manifest.name, "starship.toml")
        self.assertEqual(manifest.packages_repo, ["starship"])


class TestSavePresetRollback(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.env.configs_src = self._ctx.home / "repo-configs"
        repo_app = self.env.configs_src / "kitty"
        repo_app.mkdir(parents=True)
        (repo_app / "kitty.conf").write_text("repo")
        current = self.env.config_dir / "kitty"
        current.mkdir(parents=True)
        (current / "kitty.conf").write_text("new")
        self.user_app = self.env.presets_dir / "kitty"
        old = self.user_app / "mine"
        old.mkdir(parents=True)
        (old / "kitty.conf").write_text("original")

    def tearDown(self):
        self._ctx.__exit__()

    def test_failed_publish_and_failed_restore_keep_original_backup(self):
        real_rename = os.rename
        calls = 0

        def fail_publish_and_restore(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls in (2, 3):
                raise OSError("injected rename failure")
            return real_rename(*args, **kwargs)

        with patch(
            "nyxniri.deploy.preset.os.rename",
            side_effect=fail_publish_and_restore,
        ):
            self.assertFalse(preset.save_preset("kitty", "mine"))

        backups = list(self.user_app.glob(".preset-old.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "kitty.conf").read_text(), "original")


if __name__ == "__main__":
    unittest.main()
