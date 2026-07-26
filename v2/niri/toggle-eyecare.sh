#!/bin/bash
# NyxNiri EyeCare One-shot Self-Healing Toggle & Sync Script
# Zero background process besides wlsunset itself. Runs in < 2ms then exits.
#
# On/off state is derived from whether wlsunset is currently running rather
# than tracked in a separate state file. A config redeploy always wipes and
# recreates ~/.config/niri from the template (effects.kdl reset to Normal)
# but never touches the wlsunset process — deriving state from wlsunset
# means a stale state file can never desync from what's actually running.

NIRI_DIR="$HOME/.config/niri"
EFFECTS_LINK="$NIRI_DIR/effects.kdl"
NORMAL_EFFECTS="$NIRI_DIR/effects_normal.kdl"
EYECARE_EFFECTS="$NIRI_DIR/effects_eyecare.kdl"

# Desired EyeCare warm color temperature (in Kelvin: 5500K for subtle natural warmth)
EYECARE_TEMP=5500

HAS_NOCTALIA=false
if command -v noctalia >/dev/null 2>&1; then
    HAS_NOCTALIA=true
fi

CURRENTLY_ON=false
pgrep -x wlsunset >/dev/null 2>&1 && CURRENTLY_ON=true

# Point effects.kdl at the given target and reload niri so window
# opacity/blur pick it up. Safe to call repeatedly/idempotently.
apply_effects() {
    if [ "$1" = "on" ]; then
        ln -sfn "$EYECARE_EFFECTS" "$EFFECTS_LINK"
    else
        ln -sfn "$NORMAL_EFFECTS" "$EFFECTS_LINK"
    fi
    if command -v niri >/dev/null 2>&1; then
        niri msg action reload-config 2>/dev/null || true
    fi
}

# --sync: idempotent reconciliation only (no toggling). Called from niri's
# spawn-at-startup so a niri restart — e.g. right after a config redeploy —
# re-aligns effects.kdl with whatever wlsunset is actually doing, instead of
# staying stuck on the deploy's Normal default until the next manual toggle.
if [ "$1" = "--sync" ]; then
    if [ "$CURRENTLY_ON" = "true" ]; then
        apply_effects on
    else
        apply_effects off
    fi
    exit 0
fi

# 1. Pre-execution Self-Healing: Force Noctalia to release Wayland gamma lock
if [ "$HAS_NOCTALIA" = "true" ]; then
    noctalia msg nightlight-disable 2>/dev/null || true
fi
pkill -9 -x wlsunset 2>/dev/null || true

IS_TURNING_ON=false

if [ "$CURRENTLY_ON" = "true" ]; then
    # --- Turning EyeCare Mode OFF ---
    apply_effects off
else
    # --- Turning EyeCare Mode ON ---
    apply_effects on
    IS_TURNING_ON=true
fi

# 3. Smoothly ramp color temperature over 0.3s without GPU pipeline tearing
if [ "$IS_TURNING_ON" = "true" ]; then
    sleep 0.05
    nohup wlsunset -T 6500 -t "$EYECARE_TEMP" -d 0.3 -S 00:00 -s 00:00 >/dev/null 2>&1 &
fi

# 4. Trigger Noctalia Native OSD Card
if [ "$HAS_NOCTALIA" = "true" ]; then
    noctalia msg nightlight-force-toggle 2>/dev/null || true
fi
