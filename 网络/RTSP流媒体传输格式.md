# RTSP 流媒体传输格式：网络上的视频数据长什么样

> 关联阅读：[[理解FFmpeg编解码流程]] —— 那是发送/接收端的代码视角
>
> 本文关注"网络上的视角"：编码后的数据如何在 RTSP/RTP 协议中传输

---

## 核心结论

网络上看到的 RTSP 视频流，**就是一个连续的 RTP 包序列**，每个 RTP 包头部告诉你"这是视频 PT=96、时间戳 X、序号 Y"，包体里是按 FU-A 分片的 H.264 NALU。RTSP 只在开始/结束时露个脸做"建立/拆除"。

---

## 一、整体流程（发送端）

```
┌────────────┐  ┌─────────────┐  ┌────────────┐  ┌──────────┐
│ 摄像头/YUV  │─▶│ 编码器       │─▶│ RTP 打包    │─▶│ UDP/TCP  │── 网络
│ 原始帧      │  │ H.264/H.265 │  │ 分片+打时间  │  │ socket   │
└────────────┘  └─────────────┘  └────────────┘  └──────────┘
                                ▲
                          关键步骤：每一帧被切成若干 NALU，
                          每个 NALU 装进一个或多个 RTP 包
```

数据在网络上的"长相"和 `AVFrame` 完全不同——是**分层的**：

```
┌────────────────────────────────────┐
│  视频帧的原始数据（YUV420P 等）        │  ← 在发送方内部
├────────────────────────────────────┤
│  编码后（压缩后）的码流                │  ← H.264 / H.265 / AAC
├────────────────────────────────────┤
│  RTP 封包（按网络传输分片）            │  ← 一帧可能被切成多个 RTP 包
├────────────────────────────────────┤
│  UDP / TCP 传输                     │  ← RTSP 默认走 UDP
├────────────────────────────────────┤
│  IP / 以太网                        │
└────────────────────────────────────┘
```

---

## 二、最底层：编码后的码流（H.264 为例）

摄像头或编码器出来的**裸码流**是 H.264 / H.265 格式，由一个个 **NALU（Network Abstraction Layer Unit）** 串起来。

### 2.1 H.264 NALU 结构

```
┌──────────────┬──────────────────────────────┐
│ Start Code   │  NALU Header  +  NALU Payload│
│  0x00 00 01  │  1 byte    │   可变长度       │
│  或 0x00 00 00 01        │                  │
└──────────────┴──────────────────────────────┘
          ↑
	用于"找到NALU边界"
	在文件/字节流里定位
```

**NALU Header**（1 字节）：

```
┌─┬─────┬─────┬────────┐
│F│NRI  │TYPE │        │
└─┴─────┴─────┴────────┘
 0 1 2 3 4 5 6 7
```

| 字段           | 含义                |
| ------------ | ----------------- |
| F (1 bit)    | 错误标志，0=正常         |
| NRI (2 bit)  | 重要性（0=不参考，3=关键参考） |
| TYPE (5 bit) | NALU 类型（见下表）      |

### 2.2 常见 NALU TYPE

| TYPE | 名称      | 含义                  |
| ---- | ------- | ------------------- |
| 1    | Non-IDR | 普通 P/B 帧            |
| 5    | IDR     | 关键帧（I 帧）            |
| 6    | SEI     | 补充增强信息（时间戳、字幕等）     |
| 7    | SPS     | 序列参数集（宽高、profile 等） |
| 8    | PPS     | 图像参数集（熵编码模式等）       |
| 9    | AUD     | 访问单元分隔符             |

### 2.3 一段 H.264 码流的真实样子

```
00 00 00 01  67 42 C0 1E ...   ← SPS（NALU_TYPE=7）
00 00 00 01  68 CE 38 80 ...   ← PPS（NALU_TYPE=8）
00 00 00 01  65 88 80 40 ...   ← IDR 关键帧（NALU_TYPE=5）
00 00 00 01  41 9A 24 6C ...   ← P 帧（NALU_TYPE=1）
00 00 00 01  41 9A 24 6D ...   ← P 帧
...
```

每段以 `00 00 00 01`（4 字节起始码）开头，后面跟一字节的 NALU header。

> **H.265/HEVC** 几乎一样，只是 NALU header 是 2 字节，TYPE 含义略不同。

---

## 三、传输层：RTP 打包（最关键的一步）

RTSP 默认基于 **RTP**（Real-time Transport Protocol）传输媒体流。**一个大问题：网络 MTU 通常只有 ~1500 字节，而一帧 IDR 关键帧可能几十 KB。** 所以要把一帧切成多个 RTP 包。

### 3.1 三种打包方式（RFC 6184）

#### Single NALU Packet（NALU ≤ MTU）

最简单的情况：一个 NALU 装进一个 RTP 包。

```
RTP Header (12 字节)  +  NALU Header (1 字节)  +  NALU Payload
```

#### FU-A 分片（NALU > MTU，最常见）

一帧被切成多个 RTP 包。**FU-A = Fragmentation Unit Type A**。

```
┌──────────────────────┬─────────┬─────────────┬──────────┐
│   RTP Header (12B)   │ FU ind. │  FU Header  │  FU 载荷  │
│                      │  (1B)   │    (1B)     │  (≤MTU)  │
└──────────────────────┴─────────┴─────────────┴──────────┘
```

- **FU indicator**（1 字节）：`TYPE = 28`（FU-A）
- **FU header**（1 字节）：

```
┌─┬─┬─────┬─────┬─────┐
│S│E│R│R│  TYPE   │
└─┴─┴─────┴─────┴─────┘
 0 1 2 3 4 5 6 7
```

| 字段 | 含义 |
|------|------|
| S (Start) | 1 = 这是 NALU 的第一片 |
| E (End) | 1 = 这是 NALU 的最后一片 |
| R | 保留 |
| TYPE | 原始 NALU 的类型（1=非IDR, 5=IDR, 7=SPS, 8=PPS...） |

**一个 IDR 帧的传输示例**（假设被切成 3 个 RTP 包）：

```
RTP#1: [Header|S=1|E=0|TYPE=5] [IDR 数据第 1 段]
RTP#2: [Header|S=0|E=0|TYPE=5] [IDR 数据第 2 段]
RTP#3: [Header|S=0|E=1|TYPE=5] [IDR 数据第 3 段]
```

接收端通过 `S/E/TYPE` 重新拼出原始 NALU，交给解码器。

#### STAP-A 聚合（多 NALU 共享一个 RTP 包）

常用于**SPS + PPS + IDR 一起发**，避免分别组包。

```
RTP Header (12B) + STAP-A Header (1B, TYPE=24) + [NALU size(2B) + NALU] + [NALU size + NALU] + ...
```

### 3.2 总结：NALU 怎么变成 RTP 包

```
原始视频帧
  │
  ▼
编码器输出 NALU 序列
  │
  ├─ NALU ≤ MTU ──────────▶ Single NALU RTP 包
  │
  ├─ NALU > MTU ──────────▶ 切成多个 FU-A RTP 包
  │
  └─ 多个小 NALU 一起发 ──▶ STAP-A 聚合 RTP 包
```

---

## 四、RTP 头结构（12 字节）

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|V=2|P|X|  CC   |M|     PT      |       sequence number         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           timestamp                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           synchronization source (SSRC) identifier            |
+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
|            contributing source (CSRC) identifiers             |
|                             ....                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| 字段 | 关键作用 |
|------|---------|
| **PT (Payload Type)** | 负载类型（96 通常表示动态协商的 H.264） |
| **sequence number** | 包序号，用于检测丢包和重排序 |
| **timestamp** | 时间戳（同一帧的所有包时间戳相同，**用于同步和 A/V 对齐**） |
| **SSRC** | 同步源标识符，区分不同流 |
| **M (Marker)** | 1 = 一帧的最后一个包（用于帧边界检测） |

---

## 五、RTSP：控制协议（不传数据）

RTSP **只负责"控制"**：告诉服务器"开始推流"、"停止"、"用什么方式传输"。媒体数据通过 RTP 走。

### 5.1 一个 RTSP 会话的真实报文

```
C→S  DESCRIBE rtsp://192.168.1.10/stream
S→C  RTSP/1.0 200 OK
     Content-Type: application/sdp
     
     v=0
     o=- 123456 0 IN IP4 192.168.1.10
     s=Video Stream
     c=IN IP4 192.168.1.10
     t=0 0
     m=video 0 RTP/AVP 96        ← 视频走 RTP，端口动态协商
     a=rtpmap:96 H264/90000      ← PT=96, H.264, 时钟 90kHz
     a=fmtp:96 profile-level-id=42C01E; sprop-parameter-sets=Z0LAHtkA,aM4G4g==  ← SPS/PPS base64
     a=control:trackID=0

C→S  SETUP rtsp://192.168.1.10/stream/trackID=0
     Transport: RTP/AVP;unicast;client_port=5004-5005
S→C  RTSP/1.0 200 OK
     Transport: RTP/AVP;unicast;client_port=5004-5005;server_port=8000-8001
     Session: 12345678

C→S  PLAY rtsp://192.168.1.10/stream
     Session: 12345678
S→C  RTSP/1.0 200 OK
     Session: 12345678

[S→C 持续发送 RTP 包，5004 端口]

C→S  TEARDOWN rtsp://192.168.1.10/stream
```

### 5.2 SDP 关键字段

| 字段 | 含义 |
|------|------|
| `m=video 0 RTP/AVP 96` | 媒体类型 video，端口 0（被动协商），PT 96 |
| `a=rtpmap:96 H264/90000` | PT 96 映射为 H.264，时钟 90 kHz |
| `a=fmtp:96 profile-level-id=...;sprop-parameter-sets=...` | SPS/PPS（base64 编码） |
| `c=IN IP4 ...` | 连接地址（媒体数据发往的 IP） |

> 90 kHz 时钟 = 视频时间戳的单位。所有时间戳都按这个换算：`pts / 90000 = 秒数`。

---

## 六、抓包看实际数据

用 Wireshark 抓 RTSP 流过滤：

```
rtsp || rtp
```

典型观察：

```
192.168.1.20 → 192.168.1.10  RTSP 100 req: DESCRIBE rtsp://...
192.168.1.10 → 192.168.1.20  RTSP 200 OK  (含 SDP)
192.168.1.20 → 192.168.1.10  RTSP SETUP
192.168.1.10 → 192.168.1.20  RTSP 200 OK
192.168.1.20 → 192.168.1.10  RTSP PLAY
192.168.1.10 → 192.168.1.20  RTP 1344 bytes  ← 媒体数据
192.168.1.10 → 192.168.1.20  RTP 1344 bytes
... (持续)
192.168.1.20 → 192.168.1.10  RTSP TEARDOWN
```

---

## 七、两种 RTSP 传输模式

| 模式 | 特点 |
|------|------|
| **UDP 模式** | RTP 数据走 UDP 5004 端口。延迟低、可能丢包。**主流**。 |
| **TCP 模式（Interleaved）** | RTP 数据夹在 RTSP 报文里，端口 554。**穿防火墙方便**。URL 加 `?tcp` 或服务端强制。 |
| **HTTP 隧道** | RTSP 报文走 HTTP，更强穿透能力。 |

**Interleaved 模式**长这样：

```
RTSP/1.0 200 OK
...
RTP 数据前会有一字节 magic '$' + 1 字节 channel 号
即：`$ 0x01` + RTP 包
```

---

## 八、协议栈分层速查

| 层级 | 格式 | 谁负责 |
|------|------|--------|
| **应用层** | 视频 = H.264/H.265 NALU 串，音频 = AAC ADTS | 编码器 |
| **RTP 层** | RTP Header(12B) + 负载（FU-A/STAP-A/Single） | 发送/接收库（live555、FFmpeg） |
| **传输层** | UDP（默认）或 TCP（interleaved） | socket |
| **会话层** | RTSP 报文（DESCRIBE/SETUP/PLAY/TEARDOWN） | RTSP 服务器 |
| **协商信息** | SDP（描述媒体类型、PT、时钟、SPS/PPS） | DESCRIBE 响应中 |

---

## 九、心智模型图

```
RTSP（控制）               RTP（媒体）
  ↓                          ↓
DESCRIBE                    [RTP#1: S=1, TYPE=5, IDR 分片1]
SETUP                       [RTP#2: S=0, TYPE=5, IDR 分片2]
PLAY   ──────────────────▶  [RTP#3: S=0, E=1, TYPE=5, IDR 分片3]  ← 一帧
                           [RTP#4: TYPE=1, P 帧]
                           [RTP#5: TYPE=1, P 帧]
                           ...
TEARDOWN                    （停止）
```

**关键理解**：

- **RTSP 报文只在开始/结束时出现**，中间过程全是 RTP 包
- **一帧可能被切成多个 RTP 包**，靠 S/E 位和 sequence number 重组
- **M=1 的 RTP 包是帧的末尾**（用于帧边界检测）
- **时间戳同一帧相同**，跨帧单调递增

---

## 十、H.265 / HEVC 的差异

H.265 在码流结构上类似 H.264，但 NALU 头从 **1 字节变成 2 字节**，且引入了**VCL/Non-VCL 分类**和新的参数集。

### 10.1 H.265 NALU 头（2 字节）

```
 0                   1
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|F|  Type  |  LayerId  | TID |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| 字段 | 位数 | 含义 |
|------|------|------|
| F | 1 | 错误标志 |
| **Type** | **6** | NALU 类型（H.264 是 5 位，这里多 1 位） |
| LayerId | 6 | 分层编码时的层 ID（可伸缩视频编码） |
| TID | 3 | 时间子层 ID |

### 10.2 H.265 新增的 NALU 类型

| Type | 名称 | 含义 |
|------|------|------|
| **32** | **VPS** | 视频参数集（H.264 没有这一层，H.265 多出来） |
| **33** | **SPS** | 序列参数集 |
| **34** | **PPS** | 图像参数集 |
| 35 | AUD | 访问单元分隔符 |
| 39/40 | SEI | 补充增强信息 |
| 1~4 | VCL NAL | 实际视频数据（VCL = Video Coding Layer） |

### 10.3 VCL vs Non-VCL NAL

H.265 显式区分了两类 NALU：

- **VCL（Video Coding Layer）**：承载真正的视频数据（CTU、切片、I/P/B 帧），Type 1~4
- **Non-VCL**：元数据/参数（VPS/SPS/PPS/SEI 等），Type > 4

H.264 其实也有类似概念，但没在 header 里强制区分。**H.265 这种分类对网络传输很关键**——重传策略、QoS 可以优先保护 Non-VCL（丢了整个流就解不出来了）。

### 10.4 H.265 RTP 打包的差异（RFC 7798）

H.265 沿用 H.264 的 FU-A 思路，但**分片包类型号变了**：

| 打包方式 | H.264 (RFC 6184) | H.265 (RFC 7798) |
|---------|------------------|------------------|
| Single NALU | Type 1~23 | Type 1~47 |
| **FU-A** | **Type 28** | **Type 49** |
| **FU-B** | 不常见 | **Type 50** |
| 聚合包 | STAP-A (24) / MTAP (25/26/27) | AP (48) / FU-B 替代 |

**FU header 含义不变**，S/E/TYPE 字段照搬：

```
H.265 FU-A: [RTP Header] [FU ind(1B, Type=49)] [FU header(1B, S/E/Type)] [Payload]
```

Type 字段填的是**原始 H.265 NALU 的类型**（如 19=IDR_W_RADL、1=TRAIL_R、32=VPS）。

### 10.5 一个 H.265 RTSP 流的真实样貌

```
SDP 里:
  a=rtpmap:96 H265/90000
  a=fmtp:96 profile-space=0;profile-id=1;tier-flag=0;level-id=93;sprop-vps=QAEMAf//AWAAAAM;...
                                                                                ↑ VPS
                                                                                  ↓ SPS
                                                                                    ↓ PPS
                                                                                    都 base64
RTP 包序列:
  RTP#1: FU-A(49), Type=32, S=1, E=0  →  VPS 分片1
  RTP#2: FU-A(49), Type=32, S=0, E=1  →  VPS 分片2
  RTP#3: FU-A(49), Type=33, S=1, E=0  →  SPS 分片1
  ...
  RTP#10: FU-A(49), Type=19, S=1, E=0 →  IDR 帧分片1
  RTP#11: FU-A(49), Type=19, S=0, E=0 →  IDR 帧分片2
  RTP#12: FU-A(49), Type=19, S=0, E=1 →  IDR 帧分片3（M=1）
```

> **关键区别**：H.265 多了 **VPS**，且一个视频流要先收到 VPS+SPS+PPS 才能解出第一帧；这在网络抖动场景下恢复时间更长。

---

## 十一、AAC 音频的 RTP 传输

视频之外，RTSP 流里**通常同时有音频**（摄像头、监控、视频会议都有音轨）。最常见的是 **AAC**。

### 11.1 AAC 的原始码流格式：ADTS

AAC 编码器直接输出的是 **ADTS（Audio Data Transport Stream）** 帧，每帧 7 或 9 字节头 + 原始 AAC 数据。

```
┌─────────────────────────────────────────────────────────┐
│  ADTS Fixed Header (28 bit)  │ ADTS Variable Header     │
│  - syncword (12 bit)         │ - 18 bit 字段             │
│  - ID, layer, protection      │ - 采样率,声道数,帧长      │
└──────────────────────────────────────────────────────────┘
                     │  + Raw AAC Frame Data
                     ▼
              [Frame Data 字节]
```

**每帧都以 `0xFFF` 同步字开头**：

```
FF F1 50 80 02 00 00 00 00 23 00 ...
↑  ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑  ↑
同 M 采 私 通 声 原 帧长字段（2B）
步 号 样 有 道 始 bitrate 等
字   1 率 1 数 位 长度
```

FFmpeg 解析 AAC 时通常看到 `0xFF 0xF0` 这种就识别为 ADTS 帧头。

### 11.2 ADTS vs LATM

RTP 传输 AAC 时**有两种打包方式**：

| 方式 | 特点 | SDP 标识 |
|------|------|---------|
| **ADTS** | 完整帧，解析简单 | `a=rtpmap:97 mpeg4-generic/44100/2` |
| **LATM** | 去掉 ADTS 头，用 LATM 头替代，节省带宽 | `a=rtpmap:97 MP4A-LATM/44100/2` |

**LATM = Low-overhead Audio Transport Multiplex**，本质是把 ADTS 的元数据（采样率、声道数、帧长）集中放到一个 **AudioSpecificConfig** 结构里，通过 SDP 协商发送，避免每帧重复。

### 11.3 RTP 打包方式（RFC 3640）

AAC 在 RTP 里最常见的是 **mpeg4-generic**（PT 动态协商，典型值 96/97）：

```
一个 AAC 音频帧（1024 样本）包进 RTP 的样子：

RTP Header(12B) + AU Header(s) + AAC Raw Data
                  ↑
                  这个是 RFC 3640 引入的"访问单元头"
```

**AU Header 格式**：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     AU-Index  |     AU-Index-delta     |     CTS-flag | DTS-flag
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           AU-size            |   [CTS delta]   |   [DTS delta]   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           ... 多 AU 时重复 ...                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

> 大多数情况下，每个 RTP 包只装一个 AU，AU-Index 简化为只填 **AU-size**（2 字节，标记后面 AAC 帧的长度）。

**真实 SDP 协商**：

```
m=audio 0 RTP/AVP 97
a=rtpmap:97 mpeg4-generic/44100/2
a=fmtp:97 streamtype=5;profile-level-id=1;mode=AAC-hbr;SizeLength=13;IndexLength=3;IndexDeltaLength=3;Config=1210
                                              ↑ 标 AAC-LC
                                                          ↑ AU Header 中 SizeLength=13 bit
                                                                            ↑ AudioSpecificConfig=0x1210
                                                                              (采样率 44100, 声道 2, AAC-LC)
```

- **SizeLength=13**：AU Header 中"帧大小"字段占 13 bit（最大 8191 字节，足够一个 AAC 帧）
- **Config=1210**：AudioSpecificConfig 的十六进制，告诉解码器"采样率、声道、profile"

### 11.4 视频和音频的 RTP 时间戳

两者**用不同频率的时钟**：

| 媒体 | 时钟频率 | 原因 |
|------|---------|------|
| 视频 | 90 kHz | 历史标准，足够分辨 30fps（每帧 3000 时钟） |
| 音频 | 采样率（AAC 通常 44100/48000） | 一个采样=1个时钟，方便 A/V 同步 |

**A/V 同步的核心**：把两者的 RTP 时间戳**统一换算成墙钟时间**（毫秒/微秒），就能判断"这个画面应该配这个声音"。

---

## 十二、PSM 与负载协商扩展

### 12.1 什么是 PSM

**PSM = Payload Specific Metadata**。本质是 SDP/RTSP 在用动态 PT（96~127）时，**进一步告诉对方负载的内部细节**。

最常见的就是上面 AAC 例子里的 `a=fmtp` 那一串 —— 它就是 PSM。

### 12.2 SDP 常见 fmtp 扩展

| 协议 | fmtp 例子 | 含义 |
|------|---------|------|
| **H.264** | `profile-level-id=42C01E; sprop-parameter-sets=Z0LAHtkA,aM4G4g==; packetization-mode=1` | profile、SPS/PPS（base64）、是否 FU-A 必需 |
| **H.265** | `profile-space=0;profile-id=1;tier-flag=0;level-id=93;sprop-vps=...;sprop-sps=...;sprop-pps=...` | 同上，加 VPS |
| **AAC** | `streamtype=5;profile-level-id=1;SizeLength=13;IndexLength=3;Config=1210` | AAC 类型、AU header 布局、AudioSpecificConfig |
| **opus** | `sprop-stereo=1; maxaveragebitrate=64000` | opus 的额外参数 |
| **H.263** | `framesize=QCIF; mbps=32000; h=263` | 旧视频编码 |

### 12.3 `packetization-mode` 字段（H.264 关键）

H.264 SDP 里有 `packetization-mode`：

| 取值 | 含义 |
|------|------|
| 0 | 不允许 FU-A（只能 STAP-A 和 Single） |
| 1 | 允许 FU-A（**最常用**，一帧可超 MTU） |
| 2 | 允许 FU-A，但**不允许 STAP-A**（不允许非 FU 包的聚合） |

> 大多数现代 RTSP 服务器和客户端都协商为 `mode=1`。

---

## 十三、RTCP 反馈与 QoS 机制

RTSP/RTP 会话里，**RTCP（RTP Control Protocol）** 跑在**另一个端口**（RTP+1）。它**不传媒体数据**，只传"控制包"。

### 13.1 端口分配

```
RTP 媒体数据端口：5004
RTCP 控制包端口：5005  ← 必须比 RTP 大 1
```

### 13.2 RTCP 包类型

| 类型号 | 名称 | 作用 |
|--------|------|------|
| **200** | **SR**（Sender Report） | 发送方报告：已发送的 RTP 包数、字节数、NTP 时间戳 |
| **201** | **RR**（Receiver Report） | 接收方报告：丢包率、抖动(round-trip delay)、最近 SR 时间戳 |
| 202 | SDES | Source Description：CNAME（接收方标识）等 |
| 203 | BYE | 离开会话 |
| 204 | APP | 应用自定义 |
| 205 | RTPFB | RTP 反馈（NACK 等） |
| 206 | PSFB | Payload-specific 反馈（PLI/FIR/REMB 等） |

### 13.3 关键反馈机制

#### NACK（Negative Acknowledgment）

```
接收方发现 RTP#100 丢了，下一个收到的是 RTP#102
  → 立刻通过 RTCP 告诉发送方："包 100 没收到，请重传"
```

RTCP 包里携带**丢失包的 PID（packet ID）序列**和**可选的 BLP（bitmask of following losses）**：

```
RTCP NACK 格式（简化）：
  PID = 100          ← 丢的包
  BLP = 0x000A0000  ← 包 101 和 103 也丢了（位掩码）
```

#### PLI / FIR（关键帧请求）

| 名称 | 用途 | 时机 |
|------|------|------|
| **PLI** (Picture Loss Indication) | 接收方解码失败，要求发 IDR | 解码器报 "missing reference" |
| **FIR** (Full Intra Request) | 主动要求发全 I 帧 | 加入会议、刷新背景时 |
| **SLI** (Slice Loss Indication) | 某个 slice 丢了 | H.264 slice 级别纠错 |
| **RPSI** (Reference Picture Selection) | 选择参考帧 | 多参考帧场景 |

> **WebRTC 必开**：PLI 是 WebRTC 抗网络丢帧的核心机制。

#### REMB（Receiver Estimated Maximum Bitrate）

```
接收方告诉发送方："我的带宽只能扛 800 kbps，请降码率"
```

主要用于 WebRTC 的拥塞控制（GCC 算法）。

### 13.4 RTCP 的带宽占用

**RTCP 总带宽 ≤ 5% 媒体带宽**（RFC 3550）。如果媒体是 1 Mbps，RTCP 最多占 50 kbps —— 这就是为什么 SR/RR 不能频繁发。

```
典型间隔：
- 视频 SR:  每 1 秒发一次
- 视频 RR:  每 1 秒发一次
- 音频 SR:  每 5 秒发一次
```

### 13.5 RTCP 包在 Wireshark 里

```
Filter: rtcp

典型观察:
192.168.1.20 → 192.168.1.10  RTCP  106 bytes  Sender Report
192.168.1.10 → 192.168.1.20  RTCP  92 bytes   Receiver Report
192.168.1.20 → 192.168.1.10  RTCP  24 bytes   NACK (PID=100, BLP=...)
192.168.1.10 → 192.168.1.20  RTP   1344 bytes  ← 服务端重传包 100
192.168.1.20 → 192.168.1.10  RTCP  24 bytes   PLI (关键帧请求)
192.168.1.10 → 192.168.1.20  RTP   4520 bytes  ← 服务端发 IDR 关键帧
```

> **注意**：RTSP 2.0 时代开始，RTCP 反馈越来越多（WebRTC 几乎全靠 RTCP），但传统 RTSP 服务器（如 live555）的 RTCP 实现较简单，只发 SR/RR，**NACK/PLI 是可选的**。

---

## 十四、完整协议栈速查（更新版）

| 层级 | 视频 | 音频 | 控制 |
|------|------|------|------|
| **应用层** | H.264/H.265 NALU 串 | AAC ADTS / LATM 帧 | RTSP 报文 |
| **RTP 层** | RTP Header(12B) + FU-A 负载 | RTP Header + AU Header + AAC Raw | （无） |
| **RTCP 层** | SR/RR/NACK/PLI | SR/RR | （无） |
| **传输层** | UDP（默认）| UDP | UDP/TCP |
| **会话层** | （无）| （无）| RTSP 报文 |
| **协商** | SDP：`rtpmap` + `fmtp` (sprop-parameter-sets) | SDP：`rtpmap` + `fmtp` (Config) | SDP 整体 |

---

## 总结（更新版）

| 你想问的 | 答案 |
|---------|------|
| 网络上视频的格式？ | RTP 包序列，负载是 H.264/H.265 NALU |
| 一帧被切成多少包？ | 看 NALU 大小，超过 MTU 就用 FU-A 切 |
| 怎么识别帧边界？ | RTP Marker=1，或 FU-A 的 S=1/E=1 |
| SPS/PPS 怎么传？ | 走 SDP 协商（base64）或作为第一个 RTP 包 |
| RTSP 和 RTP 什么关系？ | RTSP 是"老板"，控制会话；RTP 是"员工"，搬数据 |
| 90 kHz 时钟是什么？ | 视频时间戳单位，所有 PTS/DTS 都按它换算成秒 |
| H.265 比 H.264 多什么？ | NALU 头 2 字节、新增 VPS、Type 多 1 位、FU-A 用 type 49 |
| 音频怎么传？ | AAC 走 mpeg4-generic 负载，AU Header 标帧大小 |
| A/V 怎么同步？ | 把视频 90kHz 和音频采样率都换算成墙钟时间 |
| 丢包了怎么办？ | 接收方发 RTCP NACK，要求重传；或发 PLI 请求关键帧 |
| FU-A 和 STAP-A 区别？ | FU-A 是"切一个大包"，STAP-A 是"合并几个小包" |
| packetization-mode 1 啥意思？ | H.264 SDP 字段，允许 FU-A 分片（最常用） |
