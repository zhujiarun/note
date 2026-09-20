# tmux 插件安装与使用

> 配合阅读：
> - [[tmux-config-reference]] —— 配置选项参考
> - [[tmux配置项速查手册]] —— 配置项速查
>
> 本文聚焦"插件"：`tmux` 本身功能强，但**插件生态**才是它真正"无敌"的部分。

---

## 零、核心思路

tmux 本身只是个"多窗口终端复用器"，但它的插件系统非常成熟。最主流的安装方式是 **TPM（Tmux Plugin Manager）**——一行命令装好，然后配置里逐个加插件、prefix + `I` 装、prefix + `U` 升级。

> 一个核心心智模型：**插件本质是一段 tmux 配置脚本**。TPM 把它们按你的 `~/.tmux.conf` 列表下载到 `~/.tmux/plugins/` 里，并在每次启动 tmux 时自动 source。**所以插件也能覆盖你的快捷键、覆盖你的颜色——小心冲突**。

---

## 一、装 TPM

```bash
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

在 `~/.tmux.conf` 末尾加上：

```bash
# 列出所有插件（每行一个）
set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'tmux-plugins/tmux-sensible'
set -g @plugin 'tmux-plugins/tmux-yank'
# ... 你想用的插件

# 这一行必须放最后（启动 TPM）
run '~/.tmux/plugins/tpm/tpm'
```

让配置生效：

```bash
tmux source-file ~/.tmux.conf
```

---

## 二、插件操作键位（最重要）

本文假设你已经把 prefix 改成 `Ctrl-a`（推荐，比默认 `Ctrl-b` 顺手）。要改成 `Ctrl-a`，先在 `~/.tmux.conf` 顶部加：

```bash
unbind C-b
set -g prefix C-a
bind C-a send-prefix   # 单独按 Ctrl-a 时仍能传给 shell
```

| 操作 | 键位 | 说明 |
|------|------|------|
| **安装**插件（首次或新增后） | `prefix + I`（大写 i） | TPM 读取 `@plugin` 列表，clone 到 `~/.tmux/plugins/` 并 source |
| **更新**所有插件 | `prefix + U`（大写 u） | 拉最新代码并重新 source |
| **卸载**已删除的插件 | `prefix + alt + u` | 先从 `~/.tmux.conf` 删掉 `@plugin` 行，再按这个 |
| **查看**插件状态 | `prefix + ?`（部分插件） | 例如 `tmux-prefix-highlight` 文档里有提示 |

> ⚠️ 小写 `i` / `u` 是 tmux 默认的 `display-message` / `choose-window`，**别和插件管理搞混**。

---

## 三、推荐插件（按性价比排序）

### 1. tmux-sensible（必装，零配置）

```bash
set -g @plugin 'tmux-plugins/tmux-sensible'
```

一套"tmux 默认就该这样"的合理设置：256 色、真彩色、聚焦事件、合理的历史限制、UTF-8 支持。**零配置**，装上就生效，不会和你已有配置打架。

### 2. tmux-yank（剪贴板互通）

```bash
set -g @plugin 'tmux-plugins/tmux-yank'
```

把 tmux 复制模式里的内容**直接送到系统剪贴板**：

| 操作 | 行为 |
|------|------|
| 选中一段文本 | 自动复制到系统剪贴板 |
| `prefix + y` | 把当前命令行复制到剪贴板 |
| 鼠标拖选 | macOS 同步到 `pbcopy` |
| `prefix + Y` | 把历史命令粘贴进命令行 |

> macOS 用户：tmux ≥ 3.2 已经内置支持 `pbcopy`。**老版本** tmux 需要装 `reattach-to-user-namespace` 并在 `tmux.conf` 顶部加：
> ```bash
> set-option -g default-command "reattach-to-user-namespace -l $SHELL"
> ```

### 3. tmux-resurrect + tmux-continuum（**会话持久化**）

```bash
set -g @plugin 'tmux-plugins/tmux-resurrect'
set -g @plugin 'tmux-plugins/tmux-continuum'
```

**这套组合是"tmux 最强插件"**——电脑重启或断网后，会话完整恢复（窗口、面板、当前工作目录）。

**resurrect 手动**：

| 操作 | 行为 |
|------|------|
| `prefix + Ctrl-s` | 保存当前会话快照 |
| `prefix + Ctrl-r` | 恢复（覆盖当前） |
| `prefix + S` | 选择性保存（按窗格选择） |
| `prefix + R` | 选择性恢复 |

**continuum 自动**：

```bash
set -g @continuum-save-interval '15'    # 每 15 分钟自动保存
set -g @continuum-restore 'on'         # tmux 启动时自动恢复
set -g @continuum-boot 'on'            # 系统启动后 tmux 自启（可选）
```

**保存文件位置**：`~/.tmux/resurrect/`（默认）。想换位置：

```bash
set -g @resurrect-dir '/path/to/backup'
```

**pane 内容恢复**（vim/htop 等 TUI 程序状态）：

```bash
set -g @resurrect-capture-pane-contents 'on'
# 按下 Ctrl-s 时自动把每个 pane 的最后若干行输出保存下来
```

> 注意：vim/htop 等真正"进程级"恢复需要额外工具，resurrect 主要恢复的是**布局 + 命令历史 + 当前路径**。

### 4. tmux-prefix-highlight（前缀提示）

```bash
set -g @plugin 'tmux-plugins/tmux-prefix-highlight'
```

按 prefix 后状态栏变色，告诉你"现在是 prefix 模式，按下一个键就执行命令"。

自定义提示样式（用 [[tmux配置项速查手册]] 里的 style 语法）：

```bash
set -g @prefix-highlight-bg 'colour235'   # 按下 prefix 后状态栏变深灰
set -g @prefix-highlight-fg 'colour39'    # 文字变青
```

### 5. tmux-pain-control（vim 式分屏）

```bash
set -g @plugin 'tmux-plugins/tmux-pain-control'
```

| 操作 | 行为 |
|------|------|
| `prefix + h/j/k/l` | 在面板间移动（左/下/上/右） |
| `prefix + H/J/K/L` | 调整面板大小 |
| `prefix + <` / `>` | 左右缩放当前面板 |

**vim 用户必备**——不用记方向键。

### 6. tmux-copycat（增强搜索选择）

```bash
set -g @plugin 'tmux-plugins/tmux-copycat'
```

在复制模式下：

| 操作 | 行为 |
|------|------|
| `prefix + /` | 在窗口里搜索并高亮所有匹配 |
| `prefix + f` | 模糊搜索 URL、UUID、单词 |
| 选中后按 `y` | 复制（配合 yank 自动送系统剪贴板） |

### 7. tmux-open（URL 和文件）

```bash
set -g @plugin 'tmux-plugins/tmux-open'
```

复制模式下选中：

| 选中内容 | 按 `o` 后行为 |
|---------|--------------|
| 完整 URL（`http://...`） | 默认浏览器打开 |
| 文件路径（`./src/main.cpp`） | 用 `$EDITOR` 打开 |
| `user@host:path` 形式 | scp 处理 |

### 8. tmux-battery（状态栏显示电量）

```bash
set -g @plugin 'tmux-plugins/tmux-battery'
```

状态栏右侧自动显示笔记本电池百分比和剩余时间。**Linux/macOS** 自动支持，**Windows WSL** 不支持。

### 9. tmux-cpu（CPU 使用率）

```bash
set -g @plugin 'tmux-plugins/tmux-cpu'
set -g @cpu-low-bg 'colour39'
set -g @cpu-medium-bg 'colour226'
set -g @cpu-high-bg 'colour196'
```

状态栏显示 CPU 占用率，颜色随负载变化。

---

## 四、推荐起步配置（可直接复制）

新建 `~/.tmux.conf`：

```bash
# ===== 基础 =====
# 256 色 / 真彩色
set -sg default-terminal 'tmux-256color'
set -ga terminal-overrides ',xterm-256color:Tc'

# 把 prefix 改成 Ctrl-a
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# 鼠标支持
set -g mouse on

# 历史保留更多
set -g history-limit 100000

# 重新加载配置（prefix + r）
bind r source-file ~/.tmux.conf \; display-message "config reloaded!"

# ===== 插件列表 =====
set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'tmux-plugins/tmux-sensible'
set -g @plugin 'tmux-plugins/tmux-yank'
set -g @plugin 'tmux-plugins/tmux-resurrect'
set -g @plugin 'tmux-plugins/tmux-continuum'
set -g @plugin 'tmux-plugins/tmux-prefix-highlight'
set -g @plugin 'tmux-plugins/tmux-pain-control'

# resurrect / continuum 配置
set -g @continuum-save-interval '15'
set -g @continuum-restore 'on'
set -g @resurrect-capture-pane-contents 'on'

# 必须放最后：启动 TPM
run '~/.tmux/plugins/tpm/tpm'
```

加载：

```bash
tmux source-file ~/.tmux.conf
```

按下 `prefix + I`（大写 i），TPM 会自动 clone 所有插件到 `~/.tmux/plugins/`，**整个过程一般几秒**。看到状态栏显示 `Installing...` 转一下就装好了。

---

## 五、键位速查（这一篇能上手）

| 操作 | 键位 |
|------|------|
| prefix | `Ctrl-a`（已改） |
| 装/更新插件 | `prefix + I` / `prefix + U` |
| 卸载插件 | `prefix + alt + u` |
| 保存会话 | `prefix + Ctrl-s` |
| 恢复会话 | `prefix + Ctrl-r` |
| 重新加载配置 | `prefix + r` |
| vim 式切换面板 | `prefix + h/j/k/l` |
| 复制当前命令 | `prefix + y` |

---

## 六、踩坑提示

| 现象 | 解决 |
|------|------|
| macOS 上 `prefix + y` 没反应 | 升级 tmux 到 ≥ 3.2，或装 `reattach-to-user-namespace` |
| resurrect 恢复后 vim/htop 内容空白 | 加 `set -g @resurrect-capture-pane-contents 'on'` |
| `prefix + I` 装失败 / 报错 | 检查 `~/.tmux/plugins/tpm/tpm` 这行是否在 `tmux.conf` **最后** |
| 插件覆盖了我的快捷键 | 装之前看插件文档，把它的 `bind` 放你 `tmux.conf` 之后，或用 `unbind` 解除冲突 |
| 想换 prefix | 必须三行配套：`unbind C-b` + `set -g prefix X` + `bind X send-prefix` |
| 插件装到一半网络卡住 | `prefix + I` 不响应就重启 tmux 重来；TPM 是基于 git 的，不影响 tmux 本身运行 |
| 启动报 `returned 127` | shell 错误码 127 = **"找不到命令"**。原因不是路径错了，而是 `~/.tmux/plugins/tpm/tpm` 这个文件**不存在或没执行权限**。通常 `git clone` 半路出问题（网络中断、目录残留）就会这样。**删掉重 clone 即可**：`rm -rf ~/.tmux/plugins/tpm && git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm`。验证：`ls -la ~/.tmux/plugins/tpm/tpm` 看到 `-rwxr-xr-x` 且文件非空；`bash ~/.tmux/plugins/tpm/tpm` 不报 `No such file or directory` |
| 按 `prefix + I` 控制台完全没反应 | 三个常见原因：(1) `run '~/.tmux/plugins/tpm/tpm'` 不是配置最后一行；(2) 用 `if-shell` 包裹了 TPM 导致首次安装时不执行；(3) `~/.tmux/plugins/tpm/` 根本没建出来（TPM 没装） |

### 启动报 `returned 127` 的排查流程

错误码 127 在 shell 里含义很明确——**"找不到命令"**。这里意思是 tmux 想执行 `~/.tmux/plugins/tpm/tpm`，但**那个文件不存在**。

**步骤 1：确认文件存在**

```bash
ls -la ~/.tmux/plugins/tpm/tpm
```

- ✅ 看到 `-rwxr-xr-x ... ~/.tmux/plugins/tpm/tpm` → 文件正常
- ❌ `No such file or directory` → 文件没下下来，进入步骤 2

**步骤 2：手动执行看真实错误**

```bash
bash ~/.tmux/plugins/tpm/tpm
```

| 输出 | 含义 |
|------|------|
| `No such file or directory` | 文件确实不在，重新 clone |
| `Permission denied` | `chmod +x ~/.tmux/plugins/tpm/tpm` |
| 进入交互或正常退出 | TPM 文件 OK，问题在别处 |

**步骤 3：重新 clone**

```bash
rm -rf ~/.tmux/plugins/tpm    # 先清掉可能损坏的残留
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

clone 完验证 `tpm` 文件存在 + 有可执行权限，然后 `tmux source-file ~/.tmux.conf` + `prefix + I`。

---

## 七、原理图（心智模型）

```
~/.tmux.conf
   │
   │  启动时 tmux 顺序读取
   ▼
┌─────────────────────────────────────┐
│  你的基础配置（prefix、颜色、绑键）   │
│  ──────────────────────────────────│
│  @plugin 'tmux-plugins/tpm'         │
│  @plugin 'tmux-plugins/tmux-yank'   │
│  @plugin 'tmux-plugins/tmux-res...' │
│  ...                                │
│  ──────────────────────────────────│
│  run '~/.tmux/plugins/tpm/tpm'      │ ← TPM 接管
└─────────────────────────────────────┘
                                      │
                                      ▼
              按 prefix + I → TPM 克隆 / 更新插件
              按 prefix + U → TPM 重新 source 所有插件配置
```

简单说：**`@plugin` 是一份"清单"，`run '~/.tmux/plugins/tpm/tpm'` 是"清单执行器"**。前者随便加，后者必须放最后。

---

## 八、完整使用流程

```
① 装 TPM
   git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

② 写配置
   把上面的"起步配置"粘到 ~/.tmux.conf

③ 加载配置
   tmux source-file ~/.tmux.conf

④ 装插件
   prefix + I（大写 i）

⑤ 验证
   prefix + y  → 复制一段命令粘贴到外面看是否生效
   prefix + Ctrl-s → 状态栏提示 "saving..."
   重启电脑后再开 tmux → 会话自动回来（continuum 生效）

⑥ 按需扩展
   在 ~/.tmux.conf 里加 @plugin 行
   prefix + I 装新插件
```
