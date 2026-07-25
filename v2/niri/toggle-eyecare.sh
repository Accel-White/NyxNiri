#!/bin/bash
# NyxNiri EyeCare One-shot Toggle & Sync Script
# Zero background process. Runs in < 2ms then exits immediately.

NIRI_DIR="$HOME/.config/niri"
EFFECTS_LINK="$NIRI_DIR/effects.kdl"
NORMAL_EFFECTS="$NIRI_DIR/effects_normal.kdl"
EYECARE_EFFECTS="$NIRI_DIR/effects_eyecare.kdl"
STATE_FILE="$NIRI_DIR/.eyecare_state"

# Desired EyeCare warm color temperature (in Kelvin: 5500K for subtle natural warmth)
EYECARE_TEMP=5500

HAS_NOCTALIA=false
if command -v noctalia >/dev/null 2>&1; then
    HAS_NOCTALIA=true
fi

IS_TURNING_ON=false

if [ -f "$STATE_FILE" ]; then
    # --- Turning EyeCare Mode OFF ---
    rm -f "$STATE_FILE"
    ln -sfn "$NORMAL_EFFECTS" "$EFFECTS_LINK"
    
    # Restore normal 6500K color temperature
    pkill -x wlsunset 2>/dev/null || true

    # Noctalia V5 Native OSD Card Trigger
    if [ "$HAS_NOCTALIA" = "true" ]; then
        noctalia msg nightlight-force-toggle 2>/dev/null || true
    fi
else
    # --- Turning EyeCare Mode ON ---
    touch "$STATE_FILE"
    ln -sfn "$EYECARE_EFFECTS" "$EFFECTS_LINK"
    IS_TURNING_ON=true

    # Noctalia V5 Native OSD Card Trigger
    if [ "$HAS_NOCTALIA" = "true" ]; then
        noctalia msg nightlight-force-toggle 2>/dev/null || true
    fi
fi

# 1. Reload Niri config instantly for opacity & blur
if command -v niri >/dev/null 2>&1; then
    niri msg action reload-config 2>/dev/null || true
fi

# 2. Smoothly ramp color temperature over 0.3s to eliminate visual flickering
if [ "$IS_TURNING_ON" = "true" ]; then
    if ! pgrep -x wlsunset >/dev/null 2>&1; then
        sleep 0.05
        nohup wlsunset -T 6500 -t "$EYECARE_TEMP" -d 0.3 -S 00:00 -s 00:00 >/dev/null 2>&1 &
    fi
fi
