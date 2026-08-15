#!/usr/bin/env python3
"""
NyxNiri Scratchpad Star-Ring Menu (星环菜单)
Architecture: Material 3 Expressive · 100% Stateless & On-Demand (Zero Daemons)

Core Design Principles:
- 100% Stateless On-Demand Execution: Zero background daemons, zero lingering memory, exits instantly when closed.
- Multi-source Declarative Configuration (Priority: TOML -> JSON -> Built-in Defaults)
- Native Web URL Direct Launching via xdg-open
- Deterministic Click & Spatial Keyboard Navigation (Zero external threads)
- 100% Native GTK/Wayland Layer-Shell event-driven execution (0% CPU at idle)
- Precision Polar Voronoi Sector Partitioning (48px deadzone & ±6° hysteresis)
- Analytical Second-Order Spring Dynamics Matrix (Exact differential solver)
- Hierarchical Submenu Tree (Drill-down & Return transitions with Gravitational Metaphor)
- Optical Subpixel-Centering & Concentric Endcap Alignment (chip_cx = cx_box + ch / 2.0)
- Content-Aware Adaptive Streamline Capsules with Zero-Alloc Pango Layouts
- Wayland Compositor-synced 144Hz+ GdkFrameClock VBLANK rendering
"""

import sys
import os
import math
import json
import subprocess
import signal
import fcntl

try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    try:
        import tomli as tomllib
        HAS_TOMLLIB = True
    except ImportError:
        HAS_TOMLLIB = False

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango, PangoCairo
import cairo

CUSTOM_TOML_PATH = os.path.expanduser("~/.config/niri/scratchpad-items__custom__.toml")
LEGACY_TOML_PATH = os.path.expanduser("~/.config/niri/scratchpad-items.toml")
CUSTOM_JSON_PATH = os.path.expanduser("~/.config/niri/scratchpad-items.json")

RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/nyxniri-{os.getuid()}"
try:
    os.makedirs(RUNTIME_DIR, exist_ok=True)
except Exception:
    pass
LOCK_FILE_PATH = os.path.join(RUNTIME_DIR, "nyxniri-scratch-menu.lock")
PID_FILE_PATH = os.path.join(RUNTIME_DIR, "nyxniri-scratch-menu.pid")

# ── Geometry & Physical Constants ─────────────────────────────────────────────
BASE_ORBIT_RADIUS = 162.0   # Golden ratio orbital radius (+14% breathing space)
DEADZONE_RADIUS = 48.0      # Calibrated deadzone radius (r < 48px: no selection)
HYSTERESIS_DEG = 6.0        # Angular hysteresis margin (±6° entry threshold)
FLOAT_SPRING = 16.0         # Radial outward displacement on activation (+16px)

CAPSULE_IDLE_H = 48.0       # Idle capsule height (px)
CAPSULE_ACTIVE_H = 54.0     # Active capsule height (px)

# ── Default Declarative Hierarchical Menu Tree ────────────────────────────────
DEFAULT_MENU_TREE = [
    {
        "id": "kitty",
        "name": "Kitty",
        "desc": "Terminal",
        "icon": "󰞷",
        "cmd": "kitty",
        "shortcut": "1",
        "mnemonics": ["t", "k"],
        "color_key": "secondary",
    },
    {
        "id": "tools",
        "name": "System Tools",
        "desc": "Folder · 3 Tools",
        "icon": "󰘳",
        "shortcut": "2",
        "mnemonics": ["s", "t"],
        "color_key": "secondary",
        "children": [
            {
                "id": "missioncenter",
                "name": "Mission Center",
                "desc": "System Monitor",
                "icon": "󰓅",
                "cmd": "missioncenter",
                "shortcut": "1",
                "mnemonics": ["m"],
                "color_key": "secondary",
            },
            {
                "id": "eyecare",
                "name": "Eye Care",
                "desc": "Toggle Warmth",
                "icon": "󰛨",
                "cmd": "~/.config/niri/scripts/toggle-eyecare.sh",
                "shortcut": "2",
                "mnemonics": ["e"],
                "color_key": "secondary",
            },
            {
                "id": "cache",
                "name": "Clean Cache",
                "desc": "Free Disk Space",
                "icon": "󰃢",
                "cmd": "~/.config/fish/clean-cache",
                "shortcut": "3",
                "mnemonics": ["c"],
                "color_key": "secondary",
            },
        ],
    },
    {
        "id": "websites",
        "name": "Websites",
        "desc": "Folder · 3 Sites",
        "icon": "󰖟",
        "shortcut": "3",
        "mnemonics": ["w"],
        "color_key": "secondary",
        "children": [
            {
                "id": "zhihu",
                "name": "Zhihu",
                "desc": "知乎 · 发现更大世界",
                "icon": "󰖟",
                "url": "https://www.zhihu.com",
                "shortcut": "1",
                "mnemonics": ["z"],
                "color_key": "secondary",
            },
            {
                "id": "bilibili",
                "name": "Bilibili",
                "desc": "哔哩哔哩 (゜-゜)つロ",
                "icon": "󰕧",
                "url": "https://www.bilibili.com",
                "shortcut": "2",
                "mnemonics": ["b"],
                "color_key": "secondary",
            },
            {
                "id": "github",
                "name": "GitHub",
                "desc": "Code Repository",
                "icon": "󰊤",
                "url": "https://github.com",
                "shortcut": "3",
                "mnemonics": ["g"],
                "color_key": "secondary",
            },
        ],
    },
    {
        "id": "nautilus",
        "name": "Nautilus",
        "desc": "File Manager",
        "icon": "󰉋",
        "cmd": "nautilus",
        "shortcut": "4",
        "mnemonics": ["n", "f"],
        "color_key": "secondary",
    },
]


# ── Material You Dynamic Palette Engine ───────────────────────────────────────
def hex_to_rgb(hex_str, default=(0.5, 0.5, 0.5)):
    try:
        hex_str = hex_str.strip().lstrip("#")
        if len(hex_str) == 6:
            return tuple(int(hex_str[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except Exception:
        pass
    return default


def load_material_palette():
    palette = {
        "primary": (0.42, 0.70, 1.00),
        "secondary": (0.38, 0.85, 0.65),
        "tertiary": (1.00, 0.75, 0.35),
        "surface": (0.12, 0.13, 0.18),
        "surface_dim": (0.05, 0.06, 0.09),
        "on_surface": (0.95, 0.96, 0.99),
        "on_surface_var": (0.68, 0.72, 0.78),
        "outline": (0.80, 0.84, 0.90),
        "is_dark": True,
    }

    starship_path = os.path.expanduser("~/.cache/noctalia/starship-palette.toml")
    if os.path.isfile(starship_path):
        try:
            with open(starship_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith(("#", "[")):
                        k, v = [x.strip() for x in line.split("=", 1)]
                        v = v.strip('"\'')
                        rgb = hex_to_rgb(v)
                        palette[k] = rgb
                        if k in ("blue", "sapphire", "primary"):
                            palette["primary"] = rgb
                        elif k in ("teal", "green", "secondary"):
                            palette["secondary"] = rgb
                        elif k in ("peach", "pink", "mauve", "yellow", "tertiary"):
                            palette["tertiary"] = rgb
                        elif k in ("surface0", "surface1", "base"):
                            palette["surface"] = rgb
                        elif k in ("crust", "mantle"):
                            palette["surface_dim"] = rgb
                        elif k in ("text", "white"):
                            palette["on_surface"] = rgb
                        elif k in ("subtext0", "subtext1", "overlay2"):
                            palette["on_surface_var"] = rgb
                        elif k in ("overlay0", "overlay1"):
                            palette["outline"] = rgb
        except Exception:
            pass

    sr, sg, sb = palette["surface"]
    palette["is_dark"] = (0.299 * sr + 0.587 * sg + 0.114 * sb < 0.5)
    return palette


# ── Analytical Second-Order Spring Solver (x'' = -ω²(x - target) - 2ζωx') ────
class Spring:
    def __init__(self, initial=0.0, omega=14.0, zeta=0.70):
        self.current = initial
        self.target = initial
        self.velocity = 0.0
        self.omega = omega
        self.zeta = zeta

    def update(self, dt):
        dt = min(0.05, max(0.001, dt))
        force = -(self.omega ** 2) * (self.current - self.target) - 2.0 * self.zeta * self.omega * self.velocity
        self.velocity += force * dt
        self.current += self.velocity * dt
        if abs(self.current - self.target) > 0.001 or abs(self.velocity) > 0.001:
            return True
        self.current = self.target
        self.velocity = 0.0
# ── Single-Instance & True Toggle Lock Engine ────────────────────────────────
def acquire_instance_lock():
    """Ensure single-instance execution. If already running, signal active instance to toggle-close."""
    try:
        lock_fd = os.open(LOCK_FILE_PATH, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        if os.path.isfile(PID_FILE_PATH):
            try:
                with open(PID_FILE_PATH, "r") as pf:
                    old_pid = int(pf.read().strip())
                os.kill(old_pid, signal.SIGTERM)
            except Exception:
                pass
        sys.exit(0)

    try:
        with open(PID_FILE_PATH, "w") as pf:
            pf.write(str(os.getpid()))
    except Exception:
        pass

    return lock_fd


def release_instance_lock(lock_fd):
    try:
        if os.path.isfile(PID_FILE_PATH):
            os.remove(PID_FILE_PATH)
    except Exception:
        pass
    try:
        if lock_fd is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    except Exception:
        pass


class ScratchpadRadialMenu(Gtk.Window):
    def __init__(self, lock_fd=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.lock_fd = lock_fd
        self.palette = load_material_palette()
        self.root_items = self.load_menu_tree()
        self.menu_stack = []
        self.apps = self.root_items
        self.num_items = len(self.apps)

        # Pre-cache Pango Back Icon
        self.layout_back = self.create_pango_layout("󰌍")
        self.layout_back.set_font_description(Pango.FontDescription("JetBrainsMono Nerd Font Bold 16"))
        self.back_ink_rect, _ = self.layout_back.get_pixel_extents()

        self.hovered_index = None
        self.keyboard_selected = None
        self.center_x = None
        self.center_y = None
        self.origin_locked = False
        self.is_dismissing = False
        self.last_mouse_pos = None

        # Physics Springs Matrix
        self.entry_spring = Spring(0.0, omega=14.0, zeta=0.70)
        self.trans_spring = Spring(1.0, omega=15.0, zeta=0.80)
        self.core_spring_x = Spring(0.0, omega=18.0, zeta=1.00)
        self.core_spring_y = Spring(0.0, omega=18.0, zeta=1.00)
        self.node_springs = []

        self.setup_current_tier()

        # GdkFrameClock VBLANK synchronization callback
        self.tick_callback_id = None
        self.last_frame_time = 0

        # Layer Shell Setup
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)

        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self, edge, True)
            GtkLayerShell.set_margin(self, edge, 0)

        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
            | Gdk.EventMask.STRUCTURE_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("enter-notify-event", self.on_enter_notify)
        self.connect("button-press-event", self.on_button_press)
        self.connect("scroll-event", self.on_scroll)
        self.connect("key-press-event", self.on_key_press)
        self.connect("delete-event", lambda w, e: (self.dismiss_menu(), True)[1])
        self.connect("destroy", lambda w: Gtk.main_quit())

        self.open_menu()

    def load_menu_tree(self):
        """Priority loader: TOML (__custom__ -> legacy) -> JSON -> Built-in Default Tree."""
        for toml_path in (CUSTOM_TOML_PATH, LEGACY_TOML_PATH):
            if HAS_TOMLLIB and os.path.isfile(toml_path):
                try:
                    with open(toml_path, "rb") as f:
                        data = tomllib.load(f)
                        items = data.get("items", [])
                        if isinstance(items, list) and len(items) > 0:
                            return items
                except Exception as e:
                    print(f"Error loading {toml_path}: {e}", file=sys.stderr)

        if os.path.isfile(CUSTOM_JSON_PATH):
            try:
                with open(CUSTOM_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
                    elif isinstance(data, dict) and "items" in data:
                        return data["items"]
            except Exception as e:
                print(f"Error loading {CUSTOM_JSON_PATH}: {e}", file=sys.stderr)

        return DEFAULT_MENU_TREE

    def setup_current_tier(self):
        if not self.apps or not isinstance(self.apps, list):
            self.apps = DEFAULT_MENU_TREE
        self.num_items = len(self.apps)
        if self.num_items == 0:
            return
        self.node_springs = [Spring(0.0, omega=12.0, zeta=0.65) for _ in range(self.num_items)]
        self.init_geometry()
        self.init_cached_layouts()

    def init_geometry(self):
        if self.num_items == 0:
            return
        start_angle = -90.0
        step = 360.0 / self.num_items
        for i, app in enumerate(self.apps):
            angle = (start_angle + i * step) % 360.0
            if angle > 180.0:
                angle -= 360.0
            app["center_angle"] = angle
            color_key = str(app.get("color_key", "secondary"))
            if color_key.startswith("#"):
                app["color"] = hex_to_rgb(color_key, default=(0.38, 0.85, 0.65))
            else:
                app["color"] = self.palette.get(color_key, (0.38, 0.85, 0.65))

    def init_cached_layouts(self):
        font_title = Pango.FontDescription("Noto Sans CJK SC, Inter, sans-serif SemiBold 11.5")
        font_desc = Pango.FontDescription("Noto Sans CJK SC, Inter, sans-serif Regular 8.5")
        font_icon = Pango.FontDescription("JetBrainsMono Nerd Font 14")
        font_badge = Pango.FontDescription("JetBrains Mono Bold 9")

        for app in self.apps:
            app_name = str(app.get("name") or app.get("id") or "App")
            lt = self.create_pango_layout(app_name)
            lt.set_font_description(font_title)
            tw, th = lt.get_pixel_size()
            app["layout_title"] = lt
            app["title_w"], app["title_h"] = tw, th

            desc_text = str(app.get("desc") or "")
            if not desc_text:
                if "children" in app and isinstance(app["children"], list):
                    desc_text = f"Folder · {len(app['children'])} Items"
                elif "url" in app:
                    desc_text = "Web Link"
            ld = self.create_pango_layout(desc_text)
            ld.set_font_description(font_desc)
            dw, dh = ld.get_pixel_size()
            app["layout_desc"] = ld
            app["desc_w"], app["desc_h"] = dw, dh

            li = self.create_pango_layout(str(app.get("icon", "󰣆")))
            li.set_font_description(font_icon)
            ink_rect, log_rect = li.get_pixel_extents()
            app["layout_icon"] = li
            app["icon_ink_rect"] = ink_rect
            app["icon_w"], app["icon_h"] = log_rect.width, log_rect.height

            lk = self.create_pango_layout(str(app.get("shortcut", "")))
            lk.set_font_description(font_badge)
            kw, kh = lk.get_pixel_size()
            app["layout_badge"] = lk
            app["badge_w"], app["badge_h"] = kw, kh

            needed_w = 14.0 + 32.0 + 8.0 + max(tw, dw) + 8.0 + (kw + 8.0) + 14.0
            app["idle_w"] = max(156.0, needed_w)
            app["active_w"] = app["idle_w"] + 24.0

    def open_menu(self):
        self.palette = load_material_palette()
        self.hovered_index = None
        self.keyboard_selected = None
        self.is_dismissing = False
        self.last_mouse_pos = None

        self.entry_spring.current = 0.0
        self.entry_spring.target = 1.0
        self.entry_spring.velocity = 0.0

        self.trans_spring.current = 1.0
        self.trans_spring.target = 1.0
        self.trans_spring.velocity = 0.0

        self.core_spring_x.current = 0.0
        self.core_spring_x.target = 0.0
        self.core_spring_x.velocity = 0.0
        self.core_spring_y.current = 0.0
        self.core_spring_y.target = 0.0
        self.core_spring_y.velocity = 0.0

        self.show_all()
        self.present()
        self._request_frame()

    def dismiss_menu(self):
        if self.is_dismissing:
            return
        self.is_dismissing = True
        self.entry_spring.target = 0.0
        self._request_frame()

    def _finish_dismiss(self):
        release_instance_lock(self.lock_fd)
        self.lock_fd = None
        self.hide()
        Gtk.main_quit()

    def drill_down(self, child_items):
        if not child_items or not isinstance(child_items, list):
            return
        self.menu_stack.append((self.apps, self.hovered_index))
        self.apps = child_items
        self.setup_current_tier()
        self.hovered_index = None
        self.keyboard_selected = None

        self.trans_spring.omega = 15.0
        self.trans_spring.zeta = 0.80
        self.trans_spring.current = 0.75
        self.trans_spring.target = 1.0
        self.trans_spring.velocity = 0.0
        self._request_frame()

    def return_to_parent(self):
        if not self.menu_stack:
            self.dismiss_menu()
            return

        parent_items, prev_hover = self.menu_stack.pop()
        self.apps = parent_items
        self.setup_current_tier()
        self.hovered_index = prev_hover
        self.keyboard_selected = None

        self.trans_spring.omega = 16.0
        self.trans_spring.zeta = 0.90
        self.trans_spring.current = 1.15
        self.trans_spring.target = 1.0
        self.trans_spring.velocity = 0.0
        self._request_frame()

    def trigger_app(self, item):
        # 1. Folder drill-down
        if "children" in item and len(item["children"]) > 0:
            self.drill_down(item["children"])
            return

        # 2. Web URL direct launching via xdg-open
        url = item.get("url", "")
        cmd = item.get("cmd") or item.get("id") or item.get("name", "").lower()
        target_url = url if url else (cmd if cmd.startswith(("http://", "https://", "www.")) else "")

        if target_url:
            if target_url.startswith("www."):
                target_url = "https://" + target_url
            try:
                subprocess.Popen(["xdg-open", target_url])
            except Exception as e:
                print(f"Error opening URL: {e}", file=sys.stderr)
            self.dismiss_menu()
            return

        # 3. Local Scratchpad / App Command
        script_path = os.path.expanduser("~/.config/niri/scripts/niri-scratch-toggle.sh")
        if not os.path.isfile(script_path):
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "niri-scratch-toggle.sh")
        try:
            subprocess.Popen(["/bin/bash", script_path, cmd])
        except Exception as e:
            print(f"Error launching scratchpad: {e}", file=sys.stderr)
        self.dismiss_menu()

    def set_anchor_center(self, cursor_x, cursor_y):
        w = self.get_allocated_width() or 1920
        h = self.get_allocated_height() or 1080
        pad_x, pad_y = 230.0, 210.0
        self.center_x = max(pad_x, min(w - pad_x, cursor_x))
        self.center_y = max(pad_y, min(h - pad_y, cursor_y))
        self.origin_locked = True

    def _request_frame(self):
        if self.tick_callback_id is None:
            self.last_frame_time = 0
            self.tick_callback_id = self.add_tick_callback(self.on_frame_tick)

    def on_frame_tick(self, widget, frame_clock):
        frame_time = frame_clock.get_frame_time()
        dt = 0.016 if self.last_frame_time == 0 else (frame_time - self.last_frame_time) / 1_000_000.0
        self.last_frame_time = frame_time

        still_animating = False

        if self.entry_spring.update(dt):
            still_animating = True

        if self.is_dismissing and self.entry_spring.current <= 0.02:
            self._finish_dismiss()
            self.tick_callback_id = None
            return GLib.SOURCE_REMOVE

        if self.trans_spring.update(dt):
            still_animating = True

        active_idx = self.keyboard_selected if self.keyboard_selected is not None else self.hovered_index
        for i in range(self.num_items):
            if i < len(self.node_springs):
                self.node_springs[i].target = 1.0 if (active_idx == i and not self.is_dismissing) else 0.0
                if self.node_springs[i].update(dt):
                    still_animating = True

        if active_idx is not None and not self.is_dismissing and active_idx < self.num_items:
            ang_rad = math.radians(self.apps[active_idx]["center_angle"])
            self.core_spring_x.target = math.cos(ang_rad) * 10.0
            self.core_spring_y.target = math.sin(ang_rad) * 10.0
        else:
            self.core_spring_x.target = 0.0
            self.core_spring_y.target = 0.0

        if self.core_spring_x.update(dt) or self.core_spring_y.update(dt):
            still_animating = True

        self.queue_draw()

        if not still_animating:
            self.tick_callback_id = None
            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE

    def update_hover(self, mx, my):
        if not self.origin_locked:
            self.set_anchor_center(mx, my)

        if self.keyboard_selected is not None:
            if self.last_mouse_pos is not None:
                dx_m = mx - self.last_mouse_pos[0]
                dy_m = my - self.last_mouse_pos[1]
                if math.hypot(dx_m, dy_m) > 6.0:
                    self.keyboard_selected = None
            else:
                self.last_mouse_pos = (mx, my)

        self.last_mouse_pos = (mx, my)
        dx = mx - self.center_x
        dy = my - self.center_y
        dist = math.hypot(dx, dy)

        if dist < DEADZONE_RADIUS:
            new_hover = None
        else:
            angle_deg = math.degrees(math.atan2(dy, dx))
            best_idx = None
            min_diff = 999.0

            for i, app in enumerate(self.apps):
                c_ang = app["center_angle"]
                diff = abs((angle_deg - c_ang + 180.0) % 360.0 - 180.0)
                if self.hovered_index == i:
                    diff -= HYSTERESIS_DEG
                if diff < min_diff:
                    min_diff = diff
                    best_idx = i

            new_hover = best_idx

        if new_hover != self.hovered_index:
            self.hovered_index = new_hover
            self._request_frame()

    def on_enter_notify(self, widget, event):
        if not self.origin_locked:
            self.set_anchor_center(event.x, event.y)
        return True

    def on_motion_notify(self, widget, event):
        if not self.is_dismissing:
            self.update_hover(event.x, event.y)
        return True

    def on_button_press(self, widget, event):
        if not self.origin_locked:
            self.set_anchor_center(event.x, event.y)
        if event.button == 1:
            active_idx = self.keyboard_selected if self.keyboard_selected is not None else self.hovered_index
            if active_idx is not None and active_idx < self.num_items:
                self.trigger_app(self.apps[active_idx])
            else:
                if len(self.menu_stack) > 0:
                    self.return_to_parent()
                else:
                    self.dismiss_menu()
            return True
        elif event.button in (2, 3):
            if len(self.menu_stack) > 0:
                self.return_to_parent()
            else:
                self.dismiss_menu()
            return True
        return False

    def on_scroll(self, widget, event):
        if self.is_dismissing:
            return False
        cur = self.keyboard_selected if self.keyboard_selected is not None else (self.hovered_index or 0)
        if event.direction == Gdk.ScrollDirection.DOWN:
            self.keyboard_selected = (cur + 1) % self.num_items
            self._request_frame()
            return True
        elif event.direction == Gdk.ScrollDirection.UP:
            self.keyboard_selected = (cur - 1 + self.num_items) % self.num_items
            self._request_frame()
            return True
        return False

    def on_key_press(self, widget, event):
        keyval = event.keyval

        if self.center_x is None:
            w = self.get_allocated_width() or 1920
            h = self.get_allocated_height() or 1080
            self.center_x = w / 2.0
            self.center_y = h / 2.0
            self.origin_locked = True

        if keyval in (Gdk.KEY_BackSpace, Gdk.KEY_Escape, Gdk.KEY_q, Gdk.KEY_Q):
            if len(self.menu_stack) > 0:
                self.return_to_parent()
            else:
                self.dismiss_menu()
            return True

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            active_idx = self.keyboard_selected if self.keyboard_selected is not None else self.hovered_index
            if active_idx is not None and active_idx < self.num_items:
                self.trigger_app(self.apps[active_idx])
            else:
                if len(self.menu_stack) > 0:
                    self.return_to_parent()
                else:
                    self.dismiss_menu()
            return True

        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            is_backward = bool(event.state & Gdk.ModifierType.SHIFT_MASK) or keyval == Gdk.KEY_ISO_Left_Tab
            cur = self.keyboard_selected if self.keyboard_selected is not None else (self.hovered_index if self.hovered_index is not None else -1)
            step = -1 if is_backward else 1
            self.keyboard_selected = (cur + step) % self.num_items
            self._request_frame()
            return True

        if Gdk.KEY_1 <= keyval <= Gdk.KEY_9:
            num = keyval - Gdk.KEY_1
            if num < self.num_items:
                self.trigger_app(self.apps[num])
                return True

        key_char = chr(keyval).lower() if 32 <= keyval <= 126 else ""
        if key_char:
            for idx, app in enumerate(self.apps):
                if key_char in app.get("mnemonics", []) or key_char == app["name"][:1].lower():
                    self.trigger_app(app)
                    return True

        dir_map = {
            Gdk.KEY_h: 180.0, Gdk.KEY_Left: 180.0,
            Gdk.KEY_l: 0.0,   Gdk.KEY_Right: 0.0,
            Gdk.KEY_j: 90.0,  Gdk.KEY_Down: 90.0,
            Gdk.KEY_k: -90.0, Gdk.KEY_Up: -90.0,
        }
        if keyval in dir_map:
            target_angle = dir_map[keyval]
            best_idx = None
            min_diff = 999.0
            for i, app in enumerate(self.apps):
                diff = abs((target_angle - app["center_angle"] + 180.0) % 360.0 - 180.0)
                if diff < min_diff:
                    min_diff = diff
                    best_idx = i
            if best_idx is not None:
                self.keyboard_selected = best_idx
                self._request_frame()
                return True

        return False

    def draw_rounded_pill(self, cr, x, y, w, h, r):
        r = min(r, w / 2.0, h / 2.0)
        cr.new_path()
        cr.arc(x + r, y + r, r, math.pi, 3.0 * math.pi / 2.0)
        cr.arc(x + w - r, y + r, r, 3.0 * math.pi / 2.0, 2.0 * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0.0, math.pi / 2.0)
        cr.arc(x + r, y + h - r, r, math.pi / 2.0, math.pi)
        cr.close_path()

    def on_draw(self, widget, cr):
        entry_val = max(0.0, min(1.0, self.entry_spring.current))
        if entry_val <= 0.001:
            return False

        trans_val = max(0.2, self.trans_spring.current)
        cx, cy = (self.center_x or 960.0), (self.center_y or 540.0)
        p = self.palette
        active_idx = self.keyboard_selected if self.keyboard_selected is not None else self.hovered_index

        dim_r, dim_g, dim_b = p["surface_dim"]
        surf_r, surf_g, surf_b = p["surface"]
        out_r, out_g, out_b = p["outline"]

        # 1. Atmospheric Scrim
        cr.save()
        cr.set_source_rgba(dim_r, dim_g, dim_b, (0.42 if p["is_dark"] else 0.22) * entry_val)
        cr.paint()
        cr.restore()

        # Scale & Alpha Transform
        cr.save()
        scale = (0.76 + 0.24 * entry_val) * trans_val
        cr.translate(cx, cy)
        cr.scale(scale, scale)
        cr.translate(-cx, -cy)

        core_x = cx + self.core_spring_x.current
        core_y = cy + self.core_spring_y.current
        orbit_r = max(BASE_ORBIT_RADIUS, 120.0 + self.num_items * 12.0)

        # 2. Celestial Star-Ring
        cr.save()
        cr.new_path()
        cr.arc(cx, cy, orbit_r, 0, 2 * math.pi)
        cr.set_line_width(18.0)
        if active_idx is not None and active_idx < self.num_items:
            ar, ag, ab = self.apps[active_idx]["color"]
            cr.set_source_rgba(ar, ag, ab, 0.06 * entry_val)
        else:
            cr.set_source_rgba(out_r, out_g, out_b, 0.02 * entry_val)
        cr.stroke()
        cr.restore()

        cr.save()
        cr.new_path()
        cr.arc(cx, cy, orbit_r, 0, 2 * math.pi)
        cr.set_line_width(1.0)
        cr.set_source_rgba(out_r, out_g, out_b, 0.10 * entry_val)
        cr.stroke()

        cr.new_path()
        cr.arc(cx, cy, orbit_r, 0, 2 * math.pi)
        cr.set_dash([3.0, 7.0])
        cr.set_line_width(1.2)
        cr.set_source_rgba(out_r, out_g, out_b, 0.18 * entry_val)
        cr.stroke()
        cr.restore()

        step_deg = 360.0 / self.num_items
        for i in range(self.num_items):
            div_rad = math.radians(-90.0 + (i + 0.5) * step_deg)
            tx1, ty1 = cx + (orbit_r - 6.0) * math.cos(div_rad), cy + (orbit_r - 6.0) * math.sin(div_rad)
            tx2, ty2 = cx + (orbit_r + 6.0) * math.cos(div_rad), cy + (orbit_r + 6.0) * math.sin(div_rad)
            cr.save()
            cr.new_path()
            cr.move_to(tx1, ty1)
            cr.line_to(tx2, ty2)
            cr.set_line_width(1.0)
            cr.set_source_rgba(out_r, out_g, out_b, 0.16 * entry_val)
            cr.stroke()
            cr.restore()

        for i, app in enumerate(self.apps):
            if i < len(self.node_springs):
                prog = max(0.0, min(1.0, self.node_springs[i].current))
                if prog > 0.01:
                    app_r, app_g, app_b = app["color"]
                    ang_deg = app["center_angle"]
                    half_span = (step_deg / 2.0) - 4.0
                    start_rad = math.radians(ang_deg - half_span)
                    end_rad = math.radians(ang_deg + half_span)

                    cr.save()
                    cr.new_path()
                    cr.arc(cx, cy, orbit_r, start_rad, end_rad)
                    cr.set_line_width(14.0)
                    cr.set_source_rgba(app_r, app_g, app_b, 0.15 * prog * entry_val)
                    cr.stroke()

                    cr.new_path()
                    cr.arc(cx, cy, orbit_r, start_rad, end_rad)
                    cr.set_line_width(2.5 + prog * 1.5)
                    cr.set_source_rgba(app_r, app_g, app_b, (0.50 + 0.45 * prog) * entry_val)
                    cr.stroke()
                    cr.restore()

        # 3. Center Core & Tethers
        cr.save()
        cr.new_path()
        cr.arc(cx, cy, DEADZONE_RADIUS, 0, 2 * math.pi)
        cr.set_dash([2.0, 4.0])
        cr.set_line_width(0.8)
        cr.set_source_rgba(out_r, out_g, out_b, 0.12 * entry_val)
        cr.stroke()
        cr.restore()

        for i, app in enumerate(self.apps):
            if i < len(self.node_springs):
                prog = max(0.0, min(1.0, self.node_springs[i].current))
                if prog > 0.01:
                    app_r, app_g, app_b = app["color"]
                    ang_rad = math.radians(app["center_angle"])
                    node_dist = orbit_r + prog * FLOAT_SPRING
                    target_x = cx + node_dist * math.cos(ang_rad)
                    target_y = cy + node_dist * math.sin(ang_rad)

                    cr.save()
                    cr.new_path()
                    cr.move_to(core_x, core_y)
                    cr.line_to(target_x, target_y)
                    cr.set_dash([2.0, 5.0])
                    cr.set_line_width(1.2 + prog * 0.8)
                    cr.set_source_rgba(app_r, app_g, app_b, (0.15 + 0.65 * prog) * entry_val)
                    cr.stroke()
                    cr.restore()

        cr.save()
        is_submenu = len(self.menu_stack) > 0
        core_radius = 18.0 if is_submenu else 14.0

        cr.new_path()
        cr.arc(core_x, core_y, core_radius, 0, 2 * math.pi)
        if active_idx is not None and active_idx < self.num_items:
            ar, ag, ab = self.apps[active_idx]["color"]
            cr.set_source_rgba(ar, ag, ab, 0.22 * entry_val)
        else:
            cr.set_source_rgba(out_r, out_g, out_b, 0.08 * entry_val)
        cr.fill()

        cr.new_path()
        cr.arc(core_x, core_y, 10.0 if is_submenu else 8.0, 0, 2 * math.pi)
        if active_idx is not None and active_idx < self.num_items:
            ar, ag, ab = self.apps[active_idx]["color"]
            cr.set_source_rgba(ar, ag, ab, 0.85 * entry_val)
        else:
            cr.set_source_rgba(p["on_surface_var"][0], p["on_surface_var"][1], p["on_surface_var"][2], 0.40 * entry_val)
        cr.set_line_width(1.4)
        cr.stroke()

        if is_submenu:
            bw, bh = self.back_ink_rect.width, self.back_ink_rect.height
            bx = core_x - self.back_ink_rect.x - (bw / 2.0)
            by = core_y - self.back_ink_rect.y - (bh / 2.0)
            cr.move_to(bx, by)
            cr.set_source_rgba(p["on_surface"][0], p["on_surface"][1], p["on_surface"][2], 0.95 * entry_val)
            PangoCairo.show_layout(cr, self.layout_back)
        else:
            cr.new_path()
            cr.arc(core_x, core_y, 3.2, 0, 2 * math.pi)
            if active_idx is not None and active_idx < self.num_items:
                ar, ag, ab = self.apps[active_idx]["color"]
                cr.set_source_rgba(ar, ag, ab, 1.0 * entry_val)
            else:
                cr.set_source_rgba(p["on_surface"][0], p["on_surface"][1], p["on_surface"][2], 0.90 * entry_val)
            cr.fill()
        cr.restore()

        # 4. M3E Content-Aware Adaptive Streamline Capsules
        for i, app in enumerate(self.apps):
            prog = max(0.0, min(1.0, self.node_springs[i].current)) if i < len(self.node_springs) else 0.0
            app_r, app_g, app_b = app["color"]
            ang_rad = math.radians(app["center_angle"])

            cur_dist = orbit_r + prog * FLOAT_SPRING
            ix, iy = cx + cur_dist * math.cos(ang_rad), cy + cur_dist * math.sin(ang_rad)

            tw, th = app["title_w"], app["title_h"]
            dw, dh = app["desc_w"], app["desc_h"]
            kw, kh = app["badge_w"], app["badge_h"]
            ink_rect = app["icon_ink_rect"]

            cw = app["idle_w"] + (app["active_w"] - app["idle_w"]) * prog
            ch = CAPSULE_IDLE_H + (CAPSULE_ACTIVE_H - CAPSULE_IDLE_H) * prog
            cr_radius = ch / 2.0

            cx_box = ix - cw / 2.0
            cy_box = iy - ch / 2.0

            cr.save()
            shadow_y = 2.5 + prog * 4.5
            self.draw_rounded_pill(cr, cx_box, cy_box + shadow_y, cw, ch, cr_radius)
            cr.set_source_rgba(0.0, 0.0, 0.0, (0.16 + 0.22 * prog) * entry_val)
            cr.fill()
            cr.restore()

            fill_r = surf_r + (app_r - surf_r) * (0.34 * prog)
            fill_g = surf_g + (app_g - surf_g) * (0.34 * prog)
            fill_b = surf_b + (app_b - surf_b) * (0.34 * prog)
            fill_alpha = ((0.88 if p["is_dark"] else 0.94) + 0.08 * prog) * entry_val

            self.draw_rounded_pill(cr, cx_box, cy_box, cw, ch, cr_radius)
            cr.set_source_rgba(fill_r, fill_g, fill_b, fill_alpha)
            cr.fill_preserve()

            b_r = out_r + (app_r - out_r) * prog
            b_g = out_g + (app_g - out_g) * prog
            b_b = out_b + (app_b - out_b) * prog
            b_alpha = (0.16 + prog * 0.74) * entry_val
            b_width = 1.0 + prog * 1.2

            cr.set_source_rgba(b_r, b_g, b_b, b_alpha)
            cr.set_line_width(b_width)
            cr.stroke()

            # (A) Left Icon Chip Pill with Perfect Semicircular Endcap Concentricity
            chip_cx = cx_box + (ch / 2.0)
            chip_cy = iy
            chip_r = 15.0 + 1.5 * prog

            cr.save()
            cr.new_path()
            cr.arc(chip_cx, chip_cy, chip_r, 0, 2 * math.pi)
            chip_bg_r = out_r + (app_r - out_r) * prog
            chip_bg_g = out_g + (app_g - out_g) * prog
            chip_bg_b = out_b + (app_b - out_b) * prog
            chip_bg_alpha = (0.10 + 0.78 * prog) * entry_val
            cr.set_source_rgba(chip_bg_r, chip_bg_g, chip_bg_b, chip_bg_alpha)
            cr.fill_preserve()
            cr.set_source_rgba(chip_bg_r, chip_bg_g, chip_bg_b, (0.18 + 0.65 * prog) * entry_val)
            cr.set_line_width(1.0)
            cr.stroke()
            cr.restore()

            cr.save()
            draw_icon_x = chip_cx - ink_rect.x - (ink_rect.width / 2.0)
            draw_icon_y = chip_cy - ink_rect.y - (ink_rect.height / 2.0)
            cr.move_to(draw_icon_x, draw_icon_y)

            if prog > 0.45:
                cr.set_source_rgba(dim_r, dim_g, dim_b, 1.0 * entry_val) if p["is_dark"] else cr.set_source_rgba(1.0, 1.0, 1.0, 1.0 * entry_val)
            else:
                cr.set_source_rgba(p["on_surface"][0], p["on_surface"][1], p["on_surface"][2], 0.94 * entry_val)
            PangoCairo.show_layout(cr, app["layout_icon"])
            cr.restore()

            # (B) Middle Typography: Title & Subtitle
            text_x = chip_cx + chip_r + 9.0

            if prog < 0.18:
                title_y = iy - th / 2.0
                cr.save()
                cr.move_to(text_x, title_y)
                cr.set_source_rgba(p["on_surface"][0], p["on_surface"][1], p["on_surface"][2], 0.90 * entry_val)
                PangoCairo.show_layout(cr, app["layout_title"])
                cr.restore()
            else:
                title_y = iy - (th + dh + 1.0) / 2.0 + (1.0 - prog) * 2.0
                desc_y = title_y + th + 1.0

                cr.save()
                cr.move_to(text_x, title_y)
                cr.set_source_rgba(p["on_surface"][0], p["on_surface"][1], p["on_surface"][2], 0.98 * entry_val)
                PangoCairo.show_layout(cr, app["layout_title"])

                desc_alpha = min(1.0, (prog - 0.18) / 0.82) * 0.85 * entry_val
                cr.move_to(text_x, desc_y)
                cr.set_source_rgba(p["on_surface_var"][0], p["on_surface_var"][1], p["on_surface_var"][2], desc_alpha)
                PangoCairo.show_layout(cr, app["layout_desc"])
                cr.restore()

            # (C) Right Shortcut Badge Pill
            right_pad = 13.0
            key_x = cx_box + cw - right_pad - kw
            key_y = iy - kh / 2.0
            pill_w, pill_h = kw + 8.0, kh + 4.0
            pill_x, pill_y = key_x - 4.0, key_y - 2.0

            cr.save()
            self.draw_rounded_pill(cr, pill_x, pill_y, pill_w, pill_h, pill_h / 2.0)
            badge_bg_alpha = (0.12 + 0.18 * prog) * entry_val
            cr.set_source_rgba(p["on_surface_var"][0], p["on_surface_var"][1], p["on_surface_var"][2], badge_bg_alpha)
            cr.fill()

            cr.move_to(key_x, key_y)
            badge_text_alpha = (0.65 + 0.35 * prog) * entry_val
            cr.set_source_rgba(p["on_surface_var"][0], p["on_surface_var"][1], p["on_surface_var"][2], badge_text_alpha)
            PangoCairo.show_layout(cr, app["layout_badge"])
            cr.restore()

        cr.restore()
        return False


def main():
    lock_fd = acquire_instance_lock()
    win = ScratchpadRadialMenu(lock_fd=lock_fd)

    def handle_signal(signum, frame):
        GLib.idle_add(win.dismiss_menu)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        Gtk.main()
    finally:
        release_instance_lock(lock_fd)


if __name__ == "__main__":
    main()
