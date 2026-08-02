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
    "ghproxy.net|https://ghproxy.net/https://github.com/ech678/NyxNiri.git"
)

clone_repo_bootstrap() {
    local target_dir="$1"
    echo -e "\e[1;34m:: [Bootstrapper] 正在克隆/更新 NyxNiri 仓库到缓存目录 ($target_dir)... \e[0m" >&2

    local idx=1
    for item in "${GIT_MIRROR_REGISTRY[@]}"; do
        local tag="${item%%|*}"
        local url="${item#*|}"

        echo -e "  [$idx/${#GIT_MIRROR_REGISTRY[@]}] 尝试从 [$tag] 节点拉取..." >&2
        
        local _t_depth
        _t_depth=$(printf '%s' "$target_dir" | tr -cd '/' | wc -c)
        if [ -n "$target_dir" ] && [ "$_t_depth" -ge 3 ] && [[ "$target_dir" == *".cache/NyxNiri" ]]; then
            rm -rf "$target_dir" 2>/dev/null || true
        fi

        if git clone --depth 1 "$url" "$target_dir"; then
            echo -e "\e[1;32m✓ 从 [$tag] 成功拉取仓库！\e[0m\n" >&2
            return 0
        fi
        idx=$((idx + 1))
    done

    echo -e "\e[1;31m[-] 所有 Git 节点拉取失败，请检查网络设置。\e[0m" >&2
    return 1
}

main() {
    # Prevent running as root
    if [ "$(id -u)" -eq 0 ]; then
        echo -e "\n\e[1;31m[-] 错误: 请勿使用 root (或 sudo) 权限运行此脚本！\e[0m"
        echo -e "    Error: Do NOT run this installer as root or with sudo!\n"
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
        chmod +x "$script_dir/lib/main.sh" 2>/dev/null || true
        if [ ! -t 0 ] && [ -t 1 ] && [ -r /dev/tty ]; then
            exec bash "$script_dir/lib/main.sh" "$@" < /dev/tty
        else
            exec bash "$script_dir/lib/main.sh" "$@"
        fi
    fi

    # Standalone mode: requires git and cache repository
    if ! command -v git >/dev/null 2>&1; then
        echo -e "\e[1;31m[-] 错误: 需要安装 git 才能在线下载或安装 NyxNiri 配置仓库。\e[0m"
        echo -e "[-] Error: git is required to download or install NyxNiri."
        exit 1
    fi

    if [ ! -d "$CACHE_DIR/.git" ]; then
        clone_repo_bootstrap "$CACHE_DIR" || exit 1
    fi

    if [ -f "$CACHE_DIR/lib/main.sh" ]; then
        chmod +x "$CACHE_DIR/lib/main.sh" 2>/dev/null || true
        if [ ! -t 0 ] && [ -t 1 ] && [ -r /dev/tty ]; then
            exec bash "$CACHE_DIR/lib/main.sh" "$@" < /dev/tty
        else
            exec bash "$CACHE_DIR/lib/main.sh" "$@"
        fi
    else
        echo -e "\e[1;31m[-] 错误: 缓存目录中未找到 lib/main.sh，仓库可能损坏。\e[0m"
        exit 1
    fi
}

main "$@"
