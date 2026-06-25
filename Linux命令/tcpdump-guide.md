# tcpdump 抓包速查手册

## 基本语法

```
tcpdump [选项] [过滤表达式]
```

## 常用选项

| 选项 | 说明 |
|------|------|
| `-i eth0` | 指定监听的网卡（`-i any` 表示所有网卡） |
| `-n` | 不将 IP 地址解析为主机名 |
| `-nn` | 不解析 IP 地址和端口名 |
| `-v` / `-vv` / `-vvv` | 显示更详细的输出，v 越多越详细 |
| `-c 100` | 抓够 100 个包后自动停止 |
| `-w file.pcap` | 将抓到的包写入文件（可用 Wireshark 分析） |
| `-r file.pcap` | 从文件读取包进行分析 |
| `-A` | 以 ASCII 格式打印包内容 |
| `-X` | 同时显示十六进制和 ASCII 格式的包内容 |
| `-s 0` | 抓取完整包（默认可能截断），0 表示不截断 |
| `-t` | 不打印时间戳 |
| `-tt` | 打印 UNIX 时间戳 |
| `-ttt` | 打印包与包之间的时间间隔 |
| `-q` | 安静模式，减少输出内容 |
| `-e` | 显示链路层头部（MAC 地址） |
| `-S` | 显示绝对 TCP 序列号而非相对值 |

## 按 IP 过滤

### 抓特定 IP 的所有流量
```
tcpdump host 192.168.1.100
```

### 只抓从该 IP 发出的
```
tcpdump src host 192.168.1.100
```

### 只抓发往该 IP 的
```
tcpdump dst host 192.168.1.100
```

### 抓某个网段（CIDR）
```
tcpdump net 192.168.1.0/24
tcpdump src net 10.0.0.0/8
tcpdump dst net 172.16.0.0/12
```

### 排除某个 IP
```
tcpdump not host 192.168.1.100
tcpdump host 192.168.1.0/24 and not host 192.168.1.1
```

### 多 IP 条件
```
tcpdump host 192.168.1.100 or host 192.168.1.200
tcpdump src host 192.168.1.100 and dst host 8.8.8.8
```

## 按端口过滤

### 指定端口
```
tcpdump port 80
tcpdump port 443
```

### 源端口或目的端口
```
tcpdump src port 8080
tcpdump dst port 80
```

### 端口范围
```
tcpdump portrange 8000-8100
```

### 多端口
```
tcpdump port 80 or port 443
```

## 按协议过滤

```
tcpdump tcp                          # 只抓 TCP 包
tcpdump udp                          # 只抓 UDP 包
tcpdump icmp                         # 只抓 ICMP 包（ping 等）
tcpdump arp                          # 只抓 ARP 包
tcpdump ip6                          # 只抓 IPv6 包
tcpdump ether proto 0x0806           # 按以太网协议号过滤
```

## 按 TCP 标志位过滤

```
tcpdump 'tcp[tcpflags] & tcp-syn != 0'                     # SYN 包
tcpdump 'tcp[tcpflags] & tcp-ack != 0'                     # ACK 包
tcpdump 'tcp[tcpflags] & (tcp-syn|tcp-fin) != 0'          # SYN 或 FIN 包
tcpdump 'tcp[tcpflags] & tcp-rst != 0'                     # RST 包
tcpdump 'tcp[tcpflags] == tcp-syn'                          # 仅 SYN（不含 ACK）
```

## 按包大小过滤

```
tcpdump greater 1000                 # 大于 1000 字节
tcpdump less 64                      # 小于 64 字节
tcpdump 'len > 1500'                 # 大于 1500 字节（含链路层头）
```

## 常用组合示例

### 抓某 IP 的 HTTP 流量并写入文件
```
tcpdump -i eth0 host 192.168.1.100 and port 80 -w http.pcap
```

### 抓两个主机之间的所有通信
```
tcpdump host 192.168.1.100 and host 192.168.1.1
```

### 抓某 IP 的 DNS 查询（只抓 UDP 53 端口）
```
tcpdump -n host 192.168.1.100 and udp port 53
```

### 实时查看某 IP 的 HTTP 请求内容
```
tcpdump -A host 192.168.1.100 and port 80
```

### 抓 TCP 三次握手（SYN 包）
```
tcpdump 'tcp[tcpflags] & tcp-syn != 0'
```

### 抓特定网卡上所有非 SSH 的流量
```
tcpdump -i eth0 not port 22
```

### 抓 VLAN 编号为 100 的流量
```
tcpdump vlan 100
```

### 限制抓包数量并及时查看
```
tcpdump -c 50 -i eth0 host 192.168.1.100 -nn -X
```

## 逻辑运算符

过滤器支持三种逻辑运算符：

| 运算符 | 写法一 | 写法二 | 写法三 |
|--------|--------|--------|--------|
| 与 | `and` | `&&` | 简单并列 |
| 或 | `or` | `||` | — |
| 非 | `not` | `!` | — |

```
tcpdump host 10.0.0.1 and (port 80 or port 443)
tcpdump not host 192.168.1.1
tcpdump src host 10.0.0.1 and not dst port 22
```

## 输出格式解读

一行典型输出：

```
12:30:45.123456 IP 192.168.1.100.54321 > 192.168.1.1.80: Flags [S], seq 123456789, win 65535, length 0
```

- `12:30:45.123456` — 时间戳
- `IP` — 协议
- `192.168.1.100.54321` — 源 IP + 源端口
- `>` — 方向
- `192.168.1.1.80` — 目的 IP + 目的端口
- `Flags [S]` — TCP 标志（S=SYN, P=PUSH, F=FIN, R=RST, A=ACK, .=无标志）
- `seq` — 序列号
- `win` — 窗口大小
- `length` — 数据载荷长度

## 权限要求

大多数系统上运行 `tcpdump` 需要 root 权限：

```
sudo tcpdump -i eth0 host 192.168.1.100
```

或者在命令前加 `sudo`，或者用 root 用户执行。
