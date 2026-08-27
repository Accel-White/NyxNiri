"""Security contracts for post-deploy work below bound configuration roots."""

import os
import stat
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


class TestBoundPostprocess(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.repo_configs = self._ctx.home / "repo-configs"
        self.repo_configs.mkdir()
        self.env.configs_src = self.repo_configs

    def tearDown(self):
        self._ctx.__exit__()

    def _app(self, name: str) -> Path:
        root = self.repo_configs / name
        root.mkdir()
        return root

    def _niri_source(self) -> Path:
        root = self._app("niri")
        (root / "config.kdl").write_text("spawn /home/user/tool\n", encoding="utf-8")
        (root / "effects_normal.kdl").write_text("normal\n", encoding="utf-8")
        scripts = root / "scripts"
        scripts.mkdir()
        tool = scripts / "tool.sh"
        tool.write_text("#!/bin/sh\n", encoding="utf-8")
        tool.chmod(0o600)
        (root / ".module.toml").write_text(
            '[packages]\nchmod = ["scripts/*.sh"]\n',
            encoding="utf-8",
        )
        return root

    def test_apply_does_not_render_through_template_leaf_symlink(self):
        from nyxniri.deploy.preset import apply_preset

        outside = self._ctx.home / "outside-config.kdl"
        original = "spawn /home/user/outside\n"
        outside.write_text(original, encoding="utf-8")
        niri = self._app("niri")
        (niri / "config.kdl").symlink_to(outside)

        self.assertTrue(apply_preset("niri", "default"))

        deployed = self.env.config_dir / "niri" / "config.kdl"
        self.assertTrue(deployed.is_symlink())
        self.assertEqual(outside.read_text(encoding="utf-8"), original)

    def test_hardware_patch_rewrites_regular_leaf_but_not_symlink(self):
        from nyxniri.deploy.hardware import _phase_hardware_patches

        safe_root = self.env.config_dir / "safe-niri"
        safe_root.mkdir()
        safe_conf = safe_root / "config.kdl"
        safe_conf.write_text('// GBM_BACKEND "nvidia-drm"\n', encoding="utf-8")

        outside = self._ctx.home / "outside-hardware.kdl"
        original = '// GBM_BACKEND "nvidia-drm"\n'
        outside.write_text(original, encoding="utf-8")
        linked_root = self.env.config_dir / "linked-niri"
        linked_root.mkdir()
        (linked_root / "config.kdl").symlink_to(outside)

        with patch("nyxniri.deploy.hardware._detect_nvidia", return_value=True):
            _phase_hardware_patches(app_root=safe_root)
            _phase_hardware_patches(app_root=linked_root)

        self.assertEqual(safe_conf.read_text(encoding="utf-8"), 'GBM_BACKEND "nvidia-drm"\n')
        self.assertEqual(outside.read_text(encoding="utf-8"), original)

    def test_manifest_chmod_binds_each_component_without_following_symlinks(self):
        from nyxniri.deploy.deploy import _phase_manifest_chmod

        app_root = self.env.config_dir / "app"
        safe_dir = app_root / "safe"
        safe_dir.mkdir(parents=True)
        safe_script = safe_dir / "safe.sh"
        safe_script.write_text("#!/bin/sh\n", encoding="utf-8")
        safe_script.chmod(0o600)

        outside_dir = self._ctx.home / "outside-scripts"
        outside_dir.mkdir()
        outside_script = outside_dir / "outside.sh"
        outside_script.write_text("#!/bin/sh\n", encoding="utf-8")
        outside_script.chmod(0o600)
        (app_root / "scripts").symlink_to(outside_dir, target_is_directory=True)

        _phase_manifest_chmod(app_root, ["safe/*.sh", "scripts/*.sh"])

        self.assertEqual(stat.S_IMODE(safe_script.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(outside_script.stat().st_mode), 0o600)

    def test_successful_app_finishes_postprocess_when_another_is_frozen(self):
        from nyxniri.deploy.deploy import _phase_atomic_deployment

        self._app("kitty").joinpath("kitty.conf").write_text("kitty\n", encoding="utf-8")
        self._niri_source()
        self.env.presets_dir.mkdir(parents=True)
        (self.env.presets_dir / "kitty.active").write_bytes(b"../../outside")

        with patch("nyxniri.deploy.hardware._detect_nvidia", return_value=False):
            failed = _phase_atomic_deployment(["kitty", "niri"])

        niri = self.env.config_dir / "niri"
        self.assertEqual(failed, ["kitty"])
        self.assertIn(str(self.env.home), (niri / "config.kdl").read_text(encoding="utf-8"))
        self.assertEqual(stat.S_IMODE((niri / "scripts" / "tool.sh").stat().st_mode), 0o755)
        self.assertTrue((niri / "effects.kdl").is_symlink())
        self.assertEqual(os.readlink(niri / "effects.kdl"), "effects_normal.kdl")

    def test_full_retries_new_active_choice_before_postprocess(self):
        from nyxniri.deploy import deploy, preset
        from nyxniri.deploy.atomic import atomic_replace_item_transaction

        kitty = self._app("kitty")
        (kitty / "kitty.conf").write_text("default\n", encoding="utf-8")
        transparent = kitty / "presets" / "transparent"
        transparent.mkdir(parents=True)
        (transparent / "kitty.conf").write_text("transparent\n", encoding="utf-8")
        current = self.env.config_dir / "kitty"
        current.mkdir(parents=True)
        (current / "kitty.conf").write_text("old\n", encoding="utf-8")
        switched = False

        def deploy_then_switch(*args, **kwargs):
            nonlocal switched
            from contextlib import contextmanager
            @contextmanager
            def wrapped():
                nonlocal switched
                with atomic_replace_item_transaction(*args, **kwargs) as swap:
                    if not switched:
                        preset.write_active_preset("kitty", "transparent")
                        switched = True
                    yield swap
            return wrapped()

        with patch.object(deploy, "atomic_replace_item_transaction", side_effect=deploy_then_switch) as atomic, \
             patch.object(deploy, "_phase_render_templates") as render:
            failed = deploy._phase_atomic_deployment(["kitty"])

        self.assertTrue(switched)
        self.assertEqual(failed, [])
        self.assertEqual(atomic.call_count, 2)
        render.assert_called_once()
        self.assertEqual(
            (self.env.config_dir / "kitty" / "kitty.conf").read_text(encoding="utf-8"),
            "transparent\n",
        )

    def test_full_keeps_bound_repo_source_and_manifest_after_root_swap(self):
        from nyxniri.deploy import deploy

        kitty = self._app("kitty")
        (kitty / "kitty.conf").write_text("safe\n", encoding="utf-8")
        (kitty / ".module.toml").write_text("[packages]\n", encoding="utf-8")
        stash = self._ctx.home / "repo-stash"
        outside_repo = self._ctx.home / "outside-repo"
        outside_kitty = outside_repo / "kitty"
        outside_kitty.mkdir(parents=True)
        (outside_kitty / "kitty.conf").write_text("outside\n", encoding="utf-8")
        real_load = deploy.load_manifest_at
        swapped = False

        def swap_then_load(*args, **kwargs):
            nonlocal swapped
            self.repo_configs.rename(stash)
            self.repo_configs.symlink_to(outside_repo, target_is_directory=True)
            swapped = True
            return real_load(*args, **kwargs)

        with patch.object(deploy, "load_manifest_at", side_effect=swap_then_load):
            failed = deploy._phase_atomic_deployment(["kitty"])

        self.assertTrue(swapped)
        self.assertEqual(failed, [])
        self.assertEqual(
            (self.env.config_dir / "kitty" / "kitty.conf").read_text(encoding="utf-8"),
            "safe\n",
        )

    def test_full_postprocess_stays_on_bound_root_after_root_swap(self):
        from nyxniri.deploy import deploy

        self._niri_source()
        config_root = self.env.config_dir
        stash = self._ctx.home / "config-stash"
        outside = self._ctx.home / "outside-config"
        outside_niri = outside / "niri"
        outside_niri.mkdir(parents=True)
        outside_conf = outside_niri / "config.kdl"
        outside_conf.write_text("outside /home/user\n", encoding="utf-8")
        sentinel = outside / "sentinel"
        sentinel.write_text("keep", encoding="utf-8")
        real_render = deploy._phase_render_templates
        swapped = False

        def swap_then_render(*args, **kwargs):
            nonlocal swapped
            config_root.rename(stash)
            config_root.symlink_to(outside, target_is_directory=True)
            swapped = True
            return real_render(*args, **kwargs)

        with patch.object(deploy, "_phase_render_templates", side_effect=swap_then_render), \
             patch("nyxniri.deploy.hardware._detect_nvidia", return_value=False):
            failed = deploy._phase_atomic_deployment(["niri"])

        self.assertTrue(swapped)
        self.assertEqual(failed, [])
        self.assertIn(str(self.env.home), (stash / "niri" / "config.kdl").read_text(encoding="utf-8"))
        self.assertTrue((stash / "niri" / "effects.kdl").is_symlink())
        self.assertEqual(outside_conf.read_text(encoding="utf-8"), "outside /home/user\n")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_post_install_executes_bound_regular_script_by_fd(self):
        from nyxniri.deploy import deploy
        from nyxniri.deploy.preset import _opened_root

        theme_root = self.env.config_dir / "noctalia"
        theme_root.mkdir()
        script = theme_root / "theme-sync.sh"
        script.write_text("#!/bin/sh\n", encoding="utf-8")
        script.chmod(0o600)

        with _opened_root(self.env.config_dir) as config_fd, \
             patch.object(deploy.shutil, "which", return_value=None), \
             patch.object(deploy.subprocess, "run") as run:
            deploy._phase_post_install_services(config_fd=config_fd)

        run.assert_called_once()
        command = run.call_args.args[0]
        passed_fd = run.call_args.kwargs["pass_fds"][0]
        self.assertEqual(command, ["bash", f"/proc/self/fd/{passed_fd}"])
        self.assertNotIn(str(self.env.config_dir), command[1])
        self.assertEqual(stat.S_IMODE(script.stat().st_mode), 0o755)

    def test_post_install_stops_if_config_root_identity_changed(self):
        from nyxniri.deploy import deploy
        from nyxniri.deploy.preset import _opened_root

        config_root = self.env.config_dir
        stash = self._ctx.home / "config-stash"
        outside = self._ctx.home / "outside-config"
        outside_theme = outside / "noctalia"
        outside_theme.mkdir(parents=True)
        (outside_theme / "theme-sync.sh").write_text("exit 99\n", encoding="utf-8")

        with _opened_root(config_root) as config_fd:
            config_root.rename(stash)
            config_root.symlink_to(outside, target_is_directory=True)
            with patch.object(deploy.shutil, "which", return_value="/bin/tool"), \
                 patch.object(deploy.subprocess, "run") as run:
                deploy._phase_post_install_services(config_fd=config_fd)

        run.assert_not_called()

    def test_post_install_accepts_stable_config_root_symlink(self):
        from nyxniri.deploy import deploy
        from nyxniri.deploy.preset import _opened_root

        config_root = self.env.config_dir
        target = self._ctx.home / "linked-config-target"
        config_root.rename(target)
        config_root.symlink_to(target, target_is_directory=True)
        theme_root = target / "noctalia"
        theme_root.mkdir()
        (theme_root / "theme-sync.sh").write_text("exit 0\n", encoding="utf-8")

        with _opened_root(config_root) as config_fd, \
             patch.object(deploy.shutil, "which", return_value=None), \
             patch.object(deploy.subprocess, "run") as run:
            deploy._phase_post_install_services(config_fd=config_fd)

        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
