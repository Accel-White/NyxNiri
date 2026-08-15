#!/bin/bash
# NyxNiri Multi-App Scratchpad Toggle
# Controls floating scratchpad lifecycle for Kitty, Mission Center, Nautilus, and custom apps.

# shellcheck disable=SC2317
set -uo pipefail

TARGET_APP="${1:-kitty}"

# ── Serialization Lock ──────────────────────────────────────────────
LOCK_NAME=$(printf '%s' "$TARGET_APP" | tr -c 'a-zA-Z0-9_' '_')
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/nyxniri-scratch-${LOCK_NAME}.lock"
flock -n 9 || exit 0

case "$TARGET_APP" in
    kitty|terminal|Kitty|Terminal)
        APP_ID="scratchpad"
        TMUX_SESSION="scratch"

        read -r win_id is_focused < <(niri msg -j windows 2>/dev/null \
            | jq -r --arg id "$APP_ID" \
                '.[] | select(.app_id == $id) | "\(.id) \(.is_focused)"' \
            | head -n1)

        spawn_kitty() {
            if command -v tmux >/dev/null 2>&1; then
                niri msg action spawn -- \
                    kitty --app-id "$APP_ID" --title "Scratchpad" \
                    tmux new-session -A -D -s "$TMUX_SESSION" \
                    "fish -C 'function fish_greeting; end' -C 'set -g fish_history scratchpad'" \; set-option status off
            else
                niri msg action spawn -- \
                    kitty --app-id "$APP_ID" --title "Scratchpad"
            fi
        }

        if [ -z "${win_id:-}" ]; then
            # No scratchpad window -> spawn and attach
            spawn_kitty
        elif [ "${is_focused:-false}" = "true" ]; then
            # Window currently focused -> hide (close frontend kitty window)
            niri msg action close-window --id "$win_id"
        else
            # Window exists on another workspace/unfocused -> relocate to current workspace
            niri msg action close-window --id "$win_id"
            sleep 0.05
            spawn_kitty
        fi
        ;;

    missioncenter|monitor|"mission center"|"Mission Center"|MissionCenter)
        APP_ID="io.missioncenter.MissionCenter"

        read -r win_id is_focused < <(niri msg -j windows 2>/dev/null \
            | jq -r --arg id "$APP_ID" \
                '.[] | select(.app_id == $id) | "\(.id) \(.is_focused)"' \
            | head -n1)

        if [ -z "${win_id:-}" ]; then
            if command -v missioncenter >/dev/null 2>&1; then
                niri msg action spawn -- missioncenter
            elif command -v flatpak >/dev/null 2>&1 && flatpak info io.missioncenter.MissionCenter >/dev/null 2>&1; then
                niri msg action spawn -- flatpak run io.missioncenter.MissionCenter
            fi
        elif [ "${is_focused:-false}" = "true" ]; then
            niri msg action close-window --id "$win_id"
        else
            niri msg action focus-window --id "$win_id"
        fi
        ;;

    nautilus|files|Nautilus|Files)
        APP_ID="org.gnome.Nautilus"

        read -r win_id is_focused < <(niri msg -j windows 2>/dev/null \
            | jq -r --arg id "$APP_ID" \
                '.[] | select(.app_id == $id) | "\(.id) \(.is_focused)"' \
            | head -n1)

        if [ -z "${win_id:-}" ]; then
            niri msg action spawn -- nautilus --new-window
        elif [ "${is_focused:-false}" = "true" ]; then
            niri msg action close-window --id "$win_id"
        else
            niri msg action focus-window --id "$win_id"
        fi
        ;;

    *)
        # Custom command or script execution
        if [[ "$TARGET_APP" =~ ^~.* ]]; then
            TARGET_APP="${TARGET_APP/#\~/$HOME}"
        fi
        if [ "$TARGET_APP" = "clean-cache" ] && [ -x "$HOME/.config/fish/clean-cache" ]; then
            TARGET_APP="$HOME/.config/fish/clean-cache"
        fi

        # If it is clean-cache or interactive terminal tool, launch inside floating scratchpad terminal
        if [ "$TARGET_APP" = "$HOME/.config/fish/clean-cache" ] || [[ "$TARGET_APP" == *clean-cache* ]]; then
            niri msg action spawn -- kitty --app-id "scratchpad" -e /bin/bash "$TARGET_APP"
        elif [ -x "$TARGET_APP" ] || command -v "$TARGET_APP" >/dev/null 2>&1; then
            niri msg action spawn -- "$TARGET_APP"
        else
            niri msg action spawn -- bash -c "$TARGET_APP"
        fi
        ;;
esac

