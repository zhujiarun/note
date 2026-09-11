# WebCodecs API 与 WebGPU 纹理互操作详解

> 基于浏览器原生 WebCodecs 与 WebGPU 的现代 Web 视频处理技术总结
> 涵盖 WebCodecs 核心概念、解码/编码接口，以及 VideoFrame 与 GPU 纹理的零拷贝互操作方案

---

## 一、WebCodecs 概述

WebCodecs 是 W3C 制定的浏览器底层编解码 API，给 Web 应用提供对**视频帧**和**音频帧**的细粒度访问能力。它是现代 Web 视频处理（视频编辑、低延迟直播、WebCodecs + WebGPU/WebAssembly 等场景）的核心基础设施。

### 1.1 定位

在 WebCodecs 出现之前，浏览器里"解码"和"编码"都被 `<video>`、`<canvas>`、MediaRecorder 等高层 API 包装起来，开发者拿不到原始帧数据。WebCodecs 把这些能力直接暴露给 JavaScript：

- **VideoDecoder / VideoEncoder**：处理 H.264、H.265、VP8/VP9、AV1 等视频帧
- **AudioDecoder / AudioEncoder**：处理 AAC、Opus、MP3、FLAC 等音频帧
- **VideoFrame / AudioData**：编解码后的原始���对象，可以零拷贝送进 Canvas、WebGL、WebGPU、WASM
- **ImageDecoder**：静态图片（JPEG、PNG、WebP、AVIF、GIF、BMP）的解码

### 1.2 与传统方案的对比

| 能力 | `<video>` + MSE | WebCodecs |
|------|-----------------|-----------|
| 帧级访问 | ✗ | ✓ |
| 自定义解码 | ✗ | ✓（搭配 WASM） |
| 自定义编码 | ✗（仅 MediaRecorder） | ✓ |
| 容器格式限制 | 必须主流容器 | 任意（自己解封装） |
| 延迟 | 较高（至少 1-2 段 buffer） | 可低至单帧 |
| WebGPU 集成 | 需经 Canvas 中转 | 几乎零拷贝 |
| 易用性 | 高 | 中（需要自己处理时间戳、PTS/DTS） |

---

## 二、核心对象

### 2.1 VideoFrame

视频解码后的原始帧，是 WebCodecs 与渲染管线之间的桥梁。

```js
const frame = new VideoFrame(buffer, {
  codedWidth: 1920,
  codedHeight: 1080,
  timestamp: 0,           // 微秒
  format: 'I420',         // 或 'I420A'、'NV12'、'RGBA' 等
});
```

**关键属性：**
- `codedWidth / codedHeight`：原始尺寸
- `displayWidth / displayHeight`：显示尺寸（可与原始不同，处理旋转、黑边）
- `timestamp`：PTS（微秒）
- `duration`：时长（微秒）
- `format`：色彩格式（`I420`、`I420A`、`NV12`、`RGBA`、`BGRA`、`RGBA10A2` 等）

**渲染方法：**
- `frame.draw(canvas)`：直接画到 `<canvas>` / OffscreenCanvas
- `frame.createImageBitmap()`：转成 ImageBitmap 供 WebGL/WebGPU/WASM 使用

**资源管理：** `frame.close()` 释放底层 GPU/内存资源，**未 close 会泄漏**。

### 2.2 AudioData

音频 PCM 数据，类似 VideoFrame 但面向采样点：

```js
const audio = new AudioData({
  format: 'f32-planar',    // 's16'、's32'、'f32'、'f32-planar' 等
  sampleRate: 48000,
  numberOfFrames: 1024,
  numberOfChannels: 2,
  timestamp: 0,
  data: buffer,
});
```

### 2.3 EncodedVideoChunk / EncodedAudioChunk

送进解码器的压缩数据：

```js
const chunk = new EncodedVideoChunk({
  type: 'key',            // 'key'、'delta'
  timestamp: 0,
  duration: 33_000,       // 微秒
  data: annexBBuffer,
});
```

---

## 三、解码器 VideoDecoder / AudioDecoder

### 3.1 工作模式

解码器是**异步**的，使用"配置 → 喂数据 → 回调输出"的模式：

```js
const decoder = new VideoDecoder({
  output: (frame) => {
    // frame: VideoFrame
    ctx.drawImage(frame, 0, 0);   // 渲染
    frame.close();
  },
  error: (e) => console.error(e),
});

decoder.configure({
  codec: 'avc1.640028',       // H.264 High@4.2
  codedWidth: 1920,
  codedHeight: 1080,
  description: sps,            // 视频参数集（可选）
  hardwareAcceleration: 'prefer-hardware',  // 'no-preference' / 'prefer-hardware' / 'prefer-software'
  optimizeForLatency: true,
});

// 喂数据
decoder.decode(chunk);

// 提示解码器：后面没有更多数据了
decoder.flush().then(() => decoder.close());
```

### 3.2 关键方法

- `configure(desc)`：初始化，需要 `codec`、`codedWidth`、`codedHeight`，H.264/H.265 通常还要传 SPS/PPS
- `decode(chunk)`：送入一个压缩包，内部排队执行
- `flush()`：返回 Promise，等待所有排队的 chunk 解码完成
- `close()`：释放解码器实例
- `reset()`：清空内部队列，丢弃未解码数据

### 3.3 状态与背压

- `decodeState`：`unconfigured` / `configured` / `closed`
- `decodeQueueSize`：等待解码的 chunk 数量，用于背压控制

### 3.4 Codec 字符串

| 格式 | codec 字符串示例 |
|------|------------------|
| H.264 Baseline 3.1 | `avc1.42001f` |
| H.264 High 4.2 | `avc1.640028` |
| H.265 Main | `hev1.1.6.L93.B0` |
| VP9 | `vp09.00.10.08` |
| AV1 | `av01.0.04M.08` |

可以用 `VideoDecoder.isConfigSupported(config)` 检查浏览器是否支持某个配置。

---

## 四、编码器 VideoEncoder / AudioEncoder

接口形态与解码器对称：

```js
const encoder = new VideoEncoder({
  output: (chunk, meta) => {
    // chunk: EncodedVideoChunk
    // meta.decoderConfig.description: 提取出来的 SPS/PPS（视频）
    sendOverNetwork(chunk, meta);
  },
  error: (e) => console.error(e),
});

encoder.configure({
  codec: 'avc1.640028',
  width: 1280,
  height: 720,
  bitrate: 2_000_000,
  framerate: 30,
  avc: { format: 'avc' },  // 'avc'（带长度前缀）或 'annexb'
});

encoder.encode(frame); // VideoFrame → H.264
```

`VideoFrame` 的来源可以是：
- `<video>` 元素（通过 `new VideoFrame(videoElement)`）
- `<canvas>` / OffscreenCanvas（通过 `new VideoFrame(canvas)`）
- WebGPU 纹理（`videoFrameFromTexture`，实验性）
- 摄像头 / `ImageCapture`
- 自定义生成的图像数据

---

## 五、WebCodecs 与其它 Web API 的协同

### 5.1 WebCodecs + WebTransport

低延迟直播、远程游戏、实时协作的经典组合。`WebTransport` 提供基于 QUIC 的可靠/不可靠双向流。

### 5.2 WebCodecs + WebGPU / WebGL2

`VideoFrame` 可以零拷贝地转成 GPU 纹理，详见下文第六部分。

### 5.3 WebCodecs + Streams API

`EncodedTransformStream` 把 WebCodecs 包装成 Streams：

```js
const decoderStream = new VideoDecoderStream({
  codec: 'avc1.640028',
  output: (frame) => { /* ... */ },
});
```

### 5.4 WebCodecs + WebAssembly

WASM 模块（FFmpeg、libavcodec 自编译版等）可以处理 WebCodecs 暂不支持的格式。

### 5.5 WebCodecs + MediaSource / MSE

`VideoFrame` 可以喂给 `SourceBuffer`，相当于把解码结果重新组装回 `<video>`。

---

## 六、WebGPU 纹理互操作（核心）

### 6.1 为什么这条路径重要

传统链路是 **解码 → CPU 拷贝回内存 → 上传回 GPU**，每帧至少多一次 `texture → readPixels → buffer → GPU upload` 的往返，1080p 一帧就要搬运 6MB（RGBA），4K 帧更是高达 24MB。在 60fps 下这是不可承受的。

零拷贝的目标是：**解码器直接产出 GPU 纹理，渲染管线直接消费它**。

### 6.2 VideoFrame → GPU 纹理

#### 方案 A：importExternalTexture（官方推荐）

Chrome 114+ 起，`VideoFrame` 可以被当作**外部纹理**直接采样，**不创建新纹理、不拷贝数据**：

```js
// 每帧调用
const texture = device.importExternalTexture({
  source: videoFrame,   // VideoFrame
  colorSpace: 'srgb',   // 或 'display-p3'、'rec709' 等
});

// 直接在 shader 里采样
@group(0) @binding(0) var videoSampler: sampler;
@group(0) @binding(1) var videoTexture: texture_external;

@fragment
fn fs(@location(0) uv: vec2f) -> @location(0) vec4f {
  return textureSample(videoTexture, videoSampler, uv);
}
```

**要点：**
- `texture_external` 不是普通 `texture_2d<f32>`，是特殊的外部纹理类型
- 采样器必须用**普通 sampler**，不能用 comparison sampler
- 不支持 mipmap、不能写入、不能存储为附件
- 每帧的 `videoFrame` 必须 close，否则 GPU 资源会泄漏
- 视频色彩空间、YUV→RGB 的转换由 GPU 内部完成（基于 `colorSpace` 参数）

#### 方案 B：copyExternalTextureToTexture

如果要把视频帧"固定"到一张普通纹理上（比如做后处理后还要多 pass 读取）：

```js
const ext = device.importExternalTexture({ source: videoFrame });
const encoder = device.createCommandEncoder();
encoder.copyExternalTextureToTexture(
  { source: ext, origin: { x: 0, y: 0 } },
  { texture: gpuTexture },
  { width: videoFrame.displayWidth, height: videoFrame.displayHeight }
);
device.queue.submit([encoder.finish()]);
```

#### 方案 C：传统 fallback

```js
// VideoFrame → ImageBitmap → Canvas → GPU
const bitmap = await createImageBitmap(videoFrame);
const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
canvas.getContext('2d').drawImage(bitmap, 0, 0);

device.queue.copyExternalImageToTexture(
  { source: canvas },
  { texture: gpuTexture },
  { width: bitmap.width, height: bitmap.height }
);
```

### 6.3 GPU 纹理 → VideoFrame（编码场景）

```js
// 提议中的 API 形态
const frame = new VideoFrame(gpuTexture, {
  timestamp: pts,
  duration: frameDuration,
});
encoder.encode(frame);
```

**支持状况：**
- Chrome / Edge：实验性 flag，需开启 `chrome://flags/#enable-experimental-web-platform-features`
- 规范层面还在 WebCodecs WG 与 WebGPU WG 之间协调

**生产环境更稳妥的 fallback：**

```js
const frame = new VideoFrame(canvas, {
  timestamp: pts,
  duration: 33_000,
});
encoder.encode(frame);
frame.close();
```

`new VideoFrame(canvas)` 在 Chrome 里是零拷贝的（canvas 后端就是 GPU），性能接近直接互操作。

---

## 七、典型管线模式

### 7.1 模式 1：解码 → 渲染

```js
decoder.configure({ codec: 'avc1.640028', codedWidth: 1920, codedHeight: 1080 });

decoder = new VideoDecoder({
  output: (frame) => {
    const external = device.importExternalTexture({
      source: frame,
      colorSpace: 'srgb',
    });

    renderPass.setPipeline(decodePipeline);
    renderPass.setBindGroup(0, bindGroupWith(external));
    renderPass.draw(6);  // 全屏 quad
    frame.close();
  },
  error: (e) => console.error(e),
});
```

### 7.2 模式 2：解码 → 后处理 → 编码（实时转码）

```js
decoder.output = (frame) => {
  const src = device.importExternalTexture({ source: frame });

  // Compute pass 做超分 / 滤镜
  const cmd = device.createCommandEncoder();
  const pass = cmd.beginComputePass();
  pass.setPipeline(processPipeline);
  pass.setBindGroup(0, bgWith(src));
  pass.dispatchWorkgroups(/* ... */);
  pass.end();

  // 渲染到 canvas（用 canvas 当编码源）
  renderToCanvas(cmd, processPipeline);

  device.queue.submit([cmd.finish()]);

  // 编码
  const outFrame = new VideoFrame(canvas, { timestamp: frame.timestamp, duration: 33_000 });
  encoder.encode(outFrame);
  outFrame.close();
  frame.close();
};
```

### 7.3 模式 3：多流合成

```js
const frames = [mainFrame, pipFrame];

bg.setTexture(0, frames[0]);  // 通过 importExternalTexture 包装
bg.setTexture(1, frames[1]);

pass.setBindGroup(0, bg);
pass.draw(6);

frames.forEach(f => f.close());
```

---

## 八、性能注意事项

### 8.1 帧生命周期

```js
// 错误示范：frame 被 GPU 还在用就 close 了
decoder.output = (frame) => {
  const ext = importExternalTexture(frame);
  frame.close();           // ❌ 可能 GPU 还在采样
  drawSomething(ext);
};

// 正确：确保 GPU 命令提交后再 close
decoder.output = (frame) => {
  const ext = importExternalTexture(frame);
  drawSomething(ext);
  device.queue.submit([encoder.finish()]);
  frame.close();           // ✓ submit 之后 frame 引用就安全了
};
```

更严格的做法是配合 fence 或在 `queue.onSubmittedWorkDone()` 之后释放。

### 8.2 色彩空间

`VideoFrame` 默认是 Rec.709 / limited range，WebGPU 默认是 sRGB / full range。色彩不对会让画面发灰或过饱和。

```js
importExternalTexture({
  source: frame,
  colorSpace: 'display-p3',  // 或者 'rec709', 'srgb'
});
```

### 8.3 HDR / 宽色域

HDR `VideoFrame`（`transferCharacteristics: 'pq'` / `hlg`）需要：
- WebGPU 设备请求 `hdr` feature
- 输出纹理使用 `rgba16float` 或更宽格式
- shader 内部做 PQ/HLG → linear 的转换

### 8.4 帧率匹配

WebGPU 的 present 节奏要跟解码节奏对齐，否则会出现画面卡顿或撕裂：

```js
let targetPts = 0;
const frameDuration = 33_333; // 30fps

decoder.output = (frame) => {
  if (frame.timestamp >= targetPts) {
    renderFrame(frame);
    targetPts += frameDuration;
  }
  frame.close();
};
```

### 8.5 背压控制

```js
if (decoder.decodeQueueSize > 10) {
  pauseFeed();              // 暂停推 chunk
}
// 在 render loop 完成后
decoder.output = (frame) => {
  renderFrame(frame);
  frame.close();
  decoder.decodeQueueSize;  // 看是否降下来，再恢复推流
};
```

---

## 九、与 WebGL2 的对比

| 维度 | WebGL2 + VideoFrame | WebGPU + 外部纹理 |
|------|---------------------|--------------------|
| 零拷贝 | ❌（需 texImage2D 上传） | ✓ |
| API 复杂度 | 中 | 较高 |
| 计算着色器 | ✗ | ✓ |
| 多 pass 管线 | 受限 | 灵活 |
| 浏览器支持 | 几乎全部 | 较新（Chrome 113+ 稳定，Safari 17+） |

---

## 十、最小实战代码

### 10.1 编解码往返

```js
// 1) 构造一个 I420 帧
const frame = new VideoFrame(
  new Uint8Array(1920 * 1080 * 1.5),
  { codedWidth: 1920, codedHeight: 1080, format: 'I420', timestamp: 0 }
);

// 2) 编码成 H.264
const chunks = [];
const encoder = new VideoEncoder({
  output: (chunk) => chunks.push(chunk),
  error: (e) => console.error(e),
});
encoder.configure({ codec: 'avc1.640028', width: 1920, height: 1080, bitrate: 1_500_000 });
encoder.encode(frame);
encoder.flush().then(() => {
  encoder.close();
  frame.close();
  console.log('encoded', chunks.length, 'chunks');
});

// 3) 解码回来
const decoder = new VideoDecoder({
  output: (decoded) => {
    ctx.drawImage(decoded, 0, 0);
    decoded.close();
  },
  error: (e) => console.error(e),
});
decoder.configure({ codec: 'avc1.640028', codedWidth: 1920, codedHeight: 1080 });
chunks.forEach((c) => decoder.decode(c));
decoder.flush().then(() => decoder.close());
```

### 10.2 WebCodecs + WebGPU 零拷贝渲染

```js
// 初始化
const device = await navigator.gpu.requestAdapter().then(a => a.requestDevice());
const canvas = document.querySelector('canvas');
const ctx = canvas.getContext('webgpu');
ctx.configure({ device, format: navigator.gpu.getPreferredCanvasFormat() });

// shader
const shader = device.createShaderModule({
  code: `
    struct VSOut { @builtin(position) pos: vec4f, @location(0) uv: vec2f };
    @vertex fn vs(@builtin(vertex_index) i: u32) -> VSOut {
      var p = vec2f(0, 0);
      if (i == 1) { p = vec2f(2, 0); }
      if (i == 2) { p = vec2f(0, 2); }
      var o: VSOut;
      o.pos = vec4f(p - 1, 0, 1);
      o.uv  = p * 0.5;
      return o;
    }
    @group(0) @binding(0) var samp: sampler;
    @group(0) @binding(1) var tex: texture_external;
    @fragment fn fs(in: VSOut) -> @location(0) vec4f {
      return textureSample(tex, samp, in.uv);
    }
  `
});

const pipeline = device.createRenderPipeline({
  layout: 'auto',
  vertex: { module: shader, entryPoint: 'vs' },
  fragment: { module: shader, entryPoint: 'fs', targets: [{ format: navigator.gpu.getPreferredCanvasFormat() }] },
  primitive: { topology: 'triangle-list' },
});

const sampler = device.createSampler({ magFilter: 'linear', minFilter: 'linear' });

// 解码 + 渲染
const decoder = new VideoDecoder({
  output: (frame) => {
    const bg = device.createBindGroup({
      layout: pipeline.getBindGroupLayout(0),
      entries: [
        { binding: 0, resource: sampler },
        { binding: 1, resource: device.importExternalTexture({ source: frame }) },
      ],
    });

    const cmd = device.createCommandEncoder();
    const pass = cmd.beginRenderPass({
      colorAttachments: [{
        view: ctx.getCurrentTexture().createView(),
        clearValue: [0, 0, 0, 1],
        loadOp: 'clear',
        storeOp: 'store',
      }],
    });
    pass.setPipeline(pipeline);
    pass.setBindGroup(0, bg);
    pass.draw(3);
    pass.end();
    device.queue.submit([cmd.finish()]);

    frame.close();
  },
  error: console.error,
});
```

这段代码每帧只做：构造外部纹理绑定 → 一次 render pass → 提交。整条链路零 CPU 拷贝，完全跑在 GPU 上。

---

## 十一、应用场景总结

1. **低延迟直播**：WebTransport + WebCodecs 把延迟压到 200ms 内
2. **视频编辑 / 剪辑器**：浏览器内做转码、裁剪、滤镜、合成
3. **云游戏 / 远程桌面**：服务端编码 → WebTransport → 浏览器解码 → WebGPU 渲染
4. **AI 视频处理**��解码 → WebGPU 跑推理（超分、背景虚化、美颜） → 编码上传
5. **实时通信**：WebRTC 内部也在逐步迁移到 WebCodecs
6. **自定义播放器**：自研解封装器 + WebCodecs 解码，摆脱 MSE 对容器和 codec 的限制

---

## 十二、浏览器支持

- **Chrome / Edge**：完整支持
- **Firefox**：较新版本已开启（默认可能关闭，需要 flag）
- **Safari**：iOS 16.4+ / macOS Safari 16.4+ 起支持较完整

可以用 `VideoDecoder.isConfigSupported()` 做能力探测，给不支持的浏览器降级到 `<video>` + MSE。

---

## 参考资料

- [W3C WebCodecs Specification](https://www.w3.org/TR/webcodecs/)
- [WebGPU Specification](https://www.w3.org/TR/webgpu/)
- [MDN - WebCodecs API](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API)
- [Chrome Developers - Video processing with WebCodecs](https://developer.chrome.com/docs/web-platform/video-codecs)