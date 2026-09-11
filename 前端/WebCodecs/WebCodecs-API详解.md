# WebCodecs API 完整详解

> W3C WebCodecs 规范详细参考手册
> 涵盖所有核心 API：VideoDecoder/Encoder、AudioDecoder/Encoder、ImageDecoder、VideoFrame、AudioData、EncodedVideoChunk、EncodedAudioChunk、VideoColorSpace 等
> 适合作为浏览器端音视频开发的速查手册

---

## 目录

- [一、概述与架构](#一概述与架构)
- [二、VideoFrame 详解](#二videoframe-详解)
- [三、AudioData 详解](#三audiodata-详解)
- [四、EncodedVideoChunk / EncodedAudioChunk](#四encodedvideochunk--encodedaudiochunk)
- [五、VideoDecoder 详解](#五videodecoder-详解)
- [六、VideoEncoder 详解](#六videoencoder-详解)
- [七、AudioDecoder 详解](#七audiodecoder-详解)
- [八、AudioEncoder 详解](#八audioencoder-详解)
- [九、ImageDecoder 详解](#九imagedecoder-详解)
- [十、VideoColorSpace 与色彩元数据](#十videocolorspace-与色彩元数据)
- [十一、关键参数集 SPS / PPS / VPS](#十一关键参数集-sps--pps--vps)
- [十二、Worker 中的 WebCodecs](#十二worker-中的-webcodecs)
- [十三、错误处理与恢复策略](#十三错误处理与恢复策略)
- [十四、队列控制与背压机制](#十四队列控制与背压机制)
- [十五、性能调优清单](#十五性能调优清单)
- [十六、典型实战代码合集](#十六典型实战代码合集)
- [十七、浏览器兼容性与能力探测](#十七浏览器兼容性与能力探测)

---

## 一、概述与架构

### 1.1 WebCodecs 的定位

WebCodecs 是 W3C 编解码工作组制定的浏览器底层 API，目标是**直接暴露编解码能力给 JavaScript**，突破 `<video>`、`<canvas>`、MediaRecorder 等高层 API 的限制，让 Web 应用获得帧级的音视频处理能力。

它包含两大类对象：

1. **未压缩帧对象**：`VideoFrame`、`AudioData`、`ImageBitmap` 等
2. **压缩包对象**：`EncodedVideoChunk`、`EncodedAudioChunk`

围绕它们构建四类**编解码器**：

| 编解码器 | 作用 |
|---------|------|
| `VideoDecoder` | H.264/H.265/VP9/AV1 → VideoFrame |
| `VideoEncoder` | VideoFrame → H.264/H.265/VP9/AV1 |
| `AudioDecoder` | AAC/Opus/MP3 → AudioData |
| `AudioEncoder` | AudioData → AAC/Opus |
| `ImageDecoder` | 图片 → VideoFrame（静态图片的批量解码） |

### 1.2 数据流模型

WebCodecs 的核心是**异步、事件驱动、零拷贝**：

```
┌──────────────┐      decode()       ┌──────────────��
│ EncodedChunk │ ──────────────────► │   Decoder    │
└──────────────┘                     └──────┬───────┘
                                            │ output 回调
                                            ▼
                                     ┌──────────────┐
                                     │  VideoFrame  │ ──► Canvas/WebGPU/WASM
                                     │  /AudioData  │
                                     └──────────────┘
                                            │ encode()
                                            ▼
                                     ┌──────────────┐
                                     │   Encoder    │
                                     └──────┬───────┘
                                            │ output 回调
                                            ▼
                                     ┌──────────────┐
                                     │ EncodedChunk │ ──► 网络/文件
                                     └──────────────┘
```

**关键特性：**
- **异步**：所有 codec 操作不阻塞主线程
- **事件驱动**：通过 `output` / `error` 回调获取结果
- **零拷贝**：VideoFrame 直接持有 GPU 内存，可送 Canvas / WebGPU / WebGL
- **可背压**：通过 `decodeQueueSize` 控制节奏

### 1.3 与高层 API 的关系

```
┌──────────────────────────────────────────┐
│           高级 API 层                      │
│   <video> / MediaRecorder / Canvas       │
└────────────────┬─────────────────────────┘
                 │ 内部实现
┌────────────────▼─────────────────────────┐
│           WebCodecs 层                    │  ← 本文档主题
│   VideoDecoder/Encoder/AudioDecoder/...   │
└────────────────┬─────────────────────────┘
                 │ 硬件加速
┌────────────────▼─────────────────────────┐
│           硬件 / 系统 codec                │
│   VideoToolbox / VAAPI / DXVA / NVDEC    │
└──────────────────────────────────────────┘
```

---

## 二、VideoFrame 详解

`VideoFrame` 表示一帧**未压缩的视频数据**，是 WebCodecs 与渲染管线的核心载体。

### 2.1 构造函数

#### 从内存创建（裸像素数据）

```js
const frame = new VideoFrame(buffer, {
  codedWidth: 1920,
  codedHeight: 1080,
  codedRect: { x: 0, y: 0, width: 1920, height: 1080 },  // 可选
  displayWidth: 1920,       // 显示宽度（可与 coded 不同，用于旋转/黑边）
  displayHeight: 1080,
  format: 'I420',           // 像素格式
  timestamp: 0,             // PTS（微秒）
  duration: 33_333,         // 单帧时长（微秒，可选）
  colorSpace: { primaries: 'bt709', transfer: 'bt709', matrix: 'bt709', fullRange: false },
  rotation: 0,              // 0/90/180/270
  flip: false,              // 水平翻转
  visibleRect: { x: 0, y: 0, width: 1920, height: 1080 },  // 可视区域
});
```

**支持的格式：**
- `I420`（YUV 4:2:0 planar，12 bpp）
- `I420A`（I420 + Alpha）
- `I422`（YUV 4:2:2 planar，16 bpp）
- `I444`（YUV 4:4:4 planar，24 bpp��
- `NV12`（YUV 4:2:0 semi-planar）
- `RGBA` / `BGRA` / `ARGB`（32 bpp）
- `RGBA10A2`（10-bit HDR）

#### 从 video 元素创建

```js
const frame = new VideoFrame(videoElement, {
  timestamp: performance.now() * 1000,
});
```

自动捕获 video 当前帧。

#### 从 canvas 创建

```js
const frame = new VideoFrame(canvas, {
  timestamp: pts,
  duration: 33_333,
});
```

从 OffscreenCanvas 创建也是同样的语法，常用于编码路径。

#### 从 ImageBitmap 创建

```js
const bitmap = await createImageBitmap(image);
const frame = new VideoFrame(bitmap, { timestamp: 0 });
```

### 2.2 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `codedWidth` | number | 原始编码宽度 |
| `codedHeight` | number | 原始编码高度 |
| `displayWidth` | number | 显示宽度（处理旋转/黑边后） |
| `displayHeight` | number | 显示高度 |
| `timestamp` | number | PTS（微秒） |
| `duration` | number | 时长（微秒），可选 |
| `format` | string \| null | 像素格式，可能为 null（如 opaque handle） |
| `colorSpace` | VideoColorSpace | 色彩空间元数据 |
| `visibleRect` | DOMRectReadOnly | 可视区域 |
| `rotation` | number | 0/90/180/270 |
| `flip` | boolean | 是否水平翻转 |
| `metadata` | VideoFrameMetadata | RTP/HDR 等扩展元数据（RTP 注入时） |

### 2.3 方法

#### 渲染到 Canvas

```js
frame.draw(canvasOrContext, {
  rect: { x: 0, y: 0, width: 1920, height: 1080 },  // 目标矩形
  visibleRect: { x: 0, y: 0, width: 1920, height: 1080 },  // 源可视区域
  alpha: 'keep',  // 'keep' | 'discard'
});
```

比 `canvas.drawImage(frame)` 更灵活，可指定源可视区域。

#### 转 ImageBitmap

```js
const bitmap = await frame.createImageBitmap({
  resizeWidth: 1280,
  resizeHeight: 720,
  resizeQuality: 'high',  // 'low' | 'medium' | 'high'
  rotation: 90,
});
```

可同时做缩放和旋转。

#### 复制（克隆）

```js
const newFrame = await frame.clone();
```

创建独立副本，GPU 内存会真正复制（用于多路消费）。

#### 关闭

```js
frame.close();
```

释放底层 GPU/内存资源。**未 close 会导致内存泄漏**。

#### 序列化为像素数据

```js
const data = new Uint8Array(frame.allocationSize());
frame.copyTo(data, { rect: { x: 0, y: 0, width: 1920, height: 1080 } });
```

`allocationSize()` 返回当前帧需要的字节数（基于 format 和 resolution）。

### 2.4 资源管理最佳实践

```js
// ❌ 错误：可能泄漏
decoder.output = (frame) => {
  ctx.drawImage(frame, 0, 0);
  // 忘记 close
};

// ✅ 正确：try-finally 模式
decoder.output = (frame) => {
  try {
    ctx.drawImage(frame, 0, 0);
  } finally {
    frame.close();
  }
};

// ✅✅ 最佳：在异步链末端 close
decoder.output = (frame) => {
  const bg = createBindGroup(frame);
  renderPass.setBindGroup(0, bg);
  pass.draw(6);
  device.queue.submit([encoder.finish()]);
  frame.close();  // submit 之后才安全 close
};
```

---

## 三、AudioData 详解

`AudioData` 表示一段**未压缩的 PCM 音频数据**。

### 3.1 构造函数

```js
const audioData = new AudioData({
  format: 'f32-planar',     // PCM 格式
  sampleRate: 48000,        // 采样率
  numberOfFrames: 1024,     // 单声道采样点数
  numberOfChannels: 2,      // 声道数
  timestamp: 0,             // PTS（微秒）
  data: buffer,             // 原始 PCM 数据
});
```

**支持的格式：**

| 格式 | 说明 | 字节/采样点 |
|------|------|-------------|
| `u8` | unsigned 8-bit | 1 |
| `s16` | signed 16-bit | 2 |
| `s32` | signed 32-bit | 4 |
| `f32` | float 32-bit | 4 |
| `u8-planar` | u8, 声道分开存储 | 1 |
| `s16-planar` | s16, 声道分开 | 2 |
| `s32-planar` | s32, 声道分开 | 4 |
| `f32-planar` | float, 声道分开 | 4 |

`planar` 模式：每个声道的数据连续存储（左声道全部数据 → 右声道全部数据）。
`interleaved` 模式（`f32` 等）：所有声道交织存储（左 1 → 右 1 → 左 2 → 右 2 ...）。

### 3.2 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `format` | string | PCM 格式 |
| `sampleRate` | number | 采样率（Hz） |
| `numberOfFrames` | number | 每声道采样点数 |
| `numberOfChannels` | number | 声道数 |
| `timestamp` | number | PTS（微秒） |
| `duration` | number | 时长（微秒），可选 |
| `numberOfSamples` | number | `numberOfFrames * numberOfChannels` |

### 3.3 方法

#### 复制 / 切片

```js
// 全量复制
const cloned = audioData.clone();

// 切片：从第 500 个采样点开始，取 1024 个采样点
const sliced = audioData.slice(500, 1024);
```

#### 转为普通数组

```js
const f32 = new Float32Array(audioData.numberOfSamples);
audioData.copyTo(f32, { planeIndex: 0 });  // 读取第一个声道
```

#### 关闭

```js
audioData.close();
```

### 3.4 使用场景

```js
// 解码输出
audioDecoder.output = (audioData) => {
  // 1. 送 Web Audio API 播放
  const buf = audioBufferFromAudioData(audioData);  // 自实现转换
  audioContext.createBufferSource().start();

  // 2. 送 WASM 处理（降噪、识别等）
  wasmModule.process(audioData.getChannelData(0));

  audioData.close();
};
```

---

## 四、EncodedVideoChunk / EncodedAudioChunk

### 4.1 EncodedVideoChunk

表示一个压缩视频包（NALU、OBU 等）。

```js
const chunk = new EncodedVideoChunk({
  type: 'key',         // 'key'（IDR/I-frame）、'delta'（P/B-frame）
  timestamp: 0,        // PTS（微秒）
  duration: 33_000,    // 单帧时长（微秒）
  data: annexBBuffer,  // 压缩数据（ArrayBuffer / TypedArray）
});
```

**属性：**
- `type`：`'key'` | `'delta'`
- `timestamp`：PTS（微秒）
- `duration`：时长（微秒）
- `byteLength`：数据字节数

**方法：**
- `copyTo(dest)`：复制数据到目标 buffer

### 4.2 EncodedAudioChunk

```js
const chunk = new EncodedAudioChunk({
  type: 'key',           // AAC 所有包都是 'key'，Opus 可能不是
  timestamp: 0,
  duration: 21_333,      // 1024/48000 秒 = 21333 微秒
  data: aacBuffer,
});
```

**属性：**
- `type`：`'key'` | `'delta'`
- `timestamp`：PTS
- `duration`：时长
- `byteLength`：字节数

### 4.3 ChunkMetadata

编码器 output 回调的第二参数，提供了��码所需的元数据：

```js
encoder.output = (chunk, meta) => {
  // meta 包含：
  // - decoderConfig: { codec, description, codedWidth, codedHeight, ... }
  // - svc: { temporalLayerId, ... }（可分级编码）
  // - alpha: side data for alpha channel

  if (meta.decoderConfig) {
    // 编码器变更了 codec 参数，需要通知解码端
    network.sendConfig(meta.decoderConfig);
  }
  network.sendChunk(chunk);
};
```

---

## 五、VideoDecoder 详解

### 5.1 构造函数

```js
const decoder = new VideoDecoder({
  output: (frame) => { /* 处理 VideoFrame */ },
  error: (e) => { /* 处理错误 */ },
});
```

`output` 回调会从 decoder 内部队列自动拉取，不会阻塞。

### 5.2 configure()

```js
decoder.configure({
  codec: 'avc1.640028',          // 必填
  codedWidth: 1920,              // 必填
  codedHeight: 1080,             // 必填
  description: spsAndPps,        // 可选，但 H.264/H.265 通常需要
  hardwareAcceleration: 'prefer-hardware',  // 'no-preference' | 'prefer-hardware' | 'prefer-software'
  optimizeForLatency: true,      // 优化延迟（减少缓冲）
  colorSpace: { ... },           // 可选，色彩空间
});
```

**`codec` 字符串格式：**

| 格式 | 字符串示例 | 说明 |
|------|-----------|------|
| H.264 Baseline 3.1 | `avc1.42001f` | `avc1.{profile}{level}` |
| H.264 Main 4.0 | `avc1.4d4028` | |
| H.264 High 4.2 | `avc1.640028` | |
| H.265 Main | `hev1.1.6.L93.B0` | 较复杂 |
| H.265 Main 10 | `hev1.2.4.L93.B0` | 10-bit |
| VP9 | `vp09.00.10.08` | profile.level.bit-depth |
| VP9 Profile 2 HDR | `vp09.02.51.10` | |
| AV1 Main | `av01.0.04M.08` | |
| AV1 High | `av01.1.04M.08` | |

**`description`（SPS/PPS/VPS）：**

H.264：`Annex B` 格式的 SPS + PPS 拼接：
```
00 00 00 01 [SPS NALU] 00 00 00 01 [PPS NALU]
```

H.265：SPS + PPS + VPS 都包含：
```
00 00 00 01 [VPS] 00 00 00 01 [SPS] 00 00 00 01 [PPS]
```

可以从编码器的 output meta 中自动获取：
```js
encoder.output = (chunk, meta) => {
  if (meta.decoderConfig?.description) {
    // 保存这个 SPS/PPS 给解码端用
    saveSPS(meta.decoderConfig.description);
  }
};
```

### 5.3 decode()

```js
decoder.decode(chunk);
```

非阻塞，内部排队执行。返回值是 `undefined`。

**注意：** 调用前必须 `configure()`，否则会抛 `InvalidStateError`。

### 5.4 flush()

```js
await decoder.flush();
```

等待所有已入队的 chunk 解码完成。**调用后仍可继续 decode**，但解码器会重置内部参考帧。

### 5.5 reset()

```js
decoder.reset();
```

立即清空内部队列，丢弃未解码数据。不返回 Promise（同步）。适合做 seek / 切流。

### 5.6 close()

```js
decoder.close();
```

彻底释放解码器实例。之后调用任何方法都会抛 `InvalidStateError`。

### 5.7 属性

```js
decoder.decodeState;       // 'unconfigured' | 'configured' | 'closed'
decoder.decodeQueueSize;   // 等待解码的 chunk 数量，用于背压
```

### 5.8 isConfigSupported()

```js
const result = await VideoDecoder.isConfigSupported({
  codec: 'avc1.640028',
  codedWidth: 1920,
  codedHeight: 1080,
  hardwareAcceleration: 'prefer-hardware',
});

if (result.supported) {
  decoder.configure(result.config);  // 用浏览器"修正"后的 config
} else {
  // 降级方案
}
```

**生产代码必须先探测**，不同浏览器/平台能力差异很大。

### 5.9 完整示例：H.264 软解码

```js
// 假设从 FLV 解析出 SPS/PPS 和 NALU
const decoder = new VideoDecoder({
  output: (frame) => {
    ctx.drawImage(frame, 0, 0);
    frame.close();
  },
  error: (e) => console.error('decode error:', e),
});

// 探测
const support = await VideoDecoder.isConfigSupported({
  codec: 'avc1.640028',
  codedWidth: 1920,
  codedHeight: 1080,
  description: spsAndPps,
});

if (!support.supported) {
  alert('浏览器不支持该视频格式');
} else {
  decoder.configure(support.config);

  // 喂数据
  for (const nalu of nalus) {
    const chunk = new EncodedVideoChunk({
      type: nalu.isKeyframe ? 'key' : 'delta',
      timestamp: nalu.pts,
      duration: 33_333,
      data: nalu.data,
    });
    decoder.decode(chunk);
  }

  await decoder.flush();
  decoder.close();
}
```

---

## 六、VideoEncoder 详解

### 6.1 构造函数与配置

```js
const encoder = new VideoEncoder({
  output: (chunk, meta) => { /* 发送 EncodedVideoChunk */ },
  error: (e) => { /* 处理错误 */ },
});

encoder.configure({
  codec: 'avc1.640028',
  width: 1280,
  height: 720,
  bitrate: 2_000_000,           // 平均比特率（bps）
  framerate: 30,

  // 可选：高级控制
  bitrateMode: 'variable',       // 'variable'（VBR）| 'constant'（CBR）| 'quantizer'
  latencyMode: 'realtime',       // 'realtime' | 'quality'
  avc: { format: 'avc' },        // 'avc'（长度前缀）或 'annexb'（Annex B）
  hardwareAcceleration: 'prefer-hardware',
  scalabilityMode: 'L1T2',       // 可分级编码（SVC）
  alpha: 'keep',                 // 'keep' | 'discard'（是否保留 alpha 通道）

  // 可选：编码器特定参数（H.264）
  encoderConfig: {
    profile: 'high',
    level: '4.2',
  },
});
```

### 6.2 encode()

```js
encoder.encode(frame, options);
```

`options` 可选：
```js
{
  keyFrame: true,    // 强制 IDR 帧
}
```

### 6.3 完整示例：Canvas 录制

```js
const canvas = document.querySelector('canvas');
const stream = canvas.captureStream(30);  // 30fps

// 从 stream 抓 video track
const videoTrack = stream.getVideoTracks()[0];

// 用 VideoEncoder 直接编码（比 MediaRecorder 更可控）
const encoder = new VideoEncoder({
  output: async (chunk, meta) => {
    // 上传到服务器
    const buf = new ArrayBuffer(chunk.byteLength);
    chunk.copyTo(buf);
    uploadToServer(buf, chunk.timestamp);

    // 第一次输出时发送 SPS/PPS
    if (meta.decoderConfig) {
      uploadToServer(meta.decoderConfig.description);
    }
  },
  error: (e) => console.error(e),
});

encoder.configure({
  codec: 'vp09.00.10.08',  // 用 VP9 避免专利问题
  width: canvas.width,
  height: canvas.height,
  bitrate: 1_500_000,
  framerate: 30,
});

// 从 video 元素逐帧送
videoTrack.requestFrame();  // 触发一帧

const videoEl = document.createElement('video');
videoEl.srcObject = stream;
await videoEl.play();

function captureFrame() {
  if (encoder.encodeQueueSize < 5) {
    const frame = new VideoFrame(videoEl, {
      timestamp: performance.now() * 1000,
    });
    encoder.encode(frame, { keyFrame: frame.timestamp % 5000 < 50 });
    frame.close();
  }
  requestAnimationFrame(captureFrame);
}
captureFrame();
```

### 6.4 编码器属性

- `encodeState`：`'unconfigured'` | `'configured'` | `'closed'`
- `encodeQueueSize`：待编码帧数（背压控制）
- `output`：output 回调引用

---

## 七、AudioDecoder 详解

接口形态与 VideoDecoder 完全对称。

### 7.1 配置

```js
audioDecoder.configure({
  codec: 'mp4a.40.2',       // AAC LC
  sampleRate: 48000,
  numberOfChannels: 2,

  // 可选：AAC 特定
  description: esdsBox,      // AudioSpecificConfig（从 MP4 esds 盒子提取）

  // Opus 特定
  // codec: 'opus',
  // description: ... OpusChannelMapping 等等
});
```

**常用 codec 字符串：**

| 格式 | 字符串 |
|------|--------|
| AAC LC | `mp4a.40.2` |
| AAC HE-AAC | `mp4a.40.5` |
| AAC HE-AACv2 | `mp4a.40.29` |
| Opus | `opus` |
| MP3 | `mp3` |
| FLAC | `flac` |
| Vorbis | `vorbis` |
| PCM (WAV) | `pcm` / `pcm-s16le` / `pcm-f32le` |

### 7.2 输出

```js
audioDecoder.output = (audioData) => {
  // audioData: AudioData

  // 方案 1：送 Web Audio API
  const audioBuffer = audioContext.createBuffer(
    audioData.numberOfChannels,
    audioData.numberOfFrames,
    audioData.sampleRate
  );

  for (let ch = 0; ch < audioData.numberOfChannels; ch++) {
    const channelData = new Float32Array(audioData.numberOfFrames);
    audioData.copyTo(channelData, { planeIndex: ch });
    audioBuffer.copyToChannel(channelData, ch);
  }

  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);

  // 精确对齐 PTS
  const startAt = audioContext.currentTime + (audioData.timestamp - performance.now() * 1000) / 1_000_000;
  source.start(startAt);

  audioData.close();
};
```

---

## 八、AudioEncoder 详解

### 8.1 配置

```js
audioEncoder.configure({
  codec: 'opus',
  sampleRate: 48000,
  numberOfChannels: 2,
  bitrate: 64_000,

  // Opus 特定
  opus: {
    application: 'voip',      // 'voip' | 'audio' | 'lowdelay'
    frameDuration: 20_000,    // 20ms（微秒）
    signal: 'music',          // 'auto' | 'music' | 'voice'
  },
});
```

### 8.2 编码

```js
// 从 microphone 捕获
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const audioTrack = stream.getAudioTracks()[0];

// 用 AudioContext 抓 PCM
const audioContext = new AudioContext({ sampleRate: 48000 });
const source = audioContext.createMediaStreamSource(stream);
const processor = audioContext.createScriptProcessor(1024, 2, 2);

source.connect(processor);
processor.connect(audioContext.destination);

processor.onaudioprocess = (e) => {
  const left = e.inputBuffer.getChannelData(0);
  const right = e.inputBuffer.getChannelData(1);
  const interleaved = interleave(left, right);  // L R L R L R...

  const audioData = new AudioData({
    format: 'f32',
    sampleRate: 48000,
    numberOfFrames: 1024,
    numberOfChannels: 2,
    timestamp: e.playbackTime * 1_000_000,
    data: interleaved,
  });

  audioEncoder.encode(audioData);
  audioData.close();
};

audioEncoder.output = (chunk, meta) => {
  // 发送到服务器
  send(chunk);
};
```

---

## 九、ImageDecoder 详解

`ImageDecoder` 用于**批量解码静态图片**（PNG、JPEG、WebP、AVIF、GIF、BMP），底层复用 WebCodecs 的视频解码器。

### 9.1 基本用法

```js
const response = await fetch('/large-image.avif');
const blob = await response.blob();

const decoder = new ImageDecoder({
  data: blob,
  type: 'image',  // 'image' | 'track'（动图）
});

const { image } = await decoder.decode();  // image: VideoFrame

canvas.drawImage(image, 0, 0);
image.close();
```

### 9.2 动图（GIF / animated WebP / animated AVIF）

```js
const decoder = new ImageDecoder({
  data: blob,
  type: 'track',
});

const track = decoder.tracks.selectedTrack;

// 逐帧解码
for (let i = 0; i < track.frameCount; i++) {
  const { image } = await decoder.decode({ frameIndex: i });
  await new Promise(r => setTimeout(r, track.frame(i).duration));  // 按 GIF 时长延迟
  canvas.drawImage(image, 0, 0);
  image.close();
}
```

### 9.3 解码进度

```js
const decoder = new ImageDecoder({
  data: blob,
  type: 'image',
  // 可选：渐进式解码
  progressive: true,  // Chrome 启用 AVIF 渐进式解码
});

decoder.decode({ completeFramesOnly: false });  // 边下边解
```

### 9.4 应用场景

- **图片懒加载 + 缩略图**：批量解码、缓存 VideoFrame
- **动图替代方案**：GIF → AVIF/WebP，性能更好
- **AI 推理预处理**：解码 → 直接送 WebGPU/WASM 模型

---

## 十、VideoColorSpace 与色彩元数据

### 10.1 VideoColorSpace 接口

```js
const cs = new VideoColorSpace({
  primaries: 'bt709',          // 'bt709' | 'bt470bg' | 'smpte170m' | 'bt2020' | 'smpte432'（p3） | ...
  transfer: 'bt709',            // 'bt709' | 'iec61966-2-1'（sRGB） | 'smpte2084'（PQ/HDR10） | 'hlg' | 'linear'
  matrix: 'bt709',              // 'bt709' | 'bt470bg' | 'smpte170m' | 'bt2020-ncl'
  fullRange: false,             // true: full range（0-255），false: limited range（16-235）
});
```

### 10.2 在 VideoFrame 中使用

```js
const frame = new VideoFrame(buffer, {
  codedWidth: 1920,
  codedHeight: 1080,
  format: 'I420',
  colorSpace: {
    primaries: 'bt2020',
    transfer: 'smpte2084',  // HDR10 PQ
    matrix: 'bt2020-ncl',
    fullRange: false,
  },
});
```

### 10.3 在 WebGPU 中转换

WebGPU shader 需要手动做 YUV → RGB 和色彩空间转换：

```wgsl
// BT.709 limited → RGB（标准高清）
fn yuvToRgb(y: f32, u: f32, v: f32) -> vec3f {
  let yScaled = (y - 0.0625) * 1.164;        // limited range 偏移
  return vec3f(
    yScaled + 1.793 * (v - 0.5),
    yScaled - 0.213 * (u - 0.5) - 0.534 * (v - 0.5),
    yScaled + 2.112 * (u - 0.5)
  );
}

// BT.2020 PQ → linear（HDR10）
fn pqToLinear(pq: f32) -> f32 {
  let m1 = 0.1593017578125;
  let m2 = 78.84375;
  let c1 = 0.8359375;
  let c2 = 18.8515625;
  let c3 = 18.6875;
  let x = pow(pq, 1.0 / m2);
  let num = max(x - c1, 0.0);
  let den = c2 - c3 * x;
  return pow(num / den, 1.0 / m1);
}
```

### 10.4 HDR 支持要点

- WebGPU 设备需要请求 `hdr`：`device.requestDevice({ requiredFeatures: ['hdr'] })`
- 渲染目标使用 `rgba16float` 格式
- 输出到 HDR 显示器需要 `present()` 模式配合 OS HDR 设置
- macOS Safari / Windows HDR 行为差异较大，需要充分测试

---

## 十一、关键参数集 SPS / PPS / VPS

### 11.1 为什么需要这些参数

视频编码依赖**帧间预测**（P 帧参考前面的帧，B 帧参考前后帧），要正确解码，必须知道：
- 图像尺寸、帧率
- 编码档次（profile/level）
- 参考帧数量、缓冲模型
- **等等……**

这些信息存储在**参数集 NALU** 中，解码器必须先有 SPS/PPS 才能开始解码 I 帧。

### 11.2 H.264 的 SPS / PPS

```js
// FLV 容器通常用 AVCDecoderConfigurationRecord 存储 SPS/PPS
// 解析示例
function parseAVCConfig(buffer) {
  const view = new DataView(buffer);
  const numSPS = view.getUint8(5) & 0x1F;

  let offset = 6;
  const spsList = [];
  for (let i = 0; i < numSPS; i++) {
    const len = view.getUint16(offset);
    offset += 2;
    spsList.push(new Uint8Array(buffer, offset, len));
    offset += len;
  }

  const numPPS = view.getUint8(offset);
  offset += 1;
  const ppsList = [];
  for (let i = 0; i < numPPS; i++) {
    const len = view.getUint16(offset);
    offset += 2;
    ppsList.push(new Uint8Array(buffer, offset, len));
    offset += len;
  }

  return { sps: spsList, pps: ppsList };
}

// 转换为 Annex B 格式（00 00 00 01 前缀）
function toAnnexB(sps, pps) {
  const result = [];
  sps.forEach(s => {
    result.push(new Uint8Array([0, 0, 0, 1]));
    result.push(s);
  });
  pps.forEach(p => {
    result.push(new Uint8Array([0, 0, 0, 1]));
    result.push(p);
  });
  // 合并
  const totalLen = result.reduce((sum, arr) => sum + arr.length, 0);
  const out = new Uint8Array(totalLen);
  let offset = 0;
  result.forEach(arr => {
    out.set(arr, offset);
    offset += arr.length;
  });
  return out;
}

// 喂给 VideoDecoder
decoder.configure({
  codec: 'avc1.640028',
  codedWidth: 1920,
  codedHeight: 1080,
  description: toAnnexB(sps, pps),
});
```

### 11.3 H.265 的 VPS / SPS / PPS

H.265 多了一个 VPS（Video Parameter Set）：

```js
function toAnnexB_HEVC(vps, sps, pps) {
  // VPS + SPS + PPS，每个前面加 00 00 00 01
  // 顺序：VPS → SPS → PPS
}
```

### 11.4 从编码器自动获取

```js
encoder.output = (chunk, meta) => {
  if (meta.decoderConfig) {
    const { codec, description } = meta.decoderConfig;
    // description 是 Annex B 格式，可直接用于 VideoDecoder.configure
    // 或通过 SDP/RTP 发送给对端
    saveDecoderConfig({ codec, description });
  }
  send(chunk);
};
```

---

## 十二、Worker 中的 WebCodecs

### 12.1 为什么放 Worker

- **不阻塞主线程**：解码/编码是 CPU 密集型
- **可并行**：用 SharedArrayBuffer + Atomics 做多线程
- **可隔离**：避免主线程的 GC 抖动影响解码节奏

### 12.2 基础模式：DedicatedWorker

```js
// main.js
const worker = new Worker('codec-worker.js');

worker.postMessage({
  type: 'init',
  codec: 'avc1.640028',
  spsPps: spsAndPps,
}, [spsAndPps.buffer]);

worker.postMessage({
  type: 'decode',
  chunk: naluBuffer,
  timestamp: pts,
}, [naluBuffer.buffer]);

worker.onmessage = (e) => {
  if (e.data.type === 'frame') {
    // e.data.frame: VideoFrame（可转移回主线程）
    canvas.drawImage(e.data.frame, 0, 0);
    e.data.frame.close();
  }
};
```

```js
// codec-worker.js
let decoder;

self.onmessage = async (e) => {
  if (e.data.type === 'init') {
    decoder = new VideoDecoder({
      output: (frame) => {
        self.postMessage({ type: 'frame', frame }, [frame]);  // 转移 VideoFrame
      },
      error: (err) => self.postMessage({ type: 'error', message: err.message }),
    });

    decoder.configure({
      codec: e.data.codec,
      codedWidth: 1920,
      codedHeight: 1080,
      description: e.data.spsPps,
    });
  } else if (e.data.type === 'decode') {
    const chunk = new EncodedVideoChunk({
      type: 'key',
      timestamp: e.data.timestamp,
      data: e.data.chunk,
    });
    decoder.decode(chunk);
  }
};
```

### 12.3 OffscreenCanvas + Worker

```js
// 主线程把 canvas 转移到 worker
const offscreen = canvas.transferControlToOffscreen();
worker.postMessage({ type: 'canvas', canvas: offscreen }, [offscreen]);

// worker 里直接画
self.onmessage = (e) => {
  if (e.data.type === 'canvas') {
    const canvas = e.data.canvas;
    const ctx = canvas.getContext('2d');

    decoder.output = (frame) => {
      ctx.drawImage(frame, 0, 0);
      frame.close();
    };
  }
};
```

### 12.4 SharedArrayBuffer + 多线程

```js
// 多 worker 并行解码不同流（如多机位）
const worker1 = new Worker('codec-worker.js');
const worker2 = new Worker('codec-worker.js');

const sharedBuf = new SharedArrayBuffer(1024 * 1024);  // 共享环形缓冲
worker1.postMessage({ type: 'init', buffer: sharedBuf });
worker2.postMessage({ type: 'init', buffer: sharedBuf });
```

**注意：SharedArrayBuffer 需要 COOP/COEP 头部：**
```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

### 12.5 VideoFrame 跨线程转移

```js
// Worker A → Worker B
const frame = new VideoFrame(buffer, { ... });
workerB.postMessage({ type: 'frame', frame }, [frame]);
// Worker A 不再持有 frame，必须不再使用
```

`VideoFrame` 和 `AudioData` 都是 **Transferable**，跨线程零拷贝。

---

## 十三、错误处理与恢复策略

### 13.1 错误类型

```js
decoder.error = (e) => {
  console.error('DecoderError:', e);
  // e 是 DOMException 子类
};
```

**常见错误：**
- `InvalidStateError`：在错误的生命周期调用方法
- `NotSupportedError`：codec 不支持
- `DataError`：数据损坏
- `QuotaExceededError`：队列溢出

### 13.2 恢复策略

#### 简单场景：重建解码器

```js
let decoder;

async function rebuildDecoder() {
  if (decoder) decoder.close();

  decoder = new VideoDecoder({
    output: handleFrame,
    error: (e) => {
      console.error('decoder crashed:', e);
      rebuildDecoder();  // 自动重建
      requestKeyFrame(); // 通知发送方发 I 帧
    },
  });

  const support = await VideoDecoder.isConfigSupported(config);
  decoder.configure(support.config);
}
```

#### seek 场景：reset + 新 SPS

```js
// 切换码流
function seekTo(newConfig) {
  decoder.reset();  // 清空队列，不等剩余 chunk

  // 关键：必须等 SPS/PPS 到达后再 decode
  pendingConfig = newConfig;
}

decoder.output = (frame) => {
  if (pendingConfig) {
    decoder.configure(pendingConfig);
    pendingConfig = null;
  }
  handleFrame(frame);
};
```

#### 解码错误：请求 IDR

```js
let errorCount = 0;

decoder.error = (e) => {
  errorCount++;
  if (errorCount > 3) {
    // 多次失败，放弃该流
    destroyStream();
  } else {
    // 请求关键帧重建
    decoder.reset();
    requestKeyFrame();
  }
};
```

### 13.3 编码器错误

```js
encoder.error = (e) => {
  console.error('encoder error:', e);
  // 通常是输入参数错误，需要检查 VideoFrame 的 format、尺寸
};
```

---

## 十四、队列控制与背压机制

### 14.1 背压原理

```
┌─────────┐  decode(chunk)   ┌──────────┐  output(frame)   ┌──────────┐
│ 推送端   │ ───────────────► │  Decoder │ ───────────────► │  消费端   │
└─────────┘                  │  内部队列 │                  └──────────┘
                             └──────────┘
                              ↑
                              │ decodeQueueSize
```

如果消费端处理慢（渲染卡顿、AI 推理慢），队列会无限增长，最终**耗尽内存**。

### 14.2 基本背压

```js
function feed(chunk) {
  if (decoder.decodeQueueSize > MAX_QUEUE) {
    // 队列满了，等待
    pendingChunks.push(chunk);
    return;
  }
  decoder.decode(chunk);
}

decoder.output = (frame) => {
  handleFrame(frame);
  frame.close();

  // 消费一帧，尝试喂下一个
  const next = pendingChunks.shift();
  if (next) feed(next);
};
```

### 14.3 基于时间的背压

```js
const FRAME_BUDGET = 30;  // 最多堆积 30 帧
let bufferedFrames = 0;

decoder.output = (frame) => {
  bufferedFrames++;

  scheduleRender(frame);
  frame.close();

  if (bufferedFrames > FRAME_BUDGET) {
    // 直接丢弃后续帧，避免累积
    paused = true;
  }
};

// 渲染完成后
function onRendered() {
  bufferedFrames--;
  if (paused && bufferedFrames < FRAME_BUDGET / 2) {
    paused = false;
    resumeFeeding();
  }
}
```

### 14.4 编码器背压

```js
function captureAndEncode() {
  if (encoder.encodeQueueSize > 5) return;  // 编码器也有限制

  const frame = new VideoFrame(canvas, { timestamp: ... });
  encoder.encode(frame);
  frame.close();
}
```

---

## 十五、性能调优清单

### 15.1 解码性能

- ✅ 优先硬件加速：`hardwareAcceleration: 'prefer-hardware'`
- ✅ 优化延迟：`optimizeForLatency: true`（直播场景）
- ✅ 及时 `close()` VideoFrame
- ✅ 控制解码队列（避免内存爆炸）
- ✅ 用 `isConfigSupported()` 探测最佳配置
- ✅ Worker 中解码（不阻塞 UI）
- ❌ 避免在主线程做大量 GC（会产生 jank）
- ❌ 避免过大的 `codedWidth/codedHeight`（优先用显示尺寸）

### 15.2 编码性能

- ✅ 选用硬件支持的 codec（H.264、VP9、AV1）
- ✅ `latencyMode: 'realtime'` 直播场景
- ✅ 适当分辨率与比特率（不要盲目上 4K）
- ✅ 关键帧间隔（GOP）合理（直播 1-2s，点播 5-10s）
- ❌ 避免频繁动态切换码率（会产生关键帧风暴）

### 15.3 内存占用

```js
// 监控内存
if ('memory' in performance) {
  console.log('JS heap:', performance.memory.usedJSHeapSize / 1024 / 1024, 'MB');
}

// 监控 WebCodecs 队列
console.log('decode queue:', decoder.decodeQueueSize);
console.log('encode queue:', encoder.encodeQueueSize);
```

### 15.4 时间戳管理

```js
// 时间戳基准：micros (微秒)
const TIMEBASE = 1_000_000;

function ptsToMicros(seconds) {
  return Math.round(seconds * TIMEBASE);
}

function microsToSeconds(micros) {
  return micros / TIMEBASE;
}

// 解码器输出帧的 timestamp 就是 PTS
// 如果做 PTS ↔ DTS 处理（直播流）：
// DTS = 解码顺序，PTS = 显示顺序
// B 帧的情况下 PTS > DTS
```

---

## 十六、典型实战代码合集

### 16.1 完整 FLV → WebCodecs 解码管线

```js
// 解析 FLV（简化版）
class FLVParser {
  parseTag(tagType, data) {
    if (tagType === 0x09) {  // Video tag
      const codecId = data[0] & 0x0F;
      if (codecId === 7) {  // AVC
        const avcPacketType = data[1];
        const cts = (data[2] << 16) | (data[3] << 8) | data[4];
        const compositionTime = (cts & 0x800000) ? (cts - 0x1000000) : cts;

        if (avcPacketType === 0) {
          // AVCDecoderConfigurationRecord
          this.handleAVCConfig(data.slice(5));
        } else {
          // NALU
          const pts = this.currentTagTimestamp * 1000;
          this.handleNALU(data.slice(5), pts + compositionTime * 1000);
        }
      }
    }
  }
}
```

### 16.2 从视频流采样并编码

```js
async function streamToWebM(videoEl) {
  const encoder = new VideoEncoder({
    output: writeChunk,
    error: console.error,
  });

  encoder.configure({
    codec: 'vp09.00.10.08',
    width: videoEl.videoWidth,
    height: videoEl.videoHeight,
    bitrate: 2_000_000,
    framerate: 30,
  });

  let frameIndex = 0;
  function nextFrame() {
    if (videoEl.ended || encoder.encodeQueueSize > 10) {
      encoder.flush().then(() => {
        encoder.close();
        finalizeFile();
      });
      return;
    }

    const frame = new VideoFrame(videoEl, {
      timestamp: (frameIndex / 30) * 1_000_000,
    });

    encoder.encode(frame, {
      keyFrame: frameIndex % 90 === 0,  // 每 3 秒一个关键帧
    });

    frame.close();
    frameIndex++;

    videoEl.requestVideoFrameCallback(nextFrame);
  }
  videoEl.requestVideoFrameCallback(nextFrame);
}
```

### 16.3 自适应码率（ABR）

```js
let currentEncoder;
let currentBitrate = 2_000_000;

function switchQuality(newBitrate) {
  if (Math.abs(newBitrate - currentBitrate) / currentBitrate < 0.2) return;

  // 1. flush 当前编码器
  currentEncoder.flush().then(() => {
    currentEncoder.close();

    // 2. 用新码率重建
    currentEncoder = new VideoEncoder({ ... });
    currentEncoder.configure({
      codec: 'avc1.640028',
      width: 1920,
      height: 1080,
      bitrate: newBitrate,
      framerate: 30,
    });

    currentBitrate = newBitrate;
  });
}

// 根据网络状况调用
networkMonitor.on('bandwidth-changed', switchQuality);
```

### 16.4 视频水印（解码 → 处理 → 编码）

```js
// Worker 中处理
self.onmessage = (e) => {
  const { frame } = e.data;

  // 1. 用 Canvas 叠加水印
  const canvas = new OffscreenCanvas(frame.displayWidth, frame.displayHeight);
  const ctx = canvas.getContext('2d');

  ctx.drawImage(frame, 0, 0);
  ctx.font = '48px sans-serif';
  ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
  ctx.fillText('CONFIDENTIAL', 50, 100);

  // 2. 转回 VideoFrame
  const watermarkedFrame = new VideoFrame(canvas, {
    timestamp: frame.timestamp,
    duration: frame.duration || 33_333,
  });

  // 3. 发回主线程或送编码器
  self.postMessage({ frame: watermarkedFrame }, [watermarkedFrame]);

  frame.close();
};
```

### 16.5 AI 滤镜（WebGPU + WebCodecs）

```js
async function applyAISuperResolution(decoder, encoder, wasmModule) {
  decoder.output = async (frame) => {
    // 1. 视频帧 → WebGPU 纹理（零拷贝）
    const src = device.importExternalTexture({ source: frame });

    // 2. AI 超分（WebGPU compute shader）
    const cmd = device.createCommandEncoder();
    const pass = cmd.beginComputePass();
    pass.setPipeline(superResPipeline);
    pass.setBindGroup(0, bgWith(src));
    pass.dispatchWorkgroups(1920 / 8, 1080 / 8);  // 8x8 tiles
    pass.end();
    device.queue.submit([cmd.finish()]);

    // 3. 读回纹理到 canvas（临时方案，等待 GPU 纹理 → VideoFrame 标准化）
    await readTextureToCanvas(superResTexture);

    // 4. canvas → VideoFrame → 编码
    const outFrame = new VideoFrame(canvas, {
      timestamp: frame.timestamp,
      duration: frame.duration,
    });
    encoder.encode(outFrame);
    outFrame.close();
    frame.close();
  };
}
```

---

## 十七、浏览器兼容性与能力探测

### 17.1 当前支持

| 浏览器 | VideoCodecs | AudioCodecs | ImageDecoder | 外部纹理 |
|--------|-------------|-------------|--------------|----------|
| Chrome / Edge 94+ | ✅ | ✅ | ✅ | ✅ 114+ |
| Firefox 130+ | ✅ | ✅ | ✅ | ⚠️ 实验 |
| Safari 16.4+ | ✅ | ✅ | ✅ | ⚠️ 实验 |

### 17.2 能力探测

```js
async function probeCapabilities() {
  const probes = [
    { codec: 'avc1.640028', type: 'video', label: 'H.264 High 4.2' },
    { codec: 'avc1.42E01E', type: 'video', label: 'H.264 Baseline 3.0' },
    { codec: 'hev1.1.6.L93.B0', type: 'video', label: 'H.265 Main' },
    { codec: 'vp09.00.10.08', type: 'video', label: 'VP9' },
    { codec: 'av01.0.04M.08', type: 'video', label: 'AV1' },
    { codec: 'mp4a.40.2', type: 'audio', label: 'AAC LC' },
    { codec: 'opus', type: 'audio', label: 'Opus' },
  ];

  const results = await Promise.all(probes.map(async (p) => {
    try {
      const support = await (p.type === 'video'
        ? VideoDecoder.isConfigSupported({ codec: p.codec })
        : AudioDecoder.isConfigSupported({ codec: p.codec }));

      return { ...p, supported: support.supported };
    } catch {
      return { ...p, supported: false };
    }
  }));

  return results;
}
```

### 17.3 降级策略

```js
async function createBestDecoder() {
  const hierarchy = [
    { codec: 'avc1.640028', description: spsPps },  // H.264 优先
    { codec: 'vp09.00.10.08' },                       // VP9 次选
    { codec: 'av01.0.04M.08' },                       // AV1 最后
  ];

  for (const config of hierarchy) {
    const support = await VideoDecoder.isConfigSupported(config);
    if (support.supported) {
      const decoder = new VideoDecoder({ output, error });
      decoder.configure(support.config);
      return decoder;
    }
  }

  // 全部不支持，降级到 <video>
  return null;
}
```

### 17.4 运行时特性检测

```js
const features = {
  webCodecs: 'VideoDecoder' in self,
  webGPU: 'gpu' in navigator,
  webTransport: 'WebTransport' in self,
  externalTexture: 'GPUExternalTexture' in self,
  hardwareAcceleration: 'VideoEncoder' in self,  // 编码器比解码器晚
};
```

---

## 附录 A：完整 API 速查表

| API | 类型 | 作用 |
|-----|------|------|
| `VideoFrame` | 类 | 未压缩视频帧 |
| `AudioData` | 类 | 未压缩音频 PCM |
| `EncodedVideoChunk` | 类 | 压缩视频包 |
| `EncodedAudioChunk` | 类 | 压缩音频包 |
| `VideoColorSpace` | 类 | 色彩空间元数据 |
| `VideoFrameMetadata` | 类型 | RTP/HDR 元数据 |
| `VideoDecoder` | 类 | 视频解码器 |
| `VideoEncoder` | 类 | 视频编码器 |
| `AudioDecoder` | 类 | 音频解码器 |
| `AudioEncoder` | 类 | 音频编码器 |
| `ImageDecoder` | 类 | 图片解码器 |
| `ImageTrackList` | 类 | 动图轨道列表 |
| `ImageDecodeResult` | 类型 | 解码结果（{image, complete}）|
| `EncodedTransformStream` | 类 | WebCodecs 的 Streams 包装 |
| `VideoDecoderStream` | 类 | 解码 Streams |
| `VideoEncoderStream` | 类 | 编码 Streams |

## 附录 B：常见坑

1. **忘记 close() VideoFrame** → 内存泄漏
2. **VideoFrame 在异步回调中 close** → GPU 仍在采样导致画面撕裂
3. **不在 Worker 中解码** → 主线程卡顿
4. **H.264/H.265 不传 description** → 解码器找不到 SPS/PPS
5. **flush 后立即 close** → flush 是 Promise，要 await
6. **混淆 DTS 和 PTS** → B 帧流画面顺序错乱
7. **色彩空间不匹配** → 画面发灰或过饱和
8. **WebCodecs 编 WebCodecs 编 WebCodecs 循环引用** → 内存泄漏
9. **HDR 视频用 sRGB 输出** → 高光细节丢失
10. **在不支持的浏览器没降级** → 完全无法播放

## 附录 C：参考资源

- [W3C WebCodecs 规范](https://www.w3.org/TR/webcodecs/)
- [MDN - WebCodecs API](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API)
- [Chrome for Developers - WebCodecs](https://developer.chrome.com/docs/web-platform/video-codecs)
- [WebCodecs 示例集合](https://webcodecs.dev/)
- [W3C WebCodecs Use Cases](https://www.w3.org/TR/webcodecs-use-cases/)

---

*文档版本：2026-08-27*
*适用于 W3C WebCodecs Candidate Recommendation 及之后的浏览器实现*