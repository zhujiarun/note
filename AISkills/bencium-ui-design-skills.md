# UI 设计 Skill 与 Dashboard 版本对比

> 整理日期：2026-07-13

---

## 一、已安装的 UI 设计 Skill

### Bencium Marketplace（系统级）

来源：[bencium/bencium-marketplace](https://github.com/bencium/bencium-marketplace)，通过 `npx skills add` 安装到 `~/.agents/skills/`。

| Skill | 用途 | 适合场景 |
|---|---|---|
| bencium-controlled-ux-designer | 系统化 UX，WCAG 2.1 AA，数学比例 | 企业后台、B 端 SaaS |
| bencium-innovative-ux-designer | 大胆创意，实验性排版，反 AI 模板 | Landing Page、品牌页 |
| bencium-impact-designer | 生产级前端界面，可交付代码 | 产品界面开发 |
| design-audit | 视觉 UI/UX 审查，分阶段改版计划 | 设计改版、质量评估 |
| ui-typography | 出版级排版：引号、破折号、层级比例 | 内容密集型页面 |
| agentic-ux-design-relationship-centric-interfaces | AI 原生交互，记忆与信任演进 | AI 助手、长期工具 |

安装命令：
```bash
npx skills add bencium/bencium-marketplace -g --all
```

### 用户上传的 UI 设计 Skill（Cowork 可用）

以下 skill 已上传到 Cowork 的 `.claude/skills/` 目录，当前会话可调用：

| Skill | 定位 | 核心特征 |
|---|---|---|
| design-taste-frontend-v1 | 反 AI-slop 前端设计 v1 | 三档拨盘、反居中 Hero、翠绿单色 |
| minimalist-ui | 极简编辑风 | 暖白单色、衬线标题、1px 边框、无渐变 |
| industrial-brutalist-ui | 工业 CRT 终端风 | 零圆角、等宽字体、红色强调、扫描线 |
| gpt-taste | Awwwards 级 + GSAP 动效 | AIDA 结构、H1 2-3 行铁律、无缝便当网格 |
| high-end-visual-design | $150k Agency 级别 | Double-bezel 嵌套卡、Button-in-Button、浮动玻璃导航 |
| imagegen-frontend-web | 图片生成型设计参考 | 全幅氛围渐变、电影级 Hero、反默认左文右图 |
| redesign-existing-projects | 现有项目升级审计 | 扫描→诊断→修复，不改功能只升设计 |
| design-taste-frontend | 反 AI-slop 前端设计 v2 | 设计推断、场景预设表、设计系统映射 |

---

## 二、Dashboard 七版方案对比

需求：视频处理平台首页（功能导航），两张核心模块卡片（国标对接、视频拼接），点击打开 Tab 工作区。

| #   | 使用 Skill                 | 配色                          | 核心特征                                  |
| --- | ------------------------ | --------------------------- | ------------------------------------- |
| 1   | 手工调整                     | 暗色 + 青绿 `#00d4aa`           | 点阵纹理背景，hover 发光边框，激活态反转               |
| 2   | design-taste-frontend-v1 | 暗色 + 翠绿 `#10b981`           | 非对称 1.4fr/1fr 网格，staggered 入场动画       |
| 3   | minimalist-ui            | 浅色暖白 `#f7f6f3`              | 唯一浅色方案，衬线标题，IntersectionObserver 滚动显影 |
| 4   | industrial-brutalist-ui  | 暗黑 `#0a0a0a` + 红色 `#e61919` | CRT 扫描线，零圆角，等宽字体，ASCII 语法装饰           |
| 5   | high-end-visual-design   | 暗色 + 翠绿 + 紫                 | Double-bezel 双层嵌套卡，浮动玻璃丸导航            |
| 6   | gpt-taste                | 暗色 + 翠绿 `#00e0a0`           | AIDA 全屏 Hero，呼吸空态脉冲动画                 |
| 7   | imagegen-frontend-web    | 暗色 + 翠绿 `#00d8a0`           | 三层 ambient 渐变背景，Hero bottom-left 锚点   |

所有文件位于 outputs 目录，纯 HTML 单文件，浏览器直接打开即可预览。

---

## 三、各版本设计要点

### 1. dashboard.html（暗色科技风）

- 背景 `#13131f` + 32px 点阵纹理
- 卡片 `#222236`，hover 浮现青绿外发光
- 激活态整张卡变深青底 + 实色发光边框
- Share Tech Mono 等宽标签 + Noto Sans SC 正文
- 1.4fr/1fr 非对称网格

### 2. dashboard-v4.html（design-taste-frontend-v1）

- 严格按 v1 skill 三大拨盘：VARIANCE 8 / MOTION 6 / Density 4
- Outfit 标题字体 + Noto Sans SC
- 「LILA BAN」——无紫色/蓝色辉光，单翠绿强调
- 反居中 Hero：左对齐标题 + 右侧空白数字（02）
- 卡片 staggered 入场：animation-delay 0.1s / 0.25s
- 激活态 scale(0.985) 触觉反馈

### 3. dashboard-minimalist.html（minimalist-ui）

- 暖白 `#f7f6f3` 底色 + 极淡径向光斑
- Noto Serif SC 衬线标题（编辑感）+ Plus Jakarta Sans 正文
- 卡片仅 1px `#eaeaea` 边框，无阴影无渐变
- 标签用超淡粉彩：淡绿 `#edf3ec`、淡黄 `#fbf3db`
- `<kbd>` 快捷键标签：`Cmd + K Available Modules`
- IntersectionObserver 滚动显影，600ms 缓动

### 4. dashboard-industrial.html（industrial-brutalist-ui）

- 暗黑 `#0a0a0a` CRT 底色 + 扫描线伪元素
- IBM Plex Mono 全等宽字体 + Archivo Black 标题
- 零 border-radius，直角工业感
- `#e61919` 红色唯一强调，无第二种彩色
- 卡片用 `gap:1px` 网格 + 实色分割线
- ASCII 语法 `[ MODULE ]` `>>>` `///` 装饰
- 顶部闪烁红点（step-end 动画）+ `REV 3.7 // UNIT D-01` 伪终端状态行
- SVG 噪点纹理叠加

### 5. dashboard-high-end.html（high-end-visual-design）

- Double-bezel：外层 card-shell（`border-radius:32px` + 微白底）+ 内层 card-core（`border-radius:26px` + inset 高光线）
- 浮动玻璃丸导航：`backdrop-blur:24px` + `position:sticky` 置顶
- 自定义 cubic-bezier(0.32, 0.72, 0, 1) 全局缓动
- 三层 ambient glow 背景
- Tab 栏圆角胶囊式 + 每个 tab 独立圆角
- 空状态虚线环 + 居中标记

### 6. dashboard-gsap-taste.html（gpt-taste）

- AIDA 四段结构：Hero → Bento Grid → Tab 工作区 → Footer
- 全屏 Hero（90dvh）：Outfit 800 字重 + 翠绿高亮 + 双 CTA
- 滚动提示：渐隐竖线 + 浮动 "Scroll" 文字
- 便当网格 1.5fr/1fr，grid-auto-flow:dense
- 卡片 hover 上浮 3px + 翠绿边框光晕
- 空状态脉冲环动画（2.5s 呼吸周期）
- "浏览模块" / "快速开始" 双按钮，高对比度

### 7. dashboard-imagegen.html（imagegen-frontend-web）

- Hero bottom-left 锚点——刻意避免"左文右图"AI 默认模式
- 全幅三层 radial-gradient ambient 氛围（青绿 + 紫 + 深绿），无纯色底
- 36px 间距微点阵叠加
- 装饰性竖线（vertical rhythm line）——skill 要求的第二读时刻
- 卡片带 module ref 编号标签（`Module / Protocol — GB/T 28181`）
- CTA button-in-button：箭头嵌在独立小方块内
- Outfit 300-800 字重全系列 + Share Tech Mono 标签
