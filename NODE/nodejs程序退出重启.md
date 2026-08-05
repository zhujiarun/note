# Node.js 进程退出方式总结

## 两种主要方式

### `process.exit([code])` — 直接终止

立即终止进程，不可阻止，不可拦截。

```js
process.exit(0); // 正常退出
process.exit(1); // 异常退出
```

**特点：**

- 尽快退出，不会等待未完成的异步操作（如网络请求、文件写入）
- 会触发 `exit` 事件，但回调中**只能做同步操作**，异步操作不会被执行
- 无法阻止退出，`exit` 事件回调中无法反悔

```js
// exit 事件 — 仅能做同步清理
process.on('exit', (code) => {
  console.log(`即将退出，状态码: ${code}`);
  // fs.writeFileSync 可以，但 fs.writeFile 不会被执行
});
```

### `process.kill(pid, signal)` — 发送信号

向进程发送信号，信号可以被**捕获并处理**。

```js
process.kill(process.pid, 'SIGTERM'); // 优雅终止
process.kill(process.pid, 'SIGINT');  // 模拟 Ctrl+C
process.kill(process.pid, 'SIGHUP');  // 终端断开（常用于重启）
```

**特点：**

- 信号处理函数中可以做**异步清理**（关闭服务器、断开数据库、写入日志等）
- 退出时机由你控制——清理完毕后再调用 `process.exit()`
- 这是生产环境（pm2、Docker、Kubernetes）的标准做法

```js
// 捕获 SIGTERM，做异步清理
process.on('SIGTERM', async () => {
  console.log('收到 SIGTERM，开始优雅关闭...');
  server.close();                        // 停止接收新请求
  await db.disconnect();                 // 断开数据库
  await fs.promises.writeFile(logFile);  // 写入日志
  process.exit(0);                       // 最后一步才退出
});
```

## 对比

| | `process.exit()` | `process.kill(pid, signal)` |
|---|---|---|
| 能否拦截 | 不能，退出不可阻止 | 能，可注册信号处理函数 |
| 异步清理 | 不支持，仅同步 | 支持，回调中可做异步操作 |
| 触发的事件 | `exit` 事件（仅同步） | 对应信号事件（支持异步） |
| 退出速度 | 立即 | 取决于处理逻辑的耗时 |
| 典型场景 | 脚本、批处理 | HTTP 服务、长期运行进程 |

## 常用信号

| 信号 | 含义 | 场景 |
|---|---|---|
| SIGTERM | 终止请求 | pm2 stop、Docker stop 的默认信号 |
| SIGINT | 中断（Ctrl+C） | 终端手动停止 |
| SIGHUP | 挂断 | 终端关闭时发送；pm2 reload 的默认信号 |
| SIGKILL | 强制杀死 | 不可捕获，做超时兜底（如先发 SIGTERM 等 10 秒再 SIGKILL） |

## 实际最佳实践

### 开发环境

使用 nodemon 监听文件变化自动重启：

```bash
nodemon app.js
```

### 生产环境

使用 pm2 管理进程，配合信号做优雅关闭：

```js
// 捕获 SIGINT（pm2 stop 发这个）
let shuttingDown = false;
process.on('SIGINT', async () => {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log('收到关闭信号，优雅退出中...');
  server.close();          // 停止接受新连接
  await cleanup();         // 异步清理
  process.exit(0);
});
```

```bash
# pm2 命令
pm2 start app.js           # 启动，崩溃自动重启
pm2 stop app.js            # 停止（发 SIGINT，等待优雅退出）
pm2 reload app.js          # 零停机重载（发 SIGHUP）
pm2 delete app.js          # 彻底删除进程
```

### Docker

Docker 发 SIGTERM 后默认等 10 秒，超时则发 SIGKILL。所以应用必须在 10 秒内完成清理并退出。

```dockerfile
# 用 exec form 确保信号能传递到 Node 进程
CMD ["node", "app.js"]
```

## 自然退出

当事件循环为空（没有定时器、没有未完成的 I/O 操作）时，Node.js 会自动退出，无需手动调用任何方法。这适用于批处理脚本和一次性任务。

## 自重启方案

```js
const { spawn } = require('child_process');

function restart() {
  const child = spawn(process.execPath, process.argv.slice(1), {
    stdio: 'inherit',
    env: process.env,
  });
  child.on('exit', (code) => {
    console.log(`新进程退出，状态码: ${code}`);
  });
  process.exit(0);
}
```

更推荐的方案是依赖外部进程管理器（pm2、Docker、systemd）来负责重启逻辑，应用本身只需做好优雅退出即可。
