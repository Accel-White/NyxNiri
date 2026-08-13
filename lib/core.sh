#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Core Infrastructure (Logging, Traps, Mode & Version Detection)
# ==============================================================================

set -euo pipefail

# Registry of temp paths created during this run; cleanup() sweeps all of them
# on exit/interrupt instead of relying on a single tracked path.
declare -a CLEANUP_TEMP_PATHS=()
register_temp_path() {
    CLEANUP_TEMP_PATHS+=("$1")
}

# Cleanup trap handler for unexpected signals or interruptions
cleanup() {
    local exit_code=$?
    printf '\e[?25h' 2>/dev/null || true
    release_lock
    local p
    if [ ${#CLEANUP_TEMP_PATHS[@]} -gt 0 ]; then
        for p in "${CLEANUP_TEMP_PATHS[@]:-}"; do
            [ -n "$p" ] && rm -rf "$p" 2>/dev/null || true
        done
    fi
    if [ $exit_code -ne 0 ] && [ $exit_code -ne 130 ]; then
        msg err_aborted_code "$exit_code"
    fi
}
trap cleanup EXIT INT TERM

# Resolve the user's Pictures directory (XDG-aware with HOME fallback).
# xdg-user-dir returns bare $HOME when the XDG user-dirs config is missing
# (headless/minimal setups), which is never the intended wallpaper location —
# remap it to the conventional $HOME/Pictures. Single source of truth shared
# by deploy (wallpapers), backup (purge) and doctor (health check).
get_pics_dir() {
    local d
    d=$(xdg-user-dir PICTURES 2>/dev/null || true)
    if [ -z "$d" ] || [ "$d" = "$HOME" ]; then
        d="$HOME/Pictures"
    fi
    printf '%s' "$d"
}

# Lightweight PID single-instance lock to prevent concurrent write collisions
NYXNIRI_LOCK_FILE=""
acquire_lock() {
    mkdir -p "$LOG_DIR" 2>/dev/null || true
    NYXNIRI_LOCK_FILE="$LOG_DIR/${CLI_CMD}.lock"
    if [ -f "$NYXNIRI_LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(cat "$NYXNIRI_LOCK_FILE" 2>/dev/null || echo "")
        if [ -n "$lock_pid" ] && [ "$lock_pid" != "$$" ] && kill -0 "$lock_pid" 2>/dev/null; then
            msg err_already_running "$lock_pid"
            exit 1
        fi
    fi
    echo "$$" > "$NYXNIRI_LOCK_FILE" 2>/dev/null || true
}

release_lock() {
    if [ -n "${NYXNIRI_LOCK_FILE:-}" ] && [ -f "$NYXNIRI_LOCK_FILE" ]; then
        local pid
        pid=$(cat "$NYXNIRI_LOCK_FILE" 2>/dev/null || echo "")
        if [ "$pid" = "$$" ]; then
            rm -f "$NYXNIRI_LOCK_FILE" 2>/dev/null || true
        fi
    fi
}

# --- DOTFILES ENGINE CONFIGURATION ---
export PROJECT_NAME="NyxNiri"
export CLI_CMD="nyxniri"
export REPO_URL="https://github.com/ech678/NyxNiri.git"
export MAIN_WM="niri"
export MAIN_WM_HARDWARE_CONFIG="monitor.kdl"
export THEME_ENGINE="noctalia"
export GREETER_PKG="noctalia-greeter"
export FCITX_THEME="nyxmellow"

# Global Variables & Paths
if [[ "${LANG:-}" == *zh* ]] || [[ "${LC_ALL:-}" == *zh* ]]; then
    export LANG_MODE="zh"
else
    export LANG_MODE="en"
fi
CACHE_DIR="$HOME/.cache/$PROJECT_NAME"
CONFIG_DIR_NAME="v2"

# XDG Compliance State & Log Engine
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/$PROJECT_NAME"
mkdir -p "$LOG_DIR" 2>/dev/null || true
INSTALL_LOG="$LOG_DIR/install.log"

init_logger() {
    if [ -f "$INSTALL_LOG" ]; then
        local tmp_log
        tmp_log=$(tail -n 800 "$INSTALL_LOG" 2>/dev/null || true)
        echo "$tmp_log" > "$INSTALL_LOG"
    fi
    {
        echo "──────────────────────────────────────────────────"
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $PROJECT_NAME Session Started (${CURRENT_VERSION:-v2.x})"
        echo "──────────────────────────────────────────────────"
    } >> "$INSTALL_LOG"
}

log_msg() {
    local level="${1:-INFO}"
    shift
    local raw_msg="$*"
    local clean_msg
    # shellcheck disable=SC2001
    clean_msg=$(echo "$raw_msg" | sed 's/\x1b\[[0-9;]*m//g')
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $clean_msg" >> "$INSTALL_LOG" 2>/dev/null || true
}

# Dynamic Version Extractor (Git Tag -> CHANGELOG.md -> Fallback)
get_version() {
    local target_dir="${1:-}"
    local version=""
    if [ -n "$target_dir" ] && [ -d "$target_dir/.git" ] && command -v git >/dev/null 2>&1; then
        version=$(cd "$target_dir" && git describe --tags --abbrev=0 2>/dev/null || true)
    fi
    if [ -z "$version" ] && [ -n "$target_dir" ] && [ -f "$target_dir/CHANGELOG.md" ]; then
        version=$(grep -m1 '^## \[' "$target_dir/CHANGELOG.md" 2>/dev/null | sed -E 's/## \[([^\]]+)\].*/\1/' || true)
    fi
    echo "${version:-v2.x}"
}

# Detect running mode & resolve source repo
init_environment_paths() {
    if [ -n "${BASH_SOURCE[1]:-}" ] && [ -f "${BASH_SOURCE[1]}" ]; then
        REAL_SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[1]}" 2>/dev/null || echo "${BASH_SOURCE[1]}")"
    elif [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        REAL_SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
    else
        REAL_SCRIPT_PATH=""
    fi

    if [ -n "${REAL_SCRIPT_PATH:-}" ]; then
        local current_dir
        current_dir="$(cd "$(dirname "$REAL_SCRIPT_PATH")" 2>/dev/null && pwd)"
        if [ "$(basename "$current_dir")" = "lib" ]; then
            SCRIPT_DIR="$(cd "$current_dir/.." 2>/dev/null && pwd)"
        else
            SCRIPT_DIR="$current_dir"
        fi
    else
        SCRIPT_DIR=""
    fi

    if [ -n "${SCRIPT_DIR:-}" ] && [ -d "$SCRIPT_DIR/$CONFIG_DIR_NAME" ] && [ -d "$SCRIPT_DIR/Wallpapers" ]; then
        RUN_MODE="repo"
        MODE_LABEL="Local Path"
        REPO_DIR="$SCRIPT_DIR"
    else
        export RUN_MODE="standalone"
        export MODE_LABEL="Remote Cache"
        REPO_DIR="$CACHE_DIR"
    fi

    CURRENT_VERSION=$(get_version "$REPO_DIR")
}

# Ensure symlink ~/.local/bin/$CLI_CMD points to install.sh
ensure_nyxniri_symlink() {
    mkdir -p "$HOME/.local/bin"
    local target_bin="$HOME/.local/bin/$CLI_CMD"
    local root_installer="${SCRIPT_DIR:-}/install.sh"

    if [ -z "$root_installer" ] || [ ! -f "$root_installer" ]; then
        if [ -f "$CACHE_DIR/install.sh" ]; then
            root_installer="$CACHE_DIR/install.sh"
        else
            return 0
        fi
    fi

    if [ ! -L "$target_bin" ] || [ "$(readlink -f "$target_bin" 2>/dev/null)" != "$root_installer" ]; then
        ln -sf "$root_installer" "$target_bin"
        [ -f "$root_installer" ] && chmod +x "$root_installer" 2>/dev/null || true
    fi
}

# Pure Bash single key reader for TUI navigation (supports arrow keys, space, enter, numbers)
read_key() {
    local key=""
    IFS= read -rsn1 key < /dev/tty 2>/dev/null || return 1
    if [[ "$key" == $'\x1b' ]]; then
        local subkey=""
        read -rsn2 -t 0.05 subkey < /dev/tty 2>/dev/null || true
        case "$subkey" in
            "[A"|"OA") key="UP" ;;
            "[B"|"OB") key="DOWN" ;;
            "[C"|"OC") key="RIGHT" ;;
            "[D"|"OD") key="LEFT" ;;
            *) key="ESC" ;;
        esac
    elif [[ "$key" == "" ]]; then
        key="ENTER"
    elif [[ "$key" == " " ]]; then
        key="SPACE"
    fi
    printf '%s' "$key"
}

