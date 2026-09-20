# tmux 配置选项完全参考手册

> 适用于 tmux 2.9+（部分 3.0+ 选项会标注版本）
> 配置文件：`~/.tmux.conf`（用户级），`/etc/tmux.conf`（系统级）
> 生效方式：`tmux source-file ~/.tmux.conf` 或 prefix + `r`

---

## 目录

1. [命令速查表](#1-命令速查表)
2. [选项分类总览](#2-选项分类总览)
3. [会话选项 (server & session)](#3-会话选项-server--session)
4. [窗口选项 (window)](#4-窗口选项-window)
5. [窗格选项 (pane)](#5-窗格选项-pane)
6. [状态栏选项 (status-line)](#6-状态栏选项-status-line)
7. [键绑定选项 (key-binding)](#7-键绑定选项-key-binding)
8. [复制模式 / 缓冲区选项](#8-复制模式--缓冲区选项)
9. [终端 / TUI 选项](#9-终端--tui-选项)
10. [鼠标 / 交互选项](#10-鼠标--交互选项)
11. [钩子 / 扩展选项](#11-钩子--扩展选项)
12. [256 配色表](#12-256-配色表)
13. [样式属性速查](#13-样式属性速查)
14. [实用模板](#14-实用模板)

---

## 1. 命令速查表

| 命令 | 作用 | 示例 |
|---|---|---|
| `set -g OPT VAL` | 运行时改全局选项 | `set -g mouse on` |
| `set -s OPT VAL` | 设置服务器级选项（部分只读） | `set -s buffer-limit 50` |
| `set -w OPT VAL` | 设置窗口级选项 | `setw -g mode-keys vi` |
| `set -as OPT VAL` | 追加（数组型选项） | `set -as default-terminal "tmux-256color"` |
| `set -t SESS OPT VAL` | 针对特定 session 设置 | `set -t dev history-limit 5000` |
| `show-options -g` | 查看全局选项 | `tmux show-options -g` |
| `show-options -gw` | 查看窗口级全局选项 | `tmux show-options -gw` |

> 完整查看：`tmux list-keys`（所有键位）、`tmux info`（当前状态）、`tmux list-commands`。

---

## 2. 选项分类总览

| 类别 | 数量 | 典型例子 |
|---|---|---|
| 会话/Server | ~30 | `default-shell`, `default-terminal`, `escape-time` |
| 窗口 | ~25 | `mode-keys`, `window-status-format`, `allow-rename` |
| 窗格 | ~30 | `pane-border-lines`, `pane-base-index`, `pane-scrollbars` |
| 状态栏 | ~35 | `status-interval`, `status-left`, `status-style` |
| 键绑定 | ~10 | `prefix`, `key-table`, `user-keys` |
| 缓冲区 | ~5 | `buffer-limit`, `set-clipboard` |
| 终端 | ~20 | `terminal-features`, `terminal-overrides` |
| 鼠标/交互 | ~5 | `mouse`, `focus-events`, `extended-keys` |
| 钩子/扩展 | ~15 | `display-panes-active-colour`, `popup` 相关 |

---

## 3. 会话选项 (server & session)

设置方式：`set -g` 或 `set -s`（server 级，`-s`）。

### 基础行为

| 选项                                                                   | 默认值                                                                         | 说明                              |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------- |
| `escape-time`                                                        | `500`                                                                       | prefix 与按键间隔（ms），太短易误触          |
| `prefix`                                                             | `C-b`                                                                       | 触发前缀键，强烈建议改成 `C-a`              |
| `prefix2`                                                            | (无)                                                                         | 二级 prefix（3.2+），进入时不等待          |
| `update-environment`                                                 | `DISPLAY SSH_ASKPASS SSH_AUTH_SOCK SSH_AGENT_PID SSH_CONNECTION XAUTHORITY` | 进入 tmux 时保留的变量                  |
| `default-terminal`                                                   | `""`                                                                        | 创建新窗口使用的 TERM                   |
| `default-shell`                                                      | `"/bin/sh"`                                                                 | 新窗格的 shell                      |
| `default-size`                                                       | `80x24`                                                                     | 新窗格默认尺寸（不知道终端尺寸时）               |
| `set-clipboard`                                                      | `""`                                                                        | 是否与系统剪贴板联动（需版本支持）               |
| `editor`                                                             | (ed 变体)                                                                     | buffer 编辑器，`:buffer -b` 时使用     |
| `pager`                                                              | (more 变体)                                                                   | buffer 分页器                      |
| `word-separators`                                                    | `" '"`- 等                                                                   | 单词边界分隔符（vi 模式 w/b/e 用）          |
| `backspace`                                                          | `""`                                                                        | 退格字符（兼容旧终端）                     |
| `buffer-limit`                                                       | `50`                                                                        | 缓冲区最大数量                         |
| `command-alias`                                                      | `[]`                                                                        | 命令别名（3.2+）                      |
| `command-printer`                                                    | `""`                                                                        | 自定义命令输出渲染（3.3+，实验）              |
| `command-prompt`                                                     | `""`                                                                        | 自定义 prompt 渲染（3.3+，实验）          |
| `default-command`                                                    | `""`                                                                        | 新窗格的初始命令                        |
| `default-option-prefix`                                              | `","`                                                                       | 选项前缀（用于条件渲染）                    |
| `detach-on-destroy`                                                  | `on`                                                                        | 最后一个 session 退出是否杀掉 server      |
| `display-panes-time`                                                 | `1000`                                                                      | `-D` 显示 pane 编号的时长              |
| `display-panes-colour`                                               | `colour7`                                                                   | `-D` 显示 pane 编号时背景色             |
| `display-panes-active-colour`                                        | `colour1`                                                                   | `-D` 当前 pane 的高亮色               |
| `environment`                                                        | `[]`                                                                        | 新建 session 时注入的环境变量列表           |
| `focus-events`                                                       | `off`                                                                       | 是否向应用报告 focus 事件（vim/neovim 需要） |
| `history-limit`                                                      | `2000`                                                                      | 每个窗格的滚动行数                       |
| `message-limit`                                                      | `200`                                                                       | message 队列上限                    |
| `message-command-style`                                              | `bg=black,fg=yellow`                                                        | message 内 command 样式            |
| `message-style`                                                      | `bg=yellow,fg=black`                                                        | 顶部临时提示样式                        |
| `prompt-command`                                                     | `""`                                                                        | prompt 内命令前缀样式                  |
| `prompt-style`                                                       | `bg=green,fg=black`                                                         | `:` prompt 样式                   |
| `renumber-windows`                                                   | `off`                                                                       | 关闭窗口时是否自动重编号                    |
| `repeat-time`                                                        | `500`                                                                       | 同键连按是否重复（ms）                    |
| `session-name`                                                       | `""`                                                                        | 默认 session 名字                   |
| `set-titles`                                                         | `off`                                                                       | 是否设置终端标题（xterm/term title）      |
| `set-titles-string`                                                  | `#S:#W:#T`                                                                  | 标题内容模板                          |
| `silent-proxy`                                                       | `[]`                                                                        | 静默代理的 relay（限于 -L/-S）           |
| `socket-name`                                                        | `default`                                                                   | socket 名字（多实例隔离用）               |
| `socket-path`                                                        | (编译时决定)                                                                     | socket 路径                       |
| `startup-command`                                                    | `""`                                                                        | 启动时执  的命令                       |
| `terminal-features`                                                  | `[]`                                                                        | 终端特性声明（RGB、extkeys…）            |
| `terminal-overrides`                                                 | `[]`                                                                        | terminfo 覆盖项                    |
| `user-keys`                                                          | `[]`                                                                        | 自定义非 ASCII 键位（3.3+）             |
| `user-option`                                                        | `[]`                                                                        | 自定义用户选项                         |
| `visual-activity`, `visual-bell`, `visual-content`, `visual-silence` | `off/off/off/off`                                                           | 视觉反馈（bell、idle 提示）              |
| `monitor-activity`, `monitor-bell`, `monitor-silence`                | `off/off/off`                                                               | 后台静默检测                          |
| `activity-action`, `silence-action`, `bell-action`                   | `any/any/any`                                                               | 检测到状态变化时的动作                     |
| `lock-after-time`                                                    | `0`                                                                         | 自动锁屏时长（0 关闭）                    |
| `lock-command`                                                       | `"lock -p"`                                                                 | 锁屏命令                            |
| `lock-server-on-exit`                                                | `off`                                                                       | server 退出时是否锁定                  |

---

## 4. 窗口选项 (window)

设置方式：`setw -g` 或 `set-window-option -g`。

### 窗口基本

| 选项                                            | 默认值                                               | 说明                 |
| --------------------------------------------- | ------------------------------------------------- | ------------------ |
| `allow-rename`                                | `on`                                              | 允许自动重命名窗口          |
| `automatic-rename`                            | `on`                                              | 是否根据命令自动改窗口名       |
| `automatic-rename-format`                     | `#{?pane_in_mode,[TMUX],#{pane_current_command}}` | 自动重命名格式            |
| `clock-mode-colour`                           | `colour250`                                       | 钟表模式颜色             |
| `clock-mode-style`                            | `24`                                              | 12/24              |
| `main-pane-height`, `main-pane-width`         | `24 / 80`                                         | `main-pane` 布局尺寸   |
| `main-pane-min-width`, `main-pane-min-height` | `1 / 1`                                           | 主窗格最小尺寸            |
| `monitor-content`, `monitor-cursor-position`  | `off / off`                                       | 内容变化/Cursor 位置变化检测 |
| `other-pane-height`, `other-pane-width`       | `0 / 0`                                           | 其它窗格默认尺寸           |
| `pane-base-index`                             | `0`                                               | pane 起始编号          |
| `remain-on-exit`                              | `off`                                             | 程序退出后 pane 是否保留    |
| `rename-mode`, `renames-window`               |                                                   | 重命名模式开关            |
| `synchronize-panes`                           | `off`                                             | 广播输入到所有 pane       |
| `window-status-format`                        | `#I:#W#F`                                         | 状态栏窗口标签格式          |
| `window-status-current-format`                | `#I:#W#F`                                         | 当前窗口的格式            |
| `window-status-current-style`                 | `default`                                         | 当前窗口样式             |
| `window-status-separator`                     | `""`                                              | 窗口之间的分隔            |
| `window-status-style`                         | `default`                                         | 非激活窗口样式            |
| `window-status-activity-style`                | `reverse`                                         | 有活动提示的窗口样式         |
| `window-status-bell-style`                    | `reverse`                                         | 有 bell 的窗口样式       |
| `window-status-content-style`                 | `default`                                         | 内容变化窗口样式           |
| `window-status-last-style`                    | `default`                                         | 最近聚焦过的窗口样式（3.4+）   |
| `window-status-separator-style`               | `default`                                         | 分隔符样式              |
| `window-style`, `window-active-style`         | `default / default`                               | 窗口整体样式（3.4+）       |

### 模式与滚动

| 选项                                                                                                                        | 默认值                  | 说明                    |
| ------------------------------------------------------------------------------------------------------------------------- | -------------------- | --------------------- |
| `mode-keys`                                                                                                               | `emacs`              | 复制模式键位：`vi` / `emacs` |
| `mode-style`                                                                                                              | `bg=yellow,fg=black` | 复制模式高亮                |
| `copy-mode`                                                                                                               | (命令)                 | 进入复制模式                |
| `scroll-position`                                                                                                         | `0`                  | 滚动位置                  |
| `mouse-shift-click-in-pane`                                                                                               | `off`                | 鼠标拖动选区（3.4+）          |
| `mouse-select-pane`, `mouse-select-window`, `mouse-resize-pane`, `mouse-drag-pane`, `mouse-drag-window`, `mouse-position` |                      | 鼠标相关（见 §10）           |
| `menu-style`, `menu-selected-style`, `menu-border-style`, `menu-pagination-style`                                         |                      | 菜单样式（3.4+）            |
| `popup-style`, `popup-border-style`, `popup-pagination-style`                                                             |                      | popup 样式（3.4+）        |

---

## 5. 窗格选项 (pane)

### 边框与布局

| 选项 | 默认值 | 说明 |
|---|---|---|
| `pane-border-lines` | `single` | `none/simple/heavy/double/blank/number` |
| `pane-border-indicators` | `off` | `off/colours/pixels`（3.4+） |
| `pane-border-format` | `""` | 边框上文字格式（3.4+） |
| `pane-border-status` | `off` | `off/top/bottom`（3.1+），边框上方显示额外信息 |
| `pane-border-style` | `default` | 非激活 pane 边框样式 |
| `pane-active-border-style` | `default` | 当前 pane 边框样式 |
| `pane-scrollbars` | `off` | `off/on/panes`（3.5+），滚动条 |
| `pane-scrollbar-style` | `default` | 滚动条样式 |
| `display-panes-active-colour` | `red` | `-D` 当前 pane 颜色 |
| `display-panes-colour` | `default` | `-D` 普通 pane 颜色 |

### 尺寸与对齐

| 选项 | 默认值 | 说明 |
|---|---|---|
| `pane-base-index` | `0` | pane 编号起始 |
| `pane-border-indicators` | `off` | `off / colours / pixels` |
| `pane-resizable` | `on` | 鼠标是否能调大小 |
| `pane-scrollbars` | `off` | 见上 |
| `pane-width`, `pane-height` | `""` | 强制指定 pane 尺寸（用 `=`/数字） |
| `pane-min-width`, `pane-min-height` | `1 / 1` | 最小尺寸 |

---

## 6. 状态栏选项 (status-line)

### 栏位

| 选项 | 默认值 | 说明 |
|---|---|---|
| `status` | `on` | 是否显示状态栏 |
| `status-interval` | `15` | 状态刷新间隔 |
| `status-position` | `bottom` | `top/bottom` |
| `status-fg`, `status-bg` | `default / default` | 整体前景/背景 |
| `status-style` | `default` | 整体样式（推荐用这个） |
| `status-left`, `status-right` | `"[#{session_name}]"` / `"#{?window_bigger,"#S","` | 左右内容 |
| `status-left-length`, `status-right-length` | `20 / 80` | 左右栏最大字符数 |
| `status-left-style`, `status-right-style` | `default / default` | 左右样式 |
| `status-format` | `"[#S] #I:#W#F"` | 窗口段格式 |
| `status-format[0..n]` | - | 多段格式（数组型） |
| `current-segment-style` | `reverse` | 当前鼠标焦点段高亮（3.4+） |
| `status-separator` | `"-"` | 多段间分隔 |
| `status-keys` | `vi` | 状态栏内按键模式 |
| `status-mouse-pad-format` | - | 鼠标在状态栏上时显示格式（3.4+） |

### 窗口段（就是底部 1 2 3 4 这块）

| 选项                              | 默认值       | 说明     |
| ------------------------------- | --------- | ------ |
| `window-status-format`          | `#I:#W#F` | 通用窗口格式 |
| `window-status-current-format`  | `#I:#W#F` | 当前窗口格式 |
| `window-status-style`           | `default` | 普通窗口样式 |
| `window-status-current-style`   | `default` | 当前窗口样式 |
| `window-status-activity-style`  | `reverse` | 有活动    |
| `window-status-bell-style`      | `reverse` | 有 bell |
| `window-status-content-style`   | `default` | 内容变化   |
| `window-status-last-style`      | `default` | 最近用过   |
| `window-status-separator`       | `""`      | 窗口间分隔  |
| `window-status-separator-style` | `default` | 分隔样式   |

### 标签中可用变量（核心）

| 变量 | 含义 |
|---|---|
| `#I` | 窗口索引 |
| `#W` | 窗口名 |
| `#F` | 窗口标记（Z = zoomed, ! = 等） |
| `#S` | session 名 |
| `#T` | 窗口标题 |
| `#P` | pane 索引 |
| `#{?cond,true,false}` | 三元判断 |
| `#{pane_current_command}` | pane 当前命令 |
| `#{pane_current_path}` | 当前路径 |
| `#{battery_percentage}` | 电池电量 |
| `#{cpu_percentage}` | CPU |
| `#{loadavg}` | 负载 |
| `#{hostname}` | 主机名 |
| `#{username}` | 用户名 |
| `#{client_width}`, `#{client_height}` | 终端尺寸 |

---

## 7. 键绑定选项 (key-binding)

| 选项 | 默认值 | 说明 |
|---|---|---|
| `prefix` | `C-b` | 主 prefix |
| `prefix2` | (无) | 二级 prefix（3.2+） |
| `key-table` | `root` | 当前键表 |
| `root-refresh` | (固定) | - |
| `bind-key` | (固定) | - |
| `user-keys` | `[]` | 用户自定义非 ASCII 键（3.3+） |
| `user-option` | `[]` | 自定义选项 |

### 常用 bind/unbind 模板

```bash
bind-key -T copy-mode-vi v send-keys -X begin-selection
bind-key -T copy-mode-vi y send-keys -X copy-selection
bind-key -T copy-mode-vi r send-keys -X rectangle-toggle
bind-key -T copy-mode-vi ] send-keys -X next-prompt
bind-key -T copy-mode-vi [ send-keys -X previous-prompt
```

---

## 8. 复制模式 / 缓冲区选项

| 选项 | 默认值 | 说明 |
|---|---|---|
| `buffer-limit` | `50` | 最多保留多少 buffer |
| `set-clipboard` | `""` | 系统剪贴板联动 |
| `editor` | ed 变体 | 编辑 buffer 的命令 |
| `pager` | more 变体 | 分页命令 |
| `word-separators` | 见会话 | 单词边界 |
| `copy-mode` | - | 进入复制模式（命令） |
| `display-message -p` | - | 把命令输出当作 buffer |

---

## 9. 终端 / TUI 选项

| 选项 | 默认值 | 说明 |
|---|---|---|
| `default-terminal` | `""` | 新窗格的 TERM |
| `default-terminal-mo` | - | 鼠标模式终端（3.4+） |
| `default-terminal-overrides` | - | 默认 overrides |
| `terminal-features` | `[]` | 声明特性：`*256:RGB`, `RGB`, `extkeys`, `clipboard`, `margins`, `strike`, `title` 等 |
| `terminal-overrides` | `[]` | 老旧终端兼容：例 `xterm*:XT:Ms=\\E[?1002h*` |
| `backspace` | `""` | 退格键字符 |
| `c0-override` | `[]` | C0 字符映射（3.2+） |
| `c0-disable` | `off` | 禁用某些 C0 字符 |
| `alternate-screen` | `on` | 是否使用 alternate screen buffer |
| `extended-keys` | `off` | 扩展键（CSI u 协议） |
| `focus-events` | `off` | focus 事件 |
| `mouse-utf8` | `on` | 鼠标 utf8 模式 |
| `mouse-pane`, `mouse-window`, `mouse-any`, `mouse-other` | `on/off/on/on` | 鼠标选择粒度 |
| `utf8` | (检测) | 是否 utf8 |

---

## 10. 鼠标 / 交互选项

| 选项 | 默认值 | 说明 |
|---|---|---|
| `mouse` | `off` | 总开关，强烈建议 `on` |
| `mouse-utf8` | `on` | utf8 鼠标 |
| `mouse-position-format` | `"#{mouse_press_button}"` | 鼠标按住时状态栏显示 |
| `mouse-shift-click-select-pane` | `on` | shift+点切 pane |
| `mouse-resize-pane` | `on` | 拖动边界 |
| `mouse-drag-pane` | `on` | 拖动 pane |
| `mouse-select-pane` | `on` | 点击切换 pane |
| `mouse-select-window` | `on` | 点击切换 window |
| `mouse-drag-window` | `on` | 拖动 window |
| `mouse-wheel-up`, `mouse-wheel-down` | - | 滚轮事件 |
| `extended-keys` | `off` | 终端扩展键协议 |
| `focus-events` | `off` | 焦点事件 |

### 推荐组合（最舒适的鼠标体验）

```bash
set -g mouse on
set -g mouse-utf8 on
set -g focus-events on
```

---

## 11. 钩子 / 扩展选项

### 钩子

| 钩子名 | 触发时机 |
|---|---|
| `client-attached` | client 连入 |
| `client-detached` | client 断开 |
| `client-resized` | client 尺寸变化 |
| `session-created` | 新建 session |
| `session-closed` | session 关闭 |
| `session-renamed` | session 重命名 |
| `window-linked` | window 链接到 session |
| `window-unlinked` | window 从 session 解链 |
| `window-renamed` | window 重命名 |
| `pane-focus-in` / `pane-focus-out` | pane 焦点变化 |
| `pane-exit` | pane 退出 |
| `pane-set-clipboard` | 剪贴板写入 |
| `after-resize-pane` / `before-resize-pane` | 调整 pane |
| `alert-bell`, `alert-activity`, `alert-silence` | 提示触发 |

示例：

```bash
set-hook -g after-resize-pane {
  refresh-client -L
}
set-hook -g pane-focus-in 'select-pane -P bg=colour234'
```

### 扩展（plugin）

tmux 1.9+ 支持 `run-shell` 加载插件，常用入口：

```bash
set -g @plugin 'tmux-plugins/tpm'
run '~/.tmux/plugins/tpm/tpm'
```

---

## 12. 256 配色表

### 常用 16 色

| 名 | hex | 含义 |
|---|---|---|
| `black` | `#000000` | 黑 |
| `red` | `#800000` | 暗红（ANSI 0 阶） |
| `green` | `#008000` | 暗绿 |
| `yellow` | `#808000` | 暗黄 |
| `blue` | `#000080` | 暗蓝 |
| `magenta` | `#800080` | 暗紫 |
| `cyan` | `#008080` | 暗青 |
| `white` | `#c0c0c0` | 亮灰 |
| `brightred/brightred` | `#ff0000` | 亮红（`brightred`） |
| `brightgreen` | `#00ff00` | 亮绿 |
| `brightyellow` | `#ffff00` | 亮黄 |
| `brightblue` | `#0000ff` | 亮蓝 |
| `brightmagenta` | `#ff00ff` | 亮紫 |
| `brightcyan` | `#00ffff` | 亮青 |
| `brightwhite` | `#ffffff` | 白 |
| `default` | - | 终端默认 |

### 256 调色板速查（推荐关注的几组）

| ID | 类型 | 用途 |
|---|---|---|
| `0-15` | ANSI | 基础 |
| `16-231` | 6×6×6 立方 | 中间色 |
| `232-255` | 灰度 | 边框、底色 |

**常用灰度（边框类）**

| ID | 色 |
|---|---|
| 232 | `#080808` |
| 234 | `#1c1c1c` |
| 235 | `#262626` |
| 236 | `#303030` |
| 240 | `#585858` |
| 244 | `#808080` |
| 245 | `#8a8a8a` |
| 246 | `#949494` |
| 247 | `#9e9e9e` |
| 248 | `#a8a8a8` |
| 250 | `#bcbcbc` |
| 252 | `#d0d0d0` |
| 255 | `#eeeeee` |

**常用强调色**

| ID | 色 |
|---|---|
| 39 | `#00afff` 亮青蓝（推荐作主强调） |
| 51 | `#00ffff` cyan |
| 46 | `#00ff00` 亮绿 |
| 196 | `#ff0000` 亮红 |
| 214 | `#ffaf00` 暖橙 |
| 220 | `#ffd700` 黄金 |
| 141 | `#af00ff` 紫 |
| 33 | `#00aaff` 天蓝 |

---

## 13. 样式属性速查

### 颜色

```
fg=colour39
bg=#1c1c1c     # hex
bg=black       # 命名色
fg=default     # 默认
fg=terminal    # 3.2+ 终端默认
```

### 文字属性（可空格组合）

| 属性 | 含义 |
|---|---|
| `none` | 关闭所有属性 |
| `bold` | 加粗 |
| `dim` | 暗 |
| `underscore` | 下划线 |
| `blink` | 闪烁 |
| `reverse` | 反色 |
| `hidden` | 隐藏 |
| `italics` | 斜体 |
| `strikethrough` | 删除线 |
| `overline` | 上划线（部分终端支持） |
| `doublesize`, `simplified-chinese`, `trad-chinese` | 部分终端支持 |

### 对齐（3.2+，少用）

| 属性 | 含义 |
|---|---|
| `align=left` | 左 |
| `align=right` | 右 |
| `align=centre` | 中 |
| `align=absolute-centre` | 绝对居中 |

### 组合示例

```bash
fg=colour39,bg=colour234,bold
fg=white,bg=default,italics
fg=#ff5555,reverse
```

---

## 14. 实用模板

### 模板 A：极简黑白（高对比）

```bash
set -g status-style "fg=white,bg=black"
set -g window-status-current-style "fg=black,bg=white,bold"
set -g window-status-style "fg=colour244"
set -g pane-border-style "fg=colour240"
set -g pane-active-border-style "fg=white"
set -g pane-border-lines heavy
```

### 模板 B：赛博青蓝

```bash
set -g status-style "fg=colour39,bg=black"
set -g window-status-current-style "fg=black,bg=colour39,bold"
set -g window-status-format "#[fg=colour244] #I #[fg=colour250]#W "
set -g window-status-current-format "#[fg=black,bg=colour39,bold] #I #[fg=black,bg=colour39,bold]#W "
set -g window-status-separator "  ┃  "
set -g pane-border-lines heavy
set -g pane-border-style "fg=colour236"
set -g pane-active-border-style "fg=colour39"
set -g message-style "fg=black,bg=colour39,bold"
```

### 模板 C：暖色 retro

```bash
set -g status-style "fg=colour220,bg=colour234"
set -g window-status-current-style "fg=colour234,bg=colour220,bold"
set -g window-status-style "fg=colour240"
set -g pane-active-border-style "fg=colour214"
set -g pane-border-style "fg=colour236"
```

### 模板 D：高对比紫黑

```bash
set -g status-style "fg=white,bg=colour234"
set -g window-status-current-style "fg=colour141,bg=black,bold"
set -g pane-active-border-style "fg=colour141"
set -g pane-border-style "fg=colour236"
```

### 模板 E：完整可开工配置（推荐）

```bash
# === 基础 ===
set -g default-terminal "tmux-256color"
set -ga terminal-features ",xterm*:RGB"
set -ga terminal-features ",xterm*:extkeys"

# === prefix 改键 ===
set -g prefix C-a
unbind C-b
bind C-a send-prefix

# === 鼠标 ===
set -g mouse on
set -g mouse-utf8 on
set -g focus-events on

# === 复制模式 vi ===
setw -g mode-keys vi
bind-key -T copy-mode-vi v   send-keys -X begin-selection
bind-key -T copy-mode-vi y   send-keys -X copy-selection
bind-key -T copy-mode-vi r   send-keys -X rectangle-toggle
bind-key -T copy-mode-vi j   send-keys -X cursor-down
bind-key -T copy-mode-vi k   send-keys -X cursor-up
bind-key -T copy-mode-vi l   send-keys -X cursor-right
bind-key -T copy-mode-vi h   send-keys -X cursor-left
bind-key -T copy-mode-vi M-j send-keys -X halfpage-down
bind-key -T copy-mode-vi M-k send-keys -X halfpage-up

# === 分割快捷键 ===
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"
unbind '"'
unbind %

# === 重新加载 ===
bind r source-file ~/.tmux.conf \; display-message "tmux.conf reloaded"

# === 状态栏 ===
set -g status-interval 1
set -g status-style "fg=white,bg=colour234"
set -g status-left  "#[fg=colour39] #S "
set -g status-right "#[fg=colour244] %Y-%m-%d %H:%M "
set -g window-status-format        "#[fg=colour244] #I #[fg=colour250]#W "
set -g window-status-current-format "#[fg=black,bg=colour39,bold] #I #[fg=black,bg=colour39,bold]#W "
set -g window-status-separator "  ┃  "
set -g pane-border-lines heavy
set -g pane-border-style "fg=colour236"
set -g pane-active-border-style "fg=colour39"

# === 索引从 1 开始 ===
set -g base-index 1
setw -g pane-base-index 1
set -g renumber-windows on

# === 滚轮友好（vim/neovim 关闭默认 mouse） ===
bind -n WheelUpPane if-shell -F -t = "#{mouse_any_flag}" \
  "send-keys -M" "if -Ft= '#{pane_in_mode}' 'send-keys -M' 'select-pane -t =; send-keys -M'"

# === 关闭 esc 延迟（vim/neovim） ===
set -sg escape-time 0
```

---

## 附录 A：版本兼容速查

| 选项 | 最低 tmux 版本 |
|---|---|
| `pane-border-indicators` | 3.4 |
| `window-style`, `window-active-style` | 3.4 |
| `menu-*`, `popup-*` | 3.4 |
| `display-panes-active-colour` | 2.6 |
| `pane-border-status` | 3.1 |
| `pane-border-lines` | 2.9 |
| `extended-keys` | 3.0 |
| `set-clipboard` | 2.5 |
| `terminal-features` | 2.7 |
| `command-alias`, `command-printer`, `command-prompt` | 3.2/3.3 |
| `prefix2` | 3.2 |
| `pane-scrollbars` | 3.5 |

## 附录 B：相关命令清单

```bash
# 信息
tmux info
tmux list-keys
tmux list-commands
tmux list-options
tmux list-windows
tmux list-sessions
tmux list-clients

# 运行时改
tmux set -g mouse on
tmux setw -g pane-border-lines heavy

# 检测终端能力
tmux display-message -p "#{client_termfeatures}"
```

---

## 附录 C：推荐插件清单

| 插件                                   | 作用                   |
| ------------------------------------ | -------------------- |
| `tmux-plugins/tpm`                   | Plugin manager（必装）   |
| `tmux-plugins/tmux-resurrect`        | 持久化会话（关机后恢复）         |
| `tmux-plugins/tmux-continuum`        | 定时自动保存               |
| `tmux-plugins/tmux-yank`             | macOS/Linux 剪贴板联动    |
| `tmux-plugins/tmux-sessionist`       | session/window 跳转    |
| `christoomey/vim-tmux-navigator`     | vim/tmux 无缝跳转（vim 侧） |
| `tmux-plugins/tmux-battery`          | 状态栏电量                |
| `tmux-plugins/tmux-cpu`              | 状态栏 CPU              |
| `tmux-plugins/tmux-online-status`    | 在线状态                 |
| `tmux-plugins/tmux-prefix-highlight` | prefix 触发时高亮指示       |

---

> 💡 文档版本：tmux 3.5 时代
> 💡 配置文件位置：`~/.tmux.conf`，修改后用 `tmux source-file ~/.tmux.conf` 生效
> 💡 调试技巧：不确定某个选项的作用时，运行 `tmux show-options -g | grep xxx`