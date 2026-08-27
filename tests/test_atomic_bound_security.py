"""Security and rollback contracts for fd-bound atomic deployment."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import nyxniri.deploy.atomic as atomic
from tests.utils import TempEnv


class TestBoundAtomicReplace(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.root = self._ctx.home / "atomic-bound"
        self.root.mkdir()
        self.parent = self.root / "config"
        self.parent.mkdir()

    def tearDown(self):
        self._ctx.__exit__()

    def test_directory_stage_swap_never_writes_through_replacement_symlink(self):
        source = self.root / "source"
        source.mkdir()
        (source / "safe.conf").write_text("safe")
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("keep")
        stash = self.root / "held-stage"
        real_copytree = atomic.shutil.copytree
        swapped = False

        def swap_then_copy(src, dst, *args, **kwargs):
            nonlocal swapped
            if not swapped and str(dst).startswith("/proc/self/fd/"):
                stage = next(self.parent.glob(".app.new.*"))
                stage.rename(stash)
                stage.symlink_to(outside, target_is_directory=True)
                swapped = True
            return real_copytree(src, dst, *args, **kwargs)

        self.assertTrue(atomic.atomic_replace_item(source, self.parent / "app", bind_dest=True))

        self.assertFalse(swapped)
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertFalse((outside / "safe.conf").exists())
        self.assertTrue((self.parent / "app").exists())

    def test_file_stage_swap_is_rejected_without_touching_external_file(self):
        source = self.root / "source.toml"
        source.write_text("safe")
        outside = self.root / "outside.toml"
        outside.write_text("keep")
        stash = self.root / "held-file-stage"
        real_copystat = atomic.shutil.copystat
        swapped = False

        def swap_then_copystat(src, dst, *args, **kwargs):
            nonlocal swapped
            if not swapped and str(dst).startswith("/proc/self/fd/"):
                stage = next(self.parent.glob(".app.toml.new.*"))
                stage.rename(stash)
                stage.symlink_to(outside)
                swapped = True
            return real_copystat(src, dst, *args, **kwargs)

        self.assertTrue(atomic.atomic_replace_item(source, self.parent / "app.toml", bind_dest=True))

        self.assertFalse(swapped)
        self.assertEqual(outside.read_text(), "keep")
        self.assertTrue((self.parent / "app.toml").exists())

    def test_binding_mismatch_never_unlinks_the_replacement_entry(self):
        source = self.root / "source.toml"
        source.write_text("safe")
        moved = self.parent / "racer-held-stage"
        replacement_name = None
        real_matches = atomic._entry_matches_at

        def replace_before_binding(parent_fd, name, expected):
            nonlocal replacement_name
            if replacement_name is None and name.startswith(".app.toml.new."):
                os.rename(
                    name,
                    moved.name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                replacement_fd = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=parent_fd,
                )
                try:
                    os.write(replacement_fd, b"replacement")
                finally:
                    os.close(replacement_fd)
                replacement_name = name
            return real_matches(parent_fd, name, expected)

        with patch.object(atomic, "_entry_matches_at", side_effect=replace_before_binding):
            self.assertFalse(
                atomic.atomic_replace_item(
                    source,
                    self.parent / "app.toml",
                    bind_dest=True,
                )
            )

        self.assertIsNotNone(replacement_name)
        self.assertEqual((self.parent / replacement_name).read_text(), "replacement")
        self.assertEqual(moved.read_text(), "")

    def test_special_target_is_rejected_and_preserved(self):
        source = self.root / "source"
        source.mkdir()
        (source / "safe.conf").write_text("safe")
        target = self.parent / "app"
        os.mkfifo(target)

        self.assertFalse(
            atomic.atomic_replace_item(source, target, bind_dest=True)
        )
        self.assertTrue(target.exists())

    def test_bind_dest_rejects_unbound_parent_symlink(self):
        source = self.root / "source"
        source.mkdir()
        (source / "safe.conf").write_text("safe")
        outside = self.root / "outside"
        outside.mkdir()
        linked_parent = self.root / "linked-config"
        linked_parent.symlink_to(outside, target_is_directory=True)

        self.assertFalse(
            atomic.atomic_replace_item(
                source,
                linked_parent / "app",
                bind_dest=True,
            )
        )
        self.assertFalse((outside / "app").exists())

    def test_missing_target_appearance_is_not_overwritten(self):
        source = self.root / "source"
        source.mkdir()
        (source / "safe.conf").write_text("safe")
        target = self.parent / "app"
        real_renameat2 = atomic._renameat2
        injected = False

        def create_target_then_publish(*args, **kwargs):
            nonlocal injected
            if not injected:
                target.write_text("appeared")
                injected = True
            return real_renameat2(*args, **kwargs)

        with patch(
            "nyxniri.deploy.atomic._renameat2",
            side_effect=create_target_then_publish,
        ):
            self.assertFalse(
                atomic.atomic_replace_item(source, target, bind_dest=True)
            )

        self.assertTrue(injected)
        self.assertEqual(target.read_text(), "appeared")

    def test_existing_target_exchange_has_no_missing_name_window(self):
        source = self.root / "source"
        source.mkdir()
        (source / "value").write_text("new")
        target = self.parent / "app"
        target.mkdir()
        (target / "value").write_text("old")
        real_renameat2 = atomic._renameat2
        observed = []

        def observe_exchange(src_fd, src, dst_fd, dst, flags):
            observed.append(
                (
                    os.stat(src, dir_fd=src_fd, follow_symlinks=False),
                    os.stat(dst, dir_fd=dst_fd, follow_symlinks=False),
                )
            )
            result = real_renameat2(src_fd, src, dst_fd, dst, flags)
            observed.append(
                (
                    os.stat(src, dir_fd=src_fd, follow_symlinks=False),
                    os.stat(dst, dir_fd=dst_fd, follow_symlinks=False),
                )
            )
            return result

        with patch(
            "nyxniri.deploy.atomic._renameat2",
            side_effect=observe_exchange,
        ):
            self.assertTrue(
                atomic.atomic_replace_item(source, target, bind_dest=True)
            )

        self.assertEqual(len(observed), 2)
        self.assertEqual((target / "value").read_text(), "new")

    def test_moved_old_target_is_retained_instead_of_cleared(self):
        source = self.root / "source"
        source.mkdir()
        (source / "value").write_text("new")
        target = self.parent / "app"
        target.mkdir()
        (target / "value").write_text("old")
        retained = self.parent / ".retained-old"
        old_info = target.stat()
        real_cleanup = atomic._cleanup_bound_stage
        moved = False

        def move_old_then_cleanup(parent_fd, stage):
            nonlocal moved
            if (
                not moved
                and (stage.info.st_dev, stage.info.st_ino)
                == (old_info.st_dev, old_info.st_ino)
            ):
                os.rename(
                    stage.name,
                    retained.name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                moved = True
            return real_cleanup(parent_fd, stage)

        with patch(
            "nyxniri.deploy.atomic._cleanup_bound_stage",
            side_effect=move_old_then_cleanup,
        ):
            self.assertTrue(
                atomic.atomic_replace_item(source, target, bind_dest=True)
            )

        self.assertTrue(moved)
        self.assertEqual((target / "value").read_text(), "new")
        self.assertEqual((retained / "value").read_text(), "old")

    def test_bound_file_copy_preserves_mode_and_mtime(self):
        source = self.root / "source.toml"
        source.write_text("safe")
        source.chmod(0o640)
        os.utime(source, ns=(1_000_000_000, 2_000_000_000))
        target = self.parent / "app.toml"

        self.assertTrue(
            atomic.atomic_replace_item(source, target, bind_dest=True)
        )
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertEqual(target.stat().st_mtime_ns, 2_000_000_000)

    def test_preserved_file_never_writes_through_stage_parent_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("keep")
        source = self.root / "source"
        source.mkdir()
        (source / "nested").symlink_to(outside, target_is_directory=True)
        target = self.parent / "app"
        nested = target / "nested"
        nested.mkdir(parents=True)
        (nested / "state__custom__.conf").write_text("custom")

        self.assertFalse(
            atomic.atomic_replace_item(source, target, bind_dest=True)
        )
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertFalse((outside / "state__custom__.conf").exists())
        self.assertEqual(
            (target / "nested" / "state__custom__.conf").read_text(),
            "custom",
        )


if __name__ == "__main__":
    unittest.main()
