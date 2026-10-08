# Vue 3 全栈项目部署方案：从 macOS 到国内 Linux 云服务器

整理日期：2026-09-21

## 1. 项目背景与结论

- 前端使用 Vue 3，需要加入 Node.js 后端、Redis 和主数据库。
- 前期使用自己的 Mac 开发、部署和验证，后期迁移到 Linux 云服务器。
- 访客主要是国内客户，因此正式部署优先考虑国内访问质量和稳定性。

推荐采用 **Vue 3 + Vite + TypeScript + Node.js LTS + NestJS + PostgreSQL + Prisma + Redis + Caddy + Docker Compose**。

在 Mac 上通过 Docker Compose 搭建完整环境；正式对客户开放时，部署到中国大陆 Linux 云服务器，继续使用 Caddy 作为网站入口，不使用 Cloudflare Tunnel 作为默认的正式访问通道。

## 2. 技术选型

| 部分 | 推荐方案 | 用途与选择理由 |
| --- | --- | --- |
| 前端 | Vue 3 + Vite + TypeScript | 开发体验成熟，生产构建生成静态文件 |
| 后端 | Node.js LTS + NestJS | 提供 API、登录鉴权和业务逻辑，适合按模块组织持续增长的项目 |
| 主数据库 | PostgreSQL | 保存用户、订单、权限及其他核心业务数据，支持事务、关联查询和数据约束 |
| 数据访问 | Prisma | 定义数据模型、执行查询、管理数据库迁移 |
| 缓存与临时状态 | Redis | 用于缓存、会话和限流；按实际需求引入 |
| 异步任务（可选） | BullMQ + Redis | 在需要后台任务、重试或队列时使用 |
| 网站入口 | Caddy | 托管前端静态文件、反向代理 API、管理 HTTPS |
| 服务编排 | Docker Compose | 统一管理应用、网络和数据卷，降低 Mac 到 Linux 的迁移成本 |
| 正式运行环境 | 国内云服务器上的 Ubuntu LTS | 适合面向国内用户运行服务，可选择阿里云、腾讯云或华为云等 |

NestJS 是 Node.js 上的后端框架，并不是独立的运行时。如果已有成熟的 Node.js 后端，也不必只为了部署而更换框架。

## 3. PostgreSQL 与 MongoDB 如何选择

**初期优先选择 PostgreSQL，不同时引入两种主数据库。**

PostgreSQL 适合用户、组织、权限、订单、支付记录等相互关联的数据，事务和约束有助于保证业务数据一致性。对于部分结构灵活的字段，可以使用 JSONB，不必因此立即增加 MongoDB。

如果核心数据天然是结构变化较大、通常作为整体读写的文档，而且业务主要围绕这种数据模型组织，再评估 MongoDB。

Redis 不替代主数据库。核心业务记录仍保存到 PostgreSQL，Redis 中的普通缓存应能在失效或丢失后重建。如果 Redis 用于任务队列或其他需要保留的状态，则需要额外考虑持久化与恢复。

## 4. Caddy 和 cloudflared 是什么

### Caddy：网站的统一入口

Caddy 是 Web 服务器和反向代理，作用类似 Nginx，主要负责：

1. 返回 Vue 构建后的 HTML、CSS、JavaScript 和图片。
2. 将 `/api` 请求转发给 Node.js 后端。
3. 处理 HTTPS，并在符合证书签发条件时自动申请和续期证书。

Caddy 运行在自己的 Mac 或云服务器上，不要求流量经过 Cloudflare，也不依赖境外 CDN。Nginx 也能实现同类功能，这里推荐 Caddy 是因为其常见配置较简洁。

公开域名使用常规自动 HTTPS 时，需要正确配置域名解析，并满足证书验证的网络条件。Caddy 的证书数据也应持久化。

### cloudflared：Cloudflare Tunnel 的客户端

`cloudflared` 是 Cloudflare Tunnel 的客户端程序。它从 Mac 主动连接 Cloudflare，使外部请求能够经隧道进入本地服务，通常无需公网 IP 或路由器端口映射。

Cloudflare Tunnel 的访问质量受到地区、运营商和网络链路影响。对于主要面向国内客户的正式业务，不将它作为默认入口。后期使用有公网地址的云服务器时，通常无需运行 `cloudflared`。

**Caddy 与 cloudflared 不是同类工具，也不存在必须配套使用的关系。**

## 5. 推荐部署结构

```text
客户浏览器
    │ HTTPS / 业务域名
    ▼
Caddy
    ├── 页面、静态资源 ──► Vue 3 构建产物
    └── /api 请求 ──────► Node.js / NestJS
                              ├──► PostgreSQL
                              └──► Redis
```

前端和 API 推荐使用同一个域名：

- 页面：`https://example.com/`
- API：`https://example.com/api/`

这样可以减少跨域和 Cookie 配置的复杂度。后端是否包含 `/api` 前缀应与代理规则保持一致。

Caddy 对外提供 HTTP/HTTPS 入口；后端、PostgreSQL 和 Redis 通过 Compose 内部网络通信。生产环境不必把数据库、Redis 或后端端口直接映射到公网。

Vue Router 使用 history 模式时，为前端页面路由配置回退到 `index.html`，同时避免把 API 错误响应也回退为前端页面。

## 6. macOS 阶段的实施方式

Mac 可安装 Docker Desktop，或者选择 Colima 等兼容 Docker 的运行环境。macOS 上的 Linux 容器实际运行在 Linux 虚拟机中，因此会占用一定内存和磁盘。

建议区分两种使用方式：

| 场景 | 前端与后端 | 数据库与 Redis |
| --- | --- | --- |
| 日常开发 | 可在 Mac 上运行 Vite 和 Node.js，保留热更新 | 通过 Compose 启动 |
| 部署验证 | 前端生产构建及后端编译产物全部容器化运行 | 通过同一套 Compose 管理 |

部署验证时，不将 `npm run dev` 或 Vite preview 作为正式网站服务；使用 Caddy 托管构建产物，后端运行生产构建后的程序。

Mac 适合开发、内网演示和早期试运行。关机、休眠、家庭宽带中断都会使服务不可访问；MacBook 合盖通常也会影响持续运行。如果需要向国内客户长期开放，优先进入云服务器部署阶段。

## 7. 为迁移到 Linux 提前准备

### 7.1 应用与配置

- 为前端和后端编写 Dockerfile，使用多阶段构建减少运行镜像体积。
- 使用 Docker Compose 描述服务、内部网络、数据卷、健康检查和重启策略。
- 固定并维护 Node.js、数据库等依赖版本，避免生产环境随意使用 `latest`。
- 使用环境变量或独立配置注入域名、数据库连接、Redis 连接及密钥，不写死 Mac 的绝对路径或 IP。
- 将开发配置与生产配置分开，避免将热更新、调试端口和开发挂载带到生产环境。
- Vite 注入到浏览器的环境变量属于公开信息，不放入数据库密码或服务端密钥。

### 7.2 CPU 架构

如果 Mac 使用 Apple Silicon，通常是 ARM64；目标云服务器可能是 AMD64/x86_64。需要为目标平台构建镜像，或发布多架构镜像，并确认原生依赖兼容。

### 7.3 数据持久化与备份

- PostgreSQL 使用持久化数据卷，定期备份并验证恢复流程。
- Redis 如用于队列等需要保留的数据，按需求配置持久化，不能只依赖容器重启。
- Caddy 的证书与运行数据使用持久化存储。
- 用户上传文件保存到独立持久化目录或对象存储，不依赖容器内部临时文件系统。
- 数据卷保证数据不随容器删除而消失，但不能代替备份。

### 7.4 发布与迁移

Compose 文件可以复用，但迁移并非只复制一个配置文件。还需要处理镜像、环境变量、数据库数据、上传文件、域名及证书配置。

数据库迁移使用 Prisma migration 管理结构变更；已有数据通过 PostgreSQL 备份与恢复工具迁移。正式切换时协调暂停写入或其他数据同步方式，避免新旧环境数据分叉。

## 8. 国内云服务器上线流程

1. 选择中国大陆地区的 Linux 云服务器，先以单台服务器配合 Docker Compose 起步。
2. 准备域名。使用中国大陆服务器通过域名提供网站服务，通常需要完成 ICP 备案；具体要求以云服务商和主管部门规定为准。
3. 安装 Docker Engine 和 Compose 插件，准备生产环境配置及持久化目录。
4. 构建或拉取适配目标 CPU 架构的镜像，启动数据库、Redis 和应用。
5. 执行数据库结构迁移；如已有数据，完成备份恢复和必要的切换安排。
6. 将域名解析到服务器，配置 Caddy，并开放网站需要的 80/443 端口。管理端口按需限制来源。
7. 验证前端路由刷新、API、登录、数据库读写、Redis、HTTPS 和服务重启后的恢复。
8. 配置日志轮转、备份及基础可用性监测，再正式交付客户使用。

前期可以手动发布，流程稳定后再加入 CI/CD。后续根据访问量、数据重要性和维护成本，逐步把 PostgreSQL、Redis 或上传文件迁移到托管数据库、托管缓存和对象存储。

## 9. 最终建议

**现在：** Mac 上使用 Docker Compose 验证 Vue 3、Node.js、PostgreSQL、Redis 和 Caddy 的完整部署流程。

**正式上线：** 将镜像、配置和数据迁移到国内 Linux 云服务器，使用业务域名与 Caddy 提供 HTTPS 访问，不依赖 Cloudflare Tunnel。

**初期控制复杂度：** 选择 PostgreSQL 作为唯一主数据库；Redis 按实际业务需要使用；先用单机 Compose，不急于引入 Kubernetes 或多机集群。
