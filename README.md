<div align="right">
  <a href="#english">English</a> | <a href="#chinese">简体中文</a>
</div>

<div align="center">
<a id="english"></a>

# NyxMango

A Material You desktop configuration based on MangoWM and Noctalia V5 for Arch /
CachyOS.

<p align="center">
  <img src="https://img.shields.io/badge/License-GPLv3-89B4FA?style=flat-square&logo=gnu" alt="License" />
  <img src="https://img.shields.io/github/stars/ech678/NyxNiri?style=flat-square&color=F5C2E7&label=stars" alt="Stars" />
  <img src="https://img.shields.io/badge/CLI-nyxmango-A6E3A1?style=flat-square&logo=gnu-bash&logoColor=black" alt="CLI" />
  <img src="https://img.shields.io/badge/OS-Arch%20%7C%20CachyOS-1793D1?style=flat-square&logo=arch-linux&logoColor=white" alt="OS" />
  <img src="https://img.shields.io/badge/WM-MangoWM-89B4FA?style=flat-square&logo=wayland&logoColor=white" alt="WM" />
  <img src="https://img.shields.io/badge/Shell-Fish%20%2B%20Starship-F9E2AF?style=flat-square&logo=fish&logoColor=black" alt="Shell" />
  <img src="https://img.shields.io/badge/UI-Noctalia%20V5-F5C2E7?style=flat-square&logo=material-design&logoColor=black" alt="UI" />
</p>

<img src="./preview.webp" alt="Preview" width="92%" />

[Video preview on Bilibili](https://www.bilibili.com/video/BV1Dig16rEZ7/)

</div>

## Overview

NyxMango is a desktop configuration bundle for Arch Linux and CachyOS. It is
built around the MangoWM scroll-tiling window manager and the Noctalia V5 shell,
providing dynamic theming, basic system synchronization, and terminal
enhancements.

## Features

- **Material You Extraction**: Uses `mpvpaper` and a custom lua hook to extract
  colors from static or video wallpapers and apply them to the Noctalia theme.
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
| Window Manager | MangoWM                          |
| Desktop Shell  | Noctalia V5                      |
| Wallpaper      | mpvpaper                         |
| Terminal       | Kitty                            |
| Shell          | Fish + Starship                  |
| Fonts          | JetBrains Mono, Noto Sans CJK SC |

## Directory Structure

```text
NyxMango
├── install.sh                  # Installation script (backup, dependency check)
├── Wallpapers/                 # Wallpaper library
└── v2/                         # Noctalia V5 configurations
    ├── mango/                  # Window manager config
    ├── noctalia/               # Widgets and theme sync
    ├── kitty/                  # Terminal config
    ├── fish/                   # Shell aliases and functions
    ├── fastfetch/              # System info display
    └── starship.toml           # Prompt theme
```

> [!NOTE]
> The installation process automatically backs up existing configurations to
> `~/.config/NyxMango/backups/`.

> [!WARNING]
> The legacy Dank Material Shell (DMS) configuration has been moved to the
> `archive/v1-dms` branch. The `main` branch only maintains the V2 architecture.

## Keybindings

**Window Management**

| Shortcut                | Action                  |
| ----------------------- | ----------------------- |
| `Super` + `Enter`       | Open terminal           |
| `Super` + `Q`           | Close window            |
| `Super` + `T`           | Toggle floating/tiling  |
| `Super` + `F`           | Maximize current column |
| `Super` + `Shift` + `F` | Fullscreen              |
| `Super` + `Tab`         | Workspace overview      |
| `Super` + `Z`           | Focus left              |
| `Super` + `C`           | Focus right             |
| `Super` + `J` / `K`     | Focus up/down           |
| `Super` + `Arrows`      | Smart focus (Column/Monitor/Workspace) |
| `Super` + `Ctrl` + `Arrows` | Smart move window (Column/Monitor/Workspace) |
| `Super` + `-` / `=`     | Decrease/Increase column width |

**System & Components**

| Shortcut                | Action                  |
| ----------------------- | ----------------------- |
| `Super` + `R`           | App launcher            |
| `Super` + `E`           | File manager            |
| `Super` + `X`           | Power menu              |
| `Super` + `I`           | Control center          |
| `Super` + `V`           | Clipboard history       |
| `Super` + `W`           | Static wallpaper picker |
| `Super` + `Shift` + `W` | Live wallpaper picker   |
| `Super` + `N`           | Toggle Focus Mode       |
| `Super` + `L`           | Lock screen             |
| `Super` + `Shift` + `S` | Screenshot              |
| `Super` + `Shift` + `R` | Reload MangoWM          |

## Installation

**Quick Install**

```bash
curl -sL https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

**Git Clone (Recommended)**

```bash
git clone https://github.com/ech678/NyxNiri.git ~/NyxMango
cd ~/NyxMango && ./install.sh
```

<details>
<summary>Mirror for China</summary>

```bash
curl -sL https://ghproxy.net/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

</details>

## CLI Tool (`nyxmango`)

A lightweight utility to manage configurations and diagnose issues.

| Command                    | Description                                                  |
| -------------------------- | ------------------------------------------------------------ |
| `nyxmango`                  | Open the interactive TUI menu.                               |
| `nyxmango snapshot [note]`  | Save the current configuration state.                        |
| `nyxmango rollback [index]` | Revert to a previous snapshot (auto-backs up current state). |
| `nyxmango list`             | Show available snapshots.                                    |
| `nyxmango uninstall`        | Remove NyxMango and restore previous configs.                 |
| `nyxmango purge`            | Delete all NyxMango configs, caches, and wallpapers.          |
| `nyxmango doctor`           | Check dependencies and system health.                        |

## Cheatsheet TUI (`nyxhelp`)

An interactive terminal cheatsheet powered by `fzf` for quick navigation of shortcuts and commands.

| Command         | Description                                                    |
| --------------- | -------------------------------------------------------------- |
| `nyxhelp`       | Open the interactive dual-panel cheatsheet menu.               |
| `nyxhelp keys`  | Display MangoWM keybindings section.                           |
| `nyxhelp proxy` | Display proxy controls (`proxy_on`, `proxy_off`, `proxy_status`). |
| `nyxhelp pkg`   | Display package management shortcuts (`up`, `in`, `se`, `un`, `clean`). |
| `nyxhelp --all` | Print the full cheatsheet guide.                               |

## Troubleshooting

**Noctalia hangs on startup** This is usually caused by `ddcutil` scanning the
I2C bus for monitor brightness controls, which can timeout on certain hardware
(especially NVIDIA). _Fix_: Disable DDC/CI in
`~/.config/noctalia/noctalia-config.toml`:

```toml
[brightness]
enable_ddcutil = false
```

**Plugin repository corruption** If Noctalia hangs while checking out plugins on
startup, the local git cache might be corrupted. _Fix_: Reset the plugin
directories:

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

## Community & Acknowledgments

**Contact & Support**

- QQ: `2040244628`
- Telegram: [@Echoes678](https://t.me/Echoes678)
- Linux Ricing Group: `631425889`
- Bug Reports: Run the `Generate Bug Report` option in `install.sh` or open an
  [Issue](https://github.com/ech678/NyxNiri/issues).
- Sponsorship: [afdian.com/a/Echoes678](https://afdian.com/a/Echoes678)

**References**

- [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) -
  Desktop lyrics widget

---

<div align="center">
<a id="chinese"></a>
</div>

## 项目概述

NyxMango 是一套针对 Arch Linux 和 CachyOS 的桌面配置集。核心基于 MangoWM
滚动平铺窗口管理器与 Noctalia
V5，主要提供动态主题同步、基础系统联动以及终端环境的预设配置。

## 核心特性

- **Material You 取色**：通过 `mpvpaper` 和自定义 lua
  脚本，支持从静态图片或视频壁纸中提取颜色，并应用到 Noctalia 主题中。
- **主题同步**：包含一个后台脚本用于同步 GSettings 和 GTK
  配置，方便切换明暗模式。
- **护眼模式
  (`Super+N`)**：开启后会调整色温，关闭窗口模糊效果，并将透明度设为不透明，以降低长时间阅读的视觉疲劳。
- **终端与 Shell 配置**：预设了 Fish shell 的代理切换别名和缓存清理命令；Kitty
  终端开启了光标轨迹，并映射了部分常用的 Windows 快捷键。

## 技术栈

| 组件       | 选择                             |
| ---------- | -------------------------------- |
| 窗口管理器 | MangoWM                          |
| 桌面组件   | Noctalia V5                      |
| 壁纸引擎   | mpvpaper                         |
| 终端       | Kitty                            |
| Shell      | Fish + Starship                  |
| 字体       | JetBrains Mono, Noto Sans CJK SC |

## 目录结构

```text
NyxMango
├── install.sh                  # 安装脚本（包含依赖检测与配置备份）
├── Wallpapers/                 # 壁纸库
└── v2/                         # Noctalia V5 配置
    ├── mango/                  # 窗口管理器配置
    ├── noctalia/               # 桌面组件与主题同步
    ├── kitty/                  # 终端配置
    ├── fish/                   # Shell 别名与函数
    ├── fastfetch/              # 系统信息展示
    └── starship.toml           # 提示符主题
```

> [!NOTE]
> 安装过程会自动将现有配置备份至
> `~/.config/NyxMango/backups/`，不会直接覆盖关键文件。

> [!WARNING]
> 旧版 Dank Material Shell (DMS) 配置已移至 `archive/v1-dms` 分支。`main`
> 分支仅维护当前的 V2 架构。

## 快捷键

**窗口控制**

| 快捷键                  | 动作          |
| ----------------------- | ------------- |
| `Super` + `Enter`       | 打开终端      |
| `Super` + `Q`           | 关闭窗口      |
| `Super` + `T`           | 切换浮动/平铺 |
| `Super` + `F`           | 最大化当前列  |
| `Super` + `Shift` + `F` | 全屏          |
| `Super` + `Tab`         | 工作区总览    |
| `Super` + `Z`           | 聚焦左侧      |
| `Super` + `C`           | 聚焦右侧      |
| `Super` + `J` / `K`     | 聚焦上/下     |
| `Super` + `方向键`      | 智能焦点 (自动跨列/跨屏/跨区) |
| `Super` + `Ctrl` + `方向键` | 智能搬运 (自动跨屏/跨区) |
| `Super` + `-` / `=`     | 收缩/拉伸列宽 |

**系统与组件**

| 快捷键                  | 动作         |
| ----------------------- | ------------ |
| `Super` + `R`           | 启动器       |
| `Super` + `E`           | 文件管理器   |
| `Super` + `X`           | 电源菜单     |
| `Super` + `I`           | 控制中心     |
| `Super` + `V`           | 剪贴板       |
| `Super` + `W`           | 静态壁纸选择 |
| `Super` + `Shift` + `W` | 动态壁纸选择 |
| `Super` + `N`           | 护眼模式     |
| `Super` + `L`           | 锁屏 (swaylock) |
| `Super` + `Shift` + `S` | 截图         |
| `Super` + `Shift` + `R` | 重载 MangoWM |

## 安装部署

**一键安装**

```bash
curl -sL https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

**Git 克隆（推荐）**

```bash
git clone https://github.com/ech678/NyxNiri.git ~/NyxMango
cd ~/NyxMango && ./install.sh
```

<details>
<summary>国内网络加速</summary>

```bash
curl -sL https://ghproxy.net/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

</details>

## CLI 工具 (`nyxmango`)

用于管理配置快照和系统诊断。

| 指令                      | 作用                                   |
| ------------------------- | -------------------------------------- |
| `nyxmango`                 | 打开交互式菜单                         |
| `nyxmango snapshot [备注]` | 保存当前配置状态                       |
| `nyxmango rollback [序号]` | 恢复历史快照（恢复前自动备份当前状态） |
| `nyxmango list`            | 查看可用快照                           |
| `nyxmango uninstall`       | 卸载并复原配置                         |
| `nyxmango purge`           | 清除所有相关配置、缓存与壁纸           |
| `nyxmango doctor`          | 检查依赖与系统状态                     |

## 终端速查手册 (`nyxhelp`)

依托 `fzf` 构建的双栏 TUI 交互式快捷指令与快捷键速查终端。

| 指令            | 作用                                                           |
| --------------- | -------------------------------------------------------------- |
| `nyxhelp`       | 打开双栏 TUI 交互式速查菜单                                    |
| `nyxhelp keys`  | 快速展示 MangoWM 桌面核心快捷键                                 |
| `nyxhelp proxy` | 展示网络代理控制指令（支持 `proxy_on 10808` 动态端口）          |
| `nyxhelp pkg`   | 展示包管理与缓存清理指令 (`up`, `in`, `se`, `un`, `clean`)     |
| `nyxhelp --all` | 静态打印完整速查手册                                           |

## 故障排除

**Noctalia 启动卡死** 通常是因为 `ddcutil` 在扫描 I2C
总线获取显示器亮度控制时超时（在 NVIDIA 硬件上较常见）。 _修复_：在
`~/.config/noctalia/noctalia-config.toml` 中禁用 DDC/CI：

```toml
[brightness]
enable_ddcutil = false
```

**插件仓库损坏** 如果 Noctalia 在启动时拉取插件卡死，可能是本地 git 缓存损坏。
_修复_：重置插件目录：

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

## 社区与致谢

**交流与反馈**

- QQ：`2040244628`
- Telegram：[@Echoes678](https://t.me/Echoes678)
- Linux Ricing 交流群：`631425889`
- 提交 Bug：运行 `install.sh` 中的 `生成 Bug Report` 选项，或在 GitHub 提交
  [Issue](https://github.com/ech678/NyxNiri/issues)。
- 赞助支持：[爱发电](https://afdian.com/a/Echoes678)

**参考项目**

- [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) -
  桌面歌词组件

<div align="right">
  <a href="#english">Back to Top / 返回顶部</a>
</div>
