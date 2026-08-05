# 理解 FFmpeg 编解码流程

> 前置阅读：[[理解C++指针]]、[[理解C++栈和堆]]
> 讨论基线：C++17 + FFmpeg（3.x 及以上的现代 API）

---

## 零、从"门牌号"看 FFmpeg

FFmpeg 是一个纯 C 库。它没有类、没有析构函数，所有的对象——上下文、包、帧——都是**堆上分配的裸指针**，需要程序员手动释放。

这正好是你 [[理解C++指针]] 里学的模型：**指针变量本身在栈上，它指向的对象在堆上**。FFmpeg 所有 API 本质都是"你给我一个门牌号，我通过它去操作那块内存"。

于是整个 FFmpeg 编程的核心矛盾就浮出水面：**一个没有 RAII 的 C 库，如何用 C++17 安全地使用？** 答案是用 `unique_ptr` + 自定义 deleter 把每种"释放规则"封装起来——这正是本篇笔记反复出现的主题。

---

## 一、整体架构：两条路线

RTSP 本身只是个**传输协议**（说"我要看哪个流、用 TCP 还是 UDP 传"），真正承载视频数据的是 RTP 包。FFmpeg 的 RTSP 解复用器把这些全封装好了，你不需要直接碰 RTP——你只会看到两个抽象：

- **`AVPacket`**：压缩后的数据（H.264/H.265 码流）
- **`AVFrame`**：解码后的原始帧（YUV/RGB 像素）

```
┌──────────┐    RTSP/RTP    ┌────────────────────┐   AVPacket(压缩)   ┌────────────┐
│  RTSP 源  │ ─────────────▶ │ avformat(解复用器)  │ ────────────────▶ │  解码器     │
│ 摄像机/服务器│                │ 负责建会话/拆RTP包   │                   │ H264/H265  │
└──────────┘                 └────────────────────┘                   └─────┬──────┘
                                                                           │ AVFrame(原始)
                                                                           ▼
                                                                    YUV/RGB 像素帧
                                                                   (渲染/保存/分析)

  编码方向反向：
  AVFrame(原始帧) ──▶ 编码器 ──▶ AVPacket ──▶ avformat muxer ──▶ RTSP/RTMP/文件
```

两条路线共用同一套 API 思想：**send 进压缩数据、receive 出解压数据**。

---

## 二、上下文对象与内存管理

### 为什么看到 `AVFormatContext *ic; ic = avformat_alloc_context();`

这是 FFmpeg 里最常见的开场白，逐行拆解：

```c
AVFormatContext *ic;              // ① 声明一个指针变量
ic = avformat_alloc_context();    // ② 在堆上分配对象，取回地址
```

- **第 1 行**：只是准备了一张"门牌"，但还没写门牌号——此时 `ic` 是**野指针**，直接 `ic->...` 会崩。
- **第 2 行**：`avformat_alloc_context()` 在堆上分配一块足够装下 `AVFormatContext` 的内存（内部用 `av_mallocz` **清零**并填默认值），返回地址。`ic = ...` 把门牌号写进 `ic`。

执行完这两行，`ic` 才从"野指针"变成"指向真实对象的有效指针"。

### `AVFormatContext` 是什么

它是 FFmpeg 的**"总管家"**——描述一个媒体文件/流整体状态的大结构体，里面装着：

- `streams[]`：这个媒体里有几条流（视频流、音频流…）
- `duration`：总时长；`bit_rate`：码率
- `pb`：IO 层（底层读写的句柄）
- `iformat` / `oformat`：解复用器 / 复用器

之后所有调用（`avformat_open_input`、`av_read_frame`）都要传它进去。**整个 RTSP 会话或 MP4 文件的状态，最终都挂在某一个 `AVFormatContext` 上。**

### 为什么用指针 + 堆分配，而不是 `AVFormatContext ic;`？

1. **结构体巨大**：成员几十个，且 `streams`、`pb` 内部也是动态分配的。
2. **生命周期要跨函数**：在 `open()` 里创建，要在主循环、关闭时继续用。放栈上函数一返回就没了。
3. **FFmpeg 的 C 设计**：所有上下文都约定指针 + 堆分配。

呼应 [[理解C++栈和堆]]：`ic` 这个指针变量在栈上（8 字节），`*ic` 这个对象在堆上（几百字节）。

### 两种写法的对比

```c
// 方式一：手动分配，可先设置选项
AVFormatContext *ic = avformat_alloc_context();
// 可以预先设置 ic 的字段或自定义 IO...
avformat_open_input(&ic, url, NULL, &opts);

// 方式二：传 NULL，让 FFmpeg 自动分配
AVFormatContext *ic = NULL;
avformat_open_input(&ic, url, NULL, &opts);
```

| 写法 | 什么时候用 |
|------|-----------|
| 手动 `alloc_context` | 想**先设置 context 字段**（自定义 IO、`ic->flags`）再打开 |
| 传 `NULL` | 图省事，不需要预设置 |

### 配套释放

```c
// 成功 open 过：用它，会连 context 一起释放
avformat_close_input(&ic);

// 只 alloc 没 open：用它
avformat_free_context(ic);
```

> 坑：每种对象释放函数都不一样。`AVFormatContext` 用 `avformat_close_input`/`avformat_free_context`，`AVCodecContext` 用 `avcodec_free_context`，`AVFrame` 用 `av_frame_free`，`AVPacket` 用 `av_packet_free`。记不住就容易泄漏——这正是需要 RAII 封装的原因。

### C++17 的第一步：RAII 封装

```cpp
extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/opt.h>
}

// 每种对象对应一种释放函数，封装成 deleter
struct FmtCtxDeleter {
    void operator()(AVFormatContext* p) const noexcept { if (p) avformat_close_input(&p); }
};
struct CodecCtxDeleter {
    void operator()(AVCodecContext* p) const noexcept { if (p) avcodec_free_context(&p); }
};
struct FrameDeleter {
    void operator()(AVFrame* p) const noexcept { if (p) av_frame_free(&p); }
};
struct PacketDeleter {
    void operator()(AVPacket* p) const noexcept { if (p) av_packet_free(&p); }
};

using FmtCtxPtr   = std::unique_ptr<AVFormatContext, FmtCtxDeleter>;
using CodecCtxPtr = std::unique_ptr<AVCodecContext, CodecCtxDeleter>;
using FramePtr    = std::unique_ptr<AVFrame, FrameDeleter>;
using PacketPtr   = std::unique_ptr<AVPacket, PacketDeleter>;
```

有了这层封装，**无论中途抛异常还是提前 return，都不会泄漏**。这就是 C++17 RAII 在音视频里最实在的价值。

---

## 三、解码侧：RTSP 拉流 → 原始帧

### 核心调用时序

```
avformat_open_input()            // 建立 RTSP 会话（唯一的网络阻塞点）
avformat_find_stream_info()      // 解析流信息：分辨率/编码/帧率
av_find_best_stream()            // 找到视频流(和音频流)的 stream index
avcodec_find_decoder()           // 根据 codec_id 找解码器
avcodec_alloc_context3()
avcodec_parameters_to_context()  // 把流参数拷进解码上下文
avcodec_open2()                  // 真正打开解码器

// 主循环
while (av_read_frame(fmt_ctx, &pkt) >= 0) {
    if (pkt.stream_index == video_idx) {
        avcodec_send_packet(codec_ctx, &pkt);                    // ① 送压缩包进解码器
        while (avcodec_receive_frame(codec_ctx, frame) == 0)     // ② 取出原始帧
            handle_frame(frame);
    }
    av_packet_unref(&pkt);
}
// flush：avcodec_send_packet(codec_ctx, nullptr) 吐出残留的 B 帧
```

### 理解 send/receive 两阶段 API

解码器内部有自己的缓冲区：

- `avcodec_send_packet` 返回 `AVERROR(EAGAIN)` → 解码器内部满了，需要先 `receive` 取帧。
- `avcodec_receive_frame` 返回 `AVERROR(EAGAIN)` → 暂无输出帧，正常，继续送。
- 返回 `AVERROR_EOF` → 没有更多输出（flush 时出现）。

所以正确节奏是：**每送一个包，就把能收的帧全部收完**（内层 while）。

### 完整解码骨架

```cpp
#include <string>
#include <memory>
#include <functional>
#include <stdexcept>
// ... 上面的 deleter 和 using 声明 ...

class RtspDecoder {
public:
    explicit RtspDecoder(const std::string& url) { open(url); }

    void run(const std::function<void(AVFrame*)>& on_frame) {
        PacketPtr pkt(av_packet_alloc());
        while (av_read_frame(fmt_ctx_.get(), pkt.get()) >= 0) {
            if (pkt->stream_index != video_stream_index_) {
                av_packet_unref(pkt.get());
                continue;
            }
            if (avcodec_send_packet(codec_ctx_.get(), pkt.get()) < 0)
                throw std::runtime_error("send_packet failed");
            av_packet_unref(pkt.get());

            FramePtr frame(av_frame_alloc());
            while (avcodec_receive_frame(codec_ctx_.get(), frame.get()) == 0)
                on_frame(frame.get());
        }
        // flush：解码器可能缓存着若干 B 帧
        avcodec_send_packet(codec_ctx_.get(), nullptr);
        FramePtr frame(av_frame_alloc());
        while (avcodec_receive_frame(codec_ctx_.get(), frame.get()) == 0)
            on_frame(frame.get());
    }

    int width() const  { return codec_ctx_->width;  }
    int height() const { return codec_ctx_->height; }
    AVPixelFormat pix_fmt() const { return codec_ctx_->pix_fmt; }

private:
    void open(const std::string& url) {
        // ① RTSP 会话选项：优先 TCP，设超时
        AVDictionary* opts = nullptr;
        av_dict_set(&opts, "rtsp_transport", "tcp", 0);   // 或 "udp"
        av_dict_set(&opts, "timeout", "5000000", 0);      // 微秒 = 5 秒
        av_dict_set(&opts, "max_delay", "500000", 0);     // 缓冲时长微秒

        AVFormatContext* raw = nullptr;
        int ret = avformat_open_input(&raw, url.c_str(), nullptr, &opts);
        av_dict_free(&opts);
        if (ret < 0) throw std::runtime_error("open_input failed: " + err_str(ret));
        fmt_ctx_.reset(raw);

        if (avformat_find_stream_info(fmt_ctx_.get(), nullptr) < 0)
            throw std::runtime_error("find_stream_info failed");

        // ② 找视频流
        const AVCodec* dec = nullptr;
        video_stream_index_ = av_find_best_stream(
            fmt_ctx_.get(), AVMEDIA_TYPE_VIDEO, -1, -1, &dec, 0);
        if (video_stream_index_ < 0)
            throw std::runtime_error("no video stream");

        // ③ 初始化解码器
        codec_ctx_.reset(avcodec_alloc_context3(dec));
        if (!codec_ctx_) throw std::runtime_error("alloc context failed");
        avcodec_parameters_to_context(codec_ctx_.get(),
                                      fmt_ctx_->streams[video_stream_index_]->codecpar);
        if (avcodec_open2(codec_ctx_.get(), dec, nullptr) < 0)
            throw std::runtime_error("open decoder failed");
    }

    static std::string err_str(int err) {
        char buf[AV_ERROR_MAX_STRING_SIZE]{};
        av_strerror(err, buf, sizeof buf);
        return buf;
    }

    FmtCtxPtr   fmt_ctx_;
    CodecCtxPtr codec_ctx_;
    int         video_stream_index_{-1};
};
```

### 解码后处理：sws_scale 色彩转换（YUV → RGB）

**为什么需要转换**：视频压缩基于 YUV——人眼对亮度（Y）比对色度（U/V）更敏感，所以可以给色度降采样来省码率。因此解码器输出几乎总是 `AV_PIX_FMT_YUV420P`。但屏幕显示、保存 PNG、送 OpenGL 纹理，都要 RGB。

**YUV 是平面格式，RGB24 是打包格式**：

- YUV420P：`frame->data[0]` 是 Y 平面，`data[1]`/`data[2]` 是 U/V 平面；420 下 U/V 的宽高是 Y 的一半。
- RGB24：连续排列，每 3 个字节一个像素（R、G、B）。

转换用 libswscale 的 `sws_scale`，它还能**同时做缩放**。

**关键概念：stride（每行字节数）**。因为 SIMD 对齐，`frame->linesize[0]` 往往大于 `width`，**绝不能假设每行就是 `width` 字节**——逐行拷贝或计算偏移时都要用它。

```cpp
extern "C" {
#include <libswscale/swscale.h>
}

struct SwsCtxDeleter {
    void operator()(SwsContext* p) const noexcept { if (p) sws_freeContext(p); }
};
using SwsCtxPtr = std::unique_ptr<SwsContext, SwsCtxDeleter>;

// ① 创建转换器（一次创建，逐帧复用，放进解码器类成员）
SwsCtxPtr sws(sws_getContext(
    src->width, src->height, (AVPixelFormat)src->format,  // 源：动态取解码器输出格式
    src->width, src->height, AV_PIX_FMT_RGB24,            // 目标：RGB24（也可顺带改尺寸）
    SWS_BILINEAR, nullptr, nullptr, nullptr));

// ② 为目标图像分配缓冲区（av_image_alloc 自动算好对齐）
uint8_t* dst_data[4] = {nullptr, nullptr, nullptr, nullptr};
int      dst_linesize[4] = {0, 0, 0, 0};
av_image_alloc(dst_data, dst_linesize,
               src->width, src->height, AV_PIX_FMT_RGB24, 32);

// ③ 每解码出一帧，转换一次
sws_scale(sws.get(),
          src->data, src->linesize,   // 源帧的平面指针数组 + 每行步长
          0, src->height,             // 转换范围：行 0..height
          dst_data, dst_linesize);    // 目标缓冲区

// ④ 用完释放目标缓冲区
av_freep(&dst_data[0]);
```

要点：

- `src->format` 用 `(AVPixelFormat)` 动态转换——RTSP 解码输出可能是 YUV420P，也可能是 10-bit 的 YUV420P10，写死会出错。
- 把目标宽高改成别的值，`sws_scale` 会顺带完成缩放（比如 1080p → 640p 预览）。
- `SwsCtxPtr` 作为解码器类成员，和类生命周期一致，符合前面 RAII 封装思路。

---

## 四、编码侧：原始帧 → 压缩流 → 推送

方向反过来，核心思想完全对称：

```
avformat_alloc_output_context2()     // 建输出上下文（flv/rtsp/mp4）
avformat_new_stream()                // 加一条输出流
avcodec_find_encoder(AV_CODEC_ID_H264)
avcodec_alloc_context3()             // 设宽高/像素格式/帧率/码率/GOP
avcodec_open2()
avcodec_parameters_from_context()    // 把编码器参数写回流
avformat_write_header()              // 写封装头

// 每来一帧原始画面：
avcodec_send_frame(enc_ctx, frame)
while (avcodec_receive_packet(enc_ctx, &pkt) == 0) {
    av_packet_rescale_ts(&pkt, enc_time_base, stream_time_base); // 时间基准换算
    av_interleaved_write_frame(out_ctx, &pkt);                    // 写入并推送
}

av_write_trailer(out_ctx)            // flush 收尾
```

### 编码器参数设置要点

```cpp
enc_ctx->width     = src->width;               // 从解码帧取
enc_ctx->height    = src->height;
enc_ctx->pix_fmt   = AV_PIX_FMT_YUV420P;       // 编码器一般只要 YUV420P
enc_ctx->time_base = AVRational{1, 30};        // 时间基准
enc_ctx->framerate = AVRational{30, 1};
enc_ctx->bit_rate  = 2'000'000;                // 2 Mbps
enc_ctx->gop_size  = 30;                       // 关键帧间隔
enc_ctx->max_b_frames = 2;                     // B 帧数（越低延迟越小）
if (enc_ctx->codec_id == AV_CODEC_ID_H264)
    av_opt_set(enc_ctx->priv_data, "preset", "ultrafast", 0);  // 低延迟
```

### 关于「RTSP 推流」的真相

| 方向 | FFmpeg 支持情况 |
|------|----------------|
| **RTSP 拉流** | 支持非常好，标准场景 |
| **RTSP 推流** | 有 `rtsp` muxer 但功能有限、不常用 |
| **常用推流** | RTMP（`"flv"` muxer）或 SRT（`"srt://..."`） |
| **低延迟 RTSP 推流** | 通常用 MediaMTX / SRS 服务器中转，或 `libx264` + RTP 自定义封装 |

---

## 五、RTSP 特有注意点

1. **网络阻塞**：`avformat_open_input` 是唯一明显阻塞的调用，连接不上会卡住——必须设 `timeout`。拉流后 `av_read_frame` 在网络断开时返回错误码，需要做**重连**（关掉重开）。
2. **TCP vs UDP**：
   - `tcp`：可靠、能穿透大多数防火墙，延迟略高。
   - `udp`：延迟更低，但丢包导致花屏/卡顿。
   - 通过 `rtsp_transport` 选项选择。
3. **B 帧缓冲延迟**：解码器为了处理 B 帧会缓存若干帧，`receive_frame` 滞后于 `read_frame` 几帧是正常的，flush 时吐出来。低延迟场景设 `max_b_frames = 0`。
4. **时间戳**：解码出的 `AVFrame->pts` 基于 `stream->time_base`；编码推流前用 `av_packet_rescale_ts` 换算到目标容器的时间基准，否则画面快进/卡顿。
5. **音视频同步**：同时解码音视频时，需自行维护时间轴对齐，见下一章。

---

## 六、音视频同步

### 为什么需要同步

视频和音频是**两条独立推进的时间线**：视频按帧率（如 25 fps，每 40ms 一帧）离散地出帧，音频按采样率（如 44100 Hz）连续地播放。网络抖动、解码耗时差异会让它们逐渐错位——这就是音画不同步。

### 主时钟（master clock）模型

播放器会选一个"主时钟"，其他流以它为准对齐：

| 主时钟选择 | 说明 |
|-----------|------|
| **以音频为主**（最常用） | 人耳对声音抖动比人眼对画面抖动敏感得多，让视频去迁就音频 |
| 以视频为主 | 画面优先，音频迁就画面 |
| 以外部时钟为主 | 以墙钟/系统时间为准 |

### 核心算法

把两边的 `pts`（呈现时间戳）统一换算到**微秒**，比较差值后决定"等待"还是"跳帧"：

```cpp
#include <chrono>

// 把某流的 pts 按自己的 time_base 换算成微秒
int64_t pts_to_us(int64_t pts, AVRational time_base) {
    return av_rescale_q(pts, time_base, AVRational{1, 1'000'000});
}

// 每次要显示一帧视频前：
int64_t video_us = pts_to_us(vframe->pts, video_tb);   // 这帧"应该"显示的时间
int64_t audio_us = get_audio_clock_us();               // 音频当前播到了哪

int64_t delay_us = video_us - audio_us;
if (delay_us > 0) {
    // 视频快了，睡到该显示的时刻
    std::this_thread::sleep_for(std::chrono::microseconds(delay_us));
} else if (delay_us < -50'000) {   // 落后超过 50ms
    // 视频晚了，跳过这一帧追回时间
    skip_current_frame();
}
```

### 音频时钟怎么算

音频时钟不是"读"出来的，而是**从音频输出设备已播放的字节数反推**：

```cpp
int64_t audio_clock_us() {
    uint64_t played_bytes = audio_device.get_played_bytes();
    // bytes / bytes_per_second = 已播放秒数，再换算微秒
    return played_bytes * 1'000'000 / bytes_per_second;
}
```

（这是简化模型：假设音频自开始播放无停顿。真实播放器还要修正音频 buffer 积压带来的偏差。）

### C++17 的体现

- 用 `std::chrono::microseconds` 表达时间，避免 `int64_t` 裸算导致"单位不清楚"的错误。
- 时间基准换算统一走 `av_rescale_q`（FFmpeg 的**整数分数换算**），不用浮点，避免长期运行的精度漂移。
- 睡眠用 `std::this_thread::sleep_for(std::chrono::duration)`，语义自文档化。

---

## 七、C++17 在这里扮演的角色

FFmpeg API 是 C 的，但工程化它正是 C++17 的主场：

| 场景 | C 风格 | C++17 |
|------|--------|-------|
| 资源管理 | 手动 `avformat_close_input`、`goto fail` | `unique_ptr` + deleter，异常自动清理 |
| 错误处理 | 每个调用 `if (ret < 0) return -1;` | 抛异常 / `std::optional` / 错误码封装 |
| 时间戳 | `int64_t` 裸算 | `std::chrono` + `AV_TIME_BASE` 换算 |
| 回调帧处理 | 函数指针 + `void*` | `std::function` / lambda |
| 参数传递 | 裸指针 | `const std::string&`、`std::string_view` |

最核心的一点：**FFmpeg 对象几乎全是指针，且释放规则各不相同**——这正好是 RAII 智能指针的实战，每种 deleter 对应一种"清理规则"，编译器保证它们在所有路径上被执行。

---

## 总结

- **FFmpeg 是 C 库**：所有对象都是堆上的裸指针，用 [[理解C++指针]] 的门牌号模型去理解它最自然。
- **两个抽象**：`AVPacket`（压缩）和 `AVFrame`（原始），编解码就是在这两者之间 send/receive。
- **一个总管家**：`AVFormatContext` 承载整个媒体会话的状态，注意手动分配 vs 传 `NULL` 两种打开方式。
- **一套对称流程**：解码是 `read_frame → send_packet → receive_frame`，编码是 `send_frame → receive_packet → write_frame`。
- **C++17 的答案**：用 `unique_ptr` + 自定义 deleter 封装每种释放规则，让 FFmpeg 的 C 资源管理变成 RAII。

---

## 附录：FFmpeg 文档资源与学习方法

### 一、文档来源（按优先级排序）

| 来源                    | 地址 / 位置                                                   | 说明                                      |
| --------------------- | --------------------------------------------------------- | --------------------------------------- |
| **官方 Doxygen API 文档** | https://ffmpeg.org/doxygen/trunk/index.html               | 最权威。按模块浏览，每个结构体字段、每个函数都有注释              |
| **头文件本身**             | 本地 `/opt/homebrew/include/libav*/`                        | 注释质量高，且永远和本地库版本一致。IDE 按住 Command 点击即可跳转 |
| **官方示例代码**            | https://github.com/FFmpeg/FFmpeg/tree/master/doc/examples | 学习"怎么知道有这个东西"的最佳入口                      |
| **官方 Wiki**           | https://trac.ffmpeg.org/wiki                              | 入门文章、Using FFmpeg library               |
| **命令行工具**             | `ffprobe`、`ffmpeg -h`                                     | 探索器：看一条流的真实信息                           |

几个关键模块对应的头文件（查 API 先定模块）：

```
libavformat/avformat.h  容器层   AVFormatContext、AVStream、avformat_open_input
libavcodec/avcodec.h    编解码层  AVCodecContext、AVCodec、AVPacket、AVFrame
libavutil/avutil.h      工具层   错误码、AVRational、AVDictionary、内存
libswscale/swscale.h    像素转换  SwsContext、sws_scale
```

直接搜结构体的速记 URL：`https://ffmpeg.org/doxygen/trunk/structAVFormatContext.html`

### 二、核心方法论：流程驱动，而不是 API 驱动

FFmpeg 是**流程驱动**的库，不需要背几百个函数。记住流程的每个"阶段"，每阶段需要什么对象，再按名字去查：

```
阶段                    需要什么对象/函数
─────────────────────────────────────────────────
打开输入         →  AVFormatContext + avformat_open_input
找流信息         →  avformat_find_stream_info + AVStream
初始化解码器     →  AVCodecContext + avcodec_open2
读包             →  AVPacket + av_read_frame
解码             →  avcodec_send_packet / avcodec_receive_frame
转换像素         →  SwsContext + sws_scale
编码/写文件      →  avcodec_send_frame / av_interleaved_write_frame
```

写代码时：**"流程走到哪一步了，这一步缺哪个函数"**——有了流程，查 API 是一下的事；没有流程，API 就是大海捞针。

### 三、操作技巧

1. **按名字猜 + 验证**：函数名高度规律。想释放格式上下文？猜 `avformat_` + `free`/`close` → `avformat_close_input`，再用 IDE 补全确认。
2. **`grep` 头文件**：不确定函数在哪个库：
   ```bash
   grep -rn "avformat_open_input" /opt/homebrew/include/
   ```
3. **警惕版本敏感的旧 API**：网上老教程（如雷霄骅博客，FFmpeg 2.x 时代）的 `avcodec_decode_video2` 已废弃，被 `send_packet/receive_frame` 取代。**API 对不上时，以头文件和官方 examples 为准。**
4. **看结构体字段理解"它是什么"**：打开 `AVFormatContext` 的 doxygen 页面扫一眼字段，对"总管家装了什么"的理解立刻具体化。

### 四、实操路径

```
① brew install ffmpeg                       ← 装库（含头文件）
② 打开 GitHub 的 examples 目录               ← 看官方代码骨架
③ 打开 demuxing_decoding.c
④ 对照笔记第三章，逐个函数跳进头文件看注释     ← 建立"流程 → API"映射
⑤ 遇到 API 变化，用 ffmpeg.org/doxygen 查最新签名
```
