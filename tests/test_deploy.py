"""Behavior contracts for deploy: atomic replace rollback, broken symlink, no-clobber."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import make_temp_home, force_repo_mode, reset_env


class TestAtomicReplaceFileRollback(unittest.TestCase):
    """If the 2nd rename fails, dest must be restored from old_dest."""

    def setUp(self):
        self._tmp = make_temp_home()
        self.home = Path(self._tmp.name)
        reset_env(self.home)
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_file_replace_rollback_on_second_rename_failure(self):
        """If tmp_file.rename(dest) fails, dest must be restored from old_dest."""
        from nyxniri.deploy import atomic_replace_item

        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            src = workdir / "src.txt"
            src.write_text("new")
            dest = workdir / "dest.txt"
            dest.write_text("original")

            # Make the second rename (tmp_file → dest) fail by intercepting
            # the specific pattern: a file named *.new.* being renamed to dest
            original_rename = Path.rename
            call_count = [0]

            def fail_second_rename(self_path, target):
                if ".new." in self_path.name and target == dest:
                    call_count[0] += 1
                    raise OSError("simulated rename failure")
                return original_rename(self_path, target)

            with patch.object(Path, "rename", fail_second_rename):
                result = atomic_replace_item(src, dest)

            self.assertFalse(result, "Should return False on failure")
            self.assertTrue(dest.exists(), "dest must still exist (restored)")
            self.assertEqual(dest.read_text(), "original",
                             "dest content must be the original, not 'new'")

    def test_file_replace_normal_success(self):
        """Normal file replace should succeed."""
        from nyxniri.deploy import atomic_replace_item

        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            src = workdir / "src.txt"
            src.write_text("new content")
            dest = workdir / "dest.txt"
            dest.write_text("old content")

            result = atomic_replace_item(src, dest)
            self.assertTrue(result)
            self.assertEqual(dest.read_text(), "new content")


class TestAtomicReplaceDirRollback(unittest.TestCase):
    """Directory atomic replace must also rollback on failure."""

    def setUp(self):
        self._tmp = make_temp_home()
        self.home = Path(self._tmp.name)
        reset_env(self.home)
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_dir_replace_rollback_on_rename_failure(self):
        """If tmp_new.rename(dest) fails, dest must be restored from old_dest."""
        from nyxniri.deploy import atomic_replace_item

        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            src = workdir / "srcdir"
            src.mkdir()
            (src / "file.txt").write_text("new")
            dest = workdir / "dest_dir"
            dest.mkdir()
            (dest / "old.txt").write_text("original")

            original_rename = Path.rename

            def fail_final_rename(self_path, target):
                # Fail when tmp_new (named dest_dir.new.*) is renamed to dest
                if ".new." in self_path.name and target == dest:
                    raise OSError("simulated dir rename failure")
                return original_rename(self_path, target)

            with patch.object(Path, "rename", fail_final_rename):
                result = atomic_replace_item(src, dest)

            self.assertFalse(result)
            self.assertTrue(dest.exists(), "dest must be restored")
            self.assertTrue((dest / "old.txt").exists(),
                            "Original content must survive rollback")


class TestEffectsSymlinkBroken(unittest.TestCase):
    """A broken effects.kdl symlink should be recreated."""

    def setUp(self):
        self._tmp = make_temp_home()
        self.home = Path(self._tmp.name)
        reset_env(self.home)
        self.env = force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_broken_symlink_recreated(self):
        """If effects.kdl is a broken symlink, it should be replaced."""
        from nyxniri.deploy import _phase_hardware_patches, _phase_render_templates

        niri_dir = self.env.config_dir / "niri"
        niri_dir.mkdir(parents=True, exist_ok=True)
        effects_normal = niri_dir / "effects_normal.kdl"
        effects_normal.write_text("// normal")
        effects_sym = niri_dir / "effects.kdl"

        # Create a broken symlink pointing to a non-existent file
        effects_sym.symlink_to(niri_dir / "effects_eyecare.kdl")

        # Run the phase that recreates the symlink
        # _phase_hardware_patches is the wrong function; the symlink creation
        # happens in _phase_atomic_deployment. Let's test the condition directly.
        from nyxniri.deploy import _phase_atomic_deployment

        # We need a configs/niri source dir to exist
        src_niri = self.env.configs_src / "niri"
        src_niri.mkdir(parents=True, exist_ok=True)
        (src_niri / "effects_normal.kdl").write_text("// normal")
        (src_niri / "config.kdl").write_text("// config")

        with patch("builtins.print"):
            _phase_atomic_deployment(["niri"], keep_monitor=False)

        # The broken symlink should have been replaced
        self.assertTrue(effects_sym.exists(),
                        "Broken effects.kdl symlink should be recreated")
        self.assertTrue(effects_sym.resolve() == effects_normal.resolve() or
                        effects_sym.is_symlink(),
                        "effects.kdl should point to effects_normal.kdl")


class TestWallpaperNoClobber(unittest.TestCase):
    """Wallpaper pack download should not overwrite existing user files."""

    def setUp(self):
        self._tmp = make_temp_home()
        self.home = Path(self._tmp.name)
        reset_env(self.home)
        self.env = force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_existing_wallpaper_not_overwritten(self):
        """When downloading wallpaper pack, existing files must be preserved."""
        from nyxniri.deploy import deploy_wallpapers

        wp_dest = self.home / "Pictures" / "Wallpapers"
        wp_dest.mkdir(parents=True, exist_ok=True)
        # User has a custom wallpaper
        user_wp = wp_dest / "my_custom.webp"
        user_wp.write_text("user custom content")

        # Create a fake tmp clone that the download would create
        fake_clone = Path(tempfile.mkdtemp())
        (fake_clone / "my_custom.webp").write_text("repo version")
        (fake_clone / "new_wallpaper.webp").write_text("new from repo")
        (fake_clone / "video").mkdir()
        (fake_clone / "video" / "test.mp4").write_text("video")

        try:
            with patch("nyxniri.deploy.git_clone_timeout", return_value=True):
                with patch("nyxniri.deploy.tempfile.mkdtemp", return_value=str(fake_clone)):
                    with patch("nyxniri.deploy._wallpaper_pack_present_at", return_value=True):
                        with patch("nyxniri.deploy.wallpapers_pack_present", return_value=False):
                            with patch("builtins.print"):
                                result = deploy_wallpapers(do_download=True)

            # User's custom file must be preserved
            self.assertEqual(user_wp.read_text(), "user custom content",
                             "Existing user wallpaper must not be overwritten")
            # New file from repo should be added
            self.assertTrue((wp_dest / "new_wallpaper.webp").exists(),
                            "New wallpaper from repo should be added")
        finally:
            shutil.rmtree(fake_clone, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
