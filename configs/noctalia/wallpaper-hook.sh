#!/bin/bash
set -uo pipefail

LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/noctalia"
LOG_FILE="$LOG_DIR/hook.log"

log_error() {
    mkdir -p "$LOG_DIR" 2>/dev/null || return
    printf '%(%Y-%m-%dT%H:%M:%S%z)T %s\n' -1 "$*" >> "$LOG_FILE" 2>/dev/null || true
}

# Ensure noctalia is available
if ! command -v noctalia >/dev/null 2>&1; then
    exit 1
fi

WP=$(noctalia msg wallpaper-get 2>/dev/null || true)

# Only process video files to avoid infinite loops
if [[ -n "$WP" && -f "$WP" && "$WP" =~ \.(mp4|webm|mkv|mov|gif)$ ]]; then
    if ! command -v ffmpeg >/dev/null 2>&1; then
        log_error "Error: ffmpeg is not installed; cannot process $WP"
        exit 1
    fi

    # Define user-specific thumbnail path in a secure/private location
    THUMB_DIR="${XDG_RUNTIME_DIR:-/tmp/noctalia-$UID}"
    mkdir -p "$THUMB_DIR"
    chmod 700 "$THUMB_DIR" 2>/dev/null || true
    THUMB_PATH="$THUMB_DIR/mpvpaper_thumb.jpg"

    # Generate thumbnail
    if timeout 30 ffmpeg -y -i "$WP" -ss 00:00:01 -vframes 1 "$THUMB_PATH" 2>/dev/null; then
        # Set the thumbnail as wallpaper to extract colors and provide a static background
        noctalia msg wallpaper-set "$THUMB_PATH" 2>/dev/null \
            || log_error "Error: noctalia failed to set generated thumbnail for $WP"
    else
        log_error "Error: ffmpeg failed to extract thumbnail from $WP"
    fi
fi
