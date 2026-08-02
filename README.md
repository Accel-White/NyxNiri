<div align="right">
  <a href="#english">English</a> | <a href="#chinese">简体中文</a>
</div>

<div align="center">
<a id="english"></a>

# 𝑁𝑦𝑥𝑁𝑖𝑟𝑖

A Material You desktop configuration based on Niri and Noctalia V5 for Arch /
CachyOS.

<p align="center">
  <img src="https://img.shields.io/badge/License-GPLv3-89B4FA?style=flat-square&logo=gnu" alt="License" />
  <img src="https://img.shields.io/github/stars/ech678/NyxNiri?style=flat-square&color=F5C2E7&label=stars" alt="Stars" />
  <img src="https://img.shields.io/badge/CLI-nyxniri-A6E3A1?style=flat-square&logo=gnu-bash&logoColor=black" alt="CLI" />
  <img src="https://img.shields.io/badge/OS-Arch%20%7C%20CachyOS-1793D1?style=flat-square&logo=arch-linux&logoColor=white" alt="OS" />
  <img src="https://img.shields.io/badge/WM-Niri-89B4FA?style=flat-square&logo=wayland&logoColor=white" alt="WM" />
  <img src="https://img.shields.io/badge/Shell-Fish%20%2B%20Starship-F9E2AF?style=flat-square&logo=fish&logoColor=black" alt="Shell" />
  <img src="https://img.shields.io/badge/UI-Noctalia%20V5-F5C2E7?style=flat-square&logo=material-design&logoColor=black" alt="UI" />
</p>

<img src="./preview.webp" alt="Preview" width="92%" />

[Video preview on Bilibili](https://www.bilibili.com/video/BV1Dig16rEZ7/)

</div>

## Overview

NyxNiri is a desktop configuration bundle for Arch Linux and CachyOS. It is
built around the Niri scroll-tiling window manager and the Noctalia V5 shell,
providing dynamic theming, basic system synchronization, and terminal
enhancements.

## Features

- **Material You Extraction**: Noctalia V5 natively generates color palettes
  from wallpapers. Custom Lua hooks bridge `mpvpaper` video wallpapers into
  this pipeline by extracting frame thumbnails via `ffmpeg`.
- **Theme Synchronization**: A background script keeps GSettings and GTK
  configurations in sync when switching between light and dark modes.
- **Focus Mode (`Super+N`)**: Adjusts color temperature, disables window blur,
  and forces opaque backgrounds to reduce eye strain during long sessions.
- **Shell & Terminal Tweaks**: Includes Fish shell aliases for proxy management
  and cache cleaning, plus Kitty configurations for cursor trails and
  Windows-like shortcuts.

## Stack

| Component      | Choice                           |
| -------------- | -------------------------------- |
| Window Manager | Niri                             |
| Desktop Shell  | Noctalia V5                      |
| Wallpaper      | mpvpaper                         |
| Terminal       | Kitty                            |
| Shell          | Fish + Starship                  |
| Fonts          | JetBrains Mono, Noto Sans CJK SC |

## Directory Structure

```text
NyxNiri
├── install.sh                  # Installation script (backup, dependency check)
├── lib/                        # Core modules (deploy, backup, network, doctor, i18n…)
├── Wallpapers/                 # Wallpaper library
└── v2/                         # Noctalia V5 configurations
    ├── niri/                   # Window manager config
    ├── noctalia/               # Widgets and theme sync
    ├── kitty/                  # Terminal config
    ├── fish/                   # Shell aliases and functions
    ├── fastfetch/              # System info display
    ├── zed/                    # Zed editor config
    └── starship.toml           # Prompt theme
```

> [!TIP]
> **Customization (Dunder Mechanism)**
> NyxNiri updates atomically replace configuration directories. To preserve your personal modifications across updates:
> - **Custom Files**: Any file matching `*__custom__*` (e.g., `__custom__.kdl`, `01__custom__.fish`, `__custom__env`) will be securely preserved across updates (supports number prefixes for controlling load order).
> - **Custom Namespace**: You can create any `*__custom__*` folder inside any config directory (e.g., `~/.config/niri/__custom__/`, `~/.config/niri/01__custom__/`) to store your own scripts or assets. The entire folder and all its contents are immune to updates.

> [!NOTE]
> The installation process offers an optional backup prompt to save existing configurations to
> `~/.config/NyxNiri/backups/` before deployment.

> [!WARNING]
> The legacy Dank Material Shell (DMS) configuration has been moved to the
> `archive/v1-dms` branch. The `main` branch only maintains the V2 architecture.

## Keybindings

**Window Management**

| Shortcut | Action |
| :--- | :--- |
| <kbd>Super</kbd> + <kbd>Enter</kbd> | Open terminal |
| <kbd>Super</kbd> + <kbd>Q</kbd> | Close window |
| <kbd>Super</kbd> + <kbd>T</kbd> | Toggle floating/tiling |
| <kbd>Super</kbd> + <kbd>F</kbd> | Maximize current column |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>F</kbd> | Fullscreen |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | Workspace overview |
| <kbd>Super</kbd> + <kbd>Z</kbd> | Focus left |
| <kbd>Super</kbd> + <kbd>C</kbd> | Focus right |
| <kbd>Super</kbd> + <kbd>J</kbd> / <kbd>K</kbd> | Focus down/up |
| <kbd>Super</kbd> + <kbd>Arrows</kbd> | Smart focus (Column/Monitor/Workspace) |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Arrows</kbd> | Smart move (Column/Monitor/Workspace) |
| <kbd>Super</kbd> + <kbd>D</kbd> / <kbd>U</kbd> | Workspace down/up |
| <kbd>Super</kbd> + <kbd>Space</kbd> | Switch preset column widths |
| <kbd>Super</kbd> + <kbd>-</kbd> / <kbd>=</kbd> | Decrease/Increase column width |

> For the complete interactive keybinding reference, run `nyxhelp keys` or
> press <kbd>Super</kbd> + <kbd>/</kbd> in Niri.

**System & Components**

| Shortcut | Action |
| :--- | :--- |
| <kbd>Super</kbd> + <kbd>R</kbd> | App launcher |
| <kbd>Super</kbd> + <kbd>E</kbd> | File manager |
| <kbd>Super</kbd> + <kbd>X</kbd> | Power menu |
| <kbd>Super</kbd> + <kbd>I</kbd> | Control center |
| <kbd>Super</kbd> + <kbd>V</kbd> | Clipboard history |
| <kbd>Super</kbd> + <kbd>W</kbd> | Static wallpaper picker |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>W</kbd> | Live wallpaper picker |
| <kbd>Super</kbd> + <kbd>N</kbd> | Toggle Focus Mode |
| <kbd>Super</kbd> + <kbd>L</kbd> | Lock screen |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | Screenshot |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> | Reload Niri |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>E</kbd> | Quit Niri |

## Installation

NyxNiri supports two installation modes:

- **Standalone Mode (Online Pipeline)** — `curl ... | bash` caches the
  repository to `~/.cache/NyxNiri` and deploys automatically without creating a
  local workspace repo.
- **Repository Mode (Local / Development — Recommended)** — `git clone ... &&
  ./install.sh` runs directly inside the local repo directory for easy
  customization and version control.

### Mode 1: Quick Standalone Install

```bash
curl -sL --connect-timeout 10 https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

### Mode 2: Git Repository Install (Recommended)

```bash
git clone https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

<details>
<summary>Mirror for China (gh-proxy / CDN Acceleration)</summary>

#### Standalone Online Mirror Install
```bash
# Option 1: gh-proxy.org
curl -sL --connect-timeout 10 https://gh-proxy.org/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash

# Option 2: ghproxy.net
curl -sL --connect-timeout 10 https://ghproxy.net/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

#### Git Repository Mirror Clone
```bash
# Clone via gh-proxy.org
git clone https://gh-proxy.org/https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

*Note: `install.sh` automatically includes a built-in 3-tier fallback engine (Official -> jsDelivr CDN -> gh-proxy) with real-time latency logs.*

</details>

> [!NOTE]
> **AUR Dependencies**
> `noctalia` and `mpvpaper` are AUR packages. When running `install full` on a
> system without a usable AUR helper (paru/yay), the installer bootstraps `paru`
> automatically (requires `base-devel`, `git`, and `sudo`) — it prefers the
> official repos when available, otherwise builds the AUR source package on your
> machine (avoiding prebuilt `-bin` ABI mismatches).

## CLI Tool (`nyxniri`)

A lightweight utility to manage configurations and diagnose issues.

| Command                    | Description                                                  |
| -------------------------- | ------------------------------------------------------------ |
| `nyxniri`                  | Open the interactive TUI menu.                               |
| `nyxniri install [full\|config]` | Deploy full environment (`full`) or sync configs only (`config`). |
| `nyxniri update [--force]` | Check for updates and optionally overwrite configurations.   |
| `nyxniri snapshot [note]`  | Save the current configuration state.                        |
| `nyxniri rollback [index]` | Revert to a previous snapshot (auto-backs up current state). |
| `nyxniri list`             | Show available snapshots.                                    |
| `nyxniri uninstall`        | Remove NyxNiri and restore previous configs.                 |
| `nyxniri purge`            | Delete all NyxNiri configs, caches, and wallpapers.          |
| `nyxniri doctor`           | Check dependencies and system health.                        |
| `nyxniri greeter [install\|status\|uninstall]` | Optional Noctalia Greeter (greetd login screen) setup.       |

> [!NOTE]
> **Optional: Noctalia Greeter (Login Screen)**
> NyxNiri does not configure a display manager by default. To install and
> configure [Noctalia Greeter](https://github.com/noctalia-dev/noctalia-greeter)
> (a greetd login screen that matches the Noctalia theme), run:
>
> ```bash
> nyxniri greeter install
> ```
>
> This installs `greetd` + `noctalia-greeter` (AUR), backs up and writes
> `/etc/greetd/config.toml`, enables the `greetd` service (takes effect after
> reboot), writes a Polkit rule for passwordless theme sync, and prints a notice
> if another display manager is detected (it never disables anything itself).
> If a display manager is already running, use `nyxniri greeter status` to review
> the state before proceeding. Use `nyxniri greeter uninstall` to disable greetd
> and restore the previous `/etc/greetd/config.toml`.

## Cheatsheet TUI (`nyxhelp`)

An interactive terminal cheatsheet powered by `fzf` for quick navigation of shortcuts and commands.

| Command         | Description                                                    |
| --------------- | -------------------------------------------------------------- |
| `nyxhelp`       | Open the interactive dual-panel cheatsheet menu.               |
| `nyxhelp keys`  | Display Niri keybindings section.                             |
| `nyxhelp proxy` | Display proxy controls (`proxy_on [port]`, `proxy_off`, `proxy_status`). |
| `nyxhelp pkg`   | Display package management shortcuts (`up`, `in`, `se`, `un`, `clean`). |
| `nyxhelp all`   | Print the full cheatsheet guide.                               |

## Troubleshooting

**Noctalia hangs on startup**

This is usually caused by `ddcutil` scanning the I2C bus for monitor brightness
controls, which can timeout on certain hardware (especially NVIDIA).

_Fix_: Disable DDC/CI in `~/.config/noctalia/noctalia-config.toml`:

```toml
[brightness]
enable_ddcutil = false
```

**Plugin repository corruption**

If Noctalia hangs while checking out plugins on startup, the local git cache
might be corrupted.

_Fix_: Reset the plugin directories:

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

**Password prompt appears when syncing theme to Greeter**

Noctalia uses `pkexec` to apply the greeter theme. To avoid entering your password every time, you can add a Polkit exemption rule.

> `nyxniri greeter install` writes this rule automatically. The manual steps below are only needed when you configure the greeter yourself.

_Fix_: Run the following command to create a Polkit rule (requires `sudo`):

```bash
sudo bash -c 'cat > /etc/polkit-1/rules.d/50-noctalia-greeter.rules << EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.noctalia.greeter.apply-appearance" &&
        subject.isInGroup("wheel")) {
        return polkit.Result.YES;
    }
});
EOF'
```

## Community & Acknowledgments

**Contact & Support**

- QQ: `2040244628`
- Telegram: [@Echoes678](https://t.me/Echoes678)
- Linux Ricing Group: `631425889`
- Bug Reports: Run the `Generate Bug Report` option in `install.sh` or open an
  [Issue](https://github.com/ech678/NyxNiri/issues).
- Sponsorship: [afdian.com/a/Echoes678](https://afdian.com/a/Echoes678)

**Acknowledgments**

- [RanXom/glassy-niri](https://github.com/RanXom/glassy-niri) - Blur settings
  reference
- [SHORiN-KiWATA/shorin-niri](https://github.com/SHORiN-KiWATA/shorin-niri) - A lot

**Recommended Projects**

- [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) -
  Desktop lyrics widget
- [Ocfeather/chrome-niri-opacity](https://github.com/Ocfeather/chrome-niri-opacity) -
  Browser opacity script

---

<div align="center">
<a id="chinese"></a>
</div>

## 项目概述

NyxNiri 是一套针对 Arch Linux 和 CachyOS 的桌面配置集。核心基于 Niri 滚动平铺窗口管理器与 Noctalia V5，主要提供动态主题同步、基础系统联动以及终端环境的预设配置。

## 核心特性

- **Material You 取色**：Noctalia V5 原生支持从壁纸提取配色方案。自定义 Lua 钩子将 `mpvpaper` 视频壁纸桥接到此管线，通过 `ffmpeg` 提取帧缩略图供 Noctalia 取色。
- **主题同步**：包含一个后台脚本用于同步 GSettings 和 GTK 配置，方便切换明暗模式。
- **护眼模式 (`Super+N`)**：开启后会调整色温，关闭窗口模糊效果，并将透明度设为不透明，以降低长时间阅读的视觉疲劳。
- **终端与 Shell 配置**：预设了 Fish shell 的代理切换别名和缓存清理命令；Kitty 终端开启了光标轨迹，并映射了部分常用的 Windows 快捷键。

## 技术栈

| 组件       | 选择                             |
| ---------- | -------------------------------- |
| 窗口管理器 | Niri                             |
| 桌面组件   | Noctalia V5                      |
| 壁纸引擎   | mpvpaper                         |
| 终端       | Kitty                            |
| Shell      | Fish + Starship                  |
| 字体       | JetBrains Mono, Noto Sans CJK SC |

## 目录结构

```text
NyxNiri
├── install.sh                  # 安装脚本（包含依赖检测与配置备份）
├── lib/                        # 核心功能模块（部署、备份、网络、诊断、国际化…）
├── Wallpapers/                 # 壁纸库
└── v2/                         # Noctalia V5 配置
    ├── niri/                   # 窗口管理器配置
    ├── noctalia/               # 桌面组件与主题同步
    ├── kitty/                  # 终端配置
    ├── fish/                   # Shell 别名与函数
    ├── fastfetch/              # 系统信息展示
    ├── zed/                    # Zed 编辑器配置
    └── starship.toml           # 提示符主题
```

> [!TIP]
> **自定义配置 (Dunder 机制)**
> NyxNiri 更新时会原子覆盖配置目录。为保证你的私人配置在更新时安全保留：
> - **自定义文件**：任何命名匹配 `*__custom__*` 的文件（如 `__custom__.kdl`, `01__custom__.fish`, `__custom__env`）都会被完整继承，免于覆盖（支持添加前缀数字调控加载与执行顺序）。
> - **私有命名空间**：你可以在配置目录下建立任何 `*__custom__*` 文件夹（如 `~/.config/niri/__custom__/`, `~/.config/niri/01__custom__/`），在里面自由存放及命名个人脚本与素材，整个文件夹及其内部所有文件在更新时将被连根完整保留。

> [!NOTE]
> 安装过程提供可选的备份提示，允许你在部署前将现有配置备份至 `~/.config/NyxNiri/backups/`。

> [!WARNING]
> 旧版 Dank Material Shell (DMS) 配置已移至 `archive/v1-dms` 分支。`main` 分支仅维护当前的 V2 架构。

## 快捷键

**窗口控制**

| 快捷键 | 动作 |
| :--- | :--- |
| <kbd>Super</kbd> + <kbd>Enter</kbd> | 打开终端 |
| <kbd>Super</kbd> + <kbd>Q</kbd> | 关闭窗口 |
| <kbd>Super</kbd> + <kbd>T</kbd> | 切换浮动/平铺 |
| <kbd>Super</kbd> + <kbd>F</kbd> | 最大化当前列 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>F</kbd> | 全屏 |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | 工作区总览 |
| <kbd>Super</kbd> + <kbd>Z</kbd> | 聚焦左侧 |
| <kbd>Super</kbd> + <kbd>C</kbd> | 聚焦右侧 |
| <kbd>Super</kbd> + <kbd>J</kbd> / <kbd>K</kbd> | 聚焦下/上 |
| <kbd>Super</kbd> + <kbd>方向键</kbd> | 智能焦点（自动跨列/跨屏/跨区） |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>方向键</kbd> | 智能搬运（自动跨屏/跨区） |
| <kbd>Super</kbd> + <kbd>D</kbd> / <kbd>U</kbd> | 工作区下/上 |
| <kbd>Super</kbd> + <kbd>Space</kbd> | 切换预设列宽比例 |
| <kbd>Super</kbd> + <kbd>-</kbd> / <kbd>=</kbd> | 收缩/拉伸列宽 |

> 完整快捷键列表请运行 `nyxhelp keys` 或按 <kbd>Super</kbd> + <kbd>/</kbd>。

**系统与组件**

| 快捷键 | 动作 |
| :--- | :--- |
| <kbd>Super</kbd> + <kbd>R</kbd> | 启动器 |
| <kbd>Super</kbd> + <kbd>E</kbd> | 文件管理器 |
| <kbd>Super</kbd> + <kbd>X</kbd> | 电源菜单 |
| <kbd>Super</kbd> + <kbd>I</kbd> | 控制中心 |
| <kbd>Super</kbd> + <kbd>V</kbd> | 剪贴板 |
| <kbd>Super</kbd> + <kbd>W</kbd> | 静态壁纸选择 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>W</kbd> | 动态壁纸选择 |
| <kbd>Super</kbd> + <kbd>N</kbd> | 护眼模式 |
| <kbd>Super</kbd> + <kbd>L</kbd> | 锁屏 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | 截图 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> | 重载 Niri |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>E</kbd> | 退出 Niri |

## 安装部署

NyxNiri 支持两种不同的安装与运行模式：

- **独立安装模式（在线管道）** — 运行 `curl ... | bash`，脚本会自动将配置仓库缓存至
  `~/.cache/NyxNiri` 并完成部署，无需在本地保留源码目录。
- **仓库部署模式（本地离线/开发 — 推荐）** — 运行 `git clone ... && ./install.sh`，
  直接在本地仓库中运行，方便进行个人配置定制、Git 版本管理与后续一键 `git pull` 更新。

### 模式 1：独立一键安装

```bash
curl -sL --connect-timeout 10 https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

### 模式 2：Git 仓库部署（推荐）

```bash
git clone https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

<details>
<summary>国内网络加速 (gh-proxy / CDN 镜像)</summary>

#### 1. 独立一键镜像安装
```bash
# 方案 1: gh-proxy.org
curl -sL --connect-timeout 10 https://gh-proxy.org/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash

# 方案 2: ghproxy.net
curl -sL --connect-timeout 10 https://ghproxy.net/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

#### 2. Git 仓库镜像克隆
```bash
# 通过 gh-proxy.org 镜像克隆仓库
git clone https://gh-proxy.org/https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

*提示：`install.sh` 脚本内置三级自动降级引擎（官方直连 → jsDelivr CDN → gh-proxy）与实时耗时 Log。*

</details>

> [!NOTE]
> **AUR 依赖**
> `noctalia` 与 `mpvpaper` 为 AUR 包。执行 `install full` 时若系统没有可用的
> AUR helper（paru/yay），安装器会自动自举安装 `paru`（需 `base-devel`、`git`
> 与 `sudo`）——优先官方软件源，否则在本机编译 AUR 源码包（规避预编译
> `-bin` 包的 ABI 不匹配问题）。

## CLI 工具 (`nyxniri`)

用于管理配置快照和系统诊断。

| 指令                      | 作用                                   |
| ------------------------- | -------------------------------------- |
| `nyxniri`                 | 打开交互式菜单                         |
| `nyxniri install [full\|config]` | 全量安装（`full`）或仅同步配置文件（`config`）  |
| `nyxniri update [--force]` | 检查仓库更新与可选覆盖升级             |
| `nyxniri snapshot [备注]` | 保存当前配置状态                       |
| `nyxniri rollback [序号]` | 恢复历史快照（恢复前自动备份当前状态） |
| `nyxniri list`            | 查看可用快照                           |
| `nyxniri uninstall`       | 卸载并复原配置                         |
| `nyxniri purge`           | 清除所有相关配置、缓存与壁纸           |
| `nyxniri doctor`          | 检查依赖与系统状态                     |
| `nyxniri greeter [install\|status\|uninstall]` | 可选 Noctalia Greeter（greetd 登录界面）配置 |

> [!NOTE]
> **可选：Noctalia Greeter（登录启动器）**
> NyxNiri 默认不配置显示管理器。如需安装并配置
> [Noctalia Greeter](https://github.com/noctalia-dev/noctalia-greeter)
> （与 Noctalia 主题一致的 greetd 登录界面），运行：
>
> ```bash
> nyxniri greeter install
> ```
>
> 该命令会安装 `greetd` + `noctalia-greeter`（AUR），备份并写入
> `/etc/greetd/config.toml`，启用 `greetd` 服务（重启后生效），写入
> Greeter 主题免密同步所需的 Polkit 规则，并在检测到其他显示管理器时给出
> 一行提示（**绝不会自动禁用任何管理器**）。若已在使用其他显示管理器，请先
> 用 `nyxniri greeter status` 查看状态再决定。使用 `nyxniri greeter uninstall`
> 可停用 greetd 并还原原有的 `/etc/greetd/config.toml`。

## 终端速查手册 (`nyxhelp`)

依托 `fzf` 构建的双栏 TUI 交互式快捷指令与快捷键速查终端。

| 指令            | 作用                                                           |
| --------------- | -------------------------------------------------------------- |
| `nyxhelp`       | 打开双栏 TUI 交互式速查菜单                                    |
| `nyxhelp keys`  | 快速展示 Niri 桌面核心快捷键                                   |
| `nyxhelp proxy` | 展示网络代理控制指令（支持 `proxy_on 10808` 动态端口）          |
| `nyxhelp pkg`   | 展示包管理与缓存清理指令 (`up`, `in`, `se`, `un`, `clean`)     |
| `nyxhelp all`   | 静态打印完整速查手册                                           |

## 故障排除

**Noctalia 启动卡死**

通常是因为 `ddcutil` 在扫描 I2C 总线获取显示器亮度控制时超时（在 NVIDIA
硬件上较常见）。

_修复_：在 `~/.config/noctalia/noctalia-config.toml` 中禁用 DDC/CI：

```toml
[brightness]
enable_ddcutil = false
```

**插件仓库损坏**

如果 Noctalia 在启动时拉取插件卡死，可能是本地 git 缓存损坏。

_修复_：重置插件目录：

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

**每次同步 Greeter 外观都需要输入密码**

Noctalia 依靠 `pkexec` 来应用 Greeter 主题。为了实现免密静默同步，可以添加一条 Polkit 豁免规则。

> `nyxniri greeter install` 会自动写入该规则。以下手动步骤仅在你自行配置 Greeter 时使用。

_修复_：运行以下命令创建免密规则（需要 `sudo` 权限）：

```bash
sudo bash -c 'cat > /etc/polkit-1/rules.d/50-noctalia-greeter.rules << EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.noctalia.greeter.apply-appearance" &&
        subject.isInGroup("wheel")) {
        return polkit.Result.YES;
    }
});
EOF'
```

## 社区与致谢

**交流与反馈**

- QQ：`2040244628`
- Telegram：[@Echoes678](https://t.me/Echoes678)
- Linux Ricing 交流群：`631425889`
- 提交 Bug：运行 `install.sh` 中的 `生成 Bug Report` 选项，或在 GitHub 提交
  [Issue](https://github.com/ech678/NyxNiri/issues)。
- 赞助支持：[爱发电](https://afdian.com/a/Echoes678)

**致谢**

- [RanXom/glassy-niri](https://github.com/RanXom/glassy-niri) - 模糊效果设置参考
- [SHORiN-KiWATA/shorin-niri](https://github.com/SHORiN-KiWATA/shorin-niri) - 参考了很多!

**推荐项目**

- [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) -
  桌面歌词组件
- [Ocfeather/chrome-niri-opacity](https://github.com/Ocfeather/chrome-niri-opacity) -
  浏览器透明度脚本

---

<div align="right">
  <a href="#english">Back to Top / 返回顶部</a>
</div>
