"""Hardware self-adaptation layer — NVIDIA env patching in niri config.kdl.

Kept as a SEPARATE layer from the preset system on purpose (§6): hardware
adaptation is auto-detected and user-invisible; presets are an explicit,
user-visible choice — different concepts, different mechanism. The patch
stays here until hardware variants exceed ~3 (then overlay presets; §11).
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from nyxniri.constants import MAIN_WM
from nyxniri.core import get_env, log_msg
from nyxniri.deploy.templates import _rewrite_regular_leaf
from nyxniri.i18n import msg

_IS_NVIDIA: Optional[bool] = None


def _detect_nvidia() -> bool:
    global _IS_NVIDIA
    if _IS_NVIDIA is not None:
        return _IS_NVIDIA
    try:
        res = subprocess.run(["lspci"], capture_output=True, text=True, check=False, env={**os.environ, "LC_ALL": "C"})
        _IS_NVIDIA = "nvidia" in res.stdout.lower()
    except Exception:
        _IS_NVIDIA = False
    return _IS_NVIDIA


def _phase_hardware_patches(*, app_root: Optional[Path] = None) -> None:
    env = get_env()
    niri_root = app_root or env.config_dir / MAIN_WM

    def patch_niri(content: str) -> str:
        if _detect_nvidia():
            print(msg("log_nvidia_gpu_detected"))
            log_msg("INFO", "NVIDIA GPU detected. Enabling NVIDIA envs in config.kdl")
            content = re.sub(r'^(\s*)//\s*(GBM_BACKEND\s+"nvidia-drm")', r'\1\2', content, flags=re.MULTILINE)
            content = re.sub(r'^(\s*)//\s*(__GLX_VENDOR_LIBRARY_NAME\s+"nvidia")', r'\1\2', content, flags=re.MULTILINE)
            return re.sub(r'^(\s*)//\s*(LIBVA_DRIVER_NAME\s+"nvidia")', r'\1\2', content, flags=re.MULTILINE)
        print(msg("log_nvidia_gpu_not_detected"))
        log_msg("INFO", "Non-NVIDIA GPU detected. NVIDIA envs kept disabled.")
        return content

    _rewrite_regular_leaf(niri_root, "config.kdl", patch_niri)
