#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Repository Management & Network Operations (Fallback & CDN Mirrored)
# ==============================================================================

set -euo pipefail

GIT_MIRROR_REGISTRY=(
    "Official|https://github.com/ech678/NyxNiri.git"
    "gh-proxy.org|https://gh-proxy.org/https://github.com/ech678/NyxNiri.git"
)

RAW_MIRROR_TEMPLATES=(
    "Official|https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"
    "jsDelivr-CDN|https://fastly.jsdelivr.net/gh/{USER_REPO}@{BRANCH}/{FILE_PATH}"
    "gh-proxy.org|https://gh-proxy.org/https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"
)

# Shallow clone with network hardening: never block on interactive credential
# prompts (GIT_TERMINAL_PROMPT=0) and abort stalled transfers instead of hanging
# forever (http.lowSpeedTime/Limit). The single canonical clone invocation so
# all mirror-fallback paths share identical behavior.
git_clone_timeout() {
    local url="$1" target_dir="$2"
    env GIT_TERMINAL_PROMPT=0 git clone -c http.lowSpeedTime=15 -c http.lowSpeedLimit=1000 --depth 1 "$url" "$target_dir"
}

# Select best working Git mirror url with explicit terminal logging
clone_repo_with_fallback() {
    local target_dir="$1"
    log_msg INFO "Starting Git clone with fallback (Priority: Official -> gh-proxy)"
    msg net_pull_repo

    local idx=1
    for item in "${GIT_MIRROR_REGISTRY[@]}"; do
        local tag="${item%%|*}"
        local url="${item#*|}"

        msg net_pull_node "$idx" "${#GIT_MIRROR_REGISTRY[@]}" "$tag"
        rm -rf "$target_dir" 2>/dev/null || true

        if git_clone_timeout "$url" "$target_dir"; then
            msg net_pull_node_ok "$tag"
            log_msg INFO "Git clone [$tag] SUCCESS ($url)"
            return 0
        else
            msg net_pull_node_fail "$tag"
            log_msg WARN "Git clone [$tag] FAILED ($url)"
        fi
        idx=$((idx + 1))
    done

    msg net_pull_all_fail
    log_msg ERROR "All Git clone attempts failed"
    return 1
}

# Fetch raw file with 3-tier fallback (Official -> jsDelivr CDN -> gh-proxy) and payload validation
fetch_raw_with_fallback() {
    local user_repo="$1"
    local branch="$2"
    local file_path="$3"
    local output_file="$4"

    log_msg INFO "Fetching raw file: $user_repo/$file_path ($branch)"
    msg net_download_asset "$user_repo" "$file_path"

    local idx=1
    for tpl_entry in "${RAW_MIRROR_TEMPLATES[@]}"; do
        local tag="${tpl_entry%%|*}"
        local template="${tpl_entry#*|}"

        local url="$template"
        url="${url//\{USER_REPO\}/$user_repo}"
        url="${url//\{BRANCH\}/$branch}"
        url="${url//\{FILE_PATH\}/$file_path}"

        echo -n "  [$idx/${#RAW_MIRROR_TEMPLATES[@]}] [$tag] $url … "
        local tmp_file
        tmp_file=$(mktemp) || continue
        register_temp_path "$tmp_file"

        local start_t
        start_t=$(date +%s%3N 2>/dev/null || date +%s)
        local http_code
        http_code=$(curl -sfL --connect-timeout 3 -m 10 -w "%{http_code}" -o "$tmp_file" "$url" 2>/dev/null || echo "000")
        local end_t
        end_t=$(date +%s%3N 2>/dev/null || date +%s)
        local dur=$((end_t - start_t))
        [ $dur -lt 0 ] && dur=0

        if [ "$http_code" = "200" ] && [ -s "$tmp_file" ] && ! head -n 5 "$tmp_file" | grep -qi "<html"; then
            msg net_download_ok "${dur}"
            log_msg INFO "Downloaded raw file via [$tag] ($url) - ${dur}ms"
            mv "$tmp_file" "$output_file"
            msg net_download_node_ok "$tag"
            return 0
        else
            msg net_download_fail "${http_code:-FAIL}"
            log_msg WARN "Fetch failed via [$tag] ($url) - HTTP ${http_code:-FAIL}"
            rm -f "$tmp_file" 2>/dev/null || true
        fi
        idx=$((idx + 1))
    done

    log_msg ERROR "Failed to fetch raw file $user_repo/$file_path from all mirror nodes."
    msg net_download_all_fail
    return 1
}

ensure_repo() {
    if [ "${RUN_MODE:-standalone}" = "standalone" ]; then
        if ! command -v git >/dev/null 2>&1; then
            msg git_required
            exit 1
        fi
        if [ ! -d "$CACHE_DIR/.git" ]; then
            msg cloning_repo

            local _cache_depth
            _cache_depth=$(printf '%s' "$CACHE_DIR" | tr -cd '/' | wc -c)
            if [ -d "$CACHE_DIR" ] && [ -n "$CACHE_DIR" ] && [[ "$CACHE_DIR" == *".cache/NyxNiri" ]] && [ "$_cache_depth" -ge 3 ]; then
                rm -rf "$CACHE_DIR"
            fi

            if ! clone_repo_with_fallback "$CACHE_DIR"; then
                exit 1
            fi
        fi
    fi
}

show_release_notes() {
    local changelog_file="$1"
    if [ -f "$changelog_file" ]; then
        echo -e "\n\e[1;35m════════════════════════════════════════════════════════════════\e[0m"
        if [ "${LANG_MODE:-en}" = "zh" ]; then
            msg net_changelog_title
        else
            echo -e " \e[1;36m:: Latest Release Notes (Changelog)\e[0m"
        fi
        echo -e "\e[1;35m════════════════════════════════════════════════════════════════\e[0m\n"
        awk '/^## /{count++} count==1{print} count>=2{exit}' "$changelog_file"
        echo -e "\e[1;35m════════════════════════════════════════════════════════════════\e[0m\n"
    fi
}

safe_pull_or_reset() {
    local dir="$1"
    (cd "$dir" && git -c http.lowSpeedLimit=0 -c http.lowSpeedTime=15 pull --ff-only) 2>/dev/null && return 0

    local dirty
    dirty=$(cd "$dir" && git status --porcelain 2>/dev/null || true)
    if [ -n "$dirty" ]; then
        log_msg WARN "Uncommitted changes in $dir before hard reset"
        msg dirty_tree_warn "$dir"
        if [ -t 0 ] && [ -c /dev/tty ]; then
            local confirm_reset=""
            read -r -p "$(msg dirty_tree_confirm)" confirm_reset < /dev/tty || confirm_reset="n"
            if [[ ! "$confirm_reset" =~ ^[Yy]$ ]]; then
                msg update_cancelled_dirty
                return 1
            fi
        fi
    fi
    (cd "$dir" && git -c http.lowSpeedLimit=0 -c http.lowSpeedTime=15 fetch && git reset --hard origin/main) 2>/dev/null || {
        log_msg ERROR "git fetch or reset failed in $dir"
        return 1
    }
}

update_repo_and_script() {
    local flag="${1:-}"
    shift || true
    if ! command -v git >/dev/null 2>&1; then
        msg git_required
        return 1
    fi

    msg checking_updates
    if [ "${RUN_MODE:-standalone}" = "repo" ]; then
        target_dir="$REPO_DIR"
    else
        target_dir="$CACHE_DIR"
    fi

    if safe_pull_or_reset "$target_dir"; then
        show_release_notes "$target_dir/CHANGELOG.md"
        discover_config_items
        offer_overwrite_upgrade "$flag"
        msg updating_done
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -r -p "$(msg press_any_key)" -n 1 _k < /dev/tty || sleep 1.5
        else
            sleep 1.5
        fi
        release_lock
        exec bash "$target_dir/lib/main.sh" "$@"
    else
        msg updating_failed
    fi
}
