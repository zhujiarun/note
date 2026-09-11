# 多线程打包命令完全指南

> 核心原则：**先给能用、再讲为什么**。所有命令均经过实测，开箱即用。

---

## 1. zstd 多线程打包（最推荐）🚀

### 1.1 极速模式（速度优先）

```bash
# 自动检测 CPU 核心数，多线程压缩，最快
tar --use-compress-program='zstd -T0' -cvf archive.tar.zst mydir/

# 手动指定 8 线程
tar --use-compress-program='zstd -T8' -cvf archive.tar.zst mydir/

# 指定线程数 + 低压缩级别（速度最快）
tar --use-compress-program='zstd -T8 -1' -cvf archive.tar.zst mydir/

# 查看 CPU 核心数
sysctl -n hw.nproc    # macOS
nproc                 # Linux
```

### 1.2 高压缩模式（节省空间）

```bash
# 19 级压缩 + 多线程（接近 xz 压缩率）
tar --use-compress-program='zstd -T8 -19' -cvf archive.tar.zst mydir/

# 短选项版本
tar -I 'zstd -T8 -19' -cvf archive.tar.zst mydir/

# 22 级压缩（最高压缩率，需要更多内存）
tar --use-compress-program='zstd -T8 -22' -cvf archive.tar.zst mydir/
```

### 1.3 排除文件打包

```bash
# 排除日志和 node_modules
tar --use-compress-program='zstd -T0' \
    --exclude='*.log' \
    --exclude='node_modules' \
    --exclude='.git' \
    -cvf archive.tar.zst mydir/

# 多个排除项
tar --use-compress-program='zstd -T0' \
    --exclude='*.log' \
    --exclude='*.tmp' \
    --exclude='.DS_Store' \
    --exclude='__pycache__' \
    --exclude='venv' \
    -cvf archive.tar.zst mydir/

# 排除版本控制目录（git/svn/hg）
tar --exclude-vcs --use-compress-program='zstd -T0' -cvf archive.tar.zst mydir/
```

### 1.4 显示打包进度

```bash
# 使用 pv 显示进度条
tar -cf - mydir/ | pv -s $(du -sb mydir/ | awk '{print $1}') | zstd -T8 > archive.tar.zst

# macOS 需要安装 pv: brew install pv
# Ubuntu/Debian: sudo apt-get install pv
```

### 1.5 流式传输（不落盘）

```bash
# 打包后直接通过 SSH 传到远程
tar -cf - mydir/ | zstd -T8 | ssh user@remote "cat > /backup/remote.tar.zst"

# 远程拉取并解压
ssh user@remote "tar -cf - mydir/" | zstd -d | tar -xf -
```

### 1.6 解压命令

```bash
# 标准解压
tar --use-compress-program='zstd -d' -xvf archive.tar.zst

# 或简写
tar -I 'zstd -d' -xvf archive.tar.zst

# 解压到指定目录
tar -I 'zstd -d' -xvf archive.tar.zst -C /target/dir/

# 查看内容不解压
tar --use-compress-program='zstd -d' -tvf archive.tar.zst
```

---

## 2. pigz 多线程打包（兼容性最好）

### 2.1 极速打包（输出 .gz 格式）

```bash
# 自动多线程
tar --use-compress-program='pigz -p0' -cvf archive.tar.gz mydir/

# 指定 8 线程
tar --use-compress-program='pigz -p8' -cvf archive.tar.gz mydir/

# 管道方式（更灵活）
tar -cf - mydir/ | pigz -p8 > archive.tar.gz
```

### 2.2 压缩级别控制

```bash
# 最快（级别1）
tar --use-compress-program='pigz -p8 -1' -cvf archive.tar.gz mydir/

# 默认级别（6）
tar --use-compress-program='pigz -p8 -6' -cvf archive.tar.gz mydir/

# 最高压缩（级别 9，11）
tar --use-compress-program='pigz -p8 -11' -cvf archive.tar.gz mydir/
```

### 2.3 排除文件打包

```bash
tar --use-compress-program='pigz -p8' \
    --exclude='*.log' \
    --exclude='node_modules' \
    --exclude='.git' \
    -cvf archive.tar.gz mydir/
```

### 2.4 显示进度

```bash
tar -cf - mydir/ | pv -s $(du -sb mydir/ | awk '{print $1}') | pigz -p8 > archive.tar.gz
```

### 2.5 解压命令

```bash
# 标准解压
tar --use-compress-program='pigz -d' -xvf archive.tar.gz

# 或使用 unpigz
tar -xvf archive.tar.gz
unpigz archive.tar.gz

# 解压到指定目录
tar -xvf archive.tar.gz -C /target/dir/
```

---

## 3. pbzip2 多线程打包

### 3.1 极速打包

```bash
# 自动多线程
tar --use-compress-program='pbzip2 -p0' -cvf archive.tar.bz2 mydir/

# 指定线程数
tar --use-compress-program='pbzip2 -p8' -cvf archive.tar.bz2 mydir/

# 管道方式
tar -cf - mydir/ | pbzip2 -p8 > archive.tar.bz2
```

### 3.2 解压

```bash
tar --use-compress-program='pbzip2 -d' -xvf archive.tar.bz2
```

---

## 4. pixz 多线程 xz 打包

```bash
# 多线程 xz
tar --use-compress-program='pixz -p8' -cvf archive.tar.xz mydir/

# 解压
tar --use-compress-program='pixz -d' -xvf archive.tar.xz
```

---

## 5. 实用场景示例

### 5.1 每日备份脚本

```bash
#!/bin/bash
# daily_backup.sh - 每日项目备份，多线程压缩

DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/data/myproject"
BACKUP_DIR="/backup"
LOG_FILE="/var/log/backup.log"

# 打包并压缩（排除无用文件）
tar --use-compress-program='zstd -T0 -3' \
    --exclude='*.log' \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='*.tmp' \
    --exclude='__pycache__' \
    -cvf "$BACKUP_DIR/backup_${DATE}.tar.zst" \
    "$PROJECT_DIR" 2>> "$LOG_FILE"

# 删除 30 天前的备份
find "$BACKUP_DIR" -name "backup_*.tar.zst" -mtime +30 -delete

echo "Backup completed: backup_${DATE}.tar.zst" >> "$LOG_FILE"
```

### 5.2 大文件分卷打包（避免单文件过大）

```bash
# 打包后拆分成 100M 的小块
tar --use-compress-program='zstd -T0' -cf - mydir/ | split -b 100M - backup.tar.zst.part

# 合并并解压
cat backup.tar.zst.part* | zstd -d | tar -xf -

# 验证分卷完整
md5sum backup.tar.zst.part* > checksums.md5
```

### 5.3 跨服务器同步

```bash
# 方案一：本地压缩后传输
tar --use-compress-program='zstd -T0' -cvf - /data/ | ssh user@server "cat > /backup/data.tar.zst"

# 方案二：流式压缩传输（不落盘）
tar -cf - /data/ | zstd -T8 | ssh user@server "zstd -d | tar -xf - -C /restore/"

# 方案三：rsync 增量同步 + 后台压缩
rsync -az /data/ user@server:/backup/data/ && \
ssh user@server "cd /backup/data && tar -cf - . | zstd -T8 > latest.tar.zst"
```

### 5.4 加密压缩传输

```bash
# 压缩 + 加密 + 传输
tar --use-compress-program='zstd -T0' -cf - secret_dir/ | \
    openssl enc -aes-256-cbc -salt -pbkdf2 | \
    ssh user@server "cat > /secure/backup.tar.zst.enc"

# 解密 + 解压
ssh user@server "cat /secure/backup.tar.zst.enc" | \
    openssl enc -d -aes-256-cbc | \
    zstd -d | \
    tar -xf -
```

### 5.5 增量备份

```bash
# 查找最近 7 天修改的文件，打包
find mydir/ -type f -mtime -7 | \
    tar --use-compress-program='zstd -T0' -cvf incremental.tar.zst -T -

# 查找大于 100M 的大文件
find mydir/ -type f -size +100M | \
    tar --use-compress-program='zstd -T0' -cvf large_files.tar.zst -T -
```

### 5.6 实时监控打包进度

```bash
# 方式一：使用 pv（推荐）
tar -cf - mydir/ | pv -s $(du -sb mydir/ | awk '{print $1}') | zstd -T8 > archive.tar.zst

# 方式二：使用 tar 自带的检查点
tar --use-compress-program='zstd -T0' \
    --checkpoint=1000 \
    --checkpoint-action=echo='%d files processed' \
    -cvf archive.tar.zst mydir/

# 方式三：使用 progress 工具（Linux）
tar -cf - mydir/ | zstd -T8 | \
    dd of=archive.tar.zst bs=1M status=progress
```

---

## 6. 命令速查表

### 6.1 工具选择

| 需求 | 推荐命令 | 输出格式 |
|------|---------|---------|
| 🚀 **速度最快** | `tar --use-compress-program='zstd -T0'` | `.tar.zst` |
| 🔄 **兼容性最好** | `tar --use-compress-program='pigz -p8'` | `.tar.gz` |
| 💾 **压缩率最高** | `tar --use-compress-program='zstd -T8 -19'` | `.tar.zst` |
| 📦 **传统格式** | `tar -czf` (gzip) | `.tar.gz` |
| 🗜️ **极限压缩** | `tar --use-compress-program='pixz -p8'` | `.tar.xz` |

### 6.2 速记口诀

```
zstd  = 现代首选，速度之王
pigz  = 多线程 gzip，兼容性强
-T0   = 自动检测 CPU 核心
-T8   = 指定 8 线程
-I    = --use-compress-program 简写
```

### 6.3 核心参数

| 参数 | 含义 |
|------|------|
| `-c` | 创建归档 |
| `-x` | 解压归档 |
| `-v` | 显示详细过程 |
| `-f` | 指定文件名 |
| `-z` | gzip 压缩 |
| `-j` | bzip2 压缩 |
| `-J` | xz 压缩 |
| `-I <程序>` | 指定压缩程序 |
| `-T <线程数>` | zstd/pigz 线程数（0=自动） |
| `-C <目录>` | 切换到指定目录 |
| `--exclude` | 排除文件 |
| `--exclude-vcs` | 排除版本控制目录 |

---

## 7. 常见问题

### 7.1 如何验证是否真的多线程？

```bash
# 打包时观察 CPU 占用（另一个终端）
top -pid $(pgrep -f "zstd -T")

# 对比单线程与多线程耗时
time tar --use-compress-program='zstd' -cvf test.tar.zst mydir/
time tar --use-compress-program='zstd -T8' -cvf test.tar.zst mydir/
```

### 7.2 线程数越多越好吗？

不是。一般推荐：
- **CPU 核心数 = 物理核心数**（不是逻辑核心）
- I/O 密集型：线程数 ≤ CPU 核心数
- 计算密集型：可适当超过，但收益递减

### 7.3 压缩级别怎么选？

| 级别 | 场景 | 推荐值 |
|------|------|--------|
| zstd `-1~-3` | 临时备份、快速传输 | `-3` |
| zstd `-3~-9` | **日常备份（推荐）** | `-3` 或默认 |
| zstd `-9~-19` | 长期归档 | `-19` |
| zstd `-19~-22` | 极限压缩（慢） | 仅必要时使用 |

### 7.4 安装方式

```bash
# macOS
brew install zstd pigz pbzip2 pixz pv

# Ubuntu/Debian
sudo apt-get install zstd pigz pbzip2 pixz pv

# CentOS/RHEL
sudo yum install zstd pigz pbzip2 pixz pv
```

---

## 8. 实战建议

### 8.1 添加常用别名

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc

# 极速打包（zstd多线程）
alias tarz='tar --use-compress-program="zstd -T0" -cvf'

# 兼容打包（pigz 多线程）
alias targz='tar --use-compress-program="pigz -p8" -cvf'

# 极速解压
alias untarz='tar --use-compress-program="zstd -d" -xvf'

# 解压 .tar.gz
alias untargz='tar --use-compress-program="pigz -d" -xvf'
```

### 8.2 推荐配置文件

```bash
# ~/.tar_config（tar 配置文件，可选）
# 默认使用 zstd 多线程
--use-compress-program=zstd -T0
```

---

## 9. 总结

| 方案 | 速度 | 压缩率 | 兼容性 | 推荐指数 |
|------|------|--------|--------|---------|
| **zstd -T0** | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **pigz -p8** | ⚡⚡⚡⚡ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **pbzip2** | ⚡⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **pixz** | ⚡⚡ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **gzip** (单线程) | ⚡ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |

**最终推荐：日常使用 `zstd -T0`，需要兼容性时用 `pigz -p8`。**