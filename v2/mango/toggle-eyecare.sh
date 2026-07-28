#!/bin/bash
# NyxNiri EyeCare One-shot Self-Healing Toggle & Sync Script (MangoWM Edition)
# Zero background process besides wlsunset itself. Runs in < 2ms then exits.
#
# On/off state is derived from whether wlsunset is currently running rather
# than tracked in a separate state file. A config redeploy always wipes and
# recreates ~/.config/mango from the template but never touches the wlsunset
# process — deriving state from wlsunset means a stale state file can never
# desync from what's actually running.

MANGO_DIR="$HOME/.config/mango"
CONFIG_FILE="$MANGO_DIR/config.conf"

EYECARE_TEMP=5500

HAS_NOCTALIA=false
if command -v noctalia >/dev/null 2>&1; then
    HAS_NOCTALIA=true
fi

CURRENTLY_ON=false
pgrep -x wlsunset >/dev/null 2>&1 && CURRENTLY_ON=true

apply_mango_config() {
    local mode="$1"
    if [ "$mode" = "on" ]; then
        sed -i 's/^blur=[01]$/blur=0/' "$CONFIG_FILE"
        sed -i 's/^blur_layer=[01]$/blur_layer=0/' "$CONFIG_FILE"
        sed -i 's/^shadows=[01]$/shadows=0/' "$CONFIG_FILE"
        sed -i 's/^focused_opacity=[0-9.]*$/focused_opacity=1.0/' "$CONFIG_FILE"
        sed -i 's/^unfocused_opacity=[0-9.]*$/unfocused_opacity=1.0/' "$CONFIG_FILE"
    else
        sed -i 's/^blur=[01]$/blur=1/' "$CONFIG_FILE"
        sed -i 's/^blur_layer=[01]$/blur_layer=1/' "$CONFIG_FILE"
        sed -i 's/^shadows=[01]$/shadows=1/' "$CONFIG_FILE"
        sed -i 's/^focused_opacity=[0-9.]*$/focused_opacity=0.9/' "$CONFIG_FILE"
        sed -i 's/^unfocused_opacity=[0-9.]*$/unfocused_opacity=0.85/' "$CONFIG_FILE"
    fi
    if command -v mmsg >/dev/null 2>&1; then
        mmsg dispatch reload_config 2>/dev/null || true
    fi
}

if [ "$1" = "--sync" ]; then
    if [ "$CURRENTLY_ON" = "true" ]; then
        apply_mango_config on
    else
        apply_mango_config off
    fi
    exit 0
fi

if [ "$HAS_NOCTALIA" = "true" ]; then
    noctalia msg nightlight-disable 2>/dev/null || true
fi
pkill -9 -x wlsunset 2>/dev/null || true

IS_TURNING_ON=false

if [ "$CURRENTLY_ON" = "true" ]; then
    apply_mango_config off
else
    apply_mango_config on
    IS_TURNING_ON=true
fi

if [ "$IS_TURNING_ON" = "true" ]; then
    sleep 0.05
    nohup wlsunset -T 6500 -t "$EYECARE_TEMP" -d 0.3 -S 00:00 -s 00:00 >/dev/null 2>&1 &
fi

if [ "$HAS_NOCTALIA" = "true" ]; then
    noctalia msg nightlight-force-toggle 2>/dev/null || true
fi
