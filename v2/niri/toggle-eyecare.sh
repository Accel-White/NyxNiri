#!/bin/bash
# NyxNiri EyeCare One-shot Toggle Script
# Zero background process. Runs in < 2ms then exits immediately.

NIRI_DIR="$HOME/.config/niri"
EFFECTS_LINK="$NIRI_DIR/effects.kdl"
NORMAL_EFFECTS="$NIRI_DIR/effects_normal.kdl"
EYECARE_EFFECTS="$NIRI_DIR/effects_eyecare.kdl"
STATE_FILE="$NIRI_DIR/.eyecare_state"

# 1. Toggle Noctalia Nightlight Color Temp if Noctalia is running
if command -v noctalia >/dev/null 2>&1; then
    noctalia msg nightlight-force-toggle 2>/dev/null || true
fi

# 2. Toggle Niri Visual Effects (Opacity & Blur)
if [ -f "$STATE_FILE" ]; then
    rm -f "$STATE_FILE"
    ln -sfn "$NORMAL_EFFECTS" "$EFFECTS_LINK"
else
    touch "$STATE_FILE"
    ln -sfn "$EYECARE_EFFECTS" "$EFFECTS_LINK"
fi

# 3. Reload Niri config instantly
if command -v niri >/dev/null 2>&1; then
    niri msg action reload-config 2>/dev/null || true
fi
