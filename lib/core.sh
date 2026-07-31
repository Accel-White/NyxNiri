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
    local p
    if [ ${#CLEANUP_TEMP_PATHS[@]} -gt 0 ]; then
        for p in "${CLEANUP_TEMP_PATHS[@]:-}"; do
            [ -n "$p" ] && rm -rf "$p" 2>/dev/null || true
        done
    fi
    if [ $exit_code -ne 0 ] && [ $exit_code -ne 130 ]; then
        echo -e "\n\e[1;31m[-] Action interrupted or terminated unexpectedly. (Exit Code: $exit_code)\e[0m"
    fi
}
trap cleanup EXIT INT TERM

# Global Variables & Paths
LANG_MODE="en"
PROJECT_NAME="NyxNiri"
REPO_URL="https://github.com/ech678/NyxNiri.git"
CACHE_DIR="$HOME/.cache/NyxNiri"
CONFIG_DIR_NAME="v2"

# XDG Compliance State & Log Engine
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/NyxNiri"
mkdir -p "$LOG_DIR" 2>/dev/null || true
INSTALL_LOG="$LOG_DIR/install.log"

init_logger() {
    if [ -f "$INSTALL_LOG" ]; then
        local tmp_log
        tmp_log=$(tail -n 800 "$INSTALL_LOG" 2>/dev/null || true)
        echo "$tmp_log" > "$INSTALL_LOG"
    fi
    echo "==================================================" >> "$INSTALL_LOG"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] NyxNiri Session Started (${CURRENT_VERSION:-v2.x})" >> "$INSTALL_LOG"
    echo "==================================================" >> "$INSTALL_LOG"
}

log_msg() {
    local level="${1:-INFO}"
    shift
    local raw_msg="$*"
    local clean_msg
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
        RUN_MODE="standalone"
        MODE_LABEL="Remote Cache"
        REPO_DIR="$CACHE_DIR"
    fi

    CURRENT_VERSION=$(get_version "$REPO_DIR")
}

# Ensure symlink ~/.local/bin/nyxniri points to install.sh
ensure_nyxniri_symlink() {
    mkdir -p "$HOME/.local/bin"
    local target_bin="$HOME/.local/bin/nyxniri"
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
