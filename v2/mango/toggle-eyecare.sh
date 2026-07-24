#!/bin/bash

MANGO_DIR="$HOME/.config/mango"
CONFIG_FILE="$MANGO_DIR/config.conf"
STATE_FILE="$MANGO_DIR/.eyecare_state"

if command -v noctalia >/dev/null 2>&1; then
    noctalia msg nightlight-force-toggle 2>/dev/null || true
fi

if [ -f "$STATE_FILE" ]; then
    rm -f "$STATE_FILE"
    sed -i 's/^blur=[01]$/blur=1/' "$CONFIG_FILE"
    sed -i 's/^blur_layer=[01]$/blur_layer=1/' "$CONFIG_FILE"
    sed -i 's/^shadows=[01]$/shadows=1/' "$CONFIG_FILE"
    sed -i 's/^focused_opacity=[0-9.]*$/focused_opacity=0.9/' "$CONFIG_FILE"
    sed -i 's/^unfocused_opacity=[0-9.]*$/unfocused_opacity=0.85/' "$CONFIG_FILE"
else
    touch "$STATE_FILE"
    sed -i 's/^blur=[01]$/blur=0/' "$CONFIG_FILE"
    sed -i 's/^blur_layer=[01]$/blur_layer=0/' "$CONFIG_FILE"
    sed -i 's/^shadows=[01]$/shadows=0/' "$CONFIG_FILE"
    sed -i 's/^focused_opacity=[0-9.]*$/focused_opacity=1.0/' "$CONFIG_FILE"
    sed -i 's/^unfocused_opacity=[0-9.]*$/unfocused_opacity=1.0/' "$CONFIG_FILE"
fi

if command -v mmsg >/dev/null 2>&1; then
    mmsg dispatch reload_config 2>/dev/null || true
fi