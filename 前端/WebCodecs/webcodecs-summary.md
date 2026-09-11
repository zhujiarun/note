# WebCodecs API 规范总结

> 来源：<https://w3c.github.io/webcodecs/>
> 版本：Editor's Draft, 27 August 2026
> 组织：W3C Media Working Group
> 编辑：Paul Adenot（Mozilla）、Eugene Zemtsov（Google LLC）

## 1. 概述

WebCodecs 规范定义了一组用于在 Web 平台上对音频、视频、图像进行**编解码**的 JavaScript 接口。该规范本身不规定或要求任何具体的编解码器或编解码方法，目的是为已有的编解码技术实现提供 JS 接口。实现方可以自由支持任意编解码器组合，也可以完全不支持。

**核心价值**：暴露底层编解码能力（硬件加速可访问），使 Web 应用可以构建自定义的容器、协议、传输、流媒体、实时音视频等场景，而不必依赖 `<video>`/`<audio>` 标签这一层封装。

**已对接的实际编解码器（由注册表 [WEBCODECS-CODEC-REGISTRY] 定义）**：AV1、AVC（H.264）、FLAC、HEVC（H.265）、MP3、Opus、PCM、VP9 等。

**已对接的图像格式**：AVIF、BMP、GIF、ICO、JPEG、PNG、WebP。

---

## 2. 文档结构

规范分为 15 章：

| 章节 | 主题 |
| --- | --- |
| 1 | Definitions（术语） |
| 2 | Codec Processing Model（编解码处理模型） |
| 3 | AudioDecoder Interface |
| 4 | VideoDecoder Interface |
| 5 | AudioEncoder Interface |
| 6 | VideoEncoder Interface |
| 7 | Configurations（配置字典与能力探测） |
| 8 | Encoded Media Interfaces（Chunks） |
| 9 | Raw Media Interfaces（AudioData / VideoFrame / ColorSpace） |
| 10 | Image Decoding |
| 11 | Resource Reclamation（资源回收） |
| 12 | Security Considerations |
| 13 | Privacy Considerations |
| 14 | Best Practices for Authors Using WebCodecs |
| 15 | Acknowledgements |

---

## 3. 编解码处理模型（Codec Processing Model）

所有四种 Codec（AudioDecoder / VideoDecoder / AudioEncoder / VideoEncoder）都遵循同样的处理模型。

### 3.1 核心机制

- **控制消息队列（control message queue）**：每个 codec 实例内部都有一个 `[[control message queue]]`。每次调用 codec 方法（如 `encode()`）时，会把一个控制消息加入该队列。
- **并行工作队列（codec work queue）**：每个 codec 实例拥有一个 `[[codec work queue]]` 平行队列和 `[[codec implementation]]` 内部槽位，引用底层平台编解码器。涉及底层编解码器的步骤会被入队到该工作队列异步执行。
- **任务源（codec task source）**：每个 codec 实例具有唯一的 codec task source，从工作队列派发到事件循环的任务都使用该 task source。
- **阻塞机制**：每个 codec 实例有一个布尔内部槽 `[[message queue blocked]]`，某些控制消息可能在执行过程中把后续消息阻塞。阻塞消息结束后置回 `false` 并重启消息队列处理。

### 3.2 关键含义

作者可以连续发起 `decode()` 而不必等待上一次完成，旧任务完成后输出回调照常触发。这就是 WebCodecs 相比传统同步 API 能实现流水线（pipeline）并发的根源。

---

## 4. 编解码器接口（Decoder / Encoder）

四种 codec 拥有相同的接口骨架（皆为 `EventTarget` 子类，可在 `Window` 和 `DedicatedWorker` 中使用，且要求 `SecureContext`）：

```idl
interface AudioDecoder : EventTarget {
  constructor(AudioDecoderInit init);
  readonly attribute CodecState state;
  readonly attribute unsigned long decodeQueueSize;
  attribute EventHandler ondequeue;
  undefined configure(AudioDecoderConfig config);
  undefined decode(EncodedAudioChunk chunk);
  Promise<undefined> flush();
  undefined reset();
  undefined close();
  static Promise<AudioDecoderSupport> isConfigSupported(AudioDecoderConfig config);
};

interface VideoDecoder : EventTarget {
  // 同上，但 decode 接收 EncodedVideoChunk，输出 VideoFrame
};

interface AudioEncoder : EventTarget {
  // encode(AudioData data)，输出 EncodedAudioChunk
};

interface VideoEncoder : EventTarget {
  // encode(VideoFrame frame, optional VideoEncoderEncodeOptions options = {})
};
```

### 4.1 公共属性

| 属性 | 类型 | 含义 |
| --- | --- | --- |
| `state` | `CodecState` | `"unconfigured"` / `"configured"` / `"closed"` |
| `decodeQueueSize` / `encodeQueueSize` | `unsigned long` | 当前待处理任务数 |
| `ondequeue` | `EventHandler` | 队列减少时触发 |

### 4.2 公共方法

| 方法 | 行为 |
| --- | --- |
| `configure(config)` | 设置编解码配置，状态变为 `configured` |
| `decode(chunk)` / `encode(data)` | 入队一个 chunk 进行处理 |
| `flush()` | 返回 `Promise<undefined>`，所有已入队任务处理完后 resolve |
| `reset()` | 丢弃队列中的所有任务，状态仍保持 `configured` |
| `close()` | 释放底层资源，状态变为 `closed` |
| 静态 `isConfigSupported(config)` | 探测当前 UA 是否支持该配置，返回 `Promise<{supported, config}>` |

### 4.3 回调字典

```idl
dictionary AudioDecoderInit  { required AudioDataOutputCallback output; required WebCodecsErrorCallback error; };
dictionary VideoDecoderInit   { required VideoFrameOutputCallback output; required WebCodecsErrorCallback error; };
dictionary AudioEncoderInit { required EncodedAudioChunkOutputCallback output; required WebCodecsErrorCallback error; };
dictionary VideoEncoderInit { required EncodedVideoChunkOutputCallback output; required WebCodecsErrorCallback error; };

callback WebCodecsErrorCallback = undefined(DOMException error);
```

输出回调在 `output()` 中获取解码结果（`AudioData`/`VideoFrame`/`EncodedAudioChunk`/`EncodedVideoChunk`），第二可选参数 `metadata`（仅编码器）携带 decoderConfig / svc / alphaSideData。

---

## 5. 配置（Configurations）

### 5.1 通用约定

- 所有配置字典通过 `Is Config Supported(config)` 和 `Clone Config(config)` 两个标准算法操作。
- 探测支持：`AudioDecoder.isConfigSupported(cfg)` 返回 `{supported: boolean, config}`。
- `codec` 字符串遵循 [RFC6381] 的 codec-specific 格式，具体由 [WEBCODECS-CODEC-REGISTRY] 注册表定义。
- 编码器配置允许扩展 codec 私有字段（注册表定义）。

### 5.2 AudioDecoderConfig

```idl
dictionary AudioDecoderConfig {
  required DOMString codec;
  required unsigned long sampleRate;
  required unsigned long numberOfChannels;
  AllowSharedBufferSource description;  // codec-specific extradata
};
```

### 5.3 VideoDecoderConfig

```idl
dictionary VideoDecoderConfig {
  required DOMString codec;
  AllowSharedBufferSource description;
  unsigned long codedWidth;
  unsigned long codedHeight;
  unsigned long displayAspectWidth;
  unsigned long displayAspectHeight;
  VideoColorSpaceInit colorSpace;
  HardwareAcceleration hardwareAcceleration = "no-preference";
  boolean optimizeForLatency;
  double rotation = 0;
  boolean flip = false;
};
```

要点：`codedWidth/Height` 用于选择底层实现；`displayAspectWidth/Height` 提供显示宽高比；`colorSpace` 可覆盖码流内嵌的颜色元数据。

### 5.4 AudioEncoderConfig

```idl
dictionary AudioEncoderConfig {
  required DOMString codec;
  required unsigned long sampleRate;
  required unsigned long numberOfChannels;
  unsigned long long bitrate;
  BitrateMode bitrateMode = "variable";
};
```

`BitrateMode` 定义在 [MEDIASTREAM-RECORDING]，包含 `constant` / `variable`。

### 5.5 VideoEncoderConfig

```idl
dictionary VideoEncoderConfig {
  required DOMString codec;
  required unsigned long width;
  required unsigned long height;
  unsigned long displayWidth;
  unsigned long displayHeight;
  unsigned long long bitrate;
  double framerate;
  HardwareAcceleration hardwareAcceleration = "no-preference";
  AlphaOption alpha = "discard";
  DOMString scalabilityMode;
  VideoEncoderBitrateMode bitrateMode = "variable";
  LatencyMode latencyMode = "quality";
  DOMString contentHint;
};
```

要点：同时提供 `width/height`（编码尺寸）和 `displayWidth/Height`（显示尺寸，可带非方形像素）；`framerate` 是码率控制的关键输入；`bitrateMode` 支持 `"constant"` / `"variable"` / `"quantizer"`（量化模式在每帧 `VideoEncoderEncodeOptions` 中指定）。

### 5.6 通用枚举

```idl
enum HardwareAcceleration { "no-preference", "prefer-hardware", "prefer-software" };
enum AlphaOption          { "keep", "discard" };
enum LatencyMode          { "quality", "realtime" };
enum VideoEncoderBitrateMode { "constant", "variable", "quantizer" };
enum CodecState           { "unconfigured", "configured", "closed" };
```

- **HardwareAcceleration**：仅作为 hint，UA 可忽略。为防止指纹化，UA 应在支持 media-capabilities 时保证该 hint 不暴露额外信息。
- **LatencyMode**：realtime 模式可丢帧以达成目标码率/帧率，并把 framerate 作为输出截止时间；quality 模式不丢帧且不把 framerate 视作截止时间。
- **Configuration Equivalence**：用于判断两个配置是否等效，影响 codec 复用等行为。

### 5.7 VideoEncoderEncodeOptions

```idl
dictionary VideoEncoderEncodeOptions { boolean keyFrame = false; };
```

`keyFrame=true` 强制当前帧为关键帧；扩展字段由 codec 注册表定义。

---

## 6. 已编码媒体接口（Chunks）

### 6.1 EncodedAudioChunk

```idl
[Exposed=(Window, DedicatedWorker), Serializable]
interface EncodedAudioChunk {
  constructor(EncodedAudioChunkInit init);
  readonly attribute EncodedAudioChunkType type;        // "key" | "delta"
  readonly attribute long long timestamp;              // 微秒
  readonly attribute unsigned long long? duration;     // 微秒
  readonly attribute unsigned long byteLength;
  undefined copyTo(AllowSharedBufferSource destination);
};

dictionary EncodedAudioChunkInit {
  required EncodedAudioChunkType type;
  required long long timestamp;            // 微秒
  unsigned long long duration;              // 微秒
  required AllowSharedBufferSource data;
  sequence<ArrayBuffer> transfer = [];
};
```

### 6.2 EncodedVideoChunk

```idl
[Exposed=(Window, DedicatedWorker), Serializable]
interface EncodedVideoChunk {
  constructor(EncodedVideoChunkInit init);
  readonly attribute EncodedVideoChunkType type;
  readonly attribute long long timestamp;
  readonly attribute unsigned long long? duration;
  readonly attribute unsigned long byteLength;
  undefined copyTo(AllowSharedBufferSource destination);
};
```

要点：chunk 是 `Serializable` 但不可 `Transferable`；`copyTo` 用于把数据拷到目标 buffer（常用于提交到 Worker 或流回主线程时复制以脱离结构化克隆）；`EncodedVideoChunkType` 仅 `key` / `delta`。

### 6.3 编码器输出元数据

```idl
dictionary EncodedAudioChunkMetadata { AudioDecoderConfig decoderConfig; };
dictionary EncodedVideoChunkMetadata {
  VideoDecoderConfig decoderConfig;
  SvcOutputMetadata svc;
  BufferSource alphaSideData;
};
dictionary SvcOutputMetadata { unsigned long temporalLayerId; };
```

当编码器在码流中插入新的 SPS/PPS（视频）或 AudioSpecificConfig（音频）等私有头时，会通过 metadata 回调让客户端把新配置送给解码器。

---

## 7. 原始媒体接口（Raw Media）

### 7.1 内存模型

为减少昂贵拷贝，原始媒体资源采用**引用计数**机制：

- `clone()`：复制一份新引用，二者独立。
- `close()`：立即释放。文档强烈建议作者在使用完毕后立刻 `close()`。
- 通过 `postMessage` / `structuredClone` 可**转移**或**序列化**，转移后原对象不再可用。

### 7.2 AudioData

```idl
[Exposed=(Window, DedicatedWorker), Serializable, Transferable]
interface AudioData {
  constructor(AudioDataInit init);
  readonly attribute AudioSampleFormat? format;            // u8|s16|s32|f32|u8-planar|s16-planar|s32-planar|f32-planar
  readonly attribute float sampleRate;
  readonly attribute unsigned long numberOfFrames;
  readonly attribute unsigned long numberOfChannels;
  readonly attribute unsigned long long duration;         // 微秒
  readonly attribute long long timestamp;                 // 微秒
  unsigned long allocationSize(AudioDataCopyToOptions options);
  undefined copyTo(AllowSharedBufferSource destination, AudioDataCopyToOptions options);
  AudioData clone();
  undefined close();
};

dictionary AudioDataCopyToOptions {
  required unsigned long planeIndex;
  unsigned long frameOffset = 0;
  unsigned long frameCount;
  AudioSampleFormat format;
};
```

**音频采样格式**：交错（interleaved）和平面（planar）两种布局都覆盖 8-bit 无符号、s16、s32、f32 四种位宽。

### 7.3 VideoFrame

```idl
[Exposed=(Window, DedicatedWorker), Serializable, Transferable]
interface VideoFrame {
  constructor(CanvasImageSource image, optional VideoFrameInit init = {});
  constructor(AllowSharedBufferSource data, VideoFrameBufferInit init);

  readonly attribute VideoPixelFormat? format;
  readonly attribute unsigned long codedWidth;
  readonly attribute unsigned long codedHeight;
  readonly attribute DOMRectReadOnly? codedRect;
  readonly attribute DOMRectReadOnly? visibleRect;
  readonly attribute double rotation;
  readonly attribute boolean flip;
  readonly attribute unsigned long displayWidth;
  readonly attribute unsigned long displayHeight;
  readonly attribute unsigned long long? duration;        // 微秒
  readonly attribute long long timestamp;                 // 微秒
  readonly attribute VideoColorSpace colorSpace;
  VideoFrameMetadata metadata();
  unsigned long allocationSize(optional VideoFrameCopyToOptions options = {});
  Promise<sequence<PlaneLayout>> copyTo(
    AllowSharedBufferSource destination,
    optional VideoFrameCopyToOptions options = {});
  VideoFrame clone();
  undefined close();
};
```

**VideoFrameCopyToOptions**：

```idl
dictionary VideoFrameCopyToOptions {
  DOMRectInit rect;
  sequence<PlaneLayout> layout;
  VideoPixelFormat format;
  PredefinedColorSpace colorSpace;
};
dictionary PlaneLayout { required unsigned long offset; required unsigned long stride; };
```

**VideoPixelFormat**（YUV 子采样与位深）：

- 4:2:0 Y/U/V：`I420`、`I420P10`、`I420P12`
- 4:2:0 含 A：`I420A`、`I420AP10`、`I420AP12`
- 4:2:2 Y/U/V：`I422`、`I422P10`、`I422P12`；含 A：`I422A`、`I422AP10`、`I422AP12`
- 4:4:4 Y/U/V：`I444`、`I444P10`、`I444P12`；含 A：`I444A`、`I444AP10`、`I444AP12`
- 4:2:0 Y/UV 半平面：`NV12`
- 4:4:4 RGB/X：`RGBA`、`RGBX`、`BGRA`、`BGRX`

**VideoFrame 渲染**：可以从 HTMLVideoElement / HTMLCanvasElement / OffscreenCanvas / ImageBitmap / VideoFrame 构造，并可绘制回 2D canvas、`createImageBitmap`、WebGL/WebGPU `texImage2D` / `copyExternalImageToTexture` 等。

### 7.4 VideoColorSpace

```idl
[Exposed=(Window, DedicatedWorker)]
interface VideoColorSpace {
  constructor(optional VideoColorSpaceInit init = {});
  readonly attribute VideoColorPrimaries? primaries;
  readonly attribute VideoTransferCharacteristics? transfer;
  readonly attribute VideoMatrixCoefficients? matrix;
  readonly attribute boolean? fullRange;
  [Default] VideoColorSpaceInit toJSON();
};

enum VideoColorPrimaries         { "bt709", "bt470bg", "smpte170m", "bt2020", "smpte432" };
enum VideoTransferCharacteristics { "bt709", "smpte170m", "iec61966-2-1", "linear", "pq", "hlg" };
enum VideoMatrixCoefficients     { "rgb", "bt709", "bt470bg", "smpte170m", "bt2020-ncl" };
```

支持 BT.709、BT.470BG、SMPTE170M、BT.2020、SMPTE432（P3）等色彩原色；传输特性覆盖 SDR、HDR（PQ / HLG）、线性、sRGB。

---

## 8. 图像解码（Image Decoding）

为完整覆盖图像加载场景，规范引入一个并行于 `createImageBitmap` 的 `ImageDecoder`。

```idl
[Exposed=(Window, DedicatedWorker), SecureContext]
interface ImageDecoder {
  constructor(ImageDecoderInit init);
  readonly attribute DOMString type;
  readonly attribute boolean complete;
  readonly attribute Promise<undefined> completed;
  readonly attribute ImageTrackList tracks;
  Promise<ImageDecodeResult> decode(optional ImageDecodeOptions options = {});
  undefined reset();
  undefined close();
  static Promise<boolean> isTypeSupported(DOMString type);
};

typedef (AllowSharedBufferSource or ReadableStream) ImageBufferSource;
dictionary ImageDecoderInit {
  required DOMString type;
  required ImageBufferSource data;
  ColorSpaceConversion colorSpaceConversion = "default";
  unsigned long desiredWidth;
  unsigned long desiredHeight;
  boolean preferAnimation;
  sequence<ArrayBuffer> transfer = [];
};
dictionary ImageDecodeOptions  { unsigned long frameIndex = 0; boolean completeFramesOnly = true; };
dictionary ImageDecodeResult   { required VideoFrame image; required boolean complete; };
```

**ImageTrackList / ImageTrack**：处理动图（GIF/WebP/AVIF）时，`tracks` 提供图像轨道列表，`selectedIndex`/`selectedTrack` 可选择当前轨道，`ImageTrack` 暴露 `animated`、`frameCount`、`repetitionCount`、`selected` 属性。

**渐进式图像**：原生支持 progressive image，输出 `VideoFrame` 时带有 generation 标识，连续解码会逐代补全细节。

---

## 9. 资源回收（Resource Reclamation）

硬件编解码器数量有限，UA 可能在系统资源紧张时主动回收 codec。

- **回收方式**：调用相应的 close 算法并抛出 `QuotaExceededError` 错误。
- **active codec**：过去 10 秒内 `[[codec work queue]]` 有进展的 codec（典型信号是 `output()` 回调被调用过）。
- **inactive codec**：不满足 active 条件的 codec。
- **background codec**：所属 Document（包括 worker 中的 owner set）的 `hidden` 为 true。
- **回收规则**：
  - UA 只能回收 inactive 或 background（或二者兼具）的 codec。
  - 不得回收「active 且 in foreground」的 codec。
  - 不得回收「active 且 background」的 codec——这是为了避免后台活跃任务被中断丢帧。

---

## 10. 安全与隐私考虑

- **安全上下文**：所有 Codec 接口、`ImageDecoder`、`ImageTrackList`、`ImageTrack` 都标注 `[SecureContext]`，仅在 HTTPS / localhost 等安全上下文可用。
- **跨线程支持**：所有 Codec 与 Chunks、AudioData、VideoFrame 都可在 `Window` 和 `DedicatedWorker` 中使用。
- **指纹化**：HardwareAcceleration hint 不能泄露超出 [media-capabilities] 已暴露的信息。
- **内存压力**：原始媒体可能占用大量内存，建议尽快 `close()`。

---

## 11. 典型使用模式（基于规范推导）

### 11.1 解码 H.264 视频流

```js
const decoder = new VideoDecoder({
  output: (frame) => {
    // 渲染 / 上传 GPU / 持久化
    frame.close();
  },
  error: (e) => console.error(e),
});

decoder.configure({
  codec: 'avc1.42E01E',     // H.264 Baseline Level 3.0
  codedWidth: 1280,
  codedHeight: 720,
  hardwareAcceleration: 'prefer-hardware',
});

// 由外部解封装器产出 EncodedVideoChunk（来自 FLV、MP4、MSE 自定义容器等）
const chunk = new EncodedVideoChunk({
  type: frame.isKeyframe ? 'key' : 'delta',
  timestamp: frame.ptsUs,
  duration: frame.durationUs,
  data: frame.data,
});
decoder.decode(chunk);
await decoder.flush();
decoder.close();
```

### 11.2 编码视频帧

```js
const encoder = new VideoEncoder({
  output: (chunk, meta) => {
    // meta.decoderConfig 在 SPS/PPS 更新时出现，需随 chunk 一起送给远端
    sendToPeer(chunk, meta);
  },
  error: (e) => console.error(e),
});

encoder.configure({
  codec: 'avc1.42E01F',
  width: 1280,
  height: 720,
  bitrate: 2_000_000,
  framerate: 30,
  latencyMode: 'realtime',
});

// 输入 VideoFrame（来自 canvas / camera / WebGPU 输出）
encoder.encode(videoFrame, { keyFrame: true });
```

### 11.3 探测能力

```js
const { supported, config } = await VideoEncoder.isConfigSupported({
  codec: 'avc1.42E01F',
  width: 1920,
  height: 1080,
  bitrate: 5_000_000,
  framerate: 60,
});
if (supported) {
  encoder.configure(config);
}
```

### 11.4 解码动画 PNG（带多帧）

```js
const decoder = new ImageDecoder({
  type: 'image/png',
  data: pngBuffer,
  preferAnimation: true,
});
const { image, complete } = await decoder.decode({ frameIndex: 0 });
```

---

## 12. 与典型 FLV/WebCodecs 播放栈的对接点

- **解封装**：FLV 自研解封装器输出 `EncodedVideoChunk`（H.264/H.265）+ `EncodedAudioChunk`（AAC）。
- **解码**：分别喂给 `VideoDecoder` / `AudioDecoder`，回调产出 `VideoFrame` / `AudioData`。
- **渲染**：`VideoFrame` 可上传到 WebGPU 纹理（`copyExternalImageToTexture`），`AudioData` 可送入 WebAudio 处理或自行调度 PCM 播放。
- **时间戳**：chunk 与 frame 都使用**微秒**为单位的 `timestamp`，与 FLV 的毫秒时间戳需要 `×1000` 转换。

---

## 13. 参考链接

- 规范首页：<https://w3c.github.io/webcodecs/>
- 最新发布版：<https://www.w3.org/TR/webcodecs/>
- 编解码注册表：<https://w3c.github.io/webcodecs-codec-registry/>
- GitHub 仓库：<https://github.com/w3c/webcodecs/>
- Media Capabilities：<https://www.w3.org/TR/media-capabilities/>
- MediaStream Recording（BitrateMode）：<https://www.w3.org/TR/mediastream-recording/>
- WebRTC SVC（scalabilityMode）：<https://www.w3.org/TR/webrtc-svc/>