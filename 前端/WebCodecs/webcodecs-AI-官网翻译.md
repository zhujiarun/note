# WebCodecs 规范（中文翻译）

> 来源：<https://w3c.github.io/webcodecs/>
> 版本：Editor's Draft，2026 年 8 月 27 日
> 组织：W3C Media Working Group
> 当前编辑：Paul Adenot（Mozilla）、Eugene Zemtsov（Google LLC）
> 前任编辑：Bernard Aboba（Microsoft Corporation）、Chris Cunningham（Google LLC）

> 说明：本翻译保留原文档的全部章节结构与 IDL 接口定义（IDL 块以 `idl` 代码块形式保留原文，仅对说明性文字、字典字段含义、算法步骤等进行中文翻译；内部槽位 `[[xxx]]`、算法名称、属性名、IDL 类型等关键字保留原文）。

## 目录

- [1. 定义（Definitions）](#1-定义definitions)
- [2. 编解码处理模型（Codec Processing Model）](#2-编解码处理模型codec-processing-model)
- [3. AudioDecoder 接口](#3-audiodecoder-接口)
- [4. VideoDecoder 接口](#4-videodecoder-接口)
- [5. AudioEncoder 接口](#5-audioencoder-接口)
- [6. VideoEncoder 接口](#6-videoencoder-接口)
- [7. 配置（Configurations）](#7-配置configurations)
- [8. 已编码媒体接口（Chunks）](#8-已编码媒体接口chunks)
- [9. 原始媒体接口（Raw Media Interfaces）](#9-原始媒体接口raw-media-interfaces)
- [10. 图像解码（Image Decoding）](#10-图像解码image-decoding)
- [11. 资源回收（Resource Reclamation）](#11-资源回收resource-reclamation)
- [12. 安全考虑](#12-安全考虑)
- [13. 隐私考虑](#13-隐私考虑)
- [14. 使用 WebCodecs 的最佳实践](#14-使用-webcodecs-的最佳实践)
- [15. 致谢（Acknowledgements）](#15-致谢acknowledgements)

## 摘要

本规范定义了一组用于对音频、视频、图像进行**编码和解码**的接口。本规范不规定或要求任何具体的编解码器或编解码方法；其目的是为已有的、由其他组织开发的编解码技术实现提供 JavaScript 接口。实现方可以自由支持任意编解码器组合，也可以完全不支持。

> 注：本文档由 Media Working Group 作为 Editor's Draft 发布。GitHub Issues 是首选的讨论场所；也可以发送邮件至 public-media-wg@w3.org。

---

## 1. 定义（Definitions）

- **Codec**：统指 `AudioDecoder`、`AudioEncoder`、`VideoDecoder`、`VideoEncoder` 四种接口的实例。
- **Key Chunk（关键块）**：解码时不依赖于任何其他帧的已编码块。也常被称为"关键帧"。
- **Internal Pending Output（内部待输出）**：当前驻留在底层编解码器实现内部管线中的 codec 输出（如 `VideoFrame`）。底层编解码器实现可以仅在接收到新输入时才发出新的输出；底层编解码器实现必须响应一次 flush 而发出所有输出。
- **Codec System Resources（编解码器系统资源）**：包括 CPU 内存、GPU 内存以及对特定编解码硬件的独占句柄等资源。这些资源可能由用户代理（User Agent）作为编解码器配置或 `AudioData`、`VideoFrame` 对象生成的一部分而分配。这类资源可能很快耗尽，因此在不再使用时应当立即释放。
- **Temporal Layer（时间层）**：`EncodedVideoChunk` 的一个分组，其时间戳节奏产生特定的帧率。参见 `scalabilityMode`。
- **Progressive Image（渐进式图像）**：一种支持解码为多个细节层级的图像，低层级在已编码数据尚未完全缓冲时即可变得可用。
- **Progressive Image Frame Generation（渐进式图像帧生成）**：给定渐进式图像解码输出的代际标识符。每一代输出在前一代基础上增加更多细节。计算帧的生成代号的机制由实现者自行定义。
- **Primary Image Track（主图像轨道）**：由给定图像文件标记为默认轨道的图像轨道。指示主轨道的机制由格式定义。
- **RGB Format（RGB 格式）**：任意顺序或布局（交错或平面）的包含红、绿、蓝颜色通道的 `VideoPixelFormat`，无论是否存在 alpha 通道。
- **sRGB Color Space**：`VideoColorSpace` 对象，按如下方式初始化：`[[primaries]]` 设为 `bt709`，`[[transfer]]` 设为 `iec61966-2-1`，`[[matrix]]` 设为 `rgb`，`[[full range]]` 设为 `true`。
- **Display P3 Color Space**：`VideoColorSpace` 对象，按如下方式初始化：`[[primaries]]` 设为 `smpte432`，`[[transfer]]` 设为 `iec61966-2-1`，`[[matrix]]` 设为 `rgb`，`[[full range]]` 设为 `true`。
- **REC709 Color Space**：`VideoColorSpace` 对象，按如下方式初始化：`[[primaries]]` 设为 `bt709`，`[[transfer]]` 设为 `bt709`，`[[matrix]]` 设为 `bt709`，`[[full range]]` 设为 `false`。
- **Codec Saturation（编解码器饱和）**：底层编解码器实现的一种状态，此时活动的解码或编码请求数已达到实现相关的最大值，从而暂时无法接受更多工作。该最大值可以是大于 1 的任何值，包括无穷（即没有上限）。在饱和状态下，对 `decode()` 或 `encode()` 的额外调用将被缓冲到控制消息队列中，并相应增加 `decodeQueueSize` 或 `encodeQueueSize`。在当前负载取得足够进展后，编解码器实现会变为非饱和状态。

---

## 2. 编解码处理模型（Codec Processing Model）

### 2.1 背景

本节为非规范性内容。

本规范定义的编解码器接口被设计为：在前一个任务尚未完成时，仍可调度新的编解码任务。例如，Web 作者可以在不等待上一次 `decode()` 完成的情况下再次调用 `decode()`。这是通过将底层编解码任务卸载到独立的并行队列来实现的。本节从 Web 作者视角描述线程行为。实现者可以选择使用更多线程，只要阻塞与顺序的外部可见行为按如下规定保持。

### 2.2 控制消息

**控制消息（control message）**定义与对编解码器实例的方法调用（例如 `encode()`）相对应的一系列步骤。

**控制消息队列（control message queue）**是控制消息的队列。每个编解码器实例都有一个控制消息队列，存储在名为 `[[control message queue]]` 的内部槽位中。

**入队一个控制消息**意味着把消息加入编解码器的 `[[control message queue]]`。调用编解码器方法通常会入队一条控制消息以调度工作。

**运行一条控制消息**意味着执行入队该消息的方法所指定的一系列步骤。

给定控制消息的步骤可能会阻塞控制消息队列中后续消息的处理。每个编解码器实例都有一个布尔内部槽位 `[[message queue blocked]]`，在发生阻塞时被设为 `true`。一条阻塞消息会在结束时把 `[[message queue blocked]]` 置回 `false`，并重新运行"处理控制消息队列"步骤。

所有控制消息都会返回 `"processed"` 或 `"not processed"`。返回 `"processed"` 表示该消息的步骤正在（或已经）执行，可以从控制消息队列中移除；返回 `"not processed"` 表示该消息此刻不应被执行，应留在控制消息队列中等待稍后重试。

**处理控制消息队列（Process the control message queue）**执行以下步骤：

1. 当 `[[message queue blocked]]` 为 `false` 且 `[[control message queue]]` 不为空时循环执行：
   - 设 `front message` 为 `[[control message queue]]` 中的第一条消息。
   - 设 `outcome` 为运行 `front message` 所述控制消息步骤的结果。
   - 如果 `outcome` 等于 `"not processed"`，跳出循环。
   - 否则，将 `front message` 从 `[[control message queue]]` 中出队。

### 2.3 编解码器工作并行队列

每个编解码器实例都有一个内部槽位 `[[codec work queue]]`，它是一个**并行队列**。

每个编解码器实例都有一个内部槽位 `[[codec implementation]]`，引用底层平台编码器或解码器。除最初的赋值外，任何引用 `[[codec implementation]]` 的步骤都会被入队到 `[[codec work queue]]`。

每个编解码器实例都有一个唯一的 **codec task source**。从 `[[codec work queue]]` 入队到事件循环的任务都使用该 codec task source。

---

## 3. AudioDecoder 接口

```idl
[Exposed=(Window, DedicatedWorker), SecureContext]
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

dictionary AudioDecoderInit {
  required AudioDataOutputCallback output;
  required WebCodecsErrorCallback error;
};

callback AudioDataOutputCallback = undefined(AudioData output);
```

### 3.1 内部槽位（Internal Slots）

- **`[[control message queue]]`**：在此编解码器实例上执行的控制消息队列。参见上文。
- **`[[message queue blocked]]`**：布尔值，指示处理 `[[control message queue]]` 是否被待处理控制消息阻塞。
- **`[[codec implementation]]`**：由用户代理提供的底层解码器实现。
- **`[[codec work queue]]`**：用于运行引用 `[[codec implementation]]` 的并行步骤的并行队列。
- **`[[codec saturated]]`**：布尔值，指示 `[[codec implementation]]` 是否无法接受额外的解码工作。
- **`[[output callback]]`**：构造时传入的解码输出回调。
- **`[[error callback]]`**：构造时传入的解码错误回调。
- **`[[key chunk required]]`**：布尔值，指示下一次传给 `decode()` 的 chunk 必须是由 `[[type]]` 标识的关键块。
- **`[[state]]`**：当前 `AudioDecoder` 的 `CodecState`。
- **`[[decodeQueueSize]]`**：待处理解码请求数。当底层编解码器准备好接受新输入时该数字会减少。
- **`[[pending flush promises]]`**：调用 `flush()` 返回的尚未解析的 Promise 列表。
- **`[[dequeue event scheduled]]`**：布尔值，指示是否已调度一个 `dequeue` 事件，以避免事件频繁触发。

### 3.2 构造函数（Constructors）

设 `d` 为一个新的 `AudioDecoder` 对象：

- 给 `[[control message queue]]` 赋一个新的队列。
- 给 `[[message queue blocked]]` 赋 `false`。
- 给 `[[codec implementation]]` 赋 `null`。
- 给 `[[codec work queue]]` 赋一个新启动的并行队列。
- 给 `[[codec saturated]]` 赋 `false`。
- 把 `init.output` 赋给 `[[output callback]]`。
- 把 `init.error` 赋给 `[[error callback]]`。
- 给 `[[key chunk required]]` 赋 `true`。
- 给 `[[state]]` 赋 `"unconfigured"`。
- 给 `[[decodeQueueSize]]` 赋 `0`。
- 给 `[[pending flush promises]]` 赋一个新列表。
- 给 `[[dequeue event scheduled]]` 赋 `false`。
- 返回 `d`。

### 3.3 属性（Attributes）

- **`state`，类型 `CodecState`，只读**：返回 `[[state]]` 的值。
- **`decodeQueueSize`，类型 `unsigned long`，只读**：返回 `[[decodeQueueSize]]` 的值。
- **`ondequeue`，类型 `EventHandler`**：事件处理器 IDL 属性，其事件类型为 `dequeue`。

### 3.4 事件汇总（Event Summary）

- **`dequeue`**：当 `decodeQueueSize` 减少时在 `AudioDecoder` 上触发。

### 3.5 方法（Methods）

#### configure(config)

入队一条控制消息，按 `config` 配置音频解码器用于解码 chunk。

> 注：如果用户代理不支持 `config`，此方法将触发 `NotSupportedError`。建议作者先通过 `isConfigSupported()` 检查支持情况。用户代理不必支持任何特定的编解码器类型或配置。

调用时执行以下步骤：

1. 如果 `config` 不是有效的 `AudioDecoderConfig`，抛出 `TypeError`。
2. 如果 `[[state]]` 为 `"closed"`，抛出 `InvalidStateError`。
3. 将 `[[state]]` 设为 `"configured"`。
4. 将 `[[key chunk required]]` 设为 `true`。
5. 入队一条用 `config` 配置解码器的控制消息。
6. 处理控制消息队列。

**运行"配置解码器"控制消息**意味着执行以下步骤：

1. 将 `[[message queue blocked]]` 赋为 `true`。
2. 将以下步骤入队到 `[[codec work queue]]`：
   - 设 `supported` 为用 `config` 运行 Check Configuration Support 算法的结果。
   - 如果 `supported` 为 `false`，调度一个任务运行 Close AudioDecoder 算法并传入 `NotSupportedError`，然后中止这些步骤。
   - 如果需要，给 `[[codec implementation]]` 赋一个支持 `config` 的实现。
   - 用 `config` 配置 `[[codec implementation]]`。
   - 调度一个任务执行：
     - 将 `[[message queue blocked]]` 赋为 `false`。
     - 调度一个任务处理控制消息队列。
3. 返回 `"processed"`。

#### decode(chunk)

入队一条控制消息解码给定的 chunk。

调用时执行以下步骤：

1. 如果 `[[state]]` 不是 `"configured"`，抛出 `InvalidStateError`。
2. 如果 `[[key chunk required]]` 为 `true`：
   - 如果 `chunk.[[type]]` 不是 `key`，抛出 `DataError`。
   - 实现者应当检查 chunk 的 `[[internal data]]` 以验证它确实是关键块；如果检测到不匹配，抛出 `DataError`。
   - 否则，将 `[[key chunk required]]` 赋为 `false`。
3. 将 `[[decodeQueueSize]]` 加一。
4. 入队一条解码 chunk 的控制消息。
5. 处理控制消息队列。

**运行"解码 chunk"控制消息**意味着执行以下步骤：

1. 如果 `[[codec saturated]]` 为 `true`，返回 `"not processed"`。
2. 如果解码 chunk 将导致 `[[codec implementation]]` 变为饱和，将 `[[codec saturated]]` 赋为 `true`。
3. 将 `[[decodeQueueSize]]` 减一，并运行 Schedule Dequeue Event 算法。
4. 将以下步骤入队到 `[[codec work queue]]`：
   - 尝试使用 `[[codec implementation]]` 解码 chunk。
   - 如果解码导致错误，调度一个任务运行 Close AudioDecoder 算法并传入 `EncodingError`，然后返回。
   - 如果 `[[codec saturated]]` 为 `true` 且 `[[codec implementation]]` 不再饱和，调度一个任务执行：
     - 将 `[[codec saturated]]` 赋为 `false`。
     - 处理控制消息队列。
   - 设 `decoded outputs` 为 `[[codec implementation]]` 发出的已解码音频数据输出列表。
   - 如果 `decoded outputs` 不为空，调度一个任务运行 Output AudioData 算法并传入 `decoded outputs`。
5. 返回 `"processed"`。

#### flush()

完成控制消息队列中的所有控制消息并发出所有输出。

调用时执行以下步骤：

1. 如果 `[[state]]` 不是 `"configured"`，返回一个被 `InvalidStateError DOMException` 拒绝的 Promise。
2. 将 `[[key chunk required]]` 设为 `true`。
3. 设 `promise` 为一个新的 Promise。
4. 把 `promise` 加入 `[[pending flush promises]]`。
5. 入队一条带 `promise` 的刷新编解码器的控制消息。
6. 处理控制消息队列。
7. 返回 `promise`。

**运行"刷新编解码器"控制消息**意味着执行以下带 `promise` 的步骤：

1. 将以下步骤入队到 `[[codec work queue]]`：
   - 通知 `[[codec implementation]]` 发出所有内部待输出。
   - 设 `decoded outputs` 为 `[[codec implementation]]` 发出的已解码音频数据输出列表。
   - 调度一个任务执行：
     - 如果 `decoded outputs` 不为空，运行 Output AudioData 算法并传入 `decoded outputs`。
     - 把 `promise` 从 `[[pending flush promises]]` 中移除。
     - 解析 `promise`。
2. 返回 `"processed"`。

#### reset()

立即重置所有状态，包括配置、控制消息队列中的控制消息以及所有待定回调。调用时运行 Reset AudioDecoder 算法并传入 `AbortError DOMException`。

#### close()

立即中止所有待定工作并释放系统资源。Close 是终态。调用时运行 Close AudioDecoder 算法并传入 `AbortError DOMException`。

#### static isConfigSupported(config)

返回一个 Promise，指示用户代理是否支持所给 `config`。

> 注：返回的 `AudioDecoderSupport.config` 仅包含用户代理识别出的字典成员；未识别的字典成员将被忽略。作者可以通过将其与原始 `config` 比较来检测未识别的字典成员。

调用时执行以下步骤：

1. 如果 `config` 不是有效的 `AudioDecoderConfig`，返回一个被 `TypeError` 拒绝的 Promise。
2. 设 `p` 为一个新的 Promise。
3. 设 `checkSupportQueue` 为启动的新并行队列。
4. 入队以下步骤到 `checkSupportQueue`：
   - 设 `supported` 为运行 Check Configuration Support 算法的结果。
   - 调度一个任务执行：
     - 设 `decoderSupport` 为一个新构造的 `AudioDecoderSupport`，初始化为：
       - `config` 为运行 Clone Configuration 算法的结果。
       - `supported` 为 `supported`。
     - 用 `decoderSupport` 解析 `p`。
5. 返回 `p`。

### 3.6 算法（Algorithms）

- **Schedule Dequeue Event**：如果 `[[dequeue event scheduled]]` 为 `true`，返回；否则赋为 `true`，调度一个任务触发 `dequeue` 事件并把 `[[dequeue event scheduled]]` 赋回 `false`。
- **Output AudioData(outputs)**：对 `outputs` 中的每个 output 构造 `AudioData` 并调用 `[[output callback]]`，包括 timestamp、format、sample rate、number of frames、number of channels。
- **Reset AudioDecoder(exception)**：若 `[[state]]` 为 `"closed"` 则抛 `InvalidStateError`；将 `[[state]]` 设为 `"unconfigured"`；通知底层实现停止旧配置产出；清空控制消息队列；如果 `[[decodeQueueSize]] > 0` 则清零并触发 dequeue；拒绝所有 pending flush promise。
- **Close AudioDecoder(exception)**：运行 Reset AudioDecoder(exception)；将 `[[state]]` 设为 `"closed"`；清除底层实现并释放资源；若 exception 不是 `AbortError`，调用 `[[error callback]]`。

---

## 4. VideoDecoder 接口

```idl
[Exposed=(Window, DedicatedWorker), SecureContext]
interface VideoDecoder : EventTarget {
  constructor(VideoDecoderInit init);

  readonly attribute CodecState state;
  readonly attribute unsigned long decodeQueueSize;
  attribute EventHandler ondequeue;

  undefined configure(VideoDecoderConfig config);
  undefined decode(EncodedVideoChunk chunk);
  Promise<undefined> flush();
  undefined reset();
  undefined close();

  static Promise<VideoDecoderSupport> isConfigSupported(VideoDecoderConfig config);
};

dictionary VideoDecoderInit {
  required VideoFrameOutputCallback output;
  required WebCodecsErrorCallback error;
};

callback VideoFrameOutputCallback = undefined(VideoFrame output);
```

### 4.1 内部槽位

- `[[control message queue]]`、`[[message queue blocked]]`、`[[codec implementation]]`、`[[codec work queue]]`、`[[codec saturated]]`、`[[output callback]]`、`[[error callback]]`：参见 AudioDecoder。
- **`[[active decoder config]]`**：当前应用的 `VideoDecoderConfig`。
- **`[[key chunk required]]`**：布尔值，指示下一次传给 `decode()` 的 chunk 必须是由 `type` 标识的关键块。
- `[[state]]`、`[[decodeQueueSize]]`、`[[pending flush promises]]`、`[[dequeue event scheduled]]`：参见 AudioDecoder。

### 4.2 构造函数

设 `d` 为新 `VideoDecoder`，除把 `[[active decoder config]]` 初始化为 `null`、把 `[[key chunk required]]` 初始化为 `true` 外，其余步骤与 AudioDecoder 构造函数一致。返回 `d`。

### 4.3 属性

- **`state` / `decodeQueueSize` / `ondequeue`**：参见 AudioDecoder。

### 4.4 事件汇总

- **`dequeue`**：当 `decodeQueueSize` 减少时在 `VideoDecoder` 上触发。

### 4.5 方法

#### configure(config)

入队一条控制消息按 `config` 配置视频解码器。其步骤与 AudioDecoder 的 `configure` 类似，并额外把 `config` 赋给 `[[active decoder config]]`。

#### decode(chunk)

入队一条控制消息解码给定的 chunk。

> 注：建议作者在不再需要输出 `VideoFrame` 时立即对其调用 `close()`。底层 media resource 由 `VideoDecoder` 持有，不释放（或等待 GC）会导致解码停滞。

> 注：`VideoDecoder` 要求帧按其预期的呈现顺序（presentation order）输出。对于某些实现，用户代理需要把输出重排成呈现顺序。

其行为与 AudioDecoder 的 `decode` 类似，但额外要求：

1. 若 `chunk.type` 不是 `key` 且需要关键块时，抛出 `DataError`。
2. 解码后调用 Output VideoFrames 算法输出 `VideoFrame`。

#### flush()

完成控制消息队列中的所有控制消息并发出所有输出。步骤与 AudioEncoder 的 `flush` 类似，但输出为 `VideoFrame`。

#### reset() / close()

立即重置/关闭，与 AudioDecoder 行为一致，分别抛出 `AbortError DOMException`。

#### static isConfigSupported(config)

返回一个 Promise，指示用户代理是否支持所给 `config`。步骤与 AudioDecoder 版本类似，但返回 `VideoDecoderSupport`。

### 4.6 算法

- **Schedule Dequeue Event**：与 AudioDecoder 相同。
- **Output VideoFrames(outputs)**：对每个 output：
  - 取 `timestamp` 与 `duration`。
  - 如 `[[active decoder config]]` 中存在 `displayAspectWidth/Height` 则使用。
  - 取 `colorSpace`，优先使用 `[[active decoder config]]` 中提供的；否则基于码流检测；UA 可以把检测到的值替换 colorSpace 中的 null 字段。
  - 取 `rotation`、`flip`。
  - 运行 Create a VideoFrame 算法生成帧并调用 `[[output callback]]`。
- **Reset VideoDecoder(exception)**：与 AudioDecoder 的 reset 类似。
- **Close VideoDecoder(exception)**：与 AudioDecoder 的 close 类似。

---

## 5. AudioEncoder 接口

```idl
[Exposed=(Window, DedicatedWorker), SecureContext]
interface AudioEncoder : EventTarget {
  constructor(AudioEncoderInit init);

  readonly attribute CodecState state;
  readonly attribute unsigned long encodeQueueSize;
  attribute EventHandler ondequeue;

  undefined configure(AudioEncoderConfig config);
  undefined encode(AudioData data);
  Promise<undefined> flush();
  undefined reset();
  undefined close();

  static Promise<AudioEncoderSupport> isConfigSupported(AudioEncoderConfig config);
};

dictionary AudioEncoderInit {
  required EncodedAudioChunkOutputCallback output;
  required WebCodecsErrorCallback error;
};

callback EncodedAudioChunkOutputCallback = undefined(EncodedAudioChunk output, optional EncodedAudioChunkMetadata metadata = {});
```

### 5.1 内部槽位

- `[[control message queue]]`、`[[message queue blocked]]`、`[[codec implementation]]`、`[[codec work queue]]`、`[[codec saturated]]`、`[[output callback]]`、`[[error callback]]`：与 AudioDecoder 类似。
- **`[[active encoder config]]`**：当前应用的 `AudioEncoderConfig`。
- **`[[active output config]]`**：描述最近发出的 `EncodedAudioChunk` 解码方式的 `AudioDecoderConfig`。
- `[[state]]`、`[[encodeQueueSize]]`、`[[pending flush promises]]`、`[[dequeue event scheduled]]`：参见上节。

### 5.2 构造函数

设 `e` 为新 `AudioEncoder`，把 `[[active encoder config]]` 与 `[[active output config]]` 初始化为 `null`，其他槽位初始化与 AudioDecoder 类似。返回 `e`。

### 5.3 属性

- **`state` / `encodeQueueSize` / `ondequeue`**：与 AudioDecoder 类似，但 `encodeQueueSize` 是待编码请求数。

### 5.4 事件汇总

- **`dequeue`**：当 `encodeQueueSize` 减少时在 `AudioEncoder` 上触发。

### 5.5 方法

#### configure(config)

按 `config` 配置音频编码器，与 AudioDecoder 的 `configure` 类似，但额外把 `config` 赋给 `[[active encoder config]]`。

#### encode(data)

入队一条控制消息对 `data` 进行编码。

调用时执行：

1. 如果 `data` 的 `[[Detached]]` 内部槽为 `true`，抛出 `TypeError`。
2. 如果 `[[state]]` 不是 `"configured"`，抛出 `InvalidStateError`。
3. 运行 Clone AudioData 算法得到 `dataClone`。
4. `[[encodeQueueSize]]` 加一。
5. 入队对 `dataClone` 进行编码的控制消息。
6. 处理控制消息队列。

控制消息步骤与 AudioDecoder 的 decode 类似，但调用 `[[codec implementation]]` 进行编码，并在有 `encoded outputs` 时调度 Output EncodedAudioChunks 算法。

#### flush()

与 AudioDecoder 的 flush 类似，输出 `EncodedAudioChunk`。

#### reset() / close()

与 AudioDecoder 行为类似，但将 `[[state]]` 设为 `"unconfigured"` 并清空 `[[active encoder config]]` 与 `[[active output config]]`。

#### static isConfigSupported(config)

返回 `AudioEncoderSupport`，步骤与其他 codec 相同。

### 5.6 算法

- **Schedule Dequeue Event**：与其他 codec 相同。
- **Output EncodedAudioChunks(outputs)**：为每个 output 构造 `EncodedAudioChunkInit`，依据 `[[active encoder config]]` 生成 `outputConfig`（codec、sampleRate、numberOfChannels、description）。当 `outputConfig` 与 `[[active output config]]` 不同时，更新并通过 `chunkMetadata.decoderConfig` 一并送出。
- **Reset AudioEncoder(exception)**：参见上节。
- **Close AudioEncoder(exception)**：参见上节。

### 5.7 EncodedAudioChunkMetadata

```idl
dictionary EncodedAudioChunkMetadata {
  AudioDecoderConfig decoderConfig;
};
```

- **`decoderConfig`，类型 `AudioDecoderConfig`**：作者可用于解码关联 `EncodedAudioChunk` 的配置。

---

## 6. VideoEncoder 接口

```idl
[Exposed=(Window, DedicatedWorker), SecureContext]
interface VideoEncoder : EventTarget {
  constructor(VideoEncoderInit init);

  readonly attribute CodecState state;
  readonly attribute unsigned long encodeQueueSize;
  attribute EventHandler ondequeue;

  undefined configure(VideoEncoderConfig config);
  undefined encode(VideoFrame frame, optional VideoEncoderEncodeOptions options = {});
  Promise<undefined> flush();
  undefined reset();
  undefined close();

  static Promise<VideoEncoderSupport> isConfigSupported(VideoEncoderConfig config);
};

dictionary VideoEncoderInit {
  required EncodedVideoChunkOutputCallback output;
  required WebCodecsErrorCallback error;
};

callback EncodedVideoChunkOutputCallback = undefined(EncodedVideoChunk chunk, optional EncodedVideoChunkMetadata metadata = {});
```

### 6.1 内部槽位

- `[[control message queue]]`、`[[message queue blocked]]`、`[[codec implementation]]`、`[[codec work queue]]`、`[[codec saturated]]`、`[[output callback]]`、`[[error callback]]`、`[[active encoder config]]`、`[[active output config]]`、`[[state]]`、`[[encodeQueueSize]]`、`[[pending flush promises]]`、`[[dequeue event scheduled]]`：与 AudioEncoder 类似。
- **`[[active orientation]]`**：整数与布尔对，记录 `configure()` 后第一个传入 `encode()` 的 `VideoFrame` 的 `[[flip]]` 与 `[[rotation]]`。

### 6.2 构造函数

设 `e` 为新 `VideoEncoder`，把 `[[active encoder config]]`、`[[active output config]]`、`[[active orientation]]` 初始化为 `null`，其余与 AudioEncoder 相同。返回 `e`。

### 6.3 属性

- **`state` / `encodeQueueSize` / `ondequeue`**：与其他 codec 一致。

### 6.4 事件汇总

- **`dequeue`**：`encodeQueueSize` 减少时触发。

### 6.5 方法

#### configure(config)

按 `config` 配置视频编码器；额外把 `[[active orientation]]` 重置为 `null`。

#### encode(frame, options)

入队一条控制消息编码给定的 frame。

调用时执行：

1. 如果 `frame` 的 `[[Detached]]` 内部槽为 `true`，抛出 `TypeError`。
2. 如果 `[[state]]` 不是 `"configured"`，抛出 `InvalidStateError`。
3. 如果 `[[active orientation]]` 不为 `null` 且与 `frame.[[rotation]]`、`frame.[[flip]]` 不匹配，抛出 `DataError`。
4. 如果 `[[active orientation]]` 为 `null`，设为 `frame.[[rotation]]` 与 `frame.[[flip]]`。
5. 运行 Clone VideoFrame 算法得到 `frameClone`。
6. `[[encodeQueueSize]]` 加一。
7. 入队对 `frameClone` 按 `options` 编码的控制消息。
8. 处理控制消息队列。

控制消息步骤与 AudioEncoder 的 encode 类似，但调用 `[[codec implementation]]` 对 `frameClone` 进行编码，并在有输出时调用 Output EncodedVideoChunks 算法。

#### flush()

与其他 codec 的 flush 类似。

#### reset() / close()

与其他 codec 一致。

#### static isConfigSupported(config)

返回 `VideoEncoderSupport`。

### 6.6 算法

- **Schedule Dequeue Event**：与其他 codec 相同。
- **Output EncodedVideoChunks(outputs)**：对每个 output 构造 `EncodedVideoChunkInit`，依据 `[[active encoder config]]` 生成 `outputConfig`（codec、codedWidth、codedHeight、displayAspectWidth、displayAspectHeight、rotation、flip）。当 `outputConfig` 与 `[[active output config]]` 不同时更新并通过 `chunkMetadata.decoderConfig` 送出。如果 `scalabilityMode` 描述多层时间层，附加 `SvcOutputMetadata`；如果 `alpha` 为 `"keep"`，附加 `alphaSideData`。
- **Reset VideoEncoder(exception)** / **Close VideoEncoder(exception)**：与其他 codec 相同。

### 6.7 EncodedVideoChunkMetadata

```idl
dictionary EncodedVideoChunkMetadata {
  VideoDecoderConfig decoderConfig;
  SvcOutputMetadata svc;
  BufferSource alphaSideData;
};

dictionary SvcOutputMetadata {
  unsigned long temporalLayerId;
};
```

- **`decoderConfig`，类型 `VideoDecoderConfig`**：可用于解码关联 `EncodedVideoChunk` 的配置。
- **`svc`，类型 `SvcOutputMetadata`**：与配置的 `scalabilityMode` 相关的一组元数据。
- **`alphaSideData`，类型 `BufferSource`**：包含 `EncodedVideoChunk` 的额外 alpha 通道数据。
- **`temporalLayerId`，类型 `unsigned long`**：标识关联 `EncodedVideoChunk` 的时间层序号。

---

## 7. 配置（Configurations）

### 7.1 Check Configuration Support(with config)

如果 `config.codec` 不是合法的 codec 字符串或用户代理无法识别，返回 `false`。

如果 `config` 是 `AudioDecoderConfig` 或 `VideoDecoderConfig`，且用户代理无法提供能解码 `config.codec` 中所指定的确切 profile、level 与 constraint bits 的解码器，返回 `false`。

如果 `config` 是 `AudioEncoderConfig` 或 `VideoEncoderConfig`：

- 若 `config.codec` 包含 profile，且用户代理无法提供能编码该 profile 的编码器，返回 `false`。
- 若 `config.codec` 包含 level，且用户代理无法提供能编码到不大于该 level 的编码器，返回 `false`。
- 若 `config.codec` 包含 constraint bits，且用户代理无法提供至少同样受限的编码器，返回 `false`。

如果用户代理能够提供支持 `config` 所有项的编解码器（包括未提供的键的默认值），返回 `true`。

> 注：硬件可能动态变化（外置 GPU 被拔出）或硬件资源耗尽，因此配置支持能力是 best-effort 的。

否则返回 `false`。

### 7.2 Clone Configuration(with config)

> 注：本算法只复制用户代理识别为该字典类型的成员，实现"深拷贝"。这些配置对象常被用于异步操作输入，复制意味着在操作进行时修改原对象不会影响操作结果。

执行以下步骤：

1. 设 `dictType` 为 `config` 的字典类型。
2. 设 `clone` 为 `dictType` 的一个新空实例。
3. 对 `dictType` 定义的每个字典成员 `m`：
   - 如果 `m` 在 `config` 中不存在，跳过。
   - 如果 `config[m]` 是嵌套字典，则把 `clone[m]` 设为递归运行 Clone Configuration 算法的结果。
   - 否则把 `config[m]` 的副本赋给 `clone[m]`。

### 7.3 Signalling Configuration Support

#### 7.3.1 AudioDecoderSupport

```idl
dictionary AudioDecoderSupport {
  boolean supported;
  AudioDecoderConfig config;
};
```

- **`supported`，类型 `boolean`**：指示用户代理是否支持相应配置。
- **`config`，类型 `AudioDecoderConfig`**：用户代理用于判断 `supported` 的配置。

#### 7.3.2 VideoDecoderSupport

```idl
dictionary VideoDecoderSupport {
  boolean supported;
  VideoDecoderConfig config;
};
```

字段含义同上。

#### 7.3.3 AudioEncoderSupport / 7.3.4 VideoEncoderSupport

结构与上面相同，分别返回 `AudioEncoderConfig` 与 `VideoEncoderConfig`。

### 7.4 Codec String（合法 codec 字符串）

合法 codec 字符串必须满足：

- 符合相关编解码器规范的定义。
- 仅描述单个编解码器。
- 对定义了 profile/level/constraint bits 的编解码器，明确指明这些参数。

> 注：在其他媒体规范中，codec 字符串通常作为 MIME 类型的 `codecs=` 参数（`isTypeSupported()`、`canPlayType()`，[RFC6381]）。本规范中的已编码媒体未做容器化，因此只接受 codecs 参数的值。

> 注：定义了 level 与 constraint bits 的编解码器的编码器在这些参数上有一定灵活度，但不会生成 level 更高或更不受限的码流。

codec 字符串的格式与语义由 [WEBCODECS-CODEC-REGISTRY] 中的编解码器注册定义；合规实现可以支持任何组合或全部不支持。

### 7.5 AudioDecoderConfig

```idl
dictionary AudioDecoderConfig {
  required DOMString codec;
  [EnforceRange] required unsigned long sampleRate;
  [EnforceRange] required unsigned long numberOfChannels;
  AllowSharedBufferSource description;
};
```

**验证 `AudioDecoderConfig` 有效性**：

1. 如果 `codec` 去除首尾 ASCII 空白后为空，返回 `false`。
2. 如果 `description` 处于 detached 状态，返回 `false`。
3. 如果 `sampleRate` 或 `numberOfChannels` 为 0，返回 `false`。
4. 返回 `true`。

字段说明：

- **`codec`，类型 `DOMString`**：描述编解码器的 codec 字符串。
- **`sampleRate`，类型 `unsigned long`**：每秒帧样本数。
- **`numberOfChannels`，类型 `unsigned long`**：音频通道数。
- **`description`，类型 `AllowSharedBufferSource`**：编解码器特定的字节序列（extradata）。具体填充规则参见 codec 注册表。

### 7.6 VideoDecoderConfig

```idl
dictionary VideoDecoderConfig {
  required DOMString codec;
  AllowSharedBufferSource description;
  [EnforceRange] unsigned long codedWidth;
  [EnforceRange] unsigned long codedHeight;
  [EnforceRange] unsigned long displayAspectWidth;
  [EnforceRange] unsigned long displayAspectHeight;
  VideoColorSpaceInit colorSpace;
  HardwareAcceleration hardwareAcceleration = "no-preference";
  boolean optimizeForLatency;
  double rotation = 0;
  boolean flip = false;
};
```

**验证 `VideoDecoderConfig` 有效性**：

1. 如果 `codec` 去除首尾 ASCII 空白后为空，返回 `false`。
2. 如果只提供 `codedWidth` 或 `codedHeight` 之一，返回 `false`。
3. 如果 `codedWidth = 0` 或 `codedHeight = 0`，返回 `false`。
4. 如果只提供 `displayAspectWidth` 或 `displayAspectHeight` 之一，返回 `false`。
5. 如果 `displayAspectWidth = 0` 或 `displayAspectHeight = 0`，返回 `false`。
6. 如果 `description` 处于 detached 状态，返回 `false`。
7. 返回 `true`。

字段说明：

- **`codec`**：codec 字符串。
- **`description`**：extradata。
- **`codedWidth` / `codedHeight`**：VideoFrame 的像素尺寸（可能包含不可见填充）。`codedWidth/Height` 用于选择底层实现。
- **`displayAspectWidth` / `displayAspectHeight`**：显示宽高比。`displayWidth/Height` 在缩放后可与 `displayAspectWidth/Height` 比例相同但数值不同。
- **`colorSpace`，类型 `VideoColorSpaceInit`**：配置 VideoFrame 的 colorSpace；若提供，则覆盖码流内嵌值。
- **`hardwareAcceleration`，类型 `HardwareAcceleration`，默认 `"no-preference"`**：硬件加速提示，参见 HardwareAcceleration。
- **`optimizeForLatency`，类型 `boolean`**：提示底层解码器最小化产生首帧所需的 chunk 数。
- **`rotation`，类型 `double`，默认 `0`**：设置解码帧的 rotation。
- **`flip`，类型 `boolean`，默认 `false`**：设置解码帧的 flip。

### 7.7 AudioEncoderConfig

```idl
dictionary AudioEncoderConfig {
  required DOMString codec;
  [EnforceRange] required unsigned long sampleRate;
  [EnforceRange] required unsigned long numberOfChannels;
  [EnforceRange] unsigned long long bitrate;
  BitrateMode bitrateMode = "variable";
};
```

> 注：`AudioEncoderConfig` 的编解码器私有扩展定义在 codec 注册表中。

**验证有效性**：

1. `codec` 去除首尾空白后为空，返回 `false`。
2. 若 codec 注册表为该扩展定义了校验步骤，则运行并返回其结果。
3. 若 `sampleRate` 或 `numberOfChannels` 为 0，返回 `false`。
4. 返回 `true`。

字段说明：

- **`codec`**：codec 字符串。
- **`sampleRate` / `numberOfChannels`**：含义同上。
- **`bitrate`，类型 `unsigned long long`**：平均码率（bps）。
- **`bitrateMode`，类型 `BitrateMode`，默认 `"variable"`**：常量或可变码率，定义见 [MEDIASTREAM-RECORDING]。并非所有音频编解码器都支持所有 `BitrateMode`，建议先调用 `isConfigSupported()`。

### 7.8 VideoEncoderConfig

```idl
dictionary VideoEncoderConfig {
  required DOMString codec;
  [EnforceRange] required unsigned long width;
  [EnforceRange] required unsigned long height;
  [EnforceRange] unsigned long displayWidth;
  [EnforceRange] unsigned long displayHeight;
  [EnforceRange] unsigned long long bitrate;
  double framerate;
  HardwareAcceleration hardwareAcceleration = "no-preference";
  AlphaOption alpha = "discard";
  DOMString scalabilityMode;
  VideoEncoderBitrateMode bitrateMode = "variable";
  LatencyMode latencyMode = "quality";
  DOMString contentHint;
};
```

**验证有效性**：

1. `codec` 去除首尾空白后为空，返回 `false`。
2. `width = 0` 或 `height = 0`，返回 `false`。
3. `displayWidth = 0` 或 `displayHeight = 0`，返回 `false`。
4. 返回 `true`。

字段说明：

- **`codec`**：codec 字符串。
- **`width` / `height`**：编码宽高（像素）。编码器必须对 `[[visible width]]` 与此不同的 `VideoFrame` 进行缩放。
- **`displayWidth` / `displayHeight`**：期望的显示宽高，默认等于 `width/height`。若与 `width/height` 不同表示需要在解码后做显示宽高比缩放；多数编解码器只是透传该信息。
- **`bitrate`**：平均码率（bps）。
- **`framerate`，类型 `double`**：期望帧率。配合 frame timestamp 应被用于估算每帧最佳字节长度；在 `latencyMode = "realtime"` 下应被视为输出截止时间。
- **`hardwareAcceleration`**：硬件加速提示。
- **`alpha`，类型 `AlphaOption`，默认 `"discard"`**：是否保留输入 `VideoFrame` 的 alpha 通道；若为 `discard`，无论 `[[format]]` 如何都丢弃 alpha。
- **`scalabilityMode`，类型 `DOMString`**：编码可分级模式标识符，定义见 [WebRTC-SVC]。
- **`bitrateMode`，类型 `VideoEncoderBitrateMode`，默认 `"variable"`**：码率控制模式。
- **`latencyMode`，类型 `LatencyMode`，默认 `"quality"`**：延迟相关行为，参见 LatencyMode。
- **`contentHint`，类型 `DOMString`**：视频内容提示，定义见 [mst-content-hint]。UA 可据此优化编码质量，且必须尊重其他显式设置的选项；若不支持该提示，不应拒绝配置（参见 `isConfigSupported()`）。

### 7.9 Hardware Acceleration

```idl
enum HardwareAcceleration {
  "no-preference",
  "prefer-hardware",
  "prefer-software",
};
```

硬件加速将编解码卸载到专用硬件。`prefer-hardware` 与 `prefer-software` 仅为提示：用户代理应当尽量尊重，但任何场景下都可忽略。

为防止指纹化：

- 若用户代理实现了 [media-capabilities]，必须确保接受或拒绝某个 `HardwareAcceleration` 偏好不会暴露超出 [media-capabilities] 已暴露的信息。
- 若出于指纹化原因未实现 [media-capabilities]，应当忽略该偏好。

> 注：典型的 trade-off：
> - 设置 `prefer-hardware` / `prefer-software` 会显著缩小受支持的配置集合。
> - 硬件加速通常启动延迟更高，但吞吐更稳定，能降低 CPU 占用。
> - 硬件解码对错误标记或违反规范的输入鲁棒性较差。
> - 硬件加速通常比软件实现更省电。
> - 低分辨率内容上硬件加速的开销可能反而导致性能与能效下降。
> - 若作者能提供基于 WebAssembly 的软件回退，则 `prefer-hardware` 是合理选择；若作者对启动延迟或解码鲁棒性特别敏感，则 `prefer-software` 是合理选择。

字段说明：

- **`no-preference`**：可使用硬件加速（若可用且与配置兼容）。
- **`prefer-software`**：应当优先使用软件实现；在缺乏软件实现或与之不兼容时该配置可能不被支持。
- **`prefer-hardware`**：应当优先使用硬件加速；在缺乏硬件实现或与之不兼容时该配置可能不被支持。

### 7.10 Alpha Option

```idl
enum AlphaOption {
  "keep",
  "discard",
};
```

描述在不同操作中用户代理应如何处理 alpha 通道。

- **`keep`**：保留 `VideoFrame` 的 alpha 通道（若存在）。
- **`discard`**：忽略或移除 `VideoFrame` 的 alpha 通道。

### 7.11 Latency Mode

```idl
enum LatencyMode {
  "quality",
  "realtime",
};
```

- **`quality`**：优化编码质量。此模式下：可以提高编码延迟以换取质量；不得通过丢帧达成目标码率/帧率；`framerate` 不应被视为输出截止时间。
- **`realtime`**：优化低延迟。此模式下：可以牺牲质量换取低延迟；可以通过丢帧达成目标码率/帧率；`framerate` 应被视为输出截止时间。

### 7.12 Configuration Equivalence

用于判断两个配置字典是否等效，影响 codec 实例复用等行为。

### 7.13 VideoEncoderEncodeOptions

```idl
dictionary VideoEncoderEncodeOptions {
  boolean keyFrame = false;
};
```

> 注：codec 私有扩展由注册表定义。

- **`keyFrame`，类型 `boolean`，默认 `false`**：`true` 表示当前帧必须编码为关键帧；`false` 表示用户代理可自行决定。

### 7.14 VideoEncoderBitrateMode

```idl
enum VideoEncoderBitrateMode {
  "constant",
  "variable",
  "quantizer",
};
```

- **`constant`**：恒定码率（参见 `bitrate`）。
- **`variable`**：可变码率，复杂信号可使用更多空间，简单信号可使用更少空间。
- **`quantizer`**：使用量化器，每帧的量化器在 `VideoEncoderEncodeOptions` 的 codec 私有扩展中指定。

### 7.15 CodecState

```idl
enum CodecState {
  "unconfigured",
  "configured",
  "closed",
};
```

- **`unconfigured`**：编解码器未配置。
- **`configured`**：已提供有效配置，可进行编解码。
- **`closed`**：编解码器不再可用，底层系统资源已释放。

### 7.16 WebCodecsErrorCallback

```idl
callback WebCodecsErrorCallback = undefined(DOMException error);
```

---

## 8. 已编码媒体接口（Chunks）

### 8.1 EncodedAudioChunk 接口

```idl
[Exposed=(Window, DedicatedWorker), Serializable]
interface EncodedAudioChunk {
  constructor(EncodedAudioChunkInit init);

  readonly attribute EncodedAudioChunkType type;
  readonly attribute long long timestamp;        // 微秒
  readonly attribute unsigned long long? duration;  // 微秒
  readonly attribute unsigned long byteLength;

  undefined copyTo(AllowSharedBufferSource destination);
};

dictionary EncodedAudioChunkInit {
  required EncodedAudioChunkType type;
  [EnforceRange] required long long timestamp;   // 微秒
  [EnforceRange] unsigned long long duration;     // 微秒
  required AllowSharedBufferSource data;
  sequence<ArrayBuffer> transfer = [];
};

enum EncodedAudioChunkType {
  "key",
  "delta",
};
```

#### 8.1.1 内部槽位

- **`[[internal data]]`**：表示已编码 chunk 数据的字节数组。
- **`[[type]]`**：指示 chunk 是否是关键块。
- **`[[timestamp]]`**：呈现时间戳（微秒）。
- **`[[duration]]`**：呈现持续时间（微秒）。
- **`[[byte length]]`**：`[[internal data]]` 的字节长度。

#### 8.1.2 构造函数

1. 如果 `init.transfer` 中多次引用同一个 `ArrayBuffer`，抛出 `DataCloneError`。
2. 对每个 transferable，若 `[[Detached]]` 为 `true`，抛出 `DataCloneError`。
3. 创建新的 `EncodedAudioChunk`，依次赋 `[[type]]`、`[[timestamp]]`、`[[duration]]`、`[[byte length]]`，并根据 `init.transfer` 是否包含 `init.data` 引用的 `ArrayBuffer` 选择是否复用底层 buffer 或拷贝。
4. 对每个 transferable 执行 DetachArrayBuffer。
5. 返回 chunk。

#### 8.1.3 属性

- **`type`**：`EncodedAudioChunkType`，只读。
- **`timestamp`**：`long long`，只读（微秒）。
- **`duration`**：`unsigned long long?`，只读（微秒）。
- **`byteLength`**：`unsigned long`，只读。

#### 8.1.4 方法

- **`copyTo(destination)`**：若 `destination` 容量不足，抛 `TypeError`；否则把 `[[internal data]]` 拷贝进去。

#### 8.1.5 序列化

- 序列化步骤：若 `forStorage` 为 `true`，抛 `DataCloneError`；否则将各内部槽位值赋给序列化的对应字段。
- 反序列化步骤：把序列化字段赋回对应内部槽位。

> 注：由于 `EncodedAudioChunk` 不可变，用户代理可使用引用计数方式实现序列化（参见 §9.2.6）。

### 8.2 EncodedVideoChunk 接口

```idl
[Exposed=(Window, DedicatedWorker), Serializable]
interface EncodedVideoChunk {
  constructor(EncodedVideoChunkInit init);

  readonly attribute EncodedVideoChunkType type;
  readonly attribute long long timestamp;        // 微秒
  readonly attribute unsigned long long? duration;  // 微秒
  readonly attribute unsigned long byteLength;

  undefined copyTo(AllowSharedBufferSource destination);
};

dictionary EncodedVideoChunkInit {
  required EncodedVideoChunkType type;
  [EnforceRange] required long long timestamp;   // 微秒
  [EnforceRange] unsigned long long duration;     // 微秒
  required AllowSharedBufferSource data;
  sequence<ArrayBuffer> transfer = [];
};
```

#### 8.2.1 内部槽位

与 `EncodedAudioChunk` 一致。

#### 8.2.2 构造函数

步骤与 `EncodedAudioChunk` 一致。

#### 8.2.3 属性 / 8.2.4 方法 / 8.2.5 序列化

均与 `EncodedAudioChunk` 一致。

---

## 9. 原始媒体接口（Raw Media Interfaces）

### 9.1 内存模型（Memory Model）

#### 9.1.1 背景

本节为非规范性内容。

已解码媒体数据可能占用大量系统内存。为减少昂贵的拷贝，本规范定义了一套**引用计数**方案（`clone()` 与 `close()`）。

> 注：建议作者在不再需要帧时立即调用 `close()`。

#### 9.1.2 引用计数

**media resource（媒体资源）**：描述 `VideoFrame` 或 `AudioData` 的实际像素数据或音频采样数据的存储。

`AudioData.[[resource reference]]` 与 `VideoFrame.[[resource reference]]` 内部槽位持有对 media resource 的引用。

`VideoFrame.clone()` 与 `AudioData.clone()` 返回新对象，其 `[[resource reference]]` 与原对象指向同一 media resource。

`VideoFrame.close()` 与 `AudioData.close()` 会清空自身的 `[[resource reference]]` 槽位，释放其对 media resource 的引用。

media resource 必须至少在仍有 `[[resource reference]]` 引用它时保持存活。

> 注：当 media resource 不再被任何 `[[resource reference]]` 引用时即可销毁。建议用户代理尽快销毁以减轻内存压力并促进资源重用。

#### 9.1.3 Transfer 与 Serialization

本节为非规范性内容。

`AudioData` 与 `VideoFrame` 同时是 transferable 与 serializable 对象。其 transfer/serialization 步骤分别定义在 §9.2.6 与 §9.4.7。

**Transfer** 把 `[[resource reference]]` 移到目标对象并 `close()` 源对象。作者可借此在跨 realm 间移动 `AudioData` 或 `VideoFrame` 而无需拷贝底层 media resource。

**Serialize** 实际等同于 `clone()`，产生两个对象共享同一 media resource。作者可借此在跨 realm 间克隆而不拷贝底层 media resource。

### 9.2 AudioData 接口

```idl
[Exposed=(Window, DedicatedWorker), Serializable, Transferable]
interface AudioData {
  constructor(AudioDataInit init);

  readonly attribute AudioSampleFormat? format;
  readonly attribute float sampleRate;
  readonly attribute unsigned long numberOfFrames;
  readonly attribute unsigned long numberOfChannels;
  readonly attribute unsigned long long duration;   // 微秒
  readonly attribute long long timestamp;            // 微秒

  unsigned long allocationSize(AudioDataCopyToOptions options);
  undefined copyTo(AllowSharedBufferSource destination, AudioDataCopyToOptions options);
  AudioData clone();
  undefined close();
};

dictionary AudioDataInit {
  required AudioSampleFormat format;
  required float sampleRate;
  [EnforceRange] required unsigned long numberOfFrames;
  [EnforceRange] required unsigned long numberOfChannels;
  [EnforceRange] required long long timestamp;     // 微秒
  required AllowSharedBufferSource data;
  sequence<ArrayBuffer> transfer = [];
};
```

#### 9.2.1 内部槽位

- **`[[resource reference]]`**：对持有该 `AudioData` 音频采样数据的 media resource 的引用。
- **`[[format]]`**：该 `AudioData` 的 `AudioSampleFormat`。当底层格式未映射到 `AudioSampleFormat` 或 `[[Detached]]` 为 `true` 时为 `null`。
- **`[[sample rate]]`**：采样率（Hz）。
- **`[[number of frames]]`**：帧数。
- **`[[number of channels]]`**：通道数。
- **`[[timestamp]]`**：呈现时间戳（微秒）。

#### 9.2.2 构造函数

1. 如果 `init` 不是有效的 `AudioDataInit`，抛 `TypeError`。
2. 如果 `init.transfer` 多次引用同一 `ArrayBuffer`，抛 `DataCloneError`。
3. 对每个 transferable 检查 `[[Detached]]`。
4. 创建新 `AudioData` 对象，初始化各槽位；若 `init.transfer` 引用 `init.data`，UA 可选择复用底层 buffer，否则拷贝。
5. 对 transferable 执行 DetachArrayBuffer。
6. 返回 frame。

#### 9.2.3 属性

- **`format`，`AudioSampleFormat?`，只读**：当前 `AudioSampleFormat`。`[[Detached]]` 或底层未映射时为 `null`。
- **`sampleRate`，`float`，只读**：采样率（Hz）。
- **`numberOfFrames`，`unsigned long`，只读**：帧数。
- **`numberOfChannels`，`unsigned long`，只读**：通道数。
- **`timestamp`，`long long`，只读**：呈现时间戳（微秒）。
- **`duration`，`unsigned long long`，只读**：持续时间（微秒），由 `[[number of frames]] / [[sample rate]] * 1,000,000` 计算。

#### 9.2.4 方法

- **`allocationSize(options)`**：返回按 `options` 描述的复制所需字节数。若 `[[Detached]]` 为 `true` 则抛 `InvalidStateError`；`bytesPerSample * copyElementCount`。
- **`copyTo(destination, options)`**：把指定平面的采样拷贝到 `destination`。`[[Detached]]` 则抛 `InvalidStateError`；`bytesPerSample * copyElementCount` 超过 `destination.byteLength` 抛 `RangeError`；若目标格式与 `[[format]]` 不同则在拷贝过程中执行格式转换。
- **`clone()`**：返回共享同一 media resource 的新 `AudioData`。
- **`close()`**：运行 Close AudioData 算法；close 是终态。

#### 9.2.5 算法

- **Compute Copy Element Count(options)**：根据 `destFormat`、`planeIndex` 校验范围，计算 `copyFrameCount`，再根据是否交错乘以通道数。
- **Clone AudioData(data)**：返回与 `data` 共享 media resource 的新 `AudioData`，并复制其他槽位。
- **Close AudioData(data)**：把 `[[Detached]]` 置 `true`、`[[resource reference]]` 置 `null`，清空 sampleRate/numberOfFrames/numberOfChannels/format。
- **AudioDataInit 有效性**：若 `sampleRate <= 0` 返回 `false`；`numberOfFrames == 0` 返回 `false`；`numberOfChannels == 0` 返回 `false`；按 `format` 计算 `totalSize` 并与 `data` 大小比较，不足返回 `false`。

> 注：`AudioDataInit.data` 的内存布局应符合 planar/interleaved 格式的要求；规范无法验证采样值是否符合其 `AudioSampleFormat`。

#### 9.2.6 Transfer and Serialization

- **Transfer steps**：`[[Detached]]` 为 `true` 则抛 `DataCloneError`；将各内部槽位值赋给 `dataHolder`；对原值执行 Close AudioData。
- **Transfer-receiving steps**：将 `dataHolder` 字段赋回 `AudioData` 内部槽位。
- **Serialization steps**：`[[Detached]]` 或 `forStorage = true` 时抛 `DataCloneError`；否则创建对同一 resource 的新引用并赋给 `serialized.resource reference`，复制其他槽位。
- **Deserialization steps**：把序列化字段赋回 `AudioData` 内部槽位。

#### 9.2.7 AudioDataCopyToOptions

```idl
dictionary AudioDataCopyToOptions {
  [EnforceRange] required unsigned long planeIndex;
  [EnforceRange] unsigned long frameOffset = 0;
  [EnforceRange] unsigned long frameCount;
  AudioSampleFormat format;
};
```

- **`planeIndex`**：要复制的平面索引。
- **`frameOffset`，默认 `0`**：源平面的起始帧偏移。
- **`frameCount`**：要复制的帧数；缺省则为从 `frameOffset` 起所有帧。
- **`format`**：目标 `AudioSampleFormat`，缺省使用 `[[format]]`。若 UA 不支持该格式转换会抛 `NotSupportedError`；转换到 `f32-planar` 必须始终受支持。

> 注：与 [WEBAUDIO] 集成时可请求 `f32-planar` 并据此构造 `AudioBuffer` 或经 `AudioWorklet` 渲染。

### 9.3 音频采样格式（Audio Sample Format）

音频采样格式描述表示单个采样的数值类型（如 32 位浮点）以及不同通道采样的排列方式（interleaved 或 planar）。**音频采样类型**仅指存储数据的数值类型与区间，包括 `u8`、`s16`、`s32`、`f32`（分别对应 8 位无符号、16 位有符号、32 位有符号、32 位浮点）。**音频 buffer 排列**仅指样本在内存中的布局（planar 或 interleaved）。

**采样（sample）**指特定时间特定通道上信号的单个值。**帧（frame / sample-frame）**指多通道信号在同一时刻所有通道的取值集合。

> 注：若信号为单声道，frame 与 sample 含义相同。

本规范中所有音频采样都使用线性脉冲编码调制（Linear PCM），量化级别在值域内均匀分布。

> 注：预期与本规范一起使用的 Web Audio API 也使用 Linear PCM。

```idl
enum AudioSampleFormat {
  "u8",
  "s16",
  "s32",
  "f32",
  "u8-planar",
  "s16-planar",
  "s32-planar",
  "f32-planar",
};
```

- **`u8`**：8 位无符号整数，interleaved 排列。
- **`s16`**：16 位有符号整数，interleaved 排列。
- **`s32`**：32 位有符号整数，interleaved 排列。
- **`f32`**：32 位浮点，interleaved 排列。
- **`u8-planar`**：8 位无符号整数，planar 排列。
- **`s16-planar`**：16 位有符号整数，planar 排列。
- **`s32-planar`**：32 位有符号整数，planar 排列。
- **`f32-planar`**：32 位浮点，planar 排列。

#### 9.3.1 音频 buffer 排列

当 `AudioSampleFormat` 是 **interleaved** 时：来自不同通道的音频采样按 §9.3.3 通道顺序在同一 buffer 内连续排列；`AudioData` 只有一个平面，元素数为 `[[number of frames]] * [[number of channels]]`。

当格式是 **planar** 时：不同通道的音频采样位于不同 buffer（顺序参见 §9.3.3）；`AudioData` 的平面数等于 `[[number of channels]]`，每平面元素数为 `[[number of frames]]`。

> 注：Web Audio API 当前仅使用 `f32-planar`。

#### 9.3.2 采样数值范围

采样类型的最小值/最大值是音频可能发生削波（clipping）的临界值；中间处理过程中可能临时超出。偏置值（bias）通常对应值域中点（但区间往往不对称），由偏置值组成的 buffer 表示静音。

| 采样类型 | IDL 类型 | 最小值 | 偏置值 | 最大值 |
| --- | --- | --- | --- | --- |
| u8  | octet | 0 | 128 | +255 |
| s16 | short | -32768 | 0 | +32767 |
| s32 | long | -2147483648 | 0 | +2147483647 |
| f32 | float | -1.0 | 0.0 | +1.0 |

> 注：没有原生 24 位数据类型，但 24 位音频很常见，因此常用 32 位整数存放 24 位内容。

`AudioData` 若包含 24 位采样，应存储为 `s32` 或 `f32`。使用 `s32` 时每个采样必须左移 8 位，因此超出 24 位范围（[-8388608, +8388607]）会被削波。为避免削波以无损传输，可转换为 `f32`。

> 注：虽然 `u8`、`s16`、`s32` 受存储类型限制无法避免削波，但实现应在处理 `f32` 时谨慎避免内部削波。

#### 9.3.3 音频通道顺序

解码时，`AudioData` 中的音频通道顺序必须与 `EncodedAudioChunk` 中的一致。编码时亦然。**不做任何通道重排**。

> 注：容器隐式或显式给出通道映射：即某一索引对应哪个通道。

### 9.4 VideoFrame 接口

> 注：`VideoFrame` 是 `CanvasImageSource`。`VideoFrame` 可以传给任何接受 `CanvasImageSource` 的方法，包括 `CanvasDrawImage` 的 `drawImage()`。

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
  readonly attribute unsigned long long? duration;   // 微秒
  readonly attribute long long timestamp;            // 微秒
  readonly attribute VideoColorSpace colorSpace;

  VideoFrameMetadata metadata();
  unsigned long allocationSize(optional VideoFrameCopyToOptions options = {});
  Promise<sequence<PlaneLayout>> copyTo(
    AllowSharedBufferSource destination,
    optional VideoFrameCopyToOptions options = {});

  VideoFrame clone();
  undefined close();
};

dictionary VideoFrameInit {
  unsigned long long duration;    // 微秒
  long long timestamp;            // 微秒
  AlphaOption alpha = "keep";
  DOMRectInit visibleRect;
  double rotation = 0;
  boolean flip = false;
  [EnforceRange] unsigned long displayWidth;
  [EnforceRange] unsigned long displayHeight;
  VideoFrameMetadata metadata;
};

dictionary VideoFrameBufferInit {
  required VideoPixelFormat format;
  required [EnforceRange] unsigned long codedWidth;
  required [EnforceRange] unsigned long codedHeight;
  required [EnforceRange] long long timestamp;     // 微秒
  [EnforceRange] unsigned long long duration;      // 微秒
  sequence<PlaneLayout> layout;
  DOMRectInit visibleRect;
  double rotation = 0;
  boolean flip = false;
  [EnforceRange] unsigned long displayWidth;
  [EnforceRange] unsigned long displayHeight;
  VideoColorSpaceInit colorSpace;
  sequence<ArrayBuffer> transfer = [];
  VideoFrameMetadata metadata;
};

dictionary VideoFrameMetadata {
  // Possible members are recorded in the VideoFrame Metadata Registry.
};
```

#### 9.4.1 内部槽位

- **`[[resource reference]]`**：对持有该帧像素数据的 media resource 的引用。
- **`[[format]]`**：`VideoPixelFormat`，描述像素格式。
- **`[[coded width]]` / `[[coded height]]`**：像素宽高，可能包含不可见填充，未做宽高比调整。
- **`[[visible left]]` / `[[visible top]]` / `[[visible width]]` / `[[visible height]]`**：可见矩形偏移与尺寸。
- **`[[rotation]]`**：渲染时应用的顺时针旋转角度，先于 flip 应用。
- **`[[flip]]`**：渲染时是否水平翻转，后于 rotation 应用。
- **`[[display width]]` / `[[display height]]`**：应用宽高比调整后的显示尺寸。
- **`[[duration]]`**：呈现持续时间（微秒），从对应 `EncodedVideoChunk` 复制。
- **`[[timestamp]]`**：呈现时间戳（微秒），从对应 `EncodedVideoChunk` 复制。
- **`[[color space]]`**：该帧关联的 `VideoColorSpace`。
- **`[[metadata]]`**：关联的 `VideoFrameMetadata`，可能成员登记在 [webcodecs-video-frame-metadata-registry]；设计上所有 `VideoFrameMetadata` 属性可序列化。

#### 9.4.2 构造函数

**`VideoFrame(image, init)`**：

1. 检查 `image` 可用性，若抛错或返回 `bad` 则抛 `InvalidStateError`。
2. 若 `image` 不是 origin-clean，抛 `SecurityError`。
3. 根据 `image` 类型分支：
   - `HTMLImageElement`/`SVGImageElement`：必须提供 `timestamp`；若图像没有自然尺寸则抛 `InvalidStateError`；拷贝媒体数据（动图取默认帧或第一帧）；运行 Initialize Frame With Resource 算法。
   - `HTMLVideoElement`：若 `networkState = NETWORK_EMPTY`，抛 `InvalidStateError`；取当前播放位置的帧；若 `init` 中无 metadata 则使用该帧的 metadata；运行 Initialize Frame From Other Frame 算法。
   - `HTMLCanvasElement`/`ImageBitmap`/`OffscreenCanvas`：必须提供 `timestamp`；拷贝位图数据；运行 Initialize Frame With Resource 算法。
   - `VideoFrame`：运行 Initialize Frame From Other Frame 算法。

> 注：建议作者提供有意义的 `timestamp`，以供编码器（如 VideoEncoder 的 framerate 处理）做出时序决策。

**`VideoFrame(data, init)`**：

1. 若 `init` 不是有效的 `VideoFrameBufferInit`，抛 `TypeError`。
2. 解析可见矩形（默认 `(0,0,codedWidth,codedHeight)`）。
3. 计算布局与所需 buffer 大小。
4. 校验 `data.byteLength` 足够、transfer 合法性。
5. 视情况复用或拷贝 `data` 构造 resource。
6. 解析旋转、应用可见矩形/翻转、计算显示尺寸。
7. 应用 `init.colorSpace` 并通过 Pick Color Space 算法确定 `[[color space]]`。
8. 返回 frame。

#### 9.4.3 属性

- **`format`，`VideoPixelFormat?`，只读**：像素格式。
- **`codedWidth` / `codedHeight`，`unsigned long`，只读**：像素尺寸，可能包含不可见填充。
- **`codedRect`，`DOMRectReadOnly?`，只读**：宽高与 `codedWidth/Height` 相同，`x=y=0`；便于与 `allocationSize`/`copyTo` 配合。`[[Detached]]` 时为 `null`。
- **`visibleRect`，`DOMRectReadOnly?`，只读**：可见矩形。`[[Detached]]` 时为 `null`。
- **`rotation`，`double`，只读**：渲染时应用的顺时针旋转度数，先于 flip。
- **`flip`，`boolean`，只读**：渲染时是否水平翻转，后于 rotation。
- **`displayWidth` / `displayHeight`，`unsigned long`，只读**：应用 rotation 与宽高比调整后的显示尺寸。
- **`timestamp`，`long long`，只读**：呈现时间戳（微秒）。
- **`duration`，`unsigned long long?`，只读**：呈现持续时间（微秒）。
- **`colorSpace`，`VideoColorSpace`，只读**：关联的 `VideoColorSpace`。

#### 9.4.4 内部结构

- 一个 `allocationSize`（`unsigned long`）。
- 一个 `computedLayouts`（已计算平面布局列表）。

**已计算平面布局（computed plane layout）**包含：

- `destinationOffset`（`unsigned long`）
- `destinationStride`（`unsigned long`）
- `sourceTop`（`unsigned long`）
- `sourceHeight`（`unsigned long`）
- `sourceLeftBytes`（`unsigned long`）
- `sourceWidthBytes`（`unsigned long`）

#### 9.4.5 方法

- **`allocationSize(options)`**：返回按 `options` 描述复制所需最小字节长度。
- **`copyTo(destination, options)`**：异步地把帧平面拷贝到 `destination`。若目标格式为 RGBA/RGBX/BGRA/BGRX 之一，则先通过 Convert to RGB frame 转为 RGB 后再拷贝。返回 `Promise<sequence<PlaneLayout>>`。多次调用的 Promise 不保证按调用顺序解析。
- **`clone()`**：返回共享同一 media resource 的新 `VideoFrame`。
- **`close()`**：运行 Close VideoFrame 算法；close 是终态。
- **`metadata()`**：返回 `[[metadata]]` 的拷贝。

#### 9.4.6 算法

- **Create a VideoFrame(output, timestamp, duration, displayAspectWidth, displayAspectHeight, colorSpace, rotation, flip)**：构造新 `VideoFrame`，根据提供的可见矩形/旋转/翻转/显示宽高等设置内部槽位，并通过 Pick Color Space 设置 `[[color space]]`。
- **Pick Color Space(overrideColorSpace, format)**：若提供 `overrideColorSpace` 则返回以其初始化的 `VideoColorSpace`，UA 可以用启发式替换 null 字段；否则若格式为 RGB 则返回 sRGB Color Space；否则返回 REC709 Color Space。
- **Validate VideoFrameInit(format, codedWidth, codedHeight)**：校验 visibleRect、displayWidth/displayHeight 的合法性。
- **VideoFrameBufferInit 有效性**：可见矩形不能越界、`codedWidth/Height != 0`、`displayWidth/Height != 0`。
- **Initialize Frame From Other Frame(init, frame, otherFrame)**：根据 otherFrame 共享 resource 并根据 init 的 `alpha/visibleRect/rotation/flip` 等计算。
- **Initialize Frame With Resource(init, frame, resource, codedWidth, codedHeight, baseRotation, baseFlip, defaultDisplayWidth, defaultDisplayHeight)**：从 resource 直接构造。
- **Initialize Visible Rect, Orientation, and Display Size(...)**：综合 baseRotation/baseFlip 与 init 计算最终旋转/翻转/显示尺寸。
- **Clone VideoFrame(frame)** / **Close VideoFrame(frame)**：分别返回共享 resource 的新 `VideoFrame` 或清空状态。
- **Parse Rotation(rotation)**：把 rotation 规整为 0–360 度。
- **Add Rotations(baseRotation, baseFlip, rotation)**：合并基础与新旋转并规整。
- **Parse VideoFrameCopyToOptions(options)**：解析 rect/layout/format，返回 combinedLayout。
- **Verify Rect Offset Alignment(format, rect)**：检查 rect 偏移满足子采样对齐。
- **Parse Visible Rect(defaultRect, overrideRect, codedWidth, codedHeight, format)**：校验覆盖矩形的范围与对齐。
- **Compute Layout and Allocation Size(parsedRect, format, layout)**：计算每个平面的偏移/stride/大小，校验平面不重叠，返回 combinedLayout。
- **Convert PredefinedColorSpace to VideoColorSpace(colorSpace)**：把 `"srgb"` / `"display-p3"` 映射为对应 `VideoColorSpace`。
- **Convert to RGB frame(frame, format, colorSpace)**：把帧转换为指定 RGB 格式与色彩空间。
- **Copy VideoFrame metadata(metadata)**：通过 StructuredSerialize/Deserialize 创建 metadata 的副本，保证 `VideoFrame` 的 metadata 不可变。

#### 9.4.7 Transfer and Serialization

- **Transfer steps**：`[[Detached]]` 为 `true` 则抛 `DataCloneError`；将各内部槽位值赋给 `dataHolder`；对原值执行 Close VideoFrame。
- **Transfer-receiving steps**：将 `dataHolder` 字段赋回 `VideoFrame` 内部槽位。
- **Serialization steps**：`[[Detached]]` 或 `forStorage = true` 时抛 `DataCloneError`；否则创建对同一 resource 的新引用并赋给 `serialized.resource reference`，复制其他槽位。
- **Deserialization steps**：把序列化字段赋回 `VideoFrame` 内部槽位。

#### 9.4.8 Rendering

渲染时（如 `CanvasDrawImage.drawImage()`），`VideoFrame` 必须先转换为与渲染目标兼容的色彩空间，除非显式禁用了色彩空间转换。

`ImageBitmap` 构造时的色彩空间转换由 `ImageBitmapOptions.colorSpaceConversion` 控制，设为 `"none"` 可禁用。

`VideoFrame` 的渲染过程：对 media resource 做必要的色彩空间转换、裁剪到 `visibleRect`、顺时针旋转 `rotation` 度，若 `flip` 为 `true` 则再水平翻转。

### 9.5 VideoFrame CopyTo() Options

```idl
dictionary VideoFrameCopyToOptions {
  DOMRectInit rect;
  sequence<PlaneLayout> layout;
  VideoPixelFormat format;
  PredefinedColorSpace colorSpace;
};
```

> 注：`copyTo()` / `allocationSize()` 步骤会强制以下要求：`rect` 坐标按 `[[format]]` 子采样对齐；若提供 `layout`，必须为每个平面提供 `PlaneLayout`。

- **`rect`，`DOMRectInit`**：要复制的像素矩形；缺省使用 `visibleRect`。可传入 `codedRect` 使用完整 coded 区域。默认 `rect` 可能不满足采样对齐，导致调用失败。
- **`layout`，`sequence<PlaneLayout>`**：每个平面在目标 buffer 中的 offset/stride；缺省为紧密打包。指定的平面不能重叠。
- **`format`，`VideoPixelFormat`**：目标像素格式，可选值为 `RGBA`、`RGBX`、`BGRA`、`BGRX`；缺省则使用原 `format`。
- **`colorSpace`，`PredefinedColorSpace`**：仅当 `format` 为 RGBA/RGBX/BGRA/BGRX 之一时生效，用作目标色彩空间；缺省为 `"srgb"`。

### 9.6 DOMRects in VideoFrame

> 注：`VideoFrame` 像素只能按整数寻址，所有传给 `DOMRectInit` 的浮点值都会被截断。

### 9.7 Plane Layout

```idl
dictionary PlaneLayout {
  [EnforceRange] required unsigned long offset;
  [EnforceRange] required unsigned long stride;
};
```

- **`offset`**：平面在 `BufferSource` 中开始的字节偏移。
- **`stride`**：每行字节数（可包含 padding）。

### 9.8 Pixel Format

```idl
enum VideoPixelFormat {
  // 4:2:0 Y, U, V
  "I420",
  "I420P10",
  "I420P12",
  // 4:2:0 Y, U, V, A
  "I420A",
  "I420AP10",
  "I420AP12",
  // 4:2:2 Y, U, V
  "I422",
  "I422P10",
  "I422P12",
  // 4:2:2 Y, U, V, A
  "I422A",
  "I422AP10",
  "I422AP12",
  // 4:4:4 Y, U, V
  "I444",
  "I444P10",
  "I444P12",
  // 4:4:4 Y, U, V, A
  "I444A",
  "I444AP10",
  "I444AP12",
  // 4:2:0 Y, UV
  "NV12",
  // 4:4:4 RGBA
  "RGBA",
  // 4:4:4 RGBX (opaque)
  "RGBX",
  // 4:4:4 BGRA
  "BGRA",
  // 4:4:4 BGRX (opaque)
  "BGRX",
};
```

子采样指一个采样描述最终图像中多个像素，水平、垂直或两者皆有，子采样因子是图像中由子采样样本派生的最终像素数。

若 `VideoPixelFormat` 含 alpha 通道，则其等价 opaque 格式是同名的无 alpha 格式；若不含 alpha，则其等价 opaque 格式就是自身。除非另有说明，整数值均为无符号。

具体格式说明：

- **`I420`**：三平面（Y/U/V），又称 Planar YUV 4:2:0。U/V 平面相对 Y 在水平和垂直方向上 2 倍子采样。每样本 8 位。Y 平面 `codedWidth * codedHeight` 个样本（字节），按行排布；U/V 平面的行数为 `codedHeight / 2` 向上取整，每行样本数为 `codedWidth / 2` 向上取整。`visibleRect.x`、`visibleRect.y` 必须为偶数。
- **`I420P10`**：与 I420 类似但每样本 10 位，按小端序存储为 16 位整数；其他相同。
- **`I420P12`**：与 I420P10 类似但每样本 12 位。
- **`I420A`**：四平面（Y/U/V/A），又称 Planar YUV 4:2:0 with alpha。U/V 相对 Y/A 在两个方向上 2 倍子采样。每样本 8 位。其等价 opaque 格式为 `I420`。
- **`I420AP10`** / **`I420AP12`**：与 I420A 类似但分别为 10/12 位。等价 opaque 格式为 `I420P10` / `I420P12`。
- **`I422`**：三平面（Y/U/V），又称 Planar YUV 4:2:2。U/V 相对 Y 在水平方向上 2 倍子采样，垂直方向不子采样。每样本 8 位。`visibleRect.x` 必须为偶数。
- **`I422P10` / `I422P12`**：与 I422 类似但分别为 10/12 位。
- **`I422A` / `I422AP10` / `I422AP12`**：含 alpha 的 4:2:2 格式，对应 8/10/12 位。等价 opaque 格式为 `I422` / `I422P10` / `I422P12`（注意：规范中 `I422AP10`/`I422AP12` 的等价 opaque 格式存在文档笔误，原文写为 I420P10，本翻译按原文如实保留）。
- **`I444`**：三平面（Y/U/V），又称 Planar YUV 4:4:4，不做子采样。每样本 8 位。
- **`I444P10` / `I444P12`**：与 I444 类似但分别为 10/12 位。
- **`I444A` / `I444AP10` / `I444AP12`**：含 alpha 的 4:4:4 格式，对应 8/10/12 位。
- **`NV12`**：两平面（Y 与 UV）。U/V 在两个方向上相对 Y 2 倍子采样，每样本 8 位。UV 平面的行数为 `codedHeight / 2` 向上取整，每行元素数为 `codedWidth / 2` 向上取整，每个元素包含按 U、V 顺序的两个色度样本。`visibleRect.x`、`visibleRect.y` 必须为偶数。规范给出了一张 16×10 NV12 图像在内存中的示意图。
- **`RGBA`**：单平面，按 R/G/B/A 顺序排列，每样本 8 位，每像素 32 位。其等价 opaque 格式为 `RGBX`。
- **`RGBX`**：单平面，第四分量忽略，图像始终不透明。
- **`BGRA`**：单平面，按 B/G/R/A 顺序。等价 opaque 为 `BGRX`。
- **`BGRX`**：单平面，第四分量忽略，图像始终不透明。

### 9.9 Video Color Space Interface

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

dictionary VideoColorSpaceInit {
  VideoColorPrimaries? primaries = null;
  VideoTransferCharacteristics? transfer = null;
  VideoMatrixCoefficients? matrix = null;
  boolean? fullRange = null;
};
```

#### 9.9.1 内部槽位

- `[[primaries]]`：色彩原色。
- `[[transfer]]`：传输特性。
- `[[matrix]]`：矩阵系数。
- `[[full range]]`：是否使用全范围颜色值。

#### 9.9.2 构造函数

设 `c` 为新 `VideoColorSpace`，依次把 `init.primaries/transfer/matrix/fullRange` 赋给对应槽位，返回 `c`。

#### 9.9.3 属性

- **`primaries`，`VideoColorPrimaries?`，只读**：返回 `[[primaries]]`。
- **`transfer`，`VideoTransferCharacteristics?`，只读**：返回 `[[transfer]]`。
- **`matrix`，`VideoMatrixCoefficients?`，只读**：返回 `[[matrix]]`。
- **`fullRange`，`boolean?`，只读**：返回 `[[full range]]`。

### 9.10 Video Color Primaries

```idl
enum VideoColorPrimaries {
  "bt709",
  "bt470bg",
  "smpte170m",
  "bt2020",
  "smpte432",
};
```

- **`bt709`**：BT.709 与 sRGB 使用的原色，[H.273] §8.1 表 2 值 1。
- **`bt470bg`**：BT.601 PAL 使用的原色，[H.273] §8.1 表 2 值 5。
- **`smpte170m`**：BT.601 NTSC 使用的原色，[H.273] §8.1 表 2 值 6。
- **`bt2020`**：BT.2020 与 BT.2100 使用的原色，[H.273] §8.1 表 2 值 9。
- **`smpte432`**：P3 D65 使用的原色，[H.273] §8.1 表 2 值 12。

### 9.11 Video Transfer Characteristics

```idl
enum VideoTransferCharacteristics {
  "bt709",
  "smpte170m",
  "iec61966-2-1",
  "linear",
  "pq",
  "hlg",
};
```

- **`bt709`**：BT.709 传输特性，[H.273] §8.2 表 3 值 1。
- **`smpte170m`**：BT.601 传输特性，[H.273] §8.2 表 3 值 6（功能上等同于 `bt709`）。
- **`iec61966-2-1`**：sRGB 传输特性，[H.273] §8.2 表 3 值 13。
- **`linear`**：线性 RGB 传输特性，[H.273] §8.2 表 3 值 8。
- **`pq`**：BT.2100 PQ 传输特性，[H.273] §8.2 表 3 值 16。
- **`hlg`**：BT.2100 HLG 传输特性，[H.273] §8.2 表 3 值 18。

### 9.12 Video Matrix Coefficients

```idl
enum VideoMatrixCoefficients {
  "rgb",
  "bt709",
  "bt470bg",
  "smpte170m",
  "bt2020-ncl",
};
```

- **`rgb`**：sRGB 矩阵系数，[H.273] §8.3 表 4 值 0。
- **`bt709`**：BT.709 矩阵系数，[H.273] §8.3 表 4 值 1。
- **`bt470bg`**：BT.601 PAL 矩阵系数，[H.273] §8.3 表 4 值 5。
- **`smpte170m`**：BT.601 NTSC 矩阵系数，[H.273] §8.3 表 4 值 6（功能上等同于 `bt470bg`）。
- **`bt2020-ncl`**：BT.2020 NCL 矩阵系数，[H.273] §8.3 表 4 值 9。

---

## 10. 图像解码（Image Decoding）

### 10.1 背景

本章定义 `ImageDecoder`，与 `createImageBitmap` 互补，支持按帧解码动图、渐进式图像等场景，并能与 WebCodecs 的 `VideoFrame` 直接对接。

### 10.2 ImageDecoder 接口

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
```

#### 10.2.1 内部槽位

- `[[control message queue]]` / `[[message queue blocked]]` / `[[codec work queue]]`：与 codec 一致。
- **`[[ImageTrackList]]`**：描述 `[[encoded data]]` 中轨道的 `ImageTrackList`。
- **`[[type]]`**：构造时给定的 MIME 类型字符串。
- **`[[complete]]`**：布尔值，指示 `[[encoded data]]` 是否已完全缓冲。
- **`[[completed promise]]`**：当 `[[complete]]` 变为 `true` 时解析的 promise。
- **`[[codec implementation]]`**：底层图像解码器实现。
- **`[[encoded data]]`**：待解码的图像字节序列。
- **`[[prefer animation]]`**：构造时的 `preferAnimation`。
- **`[[pending decode promises]]`**：调用 `decode()` 返回的尚未解析的 promise 列表。
- **`[[internal selected track index]]`**：解码算法使用的图像轨道索引。
- **`[[tracks established]]`**：轨道列表是否已建立。
- **`[[closed]]`**：ImageDecoder 是否已处于永久关闭状态。
- **`[[progressive frame generations]]`**：帧索引到 Progressive Image Frame Generation 的映射。

#### 10.2.2 构造函数

`ImageDecoder(init)`：

> 注：在已构造的 `ImageDecoder` 上调用 `decode()` 时，若用户代理不支持 `type` 会触发 `NotSupportedError`，建议先调用 `isTypeSupported()`。

执行：

1. 若 `init` 不是有效的 `ImageDecoderInit`，抛 `TypeError`。
2. 处理 `transfer` 中的重复引用与 detached。
3. 创建 `d` 并初始化各内部槽位。
4. 根据 `init.data` 类型分支：
   - **`ReadableStream`**：创建空 `[[encoded data]]`，`[[complete]] = false`；入队配置消息；处理队列；获取 reader 并在并行中运行 Fetch Stream Data Loop。
   - **`BufferSource`**：视 `transfer` 选择复用或拷贝；`[[complete]] = true`；解析 `[[completed promise]]`；入队配置和解码元数据消息。
5. 返回 `d`。

**配置消息**：若 `Check Type Support(init.type) = false`，运行 Close ImageDecoder(`NotSupportedError`) 并返回 `"processed"`；否则赋值 `[[codec implementation]]`，按 `colorSpaceConversion`、`desiredWidth`、`desiredHeight` 配置之。

**解码元数据消息**：在 `[[codec work queue]]` 上运行 Establish Tracks。

#### 10.2.3 属性

- **`type`，`DOMString`，只读**：构造时给定的 MIME 类型。
- **`complete`，`boolean`，只读**：指示 `[[encoded data]]` 是否完全缓冲。
- **`completed`，`Promise<undefined>`，只读**：`[[complete]]` 变为 `true` 时解析的 promise。
- **`tracks`，`ImageTrackList`，只读**：可用轨道列表（含选中机制）。

#### 10.2.4 方法

- **`decode(options)`**：入队一条控制消息按 `options` 解码帧。步骤包括校验 `[[closed]]` 与轨道选择；若 `options` 未提供则新建默认 `ImageDecodeOptions`；创建 promise 并加入 `[[pending decode promises]]`；处理队列返回 promise。
  - **运行"解码图像"控制消息**：等待 `[[tracks established]]`；若 `options.completeFramesOnly = false` 且支持渐进式解码，则运行 Decode Progressive Frame；否则运行 Decode Complete Frame。
- **`reset()`**：运行 Reset ImageDecoder 算法并传入 `AbortError`。
- **`close()`**：运行 Close ImageDecoder 算法并传入 `AbortError`。
- **`static isTypeSupported(type)`**：若 type 不是合法图像 MIME 类型，返回 `TypeError` 拒绝的 Promise；否则并行运行 Check Type Support 算法并 resolve 结果。

#### 10.2.5 算法

- **Fetch Stream Data Loop(reader)**：不断从 reader 读取 chunk，按 chunk/close/error 三个回调分别将字节追加到 `[[encoded data]]`、设置 `[[complete]] = true`、触发 Close ImageDecoder(`NotReadableError`)。每次追加后若 `[[tracks established]] = false` 则运行 Establish Tracks，否则运行 Update Tracks。
- **Establish Tracks**：若数据不足以确定轨道数则视情况中止或关闭；若轨道数为 0 则关闭；为每个轨道构造 `ImageTrack`（含 animated/frameCount/repetitionCount/selected 字段），调用 Get Default Selected Track Index 选择默认轨道，最后通过任务 resolve `[[ready promise]]`。
- **Get Default Selected Track Index(trackList)**：若图像标识了 Primary Image Track，则依 `[[prefer animation]]` 决定；否则返回 0。
- **Update Tracks**：对比当前 `frameCount` 与新缓冲数据指示的 `frameCount`，生成更新列表并通过任务更新对应 `ImageTrack` 的 `[[frame count]]`。
- **Decode Complete Frame(frameIndex, promise)**：等待数据足以完整解码；若发现畸形数据则运行 Fatally Reject Bad Data；否则解码，构造 `ImageDecodeResult`（`complete = true`），生成 timestamp/duration/rotation/flip，运行 Create a VideoFrame 算法，然后 Resolve Decode。
- **Decode Progressive Frame(frameIndex, promise)**：与 Decode Complete Frame 类似，但可能产生 detail 渐增的中间帧，并把 Progressive Image Frame Generation 存入 `[[progressive frame generations]]`；只有得到最终全细节输出时 `complete = true`。
- **Resolve Decode(promise, result)**：通过任务解析 promise。
- **Reject Infeasible Decode(promise)**：若 `complete = true` 则使用 `RangeError`，否则 `InvalidStateError`，并 reject promise。
- **Fatally Reject Bad Data**：关闭 ImageDecoder 并传入 `EncodingError`。
- **Check Type Support(type)**：用户代理是否能解码该类型。
- **Reset ImageDecoder(exception)**：通知底层实现中止解码；reject 所有 pending decode promise。
- **Close ImageDecoder(exception)**：运行 Reset ImageDecoder；`[[closed]] = true`；释放资源；清空 `[[ImageTrackList]]`；若未 complete 则 reject `[[completed promise]]`。

### 10.3 ImageDecoderInit Interface

```idl
typedef (AllowSharedBufferSource or ReadableStream) ImageBufferSource;

dictionary ImageDecoderInit {
  required DOMString type;
  required ImageBufferSource data;
  ColorSpaceConversion colorSpaceConversion = "default";
  [EnforceRange] unsigned long desiredWidth;
  [EnforceRange] unsigned long desiredHeight;
  boolean preferAnimation;
  sequence<ArrayBuffer> transfer = [];
};
```

**有效性校验**：

1. 若 `type` 不是合法的图像 MIME 类型，返回 `false`。
2. 若 `data` 是 `ReadableStream` 且处于 disturbed/locked 状态，返回 `false`。
3. 若 `data` 是 `BufferSource`：若 detached 返回 `false`；若为空返回 `false`。
4. `desiredWidth` 与 `desiredHeight` 必须同时存在。
5. 返回 `true`。

> 注：合法图像 MIME 类型指根据 [RFC9110] §8.3.1 type 为 `image` 的 MIME 类型字符串。

字段说明：

- **`type`**：图像文件的 MIME 类型。
- **`data`**：`BufferSource` 或 `ReadableStream`，按 `type` 描述的已编码图像字节。
- **`colorSpaceConversion`**：色彩空间转换策略，定义见 `ImageBitmapOptions`。
- **`desiredWidth` / `desiredHeight`**：期望的解码尺寸，best-effort。
- **`preferAnimation`**：多轨道时是否优先选择动画轨道。参见 Get Default Selected Track Index 算法。

### 10.4 ImageDecodeOptions Interface

```idl
dictionary ImageDecodeOptions {
  [EnforceRange] unsigned long frameIndex = 0;
  boolean completeFramesOnly = true;
};
```

- **`frameIndex`，默认 `0`**：要解码的帧索引。
- **`completeFramesOnly`，默认 `true`**：对 Progressive Image 而言，`false` 允许输出细节较少的中间帧；对同一 `frameIndex` 的多次调用将产生更高 Progressive Image Frame Generation 的输出，最终得到全细节图。若 `true`、不是 Progressive Image 或 UA 不支持渐进式解码，则 `decode()` 只在全细节图解码完成后解析。

> 注：对于 Progressive Image，可将 `completeFramesOnly = false` 与 ReadableStream 一起使用，在图像仍在网络缓冲时就为用户提供预览；最终全细节图解析时 `ImageDecodeResult.complete = true`。

### 10.5 ImageDecodeResult Interface

```idl
dictionary ImageDecodeResult {
  required VideoFrame image;
  required boolean complete;
};
```

- **`image`，`VideoFrame`**：解码得到的图像。
- **`complete`，`boolean`**：指示 `image` 是否为最终全细节输出。`completeFramesOnly = true` 时该值总为 `true`。

### 10.6 ImageTrackList Interface

```idl
[Exposed=(Window, DedicatedWorker), SecureContext]
interface ImageTrackList {
  getter ImageTrack(unsigned long index);
  readonly attribute Promise<undefined> ready;
  readonly attribute unsigned long length;
  readonly attribute long selectedIndex;
  readonly attribute ImageTrack? selectedTrack;
};
```

#### 10.6.1 内部槽位

- **`[[ready promise]]`**：`ImageTrackList` 填充完毕时 resolve 的 promise。
- **`[[track list]]`**：`ImageTrack` 列表。
- **`[[selected index]]`**：当前选中轨道在 `[[track list]]` 中的索引，`-1` 表示未选中。

#### 10.6.2 属性

- **`ready`，`Promise<undefined>`，只读**：返回 `[[ready promise]]`。
- **`length`，`unsigned long`，只读**：返回 `[[track list]]` 长度。
- **`selectedIndex`，`long`，只读**：返回 `[[selected index]]`。
- **`selectedTrack`，`ImageTrack?`，只读**：`[[selected index]] = -1` 时返回 `null`，否则返回对应 `ImageTrack`。

### 10.7 ImageTrack Interface

```idl
[Exposed=(Window, DedicatedWorker), SecureContext]
interface ImageTrack {
  readonly attribute boolean animated;
  readonly attribute unsigned long frameCount;
  readonly attribute unrestricted float repetitionCount;
  attribute boolean selected;
};
```

#### 10.7.1 内部槽位

- **`[[ImageDecoder]]`**：构造该 `ImageTrack` 的 `ImageDecoder` 实例。
- **`[[ImageTrackList]]`**：包含该 `ImageTrack` 的 `ImageTrackList`。
- **`[[animated]]`**：该轨道是否包含多帧动画。
- **`[[frame count]]`**：该轨道帧数。
- **`[[repetition count]]`**：动画重复次数。
- **`[[selected]]`**：该轨道是否被选中解码。

#### 10.7.2 属性

- **`animated`，`boolean`，只读**：返回 `[[animated]]`。对 `frameCount` 起始为 0、随 ReadableStream 数据增加而增长的图像，可据此早期判断 `frameCount` 最终会大于 0。
- **`frameCount`，`unsigned long`，只读**：返回 `[[frame count]]`。
- **`repetitionCount`，`unrestricted float`，只读**：返回 `[[repetition count]]`。
- **`selected`，`boolean`**：getter 返回 `[[selected]]`；setter 会同步更新 `parentTrackList` 的选中索引并在 `[[ImageDecoder]]` 上触发 reset 与内部轨道更新。

---

## 11. 资源回收（Resource Reclamation）

当资源紧张时，用户代理可主动回收 codec。在硬件编解码器数量有限且被多个页面或平台应用共享时尤为常见。

**回收 codec**：用户代理必须运行相应的 close 算法（`Close AudioDecoder`、`Close AudioEncoder`、`Close VideoDecoder`、`Close VideoEncoder`）并传入 `QuotaExceededError`。

何时可回收取决于 codec 是 active、inactive 还是 background：

- **Active codec**：在过去 10 秒内 `[[codec work queue]]` 取得过进展的 codec。`output()` 回调被调用是工作队列进展的可靠信号。
- **Inactive codec**：不满足 active 定义的 codec。
- **Background codec**：其 `ownerDocument`（对 worker 中的 owner set 而言为其 Document）`hidden` 属性为 `true` 的 codec。

用户代理**只能**回收 inactive、background 或兼具二者的 codec；不得回收"active 且 in foreground"的 codec。

此外，对于 active 且 background 的 codec：

- 不得回收 Encoder（`AudioEncoder` 或 `VideoEncoder`），以避免长时间编码任务被打断。
- 不得回收 `AudioDecoder` 或 `VideoDecoder`，若同一全局对象中分别存在 active 的 `AudioEncoder` 或 `VideoEncoder`，以避免长时间转码任务被破坏。
- 不得回收标签页正在可听播放音频时的 `AudioDecoder`。

---

## 12. 安全考虑

（本章在当前 Editor's Draft 中为占位章节，尚未包含具体内容。）

## 13. 隐私考虑

（本章在当前 Editor's Draft 中为占位章节，尚未包含具体内容。）

## 14. 使用 WebCodecs 的最佳实践

（本章在当前 Editor's Draft 中为占位章节，尚未包含具体内容。）

## 15. 致谢（Acknowledgements）

编辑们感谢以下人员对本规范的贡献：Alex Russell、Chris Needham、Dale Curtis、Dan Sanders、Eugene Zemtsov、Francois Daoust、Guido Urdaneta、Harald Alvestrand、Jan-Ivar Bruaroey、Jer Noble、Mark Foltz、Peter Thatcher、Steve Anton、Matt Wolenetz、Rijubrata Bhaumik、Thomas Guilbert、Tuukka Toivonen、Youenn Fablet，同时也感谢通过邮件列表与 issue 做出贡献的众多人士。

工作组谨以此规范献给已故同事 Bernard Aboba。
