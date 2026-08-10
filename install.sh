#!/usr/bin/env bash

# ==============================================================================
# NyxNiri — Noctalia V5 & Niri Dotfiles Installer Bootstrap
# Single entry point for both local repository execution and online curl bootstraps.
# ==============================================================================

set -euo pipefail

CACHE_DIR="$HOME/.cache/NyxNiri"
REPO_URL="https://github.com/ech678/NyxNiri.git"

GIT_MIRROR_REGISTRY=(
    "Official|https://github.com/ech678/NyxNiri.git"
    "gh-proxy.org|https://gh-proxy.org/https://github.com/ech678/NyxNiri.git"
)

# Standalone bootstrap cannot source lib/network.sh, so keep a minimal local
# copy of the hardened shallow-clone helper (mirrors lib/network.sh behavior).
git_clone_timeout() {
    local url="$1" target_dir="$2"
    env GIT_TERMINAL_PROMPT=0 git clone -c http.lowSpeedTime=15 -c http.lowSpeedLimit=1000 --depth 1 "$url" "$target_dir"
}

clone_repo_bootstrap() {
    local target_dir="$1"
    echo -e "\e[1;34m:: 正在克隆与更新仓库至缓存目录 ($target_dir)…\e[0m" >&2

    local idx=1
    for item in "${GIT_MIRROR_REGISTRY[@]}"; do
        local tag="${item%%|*}"
        local url="${item#*|}"

        echo -e "  [$idx/${#GIT_MIRROR_REGISTRY[@]}] 从 [$tag] 节点拉取…" >&2
        
        local _t_depth
        _t_depth=$(printf '%s' "$target_dir" | tr -cd '/' | wc -c)
        if [ -n "$target_dir" ] && [ "$_t_depth" -ge 3 ] && [[ "$target_dir" == *".cache/NyxNiri" ]]; then
            rm -rf "$target_dir" 2>/dev/null || true
        fi

        if git_clone_timeout "$url" "$target_dir"; then
            echo -e "\e[1;32m[✓] 从 [$tag] 拉取完成\e[0m\n" >&2
            return 0
        fi
        idx=$((idx + 1))
    done

    echo -e "\e[1;31m[-] 所有 Git 节点拉取失败。请检查网络。\e[0m" >&2
    return 1
}

exec_main() {
    local target_dir="$1"
    shift
    chmod +x "$target_dir/lib/main.sh" 2>/dev/null || true
    if [ ! -t 0 ] && [ -t 1 ] && [ -r /dev/tty ]; then
        exec bash "$target_dir/lib/main.sh" "$@" < /dev/tty
    else
        exec bash "$target_dir/lib/main.sh" "$@"
    fi
}

main() {
    # Prevent running as root
    if [ "$(id -u)" -eq 0 ]; then
        echo -e "\n\e[1;31m[-] 禁止使用 root 运行。请以普通用户身份运行 ./install.sh\e[0m"
        echo -e "[-] Do not run as root. Re-run as normal user: ./install.sh\n"
        exit 1
    fi

    # Determine script location
    local real_script="" script_dir=""
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        real_script="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
        script_dir="$(cd "$(dirname "$real_script")" 2>/dev/null && pwd)"
    fi

    # Check if running inside local repository
    if [ -n "$script_dir" ] && [ -f "$script_dir/lib/main.sh" ]; then
        exec_main "$script_dir" "$@"
    fi

    # Standalone mode: requires git and cache repository
    if ! command -v git >/dev/null 2>&1; then
        echo -e "\e[1;31m[-] 未安装 git。请先安装 git\e[0m"
        echo -e "[-] git missing. Install git first."
        exit 1
    fi

    if [ ! -d "$CACHE_DIR/.git" ]; then
        clone_repo_bootstrap "$CACHE_DIR" || exit 1
    else
        echo -e "\e[1;34m:: 正在更新缓存仓库…\e[0m" >&2
        git -C "$CACHE_DIR" pull --ff-only --quiet 2>/dev/null || true
    fi

    if [ -f "$CACHE_DIR/lib/main.sh" ]; then
        exec_main "$CACHE_DIR" "$@"
    else
        echo -e "\e[1;31m[-] 缓存目录缺失 lib/main.sh。请删除 $CACHE_DIR 后重试\e[0m"
        exit 1
    fi
}

main "$@"
