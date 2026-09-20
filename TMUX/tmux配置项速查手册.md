# tmux 配置项速查手册

> - 适用版本：**tmux 3.4**（本机 `tmux -V` 实测）
> - 数据来源：`man tmux` + tmux 3.4 源码 [`options-table.c`](https://github.com/tmux/tmux/blob/3.4/options-table.c)（选项名、类型、作用域、默认值全部取自源码中的选项表，共 **121** 项）
> - 整理日期：2026-09-20

## 目录

1. [配置文件与加载方式](#1-配置文件与加载方式)
2. [作用域与设置命令（最关键）](#2-作用域与设置命令最关键)
3. [服务器选项 server（18 项）](#3-服务器选项-server18-项)
4. [会话选项 session（48 项）](#4-会话选项-session48-项)
5. [窗口选项 window（42 项）](#5-窗口选项-window42-项)
6. [窗口 + 面板选项 window-pane（13 项）](#6-窗口--面板选项-windowpane13-项)
7. [常用配置实战](#7-常用配置实战)
8. [样式 style 语法](#8-样式-style-语法)
9. [格式 format 常用变量](#9-格式-format-常用变量)
10. [完整示例配置](#10-完整示例配置)
11. [排错与参考](#11-排错与参考)

---

## 1. 配置文件与加载方式

| 文件 | 说明 |
| --- | --- |
| `~/.tmux.conf` | 用户配置，最常用 |
| `~/.config/tmux/tmux.conf` | 较新版本在 `~/.tmux.conf` 不存在时读取 |
| `/etc/tmux.conf` | 全局配置 |
| 其他文件 | 需自己 `source-file`，例如常见的 `~/.tmux.conf.local` |

### 语法要点（对应 man 的 COMMAND PARSING AND EXECUTION / PARSING SYNTAX）

- **一行一条命令**，`#` 到行尾都是注释；**tmux 不支持块注释**，批量注释只能每行加 `#`（或用 `%if 0 ... %endif` 整块禁用）。
- `#` 只有在"一个词的开头"才触发注释：`bg=#1e1e2e` 不用加引号也安全；但 `#I:#W#F` 必须写成 `"#I:#W#F"`，否则整行被当注释。
- 含 `#`、`%`、空格、`;`、`{}` 的参数一律用双引号包起来最保险（`%H:%M` 不加引号会直接报错）。
- 行尾 `\` 是续行；**注释行末尾如果有 `\`，会把下一行一起吞进注释**（不报错，极易踩坑）。
- 变量：`NAME=value` 单独成行可定义环境变量；`%hidden NAME=value` 定义不进 `show-environment` 的隐藏变量。
- 条件：`%if` / `%elif` / `%else` / `%endif`，参数按 format 求值，假（0 或空）则跳过整块。

### 加载与生效

```bash
tmux source-file ~/.tmux.conf        # 热加载
# 或在 tmux 里：prefix + : 然后输入 source-file ~/.tmux.conf
# 常见绑定：bind r source-file ~/.tmux.conf \; display "reloaded"
```

- 改完**立即生效**的：状态栏相关、`mouse`、`mode-keys`、键绑定等。
- **只对新对象生效**的：`history-limit`（新面板）、`default-shell` / `default-command` / `default-terminal`（新窗口/会话）、`default-size`（新会话）。
- 配置有语法错时该行被忽略（可能只报第一处），排查见 [第 11 节](#11-排错与参考)。

---

## 2. 作用域与设置命令（最关键）

tmux 有 **4 种作用域**，用错作用域是"配置写了但不生效"的头号原因。

| 作用域 | 含量 | 设置命令 | 查看 |
| --- | --- | --- | --- |
| server（服务器） | 18 | `set -s`（全局唯一） | `show -s` |
| session（会话） | 48 | `set` / `set -g`（全局会话） | `show` / `show -g` |
| window（窗口） | 42 | `setw` / `set -w` / `set -gw` | `showw` / `show -gw` |
| window+pane（窗口或面板） | 13 | `setw -g` 或 `set -p` | `show -gw` / `show -p` |

### `set-option`（别名 `set`）旗标

| 旗标 | 作用 |
| --- | --- |
| `-g` | 设置**全局**会话/窗口选项（新会话/新窗口的默认值） |
| `-s` | 服务器选项 | 
| `-w` | 窗口选项 |
| `-p` | 面板选项 |
| `-a` | **追加**（字符串拼接 / 样式合并），如 `set -ag status-style "fg=blue"` |
| `-u` | 取消设置，回落继承全局值（`-gu` 恢复默认） |
| `-U` | 同 `-u`，但面板选项会同时作用于窗口内所有面板 |
| `-o` | 只在未设置时设置（防覆盖） |
| `-q` | 抑制未知/歧义选项的报错 |
| `-F` | 让 value 里的 format 展开 |

**类型推断**：非用户选项时 `-w` / `-s` 可以省略，tmux 会按选项名自动推断（面板选项默认按 `-w` 处理）。所以 `set -g mode-keys vi`、`set -g window-status-separator " │ "` 都是合法的，即使 `mode-keys` / `window-status-separator` 实际是窗口选项。

```tmux
set -g mouse on                       # 会话选项
set -g status-style "bg=#1e1e2e"      # 会话选项
setw -g mode-keys vi                  # 窗口选项（全局窗口）
set -w pane-border-status top         # 当前窗口
set -s escape-time 10                 # 服务器选项
set -g @plugin 'tmux-plugins/tpm'     # 用户自定义选项（@ 开头）
```

**查看与验证**

```bash
tmux show -g                      # 全部全局会话选项
tmux show -s                      # 全部服务器选项
tmux show -gw                     # 全部全局窗口选项
tmux show -gv status-style        # 只输出值
tmux show -gA | grep window-status  # -A 连同继承来的值一起显示（带 *）
tmux show -gwv @myvar
```

---

## 3. 服务器选项 server（18 项）

用 `set -s` 设置（也可写进 `~/.tmux.conf`，仍然是 `set -s`）。

| 选项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `backspace` | 按键 | `C-h`(DEL) | 发给终端的退格键。终端里退格/删除不灵时调整 |
| `buffer-limit` | 数字 | `50` | 自动 buffer 上限，超出丢弃最旧的 |
| `command-alias` | 数组 | `split-pane=split-window, splitp=…, server-info=…, info=…, choose-window=…, choose-session=…` | 命令别名，格式 `别名=命令`，逗号分隔 |
| `copy-command` | 字符串 | 空 | 复制文本时执行的 shell 命令，空表示不执行 |
| `default-terminal` | 字符串 | `screen`（视编译而定，常见 `tmux-256color`） | 新窗口的 `TERM` 值，决定 tmux 内程序的色彩能力 |
| `editor` | 字符串 | `vi` | 编辑文件用的编辑器，常改成 `vim` / `nvim` |
| `escape-time` | 数字(ms) | `500` | 判定单独 Esc 的等待时间；**vim 用户建议 10~50** |
| `exit-empty` | 开关 | `on` | 没有会话时服务器是否退出 |
| `exit-unattached` | 开关 | `off` | 没有已连接客户端时服务器是否退出 |
| `extended-keys` | 枚举 | `off`（off/on/always） | 是否向支持扩展按键的终端请求扩展序列（kitty 协议等） |
| `focus-events` | 开关 | `off` | 是否向应用程序发送焦点获得/丢失事件 |
| `history-file` | 字符串 | 空 | 命令提示符历史文件位置，空=不写 |
| `message-limit` | 数字 | `1000` | 保留的服务器消息条数 |
| `prompt-history-limit` | 数字 | `100` | 命令提示符保留的历史条数 |
| `set-clipboard` | 枚举 | `external`（off/external/on） | 是否设置系统剪贴板；`external` = 允许 tmux 读终端剪贴板但不允许应用创建 paste buffer，`on` = 两者都允许（配合 SSH/tmux 嵌套） |
| `terminal-overrides` | 数组 | 空 | 终端能力覆盖，经典用法 `set -as terminal-overrides ",*:Tc"` 开真彩 |
| `terminal-features` | 数组 | `xterm*:clipboard:ccolour:cstyle:focus:title, screen*:title, rxvt*:…` | 自动探测失败时声明的终端特性 |
| `user-keys` | 数组 | 空 | 自定义按键序列，依次映射为 `User0`、`User1`… |

> ⚠️ 只有 `set -s`（或 `set-option -s`）设置的才是服务器选项；写成 `set -g escape-time 10` 虽然会被推断，但语义上属于服务器级。

---

## 4. 会话选项 session（48 项）

用 `set -g`（全局会话）或 `set`（当前会话）设置。

| 选项                            | 类型     | 默认值                                                                                             | 说明                                   |
| ----------------------------- | ------ | ----------------------------------------------------------------------------------------------- | ------------------------------------ |
| `activity-action`             | 枚举     | `other`（none/any/current/other）                                                                 | 监视到活动时对哪些窗口报警                        |
| `assume-paste-time`           | 数字(ms) | `1`                                                                                             | 两次输入多快算"粘贴"而非"打字"                    |
| `base-index`                  | 数字     | `0`                                                                                             | 窗口编号起点，设 `1` 让第一个窗口叫 1               |
| `bell-action`                 | 枚举     | `any`（none/any/current/other）                                                                   | 响铃时对哪些窗口报警                           |
| `default-command`             | 字符串    | 空                                                                                               | 新面板里运行的默认命令，空=启动 shell               |
| `default-shell`               | 字符串    | 空（取 `$SHELL`）                                                                                   | 默认 shell 的绝对路径                       |
| `default-size`                | 字符串    | `80x24`                                                                                         | 新会话的初始尺寸，如 `200x50`                  |
| `destroy-unattached`          | 枚举     | `off`（off/on/keep-last/keep-group）                                                              | 无客户端连接时是否销毁会话                        |
| `detach-on-destroy`           | 枚举     | `on`（off/on/no-detached/previous/next）                                                          | 当前会话被销毁时断开还是切到别的会话                   |
| `display-panes-active-colour` | 颜色     | `colour1`（红）                                                                                    | `display-panes`（`prefix q`）时当前面板编号颜色 |
| `display-panes-colour`        | 颜色     | `colour4`（蓝）                                                                                    | 其它面板编号颜色                             |
| `display-panes-time`          | 数字(ms) | `1000`                                                                                          | 面板编号显示时长                             |
| `display-time`                | 数字(ms) | `750`                                                                                           | 状态栏消息显示时长                            |
| `history-limit`               | 数字     | `2000`                                                                                          | 每个面板的回滚行数，**改动只对新面板生效**              |
| `key-table`                   | 字符串    | `root`                                                                                          | 默认按键表                                |
| `lock-after-time`             | 数字(s)  | `0`                                                                                             | 空闲多久锁定客户端，0=不锁                       |
| `lock-command`                | 字符串    | 空                                                                                               | 锁屏时执行的命令                             |
| `message-command-style`       | 字符串    | `bg=black,fg=yellow`                                                                            | vi 模式命令行的样式                          |
| `message-line`                | 枚举     | `0`（0/1/2/3/4）                                                                                  | 消息与命令行显示在第几行（0=状态栏）                  |
| `message-style`               | 字符串    | `bg=yellow,fg=black`                                                                            | 消息与命令行样式                             |
| `mouse`                       | 开关     | `off`                                                                                           | 是否识别鼠标并执行鼠标绑定                        |
| `prefix`                      | 按键     | `C-b`                                                                                           | 前缀键，常改 `C-a`                         |
| `prefix2`                     | 按键     | 无                                                                                               | 第二前缀键                                |
| `renumber-windows`            | 开关     | `off`                                                                                           | 关闭窗口后是否自动把编号补齐                       |
| `repeat-time`                 | 数字(ms) | `500`                                                                                           | 带 `-r` 的绑定可连按的时间窗                    |
| `set-titles`                  | 开关     | `off`                                                                                           | 是否设置终端标题（`xterm` 类终端）                |
| `set-titles-string`           | 字符串    | `#S:#I:#W - "#T" #{session_alerts}`                                                             | 终端标题格式                               |
| `silence-action`              | 枚举     | `other`                                                                                         | 静默告警动作                               |
| `status`                      | 枚举     | `on`（off/on/2/3/4/5）                                                                            | 状态栏行数，2~5 为多行状态栏                     |
| `status-bg`                   | 颜色     | `colour8`                                                                                       | **已废弃**，请用 `status-style`            |
| `status-fg`                   | 颜色     | `colour8`                                                                                       | **已废弃**，请用 `status-style`            |
| `status-format`               | 数组     | 内置                                                                                              | 每一行状态栏的格式，配合 `status 2/3/…` 做多行状态栏   |
| `status-interval`             | 数字(s)  | `15`                                                                                            | 状态栏刷新间隔，0=只在需要时刷新                    |
| `status-justify`              | 枚举     | `left`（left/centre/right/absolute-centre）                                                       | 窗口列表对齐方式                             |
| `status-keys`                 | 枚举     | `emacs`（emacs/vi）                                                                               | 命令提示符的按键风格                           |
| `status-left`                 | 字符串    | `[#{session_name}] `                                                                            | 状态栏左区内容                              |
| `status-left-length`          | 数字     | `10`                                                                                            | 左区最大宽度（字符）                           |
| `status-left-style`           | 字符串    | `default`                                                                                       | 左区样式                                 |
| `status-position`             | 枚举     | `bottom`（top/bottom）                                                                            | 状态栏在顶部还是底部                           |
| `status-right`                | 字符串    | 内置（时间/窗口尺寸等）                                                                                    | 状态栏右区内容                              |
| `status-right-length`         | 数字     | `40`                                                                                            | 右区最大宽度                               |
| `status-right-style`          | 字符串    | `default`                                                                                       | 右区样式                                 |
| `status-style`                | 字符串    | `bg=green,fg=black`                                                                             | 状态栏整体样式                              |
| `update-environment`          | 数组     | `DISPLAY KRB5CCNAME SSH_ASKPASS SSH_AUTH_SOCK SSH_AGENT_PID SSH_CONNECTION WINDOWID XAUTHORITY` | 客户端附加时同步到会话环境变量的列表                   |
| `visual-activity`             | 枚举     | `off`（off/on/both）                                                                              | 活动提示方式：消息 / 消息+响铃 / 无                |
| `visual-bell`                 | 枚举     | `off`（off/on/both）                                                                              | 响铃提示方式                               |
| `visual-silence`              | 枚举     | `off`（off/on/both）                                                                              | 静默提示方式                               |
| `word-separators`             | 字符串    | `` !"#$%&'()*+,-./:;<=>?@[\]^`{\|}~ ``                                                          | 视为单词分隔符的字符集                          |

---

## 5. 窗口选项 window（42 项）

用 `setw -g`（全局窗口，等价 `set -gw`）设置，或 `setw`（当前窗口）。

| 选项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `aggressive-resize` | 开关 | `off` | `window-size=smallest` 时，按"当前窗口所在的最小会话"还是"所有链接会话"算尺寸 |
| `automatic-rename` | 开关 | `on` | 自动按运行的程序重命名窗口 |
| `automatic-rename-format` | 字符串 | `#{?pane_in_mode,[tmux],#{pane_current_command}}#{?pane_dead,[dead],}` | 自动重命名用的格式 |
| `clock-mode-colour` | 颜色 | `colour4`（蓝） | 时钟模式（`prefix t`）的时钟颜色 |
| `clock-mode-style` | 枚举 | `24`（12/24） | 时钟模式显示 12/24 小时制 |
| `copy-mode-match-style` | 字符串 | `bg=cyan,fg=black` | 复制模式中搜索命中的样式 |
| `copy-mode-current-match-style` | 字符串 | `bg=magenta,fg=black` | 当前选中命中的样式 |
| `copy-mode-mark-style` | 字符串 | `bg=red,fg=black` | 复制模式中已标记行的样式 |
| `fill-character` | 字符串 | 空 | 窗口空白区域填充字符 |
| `main-pane-height` | 字符串 | `24` | `main-horizontal` 布局主面板高度，可写 `50%` |
| `main-pane-width` | 字符串 | `80` | `main-vertical` 布局主面板宽度，可写 `50%` |
| `mode-keys` | 枚举 | `emacs`（emacs/vi） | **复制模式的按键风格，vim 用户必设 `vi`** |
| `mode-style` | 字符串 | `bg=yellow,fg=black` | 模式指示器与高亮样式 |
| `monitor-activity` | 开关 | `off` | 监视窗口活动并告警 |
| `monitor-bell` | 开关 | `on` | 监视响铃并告警 |
| `monitor-silence` | 数字(s) | `0` | 静默多少秒后告警，0=关闭 |
| `other-pane-height` | 字符串 | `0` | `main-horizontal` 其它面板高度 |
| `other-pane-width` | 字符串 | `0` | `main-vertical` 其它面板宽度 |
| `pane-active-border-style` | 字符串 | `#{?pane_in_mode,fg=yellow,#{?synchronize-panes,fg=red,fg=green}}` | 活动面板边框样式（默认绿色） |
| `pane-base-index` | 数字 | `0` | 面板编号起点，配合 `prefix q` 使用 |
| `pane-border-indicators` | 枚举 | `colour`（off/colour/arrows/both） | 活动面板用颜色还是箭头标记 |
| `pane-border-lines` | 枚举 | `single`（single/double/heavy/simple/number） | 面板边框线型（UTF-8 终端才支持部分线型） |
| `pane-border-status` | 枚举 | `off`（off/top/bottom） | 面板标题栏位置 |
| `pane-border-style` | 字符串 | `default` | 非活动面板边框/标题样式 |
| `popup-style` | 字符串 | `default` | 弹出层（`display-popup`）样式 |
| `popup-border-style` | 字符串 | `default` | 弹出层边框样式 |
| `popup-border-lines` | 枚举 | `single`（single/double/heavy/simple/rounded/padded/none） | 弹出层边框线型 |
| `remain-on-exit-format` | 字符串 | 内置（`Pane is dead (status …)`） | 面板死亡提示的格式 |
| `window-active-style` | 字符串 | `default` | 活动面板整体样式（常用 `bg=#000000` 突出当前面板） |
| `window-size` | 枚举 | `latest`（largest/smallest/manual/latest） | 窗口尺寸如何确定，多客户端时最关键 |
| `window-status-activity-style` | 字符串 | `reverse` | 有活动告警的窗口在状态栏的样式 |
| `window-status-bell-style` | 字符串 | `reverse` | 有响铃的窗口在状态栏的样式 |
| `window-status-current-format` | 字符串 | `#I:#W#{?window_flags,#{window_flags}, }` | **当前窗口**在状态栏的格式 |
| `window-status-current-style` | 字符串 | `default` | **当前窗口**在状态栏的样式（默认无区分 → 需手动设置） |
| `window-status-format` | 字符串 | `#I:#W#{?window_flags,#{window_flags}, }` | 非当前窗口的格式 |
| `window-status-last-style` | 字符串 | `default` | 上一个窗口的样式 |
| `window-status-separator` | 字符串 | 单个空格 | **窗口之间的分隔符（默认只有一个空格，看不出边界就改这里）** |
| `window-status-style` | 字符串 | `default` | 普通窗口在状态栏的样式 |
| `wrap-search` | 开关 | `on` | 复制模式搜索到顶/底是否回绕 |
| `xterm-keys` | 开关 | `on` | 已废弃，不再使用 |

---

## 6. 窗口 + 面板选项 window+pane（13 项）

这类选项既可当**窗口选项**（`setw -g` 作用于窗口内所有面板），也可当**面板选项**（`set -p` 只影响一个面板）。

| 选项                      | 类型   | 默认值                                                                                   | 说明                                                  |
| ----------------------- | ---- | ------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `allow-passthrough`     | 枚举   | `off`（off/on/all）                                                                     | 是否让 tmux 内的程序用 passthrough 转义序列直接写终端                |
| `allow-rename`          | 开关   | `off`                                                                                 | 是否允许应用通过转义序列改窗口名                                    |
| `alternate-screen`      | 开关   | `on`                                                                                  | 是否允许应用使用备用屏幕                                        |
| `cursor-colour`         | 颜色   | `default`                                                                             | 光标颜色                                                |
| `cursor-style`          | 枚举   | `default`（default/blinking-block/block/blinking-underline/underline/blinking-bar/bar） | 光标形状                                                |
| `pane-border-format`    | 字符串  | `#{?pane_active,#[reverse],}#{pane_index}#[default] "#{pane_title}"`                  | 面板标题栏内容（需先开 `pane-border-status`）                   |
| `pane-colours`          | 颜色数组 | 空                                                                                     | 覆盖面板内 256 色调色板，如 `set -p pane-colours[0] '#000000'` |
| `remain-on-exit`        | 枚举   | `off`（off/on/failed）                                                                  | 面板里命令退出后是否保留（保留可看输出/报错）                             |
| `remain-on-exit-format` | 字符串  | 内置                                                                                    | 死亡面板的提示格式                                           |
| `scroll-on-clear`       | 开关   | `on`                                                                                  | 执行 `clear` 时把内容滚进历史而不是清空                            |
| `synchronize-panes`     | 开关   | `off`                                                                                 | 把输入同步到窗口内所有面板（批量改机器神器）                              |
| `window-active-style`   | 字符串  | `default`                                                                             | 活动面板整体样式                                            |
| `window-style`          | 字符串  | `default`                                                                             | 非活动面板整体样式                                           |

```tmux
# 常用组合：当前面板亮、其余面板压暗
setw -g window-style "bg=#1a1a1a"
setw -g window-active-style "bg=#000000"
# 给所有面板开同步输入（临时用 prefix + : 执行 setw synchronize-panes on）
```

---

## 7. 常用配置实战

### 7.1 前缀与基础体验

```tmux
set -g prefix C-a                 # 前缀改成 Ctrl-a
bind C-a send-prefix              # 让 Ctrl-a 能连按两次发给内层
set -s escape-time 10             # vim/neovim 用户必设，消除 Esc 延迟
set -g base-index 1               # 窗口从 1 开始
setw -g pane-base-index 1         # 面板从 1 开始
set -g renumber-windows on        # 关窗后自动补编号
set -g history-limit 50000        # 回滚缓冲（只对新面板生效）
set -g display-time 2000          # 消息显示 2 秒
set -g set-titles on              # 设置终端标题
set -g set-titles-string "#S:#I:#W"
```

### 7.2 窗口与面板

```tmux
bind c new-window -c "#{pane_current_path}"     # 新窗口沿用当前路径
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R
setw -g mode-keys vi                            # 复制模式用 vi 键
setw -g pane-border-status top                  # 每个面板顶部显示标题
setw -g pane-border-format " #{pane_index} #{pane_current_command} "
setw -g pane-border-lines heavy                 # 粗边框（UTF-8 终端）
setw -g pane-active-border-style "fg=#89b4fa"   # 活动面板边框高亮
setw -g synchronize-panes off
```

### 7.3 鼠标

```tmux
set -g mouse on
# 鼠标滚轮在普通面板里默认就会进入复制模式；拖拽选择由 tmux 处理
set -s set-clipboard on                # 复制时写入系统剪贴板（SSH 场景也能用 OSC 52）
# 想禁用滚轮进复制模式：unbind -n WheelUpPane
# 想左键拖拽直接复制：bind -T copy-mode-vi MouseDragEnd1Pane send -X copy-selection-and-cancel
```

### 7.4 复制模式与剪贴板

```tmux
setw -g mode-keys vi
bind -T copy-mode-vi v send -X begin-selection
bind -T copy-mode-vi y send -X copy-selection-and-cancel
bind -T copy-mode-vi C-c send -X copy-selection-and-cancel
setw -g copy-mode-match-style "bg=#89b4fa,fg=#1e1e2e"
setw -g copy-mode-current-match-style "bg=#f9e2af,fg=#1e1e2e"
set -s copy-command 'pbcopy'        # macOS：复制时同步到系统剪贴板
```

### 7.5 状态栏（含"看不出哪个窗口是激活的"修法）

```tmux
set -g status on
set -g status-position bottom
set -g status-justify left
set -g status-interval 5
set -g status-left-length 40
set -g status-right-length 80

set -g status-style "bg=#1e1e2e,fg=#cdd6f4"
set -g status-left  "#[fg=#1e1e2e,bg=#89b4fa,bold] #S #[fg=#89b4fa,bg=#1e1e2e] "
set -g status-right "#[fg=#6c7086]#{?window_zoomed_flag,ZOOM ,}#[fg=#a6adc8] %m-%d %H:%M "

# ★ 关键：默认分隔符只是"一个空格"，所以窗口之间没有边界（window-status-separator 默认值就是单个空格）
set -g window-status-separator " │ "
set -g window-status-style "fg=#6c7086,bg=#1e1e2e"
set -g window-status-format "#I:#W#F"
# ★ 关键：默认 window-status-current-style 是 default（等于没有区分），必须自己设
set -g window-status-current-style "fg=#1e1e2e,bg=#89b4fa,bold"
set -g window-status-current-format "#I:#W#F"
# 其它状态
set -g window-status-last-style "fg=#f9e2af,bg=#1e1e2e"
set -g window-status-activity-style "fg=#f38ba8,bg=#1e1e2e,bold"
set -g window-status-bell-style "fg=#1e1e2e,bg=#f38ba8,bold"
```

> 注意：`window-status-format` 等虽是窗口作用域，但用 `set -g` 也能生效（tmux 会推断类型）。

### 7.6 颜色与真彩（truecolor）

```tmux
set -g default-terminal "tmux-256color"      # 新窗口的 TERM
set -as terminal-overrides ",*:Tc"           # 让 tmux 内程序用 24bit 颜色（tmux 3.x 推荐写法）
# 老写法（等价）：set -as terminal-overrides ",xterm-256color:RGB"
set -g focus-events on
set -s extended-keys on                      # 支持 kitty/CSI u 的终端
set -g allow-passthrough on                  # 允许内层程序直接写终端（如图片预览）
```

验证真彩是否生效：tmux 内执行

```bash
printf '\033[38;2;255;100;0mTRUECOLOR\033[0m\n'
tmux info | grep -i -E 'Tc|RGB|256'          # 查看终端能力
echo $TERM                                    # 期望 tmux-256color 或 screen-256color
```

### 7.7 告警与提示

```tmux
setw -g monitor-activity on
set -g visual-activity off        # 只看状态栏标记，不弹消息
set -g visual-bell off
set -g bell-action none           # 关掉所有响铃动作
set -g visual-silence off
setw -g monitor-silence 0
```

### 7.8 嵌套 tmux / SSH 场景

```tmux
# 本地 tmux 里再 ssh 到远端 tmux 时，用不同的前缀键区分
set -g prefix C-a
# 远端会话把状态栏放顶部，一眼区分内外层
set -g status-position top
set -g status-style "bg=#1e3a5f,fg=#ffffff"
# 关闭外层对扩展按键的干扰
set -s extended-keys always
```

### 7.9 多客户端 / 不同屏幕尺寸

```tmux
setw -g window-size latest        # 跟随最近使用的客户端（默认）
# setw -g window-size smallest    # 迁就最小客户端（小屏 ssh 时不撑破）
setw -g aggressive-resize on      # 只有当前窗口占据完整尺寸，其它窗口保持小尺寸
```

### 7.10 插件与用户选项

```tmux
set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'tmux-plugins/tmux-sensible'
set -g @resurrect-dir '~/.tmux/resurrect'     # 用户自定义选项，插件读取
run '~/.tmux/plugins/tpm/tpm'
```

---

## 8. 样式 style 语法

所有 `*-style` 选项的值都是"样式串"，可以写成 `default`（重置为默认），或用空格/逗号分隔的属性列表：

| 写法 | 含义 |
| --- | --- |
| `fg=colour` / `bg=colour` | 前景 / 背景色 |
| `us=colour` | 下划线颜色 |
| `none` | 关闭所有属性 |
| `bright`(或 `bold`)、`dim`、`underscore`、`blink`、`reverse`、`hidden`、`italics`、`overline`、`strikethrough`、`acs` | 属性；前面加 `no` 关闭，如 `noreverse` |
| `align=left/centre/right`、`noalign` | 对齐（状态栏多行格式用） |
| `fill=colour` | 用背景色填充剩余空间 |
| `list=on` / `list=focus` / `list=left-marker` / `list=right-marker` | 标记窗口列表的组成部分（`status-format` 多行状态栏用） |
| `push-default` / `pop-default` | 保存 / 恢复当前默认样式 |
| `range=left`/`range=right`/`range=session\|X`/`range=window\|X`/`range=pane\|X` | 标记可点击区域（鼠标事件） |

**颜色的写法**（`colour` 处可填入）：

- 8 色名：`black red green yellow blue magenta cyan white`，加亮版 `brightred` 等
- 256 色：`colour0` ~ `colour255`
- `default`（终端默认色）、`terminal`（终端原始默认色）
- 真彩：`#rrggbb`（终端不支持时 tmux 会自动降到最接近的 256 色）

**内联样式**：在 format 里用 `#[` 和 `]` 临时改样式，例如

```tmux
set -g status-left "#[fg=#1e1e2e,bg=#89b4fa,bold] #S #[fg=#89b4fa,bg=#1e1e2e] "
set -g window-status-current-format "#[fg=#45475a,bg=#1e1e2e]│#[fg=#1e1e2e,bg=#89b4fa,bold] #I:#W#F #[fg=#45475a,bg=#1e1e2e]│"
```

**优先级**：format 里的 `#[...]` 内联样式会覆盖对应的 `*-style` 选项。两者混用时要清楚谁生效（例如 `window-status-format` 里写死了颜色，`window-status-activity-style` 就不会再起作用）。

---

## 9. 格式 format 常用变量

### 9.1 常用变量

| 分类  | 变量（短别名）                                                                                                                                                                                                                                                                                                     | 说明                                                  |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 会话  | `#S` / `#{session_name}`、`#{session_windows}`、`#{session_attached}`、`#{session_created}`、`#{session_path}`、`#{session_alert}`                                                                                                                                                                               | 会话名、窗口数、连接数、创建时间、路径、告警                              |
| 客户端 | `#{client_width}`、`#{client_height}`、`#{client_termname}`、`#{client_tty}`、`#{client_session}`                                                                                                                                                                                                               | 客户端尺寸/终端类型/tty                                      |
| 窗口  | `#I`（`window_index`）、`#W`（`window_name`）、`#F`（`window_flags`）、`#{window_active}`、`#{window_zoomed_flag}`、`#{window_panes}`、`#{window_width}`、`#{window_height}`、`#{window_activity}`、`#{window_last_flag}`、`#{window_activity_flag}`、`#{window_bell_flag}`、`#{window_silence_flag}`、`#{window_marked_flag}` | 窗口编号/名字/标志位（`*` 当前、`-` 上一个、`#` 活动、`!` 响铃、`Z` 放大）/状态 |
| 面板  | `#{pane_index}`、`#{pane_title}`、`#{pane_current_command}`、`#{pane_current_path}`、`#{pane_active}`、`#{pane_pid}`、`#{pane_width}`、`#{pane_height}`、`#{pane_in_mode}`、`#{pane_dead}`、`#{pane_dead_status}`、`#{pane_synchronized}`                                                                              | 面板编号/标题/当前命令/当前路径/是否活动                              |
| 系统  | `#{host}`、`#{host_short}`、`#{pid}`、`#{version}`、`#{socket_path}`                                                                                                                                                                                                                                            | 主机名、PID、版本                                          |
| 时间  | `%H:%M`、`%Y-%m-%d`、`%a`、`%b`                                                                                                                                                                                                                                                                                | strftime 格式，直接写在字符串里                                |

### 9.2 条件与运算符

```tmux
#{?window_zoomed_flag,ZOOM ,}            # 三元：条件为真取第一个
#{==:#{host},myhost}                     # 比较：== != < > <= >=
#{&&:#{pane_in_mode},#{alternate_on}}    # 与 / 或
#{m:*foo*,#{host}}                       # fnmatch 匹配；#{m/ri:^A,MYVAR} 正则+忽略大小写
#{||:#{pane_in_mode},#{alternate_on}}
```

> 在条件内部，`,` 和 `}` 要转义成 `#,` 和 `#}`；`#{` 后跟 `{` 时表示内层 format。

### 9.3 修饰符

| 修饰符 | 说明 |
| --- | --- |
| `#{=5:...}` / `#{=-5:...}` | 截断为前 5 / 后 5 个字符；`#{=/5/...:...}` 截断时追加后缀 |
| `#{p10:...}` | 左侧补空格到宽度 10（负数为右侧补） |
| `#{n:window_name}` / `#{w:window_name}` | 变量长度 / 显示宽度 |
| `#{t:window_activity}` | 时间戳转字符串（`t/p` 用简短格式，`t/f/%H#:%%M:` 自定义 strftime） |
| `#{b:pane_current_path}` / `#{d:...}` | basename / dirname |
| `#{q:...}` / `#{q/h:...}` | shell 转义 / 转义 `#`（变成 `##`） |
| `#{E:status-left}` | 把选项内容当 format 再展开一次 |
| `#{T:...}` | 同 `E:`，另外展开 strftime |
| `#{S:...}` `#{W:...}` `#{P:...}` `#{L:...}` | 遍历会话/窗口/面板/客户端逐个插入 |
| `#{N/w:foo}` / `#{N/s:foo}` | 窗口/会话名是否存在（1/0） |
| `#{s/foo/bar/:...}` | 字符串替换 |
| `#{a:98}` / `#{c:colour}` | 数字转 ASCII / 颜色转 `#rrggbb` |
| `#{e\|op\|prec:num1,num2}` | 算术运算，如 `#{e\|+\|:1,2}`；运算符 `+ - * / m M` 等，`prec` 为小数位 |
| `#{l:...}` / `#{B:...}` | 按宽度左对齐 / 取字符串宽度 |
| `##` `#,` `#}` | 字面量 `#` `,` `}` |

### 9.4 调试 format

```bash
tmux display-message -p '#{session_name} #{window_index} #{pane_current_path}'
tmux display-message -p -F '#{W:#{window_index}:#{window_name} }'   # 遍历所有窗口
tmux display-message -p '#{E:status-left}'
```

---

## 10. 完整示例配置

一份覆盖常用项的 `~/.tmux.conf` 模板（tmux 3.x）：

```tmux
# ============ 基础 ============
set -g prefix C-a
bind C-a send-prefix
set -s escape-time 10
set -g base-index 1
setw -g pane-base-index 1
set -g renumber-windows on
set -g history-limit 50000
set -g display-time 2000

# ============ 终端与颜色 ============
set -g default-terminal "tmux-256color"
set -as terminal-overrides ",*:Tc"
set -g focus-events on
set -g allow-passthrough on

# ============ 鼠标 ============
set -g mouse on

# ============ 窗口 / 面板 ============
bind c new-window -c "#{pane_current_path}"
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R
bind r source-file ~/.tmux.conf \; display "reloaded"
setw -g mode-keys vi
setw -g pane-border-status top
setw -g pane-border-format " #{pane_index} #{pane_current_command} "
setw -g pane-border-lines heavy
setw -g pane-active-border-style "fg=#89b4fa"
setw -g window-style "bg=#181825"
setw -g window-active-style "bg=#1e1e2e"

# ============ 复制模式 ============
bind -T copy-mode-vi v send -X begin-selection
bind -T copy-mode-vi y send -X copy-selection-and-cancel
bind -T copy-mode-vi C-c send -X copy-selection-and-cancel
setw -g copy-mode-match-style "bg=#89b4fa,fg=#1e1e2e"
set -s set-clipboard on

# ============ 状态栏 ============
set -g status on
set -g status-position bottom
set -g status-justify left
set -g status-interval 5
set -g status-left-length 40
set -g status-right-length 80
set -g status-style "bg=#1e1e2e,fg=#cdd6f4"
set -g status-left  "#[fg=#1e1e2e,bg=#89b4fa,bold] #S #[fg=#89b4fa,bg=#1e1e2e] "
set -g status-right "#[fg=#6c7086]#{?window_zoomed_flag,ZOOM ,}#[fg=#a6adc8] %m-%d %H:%M "
set -g window-status-separator " │ "
set -g window-status-style "fg=#6c7086,bg=#1e1e2e"
set -g window-status-format "#I:#W#F"
set -g window-status-current-style "fg=#1e1e2e,bg=#89b4fa,bold"
set -g window-status-current-format "#I:#W#F"
set -g window-status-last-style "fg=#f9e2af,bg=#1e1e2e"
set -g window-status-activity-style "fg=#f38ba8,bg=#1e1e2e,bold"
set -g window-status-bell-style "fg=#1e1e2e,bg=#f38ba8,bold"

# ============ 告警 ============
setw -g monitor-activity on
set -g visual-activity off
set -g visual-bell off
set -g bell-action none

# ============ 消息与模式 ============
set -g message-style "bg=#89b4fa,fg=#1e1e2e"
set -g message-command-style "bg=#89b4fa,fg=#1e1e2e"
setw -g mode-style "bg=#f9e2af,fg=#1e1e2e"
```

---

## 11. 排错与参考

### 11.1 配置写了不生效？

1. **作用域错了**：`status-*` 是会话选项、`window-status-*` / `mode-keys` / `pane-*` 是窗口选项、`escape-time` 是服务器选项。用 `tmux show -gwv mode-keys` 这类命令确认真正生效的值。
2. **只对新对象生效**：`history-limit`、`default-shell`、`default-command`、`default-terminal`、`default-size` 改完要新建窗口/面板/会话。
3. **没重载**：`prefix + r` 或 `tmux source-file ~/.tmux.conf`。
4. **被覆盖**：`#[...]` 内联样式覆盖 `*-style`；`-a` 追加过的东西会一直在（用 `set -gu` 恢复默认）。
5. **有语法错**：注意"注释行末尾的 `\`"会把下一行吞掉、`#I`/`%H` 不加引号会被当注释或报错。

### 11.2 常用排查命令

```bash
tmux -V                                  # 版本（不同版本选项名不同）
tmux show -g | grep status               # 看会话选项实际值
tmux show -gw | grep -E 'mode|pane-'     # 看窗口选项实际值
tmux show -s | grep escape               # 看服务器选项实际值
tmux source-file ~/.tmux.conf            # 加载并在状态栏报错
tmux -v                                  # 前台带日志启动，排查解析错误
tmux info | head -40                     # 终端能力、真彩支持
tmux list-keys                           # 当前全部键绑定
tmux display-message -p '#{version}'     # 客户端版本
```

### 11.3 版本差异提醒

| 能力 | 起始版本 |
| --- | --- |
| `*-style` 系列（`status-style`、`window-status-current-style`…） | 1.9（更早用 `status-bg`/`status-fg`/`window-status-current-fg` 等，已废弃） |
| `pane-border-status` / `pane-border-format` | 2.3 |
| `set-clipboard` 默认值改为 `external` | 3.2 前后 |
| `status-format` 多行状态栏、`#{}` 范围标记 | 2.9 / 3.0 |
| `allow-passthrough` | 3.3 |
| `pane-border-lines` / `popup-border-lines`、`cursor-style` | 3.4 |
| `%if` 条件、`terminal-features` | 2.x / 3.2 |

### 11.4 参考

- `man tmux`（最权威，本机版本 3.4，共 3896 行）
- tmux 源码选项总表：[`options-table.c` (3.4)](https://github.com/tmux/tmux/blob/3.4/options-table.c)
- tmux 源码词法/语法：[`cmd-parse.y`](https://github.com/tmux/tmux/blob/master/cmd-parse.y)
- 官方手册页在线版：<https://man.openbsd.org/tmux.1>
- 配色参考：Catppuccin for tmux <https://github.com/catppuccin/tmux>、Tokyo Night、Gruvbox 等


