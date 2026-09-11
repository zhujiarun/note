# HTTPS 本地开发指南（含 mkcert 详解）

> 适用场景：在本地开发 WebCodecs、WebTransport、WebGPU、WebRTC、Service Worker 等要求 SecureContext 的能力。

## 一、为什么需要 HTTPS

很多 API 标注了 `[SecureContext]`，仅在 HTTPS（或 `localhost` / `127.0.0.1`）下可用。涉及的就有：

- **WebCodecs**、**WebTransport**、**WebGPU**（部分实现）、**WebRTC**、**getUserMedia**
- **Service Worker**、**Push API**、**Notifications**
- **Clipboard API**、**Web Authentication**、**Payment Request**
- **SubtleCrypto**（部分用法）

`http://localhost` 和 `http://127.0.0.1` **本身被视为安全上下文**，直接用这两个访问就行。但如果用局域网 IP（如 `192.168.x.x`）或自定义域名（如 `dev.example.com`），就必须上 HTTPS。

## 二、最省事的方法：mkcert（强烈推荐）

`mkcert` 是本地最流行的工具，由 Filippo Valsorda（前 Go 团队成员，现 Let's Encrypt 工程师）开发，自动签发被系统和浏览器信任的证书。开源仓库 `github.com/FiloSottile/mkcert`。

### 安装 mkcert

**macOS**：
```bash
brew install mkcert
brew install nss   # 可选，Firefox 需要
```

**Windows**：
```powershell
choco install mkcert
# 或 scoop
scoop install mkcert
```

**Linux**：
```bash
sudo apt install mkcert
# 或手动下载 release binary
curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
```

### mkcert 的工作原理

普通自签证书（如 `openssl req -x509 ...`）在浏览器里会显示"您的连接不是私密连接"的红色警告页，因为证书颁发者不在系统信任列表。`mkcert` 的核心思路：

1. 在你的开发机上**自建一个本地 CA**
2. 把这个 CA 的根证书**安装到系统和浏览器的信任列表**
3. 用这个 CA 给你的 `localhost`、`dev.example.com` 等域名签发**叶子证书**

浏览器看到叶子证书的颁发者是自己信任的本地 CA，就不再警告。

### 初始化本地 CA

```bash
mkcert -install
```

执行后：
- 在 `~/.local/share/mkcert/`（Linux/macOS）或 `%LocalAppData%\mkcert\`（Windows）下生成根 CA 与（可选）中间 CA
- 自动调用系统的证书安装命令把根 CA 加进信任列表：
  - macOS：写入 System Keychain，提示输入开机密码
  - Linux：复制到 `/usr/share/ca-certificates/` 并 `update-ca-certificates`，或写入 `/etc/pki/ca-trust/` 并 `update-ca-trust`
  - Windows：导入到 `Cert:\LocalMachine\Root`
  - Firefox（任意系统）：写入它自己的 NSS 数据库

查看 CA 路径：
```bash
mkcert -CAROOT
```

### 签发证书

```bash
# 单个域名
mkcert dev.example.com

# 多个域名 + 通配符 + IP + IPv6
mkcert dev.example.com "*.dev.example.com" localhost 127.0.0.1 ::1

# 自定义输出路径
mkcert -cert-file cert.pem -key-file key.pem dev.example.com
```

输出文件：
- `<name>.pem`：叶子证书
- `<name>-key.pem`：私钥

### 证书的有效期与算法

| 项 | 默认值 | 说明 |
| --- | --- | --- |
| **叶子证书有效期** | **825 天（约 2.26 年）** | 遵循 Apple 在 iOS / macOS 上的策略：CA 签发的证书最长 825 天，超出会被 Safari 视为"长期有效"而拒绝信任 |
| **根 CA 有效期** | 10 年 | 长期有效，仅本机信任 |
| **中间 CA 有效期** | 10 年（部分版本默认引入） | 用中间 CA 可以让根 CA 保持离线，进一步隔离私钥风险 |
| **签名算法** | ECDSA P-256 + SHA-256 | 更小更快，现代浏览器和系统都支持；可通过 `-rsa` 回退到 RSA |
| **SAN（主体备用名）** | 命令行参数全量包含 | 多个域名 / 通配符 / IP 写在同一张证书里 |

自定义选项：
```bash
# 自定义有效期（天）
mkcert -days 365 dev.example.com

# 强制 RSA
mkcert -rsa 2048 dev.example.com
```

> 注：若客户端系��时间晚于 `Not After` 字段，证书会被视为已过期，需要重新签发。

### 私钥与证书安全

- `~/.local/share/mkcert/rootCA.pem`、`rootCA-key.pem` 仅在你的开发机上，**绝对不要**提交到 git 仓库或上传到云端
- 私钥泄露意味着攻击者可以为你的本地 CA 签发任何证书，相当于攻破了本机所有 HTTPS 测试
- 把 `certs/`、`*.pem`、`*.key` 加入 `.gitignore`

### 移动设备测试（重要）

做 FLV / 实时流开发多半要测真机，iOS / Android 默认不信任你电脑上的本地 CA。`mkcert` 提供 `pkcs12` 输出：

```bash
mkcert -pkcs12 -p12-file dev-example.p12 dev.example.com localhost 127.0.0.1
```

`-pkcs12` 把证书与私钥打包成 `.p12`（带密码），方便传输到设备。

**iOS**：
1. 把 `.p12` AirDrop 到 iPhone，会要求"安装描述文件"，到 设置 → 通用 → VPN 与设备管理 中信任
2. 关键步骤：到 设置 → 通用 → 关于 → 证书信任设置，把 mkcert 根 CA **启用完全信任**

**Android**：
1. 把根 CA `rootCA.pem` 拷贝到手机（重命名为 `.crt`）
2. 设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书（Android 7+ 要求明确选择）
3. 或用 ADB：`adb push rootCA.pem /sdcard/`，然后手动安装

> 移动端 HTTP/3 / WebTransport 测试较复杂，需要 nghttp3 + ngtcp2 或 Cloudflare 隧道，桌面端用 mkcert 即可。

### 进阶用法

**CAROOT 自定义路径**：适合团队共享或 CI：
```bash
export CAROOT=/path/to/shared/ca
mkcert -install
mkcert dev.example.com
```
每个开发者机器独立 `mkcert -install`，但根 CA 可由团队统一签发。

**包含 client cert（双向认证）**：
```bash
mkcert -client dev@example.com
```

**双证书（ECDSA + RSA）**：新版 mkcert 支持 `-ecdsa` 与 `-rsa` 分别生成，服务器配置双证书。

### 局限与替代方案

- **不能用于生产环境**：CA 仅本机信任，外部客户端会拒绝
- **团队成员需各自 `mkcert -install`**：无法跨机器共享信任
- **CI / Docker 中的处理**：用环境变量把证书注入容器，或在 CI 镜像里预装 mkcert
- **企业环境**：某些公司锁定系统 CA 信任列表，需管理员权限

备选方案（装不上 mkcert 时）：
- **`devcert`**（Node）：npm 包，API 调用生成证书
- **`local-ssl-proxy`**：Node CLI 工具，自动套 mkcert
- **`Caddy`**：自带自动 HTTPS，配置最简单
- **`trustme`**（Python）：类似 mkcert 的思路

### 卸载

```bash
mkcert -uninstall
```

自动从系统和浏览器的信任列表中移除本�� CA；已签发的叶子证书在 CA 仍然存在时仍可被验证通过，卸载只是让 CA 不再被信任。

## 三、Vue 2 项目接入

`vue.config.js`：

```js
const fs = require('fs')

module.exports = {
  devServer: {
    host: '0.0.0.0',           // 允许局域网访问
    port: 8080,
    https: {
      cert: fs.readFileSync('./certs/dev.example.com+5.pem'),
      key: fs.readFileSync('./certs/dev.example.com+5-key.pem'),
    },
    // 可选：把 HTTP 请求自动跳到 HTTPS
    setup(app) {
      app.use((req, res, next) => {
        if (!req.secure) {
          return res.redirect(`https://${req.headers.host}${req.url}`)
        }
        next()
      })
    },
  },
}
```

把生成的 `.pem` 文件放在项目里 `certs/` 目录后 `npm run serve`，浏览器打开 `https://dev.example.com:8080` 就会显示为安全连接。

> Windows 用户若想用局域网 IP 访问（如手机扫码测真机），需要在 `certs` 目录里给那个 IP 也签一份证书，例如 `mkcert 192.168.1.100`。

## 四、Vite 项目（如未来迁移）

`vite.config.js`：

```js
import { defineConfig } from 'vite'
import fs from 'fs'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: {
      cert: fs.readFileSync('./certs/dev.example.com+5.pem'),
      key: fs.readFileSync('./certs/dev.example.com+5-key.pem'),
    },
  },
})
```

或者用 `vite-plugin-mkcert` 自动调用 mkcert：

```bash
npm i -D vite-plugin-mkcert
```

```js
import mkcert from 'vite-plugin-mkcert'
export default {
  plugins: [mkcert({ hosts: ['localhost', '127.0.0.1', 'dev.local'] })],
}
```

## 五、其他备选

- **Caddy**：自带自动 HTTPS，写一个 `Caddyfile` 即可。
- **手动 OpenSSL**：能但繁琐，证书还得手动信任，不如 mkcert 省事。
- **浏览器绕过**（仅调试用，不推荐）：Chrome 启动参数 `--unsafely-treat-insecure-origin-as-secure=http://192.168.1.100:8080`。

## 六、生产环境

- **Let's Encrypt（certbot）**：免费、自动化、90 天续期。
- **云服务**：Vercel / Netlify / Cloudflare Pages 默认全站 HTTPS。
- **自托管 Nginx + certbot**：`certbot --nginx -d your.domain.com` 一条命令搞定。
- **WebTransport 还需要 HTTP/3（QUIC）**：在 Nginx 1.25+ 上启用即可，或用 Cloudflare 代理。

## 七、验证 HTTPS 是否生效

打开 `https://dev.example.com:8080`，地址栏显示锁形图标 ✅，然后在控制台运行：

```js
window.isSecureContext  // 应为 true
navigator.mediaDevices   // 应有 getUserMedia 方法
navigator.gpu            // 应非 undefined（WebGPU）
```

如果三项都符合，说明 SecureContext 已就绪，WebCodecs / WebGPU / WebTransport 都能用了。