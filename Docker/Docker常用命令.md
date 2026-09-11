# Docker 常用命令：镜像加载、查看、删除与容器创建

> 目标：覆盖"加载本地镜像 → 查看镜像 → 创建容器 → 删除镜像"的完整链路，以及容器日常管理。

---

## 零、核心概念：镜像 vs 容器

动手之前先建立一个心智模型，否则命令会越记越乱：

| | 镜像（Image） | 容器（Container） |
|---|---|---|
| 是什么 | 只读的**模板**，包含文件系统 + 配置 | 镜像的**运行实例**，可读写、有进程 |
| 类比 | 一个安装包 / 类 / ISO | 安装好的程序在运行 / 对象 |
| 创建 | 构建（build）、加载（load）、拉取（pull） | 用镜像 `run` / `create` |
| 生命周期 | 一直存在，直到被删除 | 创建 → 启动 → 停止 → 删除 |
| 能否改名 | 通过 tag | 通过 --name |

**一句话**：镜像就像"可执行文件"，容器就是"运行中的进程"。同一个镜像可以创建出无数个互不影响的容器。

---

## 一、加载本地镜像文件

别人给你一个 `.tar` 镜像文件，或者你在离线环境同步镜像，都靠下面两个命令。

### `docker load` —— 加载 `docker save` 出来的镜像归档（推荐）

```bash
# 加载单个 tar 文件
docker load -i myimage.tar
# 或等价写法
docker load < myimage.tar
```

- 专门对应 `docker save` 导出的归档（**保留了镜像的 tag、层级等完整元数据**）。
- 加载后 `docker images` 立刻能看到它，直接可用。

### `docker import` —— 导入文件系统快照

```bash
docker import myfs.tar myname:latest
```

- 导入的是**裸的文件系统快照**（通常来自 `docker export` 或手动打包）。
- **不带 tag、镜像层级等元数据**，所以导入时**必须手动指定名字和标签**（`myname:latest`）。
- 导入结果不是一个标准镜像，更适合恢复一个文件系统，通常用于特殊情况。

### 两者对比

| | `docker load` | `docker import` |
|---|---|---|
| 对应导出命令 | `docker save` | `docker export` |
| 是否保留元数据 | ✅ 保留 tag / 层级 | ❌ 不保留，需手动指定名字 |
| 产物 | 标准镜像，可直接 run | 文件系统快照，一般需后续处理 |
| 常用场景 | 镜像离线传输、备份恢复 | 容器文件系统打包迁移 |

> 经验：**传镜像就用 `save` + `load`** 这一对，别的不用记。

---

## 二、列出已加载镜像

```bash
docker images
# 等价写法
docker image ls
```

输出示例：

```
REPOSITORY    TAG       IMAGE ID       CREATED        SIZE
ubuntu        22.04     1a2b3c4d5e6f   2 weeks ago    77.8MB
nginx         latest    f7c8d9e0a1b2   4 days ago     187MB
```

各列含义：

| 列 | 含义 |
|----|------|
| `REPOSITORY` | 镜像名（本地镜像就是当初 load/pull 时给的名字） |
| `TAG` | 标签，默认 `latest`，用来区分同名镜像的版本 |
| `IMAGE ID` | 镜像唯一 ID（前 12 位） |
| `CREATED` | 创建时间 |
| `SIZE` | 大小（只显示顶层大小，不含共享底层，所以看着比实际小） |

常用变体：

```bash
docker images -a                 # 列出所有（含中间层镜像）
docker images -q                 # 只输出 IMAGE ID（脚本里好用）
docker images --filter "before=ubuntu:22.04"   # 按条件过滤
docker images --format "{{.Repository}}:{{.Tag}}"  # 自定义输出格式
```

---

## 三、根据镜像创建容器

### 最常用：`docker run`（创建并启动）

```bash
docker run [参数] 镜像名[:tag] [要执行的命令]
```

**镜像名来自 `docker images` 里的 `REPOSITORY:TAG`**，例如：

```bash
docker run ubuntu:22.04 echo "hello"
# 创建并启动一个 ubuntu 容器，执行 echo 后退出
```

常用参数（记这几个就够起步）：

| 参数 | 作用 | 示例 |
|------|------|------|
| `-it` | 交互式终端（前台运行 + 可输入） | `docker run -it ubuntu:22.04 bash` |
| `-d` | 后台运行（守护模式） | `docker run -d nginx` |
| `--name` | 给容器起名字（否则是随机名） | `docker run --name myweb nginx` |
| `-p` | 端口映射：`宿主机端口:容器端口` | `docker run -p 8080:80 nginx` |
| `-v` | 挂载数据卷：`宿主机目录:容器目录` | `docker run -v /data:/data ubuntu` |
| `--rm` | 容器退出后自动删除（适合临时容器） | `docker run --rm ubuntu echo hi` |

**前台 vs 后台**：

```bash
docker run -it ubuntu:22.04 bash   # 前台：终端直接进入容器 shell，退出即容器结束
docker run -d --name myweb nginx   # 后台：容器在后台跑，立刻返回容器 ID
```

> `-it` 通常一起出现（`-i` 保持 stdin 打开，`-t` 分配伪终端），进入容器交互 shell 必备。

### 分步版：`docker create` + `docker start`

如果你想把"创建"和"启动"分开（比如先建好、调好参数，稍后再启动）：

```bash
docker create --name myweb -p 8080:80 nginx   # 只创建，不启动
docker start myweb                            # 启动已创建的容器
```

`docker run` 本质 = `docker create` + `docker start`。

### 查看容器

```bash
docker ps          # 只看运行中的容器
docker ps -a       # 看所有容器（含已停止的）
docker ps -q       # 只输出容器 ID
```

---

## 四、删除镜像

```bash
docker rmi 镜像名:tag      # 或直接写 IMAGE ID
docker rmi ubuntu:22.04
```

### 常见报错与解决

```bash
# 报错：image is being used by running container
# 原因：还有容器（哪怕已停止）基于这个镜像
# 解决：先删掉这些容器
docker rm 容器名或ID
docker rm $(docker ps -aq)          # 删掉所有容器
docker rmi ubuntu:22.04             # 再删镜像
```

```bash
# 报错：image is being referenced in multiple repositories
# 原因：同一个 IMAGE ID 被打了多个 tag
# 解决：先删掉多余的 tag，再删
docker rmi ubuntu:22.04 ubuntu:latest
```

### 强制删除（慎用）

```bash
docker rmi -f 镜像ID     # 强删，即使有容器引用。一般不建议，会留下悬挂引用
```

---

## 五、容器日常管理（"等命令"）

镜像操作和容器操作最容易混，这里按"对象"分开列：

### 容器生命周期

```bash
docker ps                  # 列出运行中容器
docker ps -a               # 列出所有容器
docker start 容器          # 启动已停止的容器
docker stop 容器           # 停止容器（优雅，给进程留时间退出）
docker kill 容器           # 强杀容器（立即终止）
docker rm 容器             # 删除已停止的容器
docker rm -f 容器          # 强制删除运行中的容器
docker exec -it 容器 bash  # 进入运行中容器的 shell
docker logs 容器           # 查看容器日志
docker top 容器            # 查看容器内的进程
```

```bash
# 实战组合：进后台运行的容器
docker run -d --name myweb nginx
docker exec -it myweb bash
```

### 镜像导出（和 load 配对）

```bash
docker save -o myimage.tar nginx:latest     # 导出镜像为 tar
docker load -i myimage.tar                  # 另一边加载
```

```bash
# 真实示例：导出视频监控镜像 v1.1.0 为本地 tar 文件
docker save -o cc_lm_device_video_surveillance.tar cc_lm_device_video_surveillance:v1.1.0
```

- `-o`（`--output`）：指定输出的 tar 文件路径，这里是 `cc_lm_device_video_surveillance.tar`。
- 后面跟 `镜像名:标签`，这里是 `cc_lm_device_video_surveillance:v1.1.0`。
- 导出的 tar 可以拷贝到别的机器，用 `docker load -i cc_lm_device_video_surveillance.tar` 导入。

```bash
docker export -o myfs.tar 容器名             # 导出容器文件系统
docker import myfs.tar newname:tag          # 另一边导入
```

---

## 六、一个完整的实战流程

把上面串起来，跑一个真实例子：

```bash
# ① 有一个同事给的镜像文件 nginx.tar
docker load -i nginx.tar

# ② 确认镜像加载成功
docker images | grep nginx

# ③ 基于镜像创建并后台运行容器，映射端口、起名
docker run -d --name web -p 8080:80 nginx

# ④ 查看容器是否在运行
docker ps

# ⑤ 进入容器看看
docker exec -it web bash
exit   # 退出容器

# ⑥ 停掉并删掉容器
docker stop web
docker rm web

# ⑦ 容器删干净了，再删镜像
docker rmi nginx
```

---

## 七、实战：视频监控镜像的部署命令逐条解析

场景：镜像 `cc_lm_device_video_surveillance:v1.0`（视频监控应用）。下面这套命令来自真实部署流程，逐条解析。

### 1. `docker build -t cc_lm_device_video_surveillance:v1.0 .`

```bash
docker build -t cc_lm_device_video_surveillance:v1.0 .
构建命令加上 `--platform`：指定目标平台，否则按构建平台为准
docker build --platform linux/arm64 -t cc_lm_device_video_surveillance:v1.0 .
```

- **作用**：从当前目录（`.`）的 `Dockerfile` 构建出镜像，命名为 `cc_lm_device_video_surveillance`，标签 `v1.0`。
- `-t`（`--tag`）：给构建结果起"名字:标签"。
- **这是整个流程的源头**——后面所有命令用的都是这个镜像。

### 2. `docker run -itd --rm --name zjr_kylin cc_lm_device_video_surveillance:v1.0 bash`

```bash
docker run -itd --rm --name zjr_kylin cc_lm_device_video_surveillance:v1.0 bash
```

- **作用**：用该镜像创建并启动容器。
- 逐参数拆解：

| 参数 | 含义 |
|------|------|
| `-i` | 保持标准输入打开（可交互） |
| `-t` | 分配一个伪终端 |
| `-d` | 后台运行 |
| `--rm` | 容器退出时**自动删除** |
| `--name zjr_kylin` | 给容器起名（不写就是随机名） |
| `cc_lm_device_video_surveillance:v1.0` | 使用的镜像名:标签 |
| `bash` | 容器启动时执行的命令 |

- **注意 `-itd` 三个连在一起**：`-d` 让容器在后台跑，`-i -t` 保留交互能力。配合入口命令 `bash`，容器不会执行完就退出，而是**保持存活**，方便后面 `docker exec` 进去操作。
- **注意 `--rm` 的副作用**：一旦容器停止，它会被自动删除——见后面第 6 条的坑。

### 3. `docker exec -it zjr_kylin bash`

```bash
docker exec -it zjr_kylin bash
```

- **作用**：进入**正在运行**的容器 `zjr_kylin`，打开一个交互式 bash。
- 相当于"钻进运行中的容器里"执行命令。
- **前提**：容器必须是**运行中**状态（所以前面用 `-d` 让它保持运行）。

### 4. `docker ps -a`

```bash
docker ps -a
```

- **作用**：列出所有容器（含已停止的）。
- 用来确认 `zjr_kylin` 的状态——`STATUS` 列显示 `Up`（运行中）还是 `Exited`（已退出）。

### 5. `docker logs zjr_kylin`

```bash
docker logs zjr_kylin
```

- **作用**：查看容器 `zjr_kylin` 的标准输出/错误日志。
- 排查容器启动失败、程序崩溃最常用。
- 常用变体：
  ```bash
  docker logs -f zjr_kylin          # 跟随输出（实时滚动）
  docker logs --tail 100 zjr_kylin  # 只看最后 100 行
  ```

### 6. `docker stop zjr_kylin`

```bash
docker stop zjr_kylin
```

- **作用**：停止容器（优雅，给进程留时间退出）。
- ⚠️ **坑**：因为创建时带了 `--rm`，`stop` 之后容器会被**自动删除**——此时 `docker ps -a` 里就看不到它了。

### 7. `docker rm zjr_kylin`

```bash
docker rm zjr_kylin
```

- **作用**：删除容器。
- ⚠️ **注意**：如果上一步 `stop` 已触发 `--rm` 自动删除，这一步会报 `No such container: zjr_kylin`——**无害**，说明容器已经没了。
- 如果容器没被自动删（比如没用 `--rm`），这一步就是手动兜底清理。

### 8. `docker rmi cc_lm_device_video_surveillance:v1.0`

```bash
docker rmi cc_lm_device_video_surveillance:v1.0
```

- **作用**：删除镜像。
- ⚠️ **前提**：必须没有容器（包括已停止的）还在引用它，否则报 `image is being used by running container`。
- 标准清理顺序：**先 `stop` + `rm` 容器，再 `rmi` 镜像**。

### 命令之间的依赖关系

```
docker build ──▶ 产出镜像
    │
    ▼
docker run ────▶ 用镜像创建容器（-itd 后台保持运行）
    │              │
    │              ▼
    │      docker ps -a 确认状态
    │              │
    │              ▼
    │      docker exec / logs ← 进入容器 / 查日志
    │
    ▼
docker stop ──▶ (--rm 自动删) ──▶ docker rm（兜底清理）
    │
    ▼
docker rmi ────▶ 清理镜像（必须放最后）
```

### 这套流程的两个"容易懵"的点

1. **`-itd` + `--rm` + `bash` 的组合**：目的是"后台保持运行的容器，退出后不残留"。`exec` 是主入口，`logs` 看状态。
2. **`stop` 会触发 `--rm` 自动删除**：所以这串命令里 `rm` 更像"兜底保险"——容器还在就删掉；已经没了就报个无害的错。

---

## 八、速查表

| 想干什么      | 命令                                       |
| --------- | ---------------------------------------- |
| 构建镜像      | `docker build -t 名字:标签 .`                |
| 加载镜像文件    | `docker load -i xxx.tar`                 |
| 列出镜像      | `docker images`                          |
| 创建并启动容器   | `docker run -it/-d 镜像`                   |
| 只创建不启动    | `docker create 镜像`                       |
| 列出容器      | `docker ps` / `docker ps -a`             |
| 进入容器      | `docker exec -it 容器 bash`                |
| 停止 / 启动容器 | `docker stop 容器` / `docker start 容器`     |
| 删除容器      | `docker rm 容器`                           |
| 删除镜像      | `docker rmi 镜像`                          |
| 导出镜像      | `docker save -o out.tar 镜像`              |
| 导出容器文件系统  | `docker export -o out.tar 容器`            |
| 查看日志      | `docker logs 容器`                         |
| 指定构建平台    | `docker build --platform linux/arm64 -t` |

---

## 总结

- **镜像 = 只读模板，容器 = 运行实例**。分清对象，命令就不会搞混。
- **`save`/`load` 是一对**（带元数据，标准镜像），`export`/`import` 是另一对（裸文件系统）。
- **删镜像之前先删容器**，这是新手最常见的报错来源。
- **`run` = `create` + `start`**，日常直接 `run` 加 `-it`（交互）或 `-d`（后台）。
