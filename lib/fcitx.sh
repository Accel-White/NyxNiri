#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Optional Module — NyxMellow Dynamic Fcitx5 Skin (Noctalia template)
# Deploys the mellow-shaped fcitx5 theme templates and registers them as
# Noctalia user templates so colors follow the Material You palette, then
# switches fcitx5 to the rendered theme. All steps are failure-tolerant.
# ==============================================================================

set -euo pipefail

FCITX_THEME="nyxmellow"
FCITX_THEMES_DIR="$HOME/.local/share/fcitx5/themes"
FCITX_THEME_DIR="$FCITX_THEMES_DIR/$FCITX_THEME"
FCITX_TEMPLATE_DIR="$FCITX_THEME_DIR/templates"
FCITX_CLASSICUI_CONF="$HOME/.config/fcitx5/conf/classicui.conf"
FCITX_NOCTALIA_CONFIG="$HOME/.config/noctalia/noctalia-config.toml"
FCITX_STATE_FILE="$HOME/.local/state/NyxNiri/fcitx-$FCITX_THEME-theme.prev"
FCITX_TEMPLATE_PREFIX="theme.templates.user.nyxmellow_"

# Resolve the repo source dir at call time: REPO_DIR is set by
# init_environment_paths *after* this module is sourced, so it must not be
# expanded here (would wrongly fall back to "." / the current working dir).
fcitx_source_dir() {
    echo "${REPO_DIR:-.}/fcitx5/$FCITX_THEME/templates"
}

fcitx5_installed() {
    command -v fcitx5 >/dev/null 2>&1
}

noctalia_available() {
    command -v noctalia >/dev/null 2>&1
}

fcitx_templates_registered() {
    [ -f "$FCITX_NOCTALIA_CONFIG" ] && grep -q "^\[${FCITX_TEMPLATE_PREFIX}" "$FCITX_NOCTALIA_CONFIG" 2>/dev/null
}

# Remember the pre-existing Theme/DarkTheme once, so uninstall can restore them.
fcitx_backup_theme_settings() {
    mkdir -p "$(dirname "$FCITX_STATE_FILE")"
    [ -f "$FCITX_STATE_FILE" ] && return 0
    local existed=0 t="" dt=""
    if [ -f "$FCITX_CLASSICUI_CONF" ]; then
        existed=1
        t=$(grep -m1 '^Theme=' "$FCITX_CLASSICUI_CONF" 2>/dev/null | cut -d= -f2- || true)
        dt=$(grep -m1 '^DarkTheme=' "$FCITX_CLASSICUI_CONF" 2>/dev/null | cut -d= -f2- || true)
    fi
    printf 'Existed=%s\nTheme=%s\nDarkTheme=%s\n' "$existed" "$t" "$dt" > "$FCITX_STATE_FILE"
}

fcitx_deploy_templates() {
    local src_dir
    src_dir="$(fcitx_source_dir)"
    if [ ! -d "$src_dir" ]; then
        echo "  [skip] 仓库中未找到主题模板源码: $src_dir"
        return 1
    fi
    mkdir -p "$FCITX_TEMPLATE_DIR"
    cp -a "$src_dir"/. "$FCITX_TEMPLATE_DIR"/ 2>/dev/null || cp -a "$src_dir" "$FCITX_TEMPLATE_DIR"/
    msg fcitx_templates_deployed
}

# Targeted update of classicui.conf (only touches Theme/DarkTheme).
fcitx_update_conf() {
    local key="$1" val="$2"
    local esc_val
    esc_val=$(printf '%s\n' "$val" | sed 's/[|&]/\\&/g')
    if [ -f "$FCITX_CLASSICUI_CONF" ] && grep -q "^${key}=" "$FCITX_CLASSICUI_CONF"; then
        sed -i "s|^${key}=.*|${key}=${esc_val}|" "$FCITX_CLASSICUI_CONF"
    else
        mkdir -p "$(dirname "$FCITX_CLASSICUI_CONF")"
        echo "${key}=${val}" >> "$FCITX_CLASSICUI_CONF"
    fi
}

fcitx_set_theme_conf() {
    fcitx_backup_theme_settings
    fcitx_update_conf "Theme" "$FCITX_THEME"
    fcitx_update_conf "DarkTheme" "$FCITX_THEME"
    msg fcitx_theme_set "$FCITX_CLASSICUI_CONF"
}

fcitx_restart() {
    if fcitx5_installed && pgrep -x fcitx5 >/dev/null 2>&1; then
        pkill -x fcitx5 2>/dev/null || true
        sleep 1
        fcitx5 -d >/dev/null 2>&1 || true
        msg fcitx_restarted
    fi
}

# Ask Noctalia to render the user templates for the current palette.
# config-reload first so a freshly deployed registration is picked up, then
# templates-apply renders unconditionally (unlike config-reload, which is a
# no-op when nothing changed).
fcitx_trigger_render() {
    if noctalia_available; then
        noctalia msg config-reload >/dev/null 2>&1 || true
        if noctalia msg templates-apply >/dev/null 2>&1; then
            msg fcitx_render_ok
        else
            msg fcitx_render_pending
        fi
    else
        msg fcitx_render_pending
    fi
}

fcitx_install() {
    msg fcitx_install_title
    if ! fcitx_deploy_templates; then
        return 1
    fi
    if fcitx5_installed; then
        fcitx_set_theme_conf
    else
        msg fcitx_skip_no_fcitx5
    fi
    fcitx_trigger_render
    fcitx_restart
}

# Failure-tolerant entry used by the main deploy flow (never aborts set -e).
deploy_fcitx_theme() {
    fcitx_install || true
}

fcitx_status() {
    msg fcitx_status_title

    if fcitx5_installed; then
        msg doctor_ok "fcitx5: installed"
    else
        msg doctor_warn "fcitx5: not installed"
    fi

    if fcitx_templates_registered; then
        msg fcitx_registered "$FCITX_NOCTALIA_CONFIG"
    else
        msg fcitx_not_registered "$FCITX_NOCTALIA_CONFIG"
    fi

    if [ -d "$FCITX_THEME_DIR" ]; then
        msg doctor_ok "theme dir: $FCITX_THEME_DIR"
        if [ -f "$FCITX_THEME_DIR/theme.conf" ] && [ -f "$FCITX_THEME_DIR/panel.svg" ] && [ -f "$FCITX_THEME_DIR/highlight.svg" ]; then
            msg doctor_ok "rendered files: present (follows Noctalia colors)"
        else
            msg doctor_warn "rendered files: missing — run noctalia msg config-reload or nyxniri fcitx install"
        fi
    else
        msg doctor_warn "theme dir: $FCITX_THEME_DIR missing"
    fi

    if [ -f "$FCITX_CLASSICUI_CONF" ]; then
        local t="" dt=""
        t=$(grep -m1 '^Theme=' "$FCITX_CLASSICUI_CONF" 2>/dev/null | cut -d= -f2- || true)
        dt=$(grep -m1 '^DarkTheme=' "$FCITX_CLASSICUI_CONF" 2>/dev/null | cut -d= -f2- || true)
        msg doctor_ok "classicui.conf: Theme=$t DarkTheme=$dt"
    else
        msg doctor_warn "classicui.conf: missing"
    fi
}

fcitx_uninstall() {
    msg fcitx_uninstall_title

    if fcitx_templates_registered; then
        awk '
            /^\[theme\.templates\.user\.nyxmellow_/ { skip = 1; next }
            skip && /^\[/ { skip = 0 }
            skip { next }
            { print }
        ' "$FCITX_NOCTALIA_CONFIG" > "$FCITX_NOCTALIA_CONFIG.tmp" && mv "$FCITX_NOCTALIA_CONFIG.tmp" "$FCITX_NOCTALIA_CONFIG"
        echo "  - Noctalia 模板注册已移除"
    fi

    if [ -d "$FCITX_THEME_DIR" ]; then
        rm -rf "$FCITX_THEME_DIR"
        echo "  - 已删除主题目录: $FCITX_THEME_DIR"
    fi

    if [ -f "$FCITX_STATE_FILE" ]; then
        local existed t dt
        existed=$(grep -m1 '^Existed=' "$FCITX_STATE_FILE" 2>/dev/null | cut -d= -f2- || true)
        t=$(grep -m1 '^Theme=' "$FCITX_STATE_FILE" 2>/dev/null | cut -d= -f2- || true)
        dt=$(grep -m1 '^DarkTheme=' "$FCITX_STATE_FILE" 2>/dev/null | cut -d= -f2- || true)
        if [ "$existed" != "1" ]; then
            rm -f "$FCITX_CLASSICUI_CONF"
        else
            if [ -n "$t" ]; then
                fcitx_update_conf "Theme" "$t"
            else
                sed -i '/^Theme=/d' "$FCITX_CLASSICUI_CONF" 2>/dev/null || true
            fi
            if [ -n "$dt" ]; then
                fcitx_update_conf "DarkTheme" "$dt"
            else
                sed -i '/^DarkTheme=/d' "$FCITX_CLASSICUI_CONF" 2>/dev/null || true
            fi
        fi
        rm -f "$FCITX_STATE_FILE"
    fi

    fcitx_restart
    msg fcitx_uninstall_done
}

fcitx_usage() {
    echo "NyxMellow dynamic fcitx5 skin"
    echo "Usage: nyxniri fcitx [install|uninstall|status]"
    echo ""
    echo "  install     Deploy theme templates, register Noctalia templates, switch fcitx5 to nyxmellow"
    echo "  status      Show current skin / template / fcitx5 theme state"
    echo "  uninstall   Remove the theme, unregister templates and restore previous fcitx5 theme"
}
