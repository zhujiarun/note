# npm 发包流程（基于 Verdaccio）

## 适用场景

将前端项目或 npm 包发布到私有 npm 源（Verdaccio），适用于公司内部组件库、静态资源等场景。

---

## 前提条件

- Node.js 和 npm 已安装
- Verdaccio 已安装（未安装执行 `npm install -g verdaccio`）

---

## 操作步骤

### 1. 初始化项目

```bash
cd 你的项目目录
npm init -y
```

然后根据需要编辑 `package.json`：

```json
{
  "name": "my-package",       // 包名，发布时唯一标识
  "version": "1.0.0",         // 版本号
  "description": "项目描述",
  "main": "index.js",         // 入口文件
  "author": "你的名字",
  "license": "ISC"
}
```

> **注意**：`name` 不能和 Verdaccio 上已有的包重名，否则发布会失败。

### 2. 编写项目内容

根据项目类型添加文件，例如前端页面项目：

```
项目目录/
├── package.json
├── .npmrc
├── index.html
├── style.css
└── script.js
```

### 3. 配置私有源地址

在项目根目录创建 `.npmrc` 文件：

```
registry=http://localhost:4873/
```

> **说明**：这样执行 `npm publish` 时会自动发到本地 Verdaccio，而不是公网 npm。如果只想对 publish 生效，可以改为：
> ```
> publishRegistry=http://localhost:4873/
> ```

### 4. 启动 Verdaccio

```bash
# 确保 Verdaccio 已全局安装
npm install -g verdaccio

# 启动服务（默认监听 http://localhost:4873）
verdaccio
```

启动后浏览器访问 `http://localhost:4873` 可以看到 Verdaccio 的 Web 界面。

### 5. 注册/登录账号

**如果是首次使用**，需要创建一个 Verdaccio 账号：

```bash
npm adduser --registry http://localhost:4873/
```

按提示依次输入：
- Username（用户名）
- Password（密码）
- Email（邮箱）

**如果已有账号**，直接登录：

```bash
npm login --registry http://localhost:4873/
```

> 登录信息会保存在本地的 `~/.npmrc` 中，下次发布无需重复登录。

### 6. 发布

```bash
npm publish
```

发布成功后，可以访问 `http://localhost:4873` 在 Web 界面查看已发布的包。

---

## 后续更新

修改代码后，更新版本号再发布：

```bash
# 更新版本号（小版本 +1，例如 1.0.0 → 1.0.1）
npm version patch

# 发布新版本
npm publish
```

版本号更新方式：

| 命令 | 说明 | 示例 |
|------|------|------|
| `npm version patch` | 修复版本 +1 | 1.0.0 → 1.0.1 |
| `npm version minor` | 次版本 +1 | 1.0.0 → 1.1.0 |
| `npm version major` | 主版本 +1 | 1.0.0 → 2.0.0 |

---

## 安装使用

其他项目安装你发布的包：

```bash
npm install my-package --registry http://localhost:4873/
```

也可以在目标项目的 `.npmrc` 中配置 registry，之后直接用 `npm install my-package`。

---

## 常见问题

### Q: 发布时报 403 或 401 错误？

A: 通常是未登录或登录过期，重新执行：
```bash
npm login --registry http://localhost:4873/
```

### Q: 报 `You cannot publish over the previously published versions`？

A: 版本号重复了，用 `npm version patch` 更新版本号后再发布。

### Q: Verdaccio 启动报端口被占用？

A: 可以通过 `--listen` 指定其他端口：
```bash
verdaccio --listen 4874
```
同时记得把 `.npmrc` 中的端口号也改成对应的。
