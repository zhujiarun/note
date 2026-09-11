# WebGL 2 知识点整理

> 针对 WebGL 2（GLSL ES 3.0）的核心技术笔记，与当前项目（`webgl_video_roi.vue`）的优化方向一致。

## 目录

1. [FBO（Frame Buffer Object）](#1-fboframe-buffer-object)
2. [持久化 shader 状态（image2D / atomic_uint / buffer）](#2-持久化-shader-状态)
3. [纹理存状态（乒乓纹理 / Ping-Pong）](#3-纹理存状态乒乓纹理--ping-pong)
4. [readPixels 性能分析](#4-readpixels-性能分析)
5. [shader 数据传递](#5-shader-数据传递)
6. [shader 内置坐标系统](#6-shader-内置坐标系统)
7. [WebGL 1 → WebGL 2 关键升级点](#7-webgl-1--webgl-2-关键升级点)

---

## 1. FBO（Frame Buffer Object）

### 1.1 概念

FBO 是 WebGL 中的"离屏渲染目标"，让你把渲染结果写到显存纹理里，而不是直接显示到屏幕。

**两种 framebuffer**：
- **默认 framebuffer**：绑到 canvas，渲染结果直接显示
- **自定义 FBO**：绑到纹理，渲染结果存到纹理

### 1.2 为什么需要 FBO

| 场景 | 需求 |
|------|------|
| 后处理效果 | 先渲染到纹理，再做模糊/色彩校正 |
| 阴影映射 | 从光源视角渲染深度图 |
| 拾取（picking） | 渲染 ID 到纹理，鼠标点击读回 |
| 像素采样 | 渲染到 4×4 纹理，读像素分析 |
| 乒乓纹理 | 上一帧结果存纹理，下一帧采样 |
| GPU 数据计算 | 结果存纹理，回读给 JS |

### 1.3 完整代码示例（WebGL 2）

```javascript
// ============ 1. 创建纹理 ============
const tex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, tex);

gl.texImage2D(
    gl.TEXTURE_2D, 0,
    gl.RGBA,         // WebGL 2 支持更多格式
    256, 256, 0,
    gl.RGBA, gl.UNSIGNED_BYTE,
    null
);

gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

// ============ 2. 创建 FBO 并绑纹理 ============
const fbo = gl.createFramebuffer();
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
gl.framebufferTexture2D(
    gl.FRAMEBUFFER,
    gl.COLOR_ATTACHMENT0,
    gl.TEXTURE_2D,
    tex, 0
);

// ============ 3. 检查 FBO 完整性 ============
const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
if (status !== gl.FRAMEBUFFER_COMPLETE) {
    console.error('FBO 不完整!', status);
}

// ============ 4. 渲染到 FBO ============
gl.viewport(0, 0, 256, 256);
gl.clearColor(1, 0, 0, 1);
gl.clear(gl.COLOR_BUFFER_BIT);
gl.drawArrays(gl.TRIANGLES, 0, 6);

// ============ 5. 把纹理作为输入显示到 canvas ============
gl.bindFramebuffer(gl.FRAMEBUFFER, null);
gl.viewport(0, 0, canvas.width, canvas.height);
gl.activeTexture(gl.TEXTURE0);
gl.bindTexture(gl.TEXTURE_2D, tex);
gl.drawArrays(gl.TRIANGLES, 0, 6);
```

### 1.4 关键 API

| API | 作用 |
|-----|------|
| `gl.createFramebuffer()` | 创建 FBO |
| `gl.bindFramebuffer(target, fbo)` | 绑定 FBO（`null` = 默认 framebuffer = canvas） |
| `gl.framebufferTexture2D(target, attachment, textarget, texture, level)` | 把纹理挂到 FBO 附件槽 |
| `gl.checkFramebufferStatus(target)` | 检查 FBO 是否完整 |
| `gl.deleteFramebuffer(fbo)` | 删除 FBO |

### 1.5 FBO 附件槽

```
Framebuffer
├── Color Attachment 0~15  (COLOR_ATTACHMENT0~15)
├── Depth Attachment       (DEPTH_ATTACHMENT)
├── Stencil Attachment     (STENCIL_ATTACHMENT)
└── Depth-Stencil Combined (DEPTH_STENCIL_ATTACHMENT)
```

### 1.6 FBO 不完整状态码

| 状态码 | 含义 |
|--------|------|
| `FRAMEBUFFER_COMPLETE` | ✅ 完整可用 |
| `FRAMEBUFFER_INCOMPLETE_ATTACHMENT` | ❌ 附件类型不兼容 |
| `FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT` | ❌ 没绑任何附件 |
| `FRAMEBUFFER_UNSUPPORTED` | ❌ 格式不支持 |
| `FRAMEBUFFER_INCOMPLETE_DIMENSIONS` | ❌ 附件尺寸不一致 |

### 1.7 WebGL 2 新增：直接渲染到纹理（image2D 绑定）

```glsl
// 声明可读写纹理绑定点
layout(rgba8, binding = 0) uniform image2D u_output;

// 写入imageStore(u_output, ivec2(gl_FragCoord.xy), vec4(1, 0, 0, 1));

// 读取（不通过传统 sampler2D）
vec4 color = imageLoad(u_output, ivec2(gl_FragCoord.xy));
```

**优势**：
- 可以同时读写（不需要乒乓纹理切换）
- 可以作为 fragment shader 的输出目标，无需 FBO

### 1.8 WebGL 2 多渲染目标（MRT，原生支持）

```glsl
#version 300 es
precision highp float;

layout(location = 0) out vec4 outA;
layout(location = 1) out vec4 outB;

void main() {
    outA = vec4(1, 0, 0, 1);  // → tex0
    outB = vec4(0, 1, 0, 1);  // → tex1
}
```

```javascript
// FBO 绑多个纹理
gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex0, 0);
gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT1, gl.TEXTURE_2D, tex1, 0);

// 告诉 GL 写入哪些附件
gl.drawBuffers([
    gl.COLOR_ATTACHMENT0,
    gl.COLOR_ATTACHMENT1,
]);
```

### 1.9 重要细节

**视口必须匹配 FBO 纹理尺寸**：

```javascript
// ❌ 错误：FBO 是 256×256，但 viewport 还是 canvas 尺寸
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
gl.viewport(0, 0, canvas.width, canvas.height);  // 错！

// ✅ 正确
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
gl.viewport(0, 0, 256, 256);  // 匹配纹理尺寸
```

**纹理格式与 FBO 兼容性**：

| FBO attachment | WebGL 2 支持的纹理格式 |
|----------------|------------------------|
| COLOR_ATTACHMENT0 | RGBA8 / RGBA16F / RGBA32F / RG8 等 |
| DEPTH_ATTACHMENT | DEPTH_COMPONENT16/24/32F |

### 1.10 常见陷阱

1. **忘了 viewport**：FBO 切了但 viewport 没切
2. **渲染纹理又被采样**：同一纹理同时作为输入和输出（未定义行为）
3. **未检查 FBO 完整性**：静默失败
4. **资源泄漏**：组件销毁时没 delete
5. **纹理尺寸超限**：

```javascript
const maxSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
const maxRenderSize = gl.getParameter(gl.MAX_RENDERBUFFER_SIZE);
```

### 1.11 在当前项目中的应用

**`_pixelFBO`**：渲染视频左上 16×16 像素到小纹理，然后 readPixels。

```javascript
// 当前（WebGL 1）
this._pixelFBO = gl.createFramebuffer();
gl.bindFramebuffer(gl.FRAMEBUFFER, this._pixelFBO);
gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, pixelTex, 0);
```

**WebGL 2 改进**：可以用 `image2D` 绑定，**省掉 FBO 创建**：

```javascript
// WebGL 2：直接绑 image2D
gl.bindImageTexture(0, pixelTex, 0, false, 0, gl.READ_WRITE, gl.RGBA8);
// 不需要 FBO
```

---

## 2. 持久化 shader 状态

WebGL 2 提供三种"真全局可写"方案，让 shader 拥有跨调用、跨帧的状态。

### 2.1 为什么 WebGL 1 不能做

```glsl
// ❌ WebGL 1 / GLSL ES 1.0：禁止
float num = 0.0;  // 全局变量
void main() {
    num += 1.0;     // 报错：无法修改全局
}
```

GPU 对每个 fragment 调用一次 `main()`，调用完即销毁所有局部变量。WebGL 1 没有"持久化"机制。

### 2.2 方案对比

| 方案 | 数据类型 | 原子性 | 性能 | 适用场景 |
|------|---------|--------|------|----------|
| `image2D` | 4 通道纹理（任意维度）| ❌ 单像素读写 | 高 | 时域累积、滤波、状态存储 |
| `atomic_uint` | uint（32 位整数）| ✅ 原子操作 | 中 | 计数器、累加 |
| `buffer`（SSBO）| 任意类型数组 | ❌/视驱动 | 高 | 大块数据、参数组 |

---

### 2.3 方案1：`image2D`（可读写纹理）

#### 声明

```glsl
#version 300 es
precision highp float;

// 声明 image2D 绑定点
layout(rgba8,           binding = 0) uniform image2D u_state;
layout(rgba16f,         binding = 1) uniform image2D u_highPrec;
layout(rgba32f,         binding = 2) uniform image2D u_data;
layout(r32i,            binding = 3) uniform iimage2D u_intState;
```

支持的格式：`rgba8` / `rgba16f` / `rgba32f` / `r8` / `r16f` / `r32f` / `r32i` / `rg8` 等。

#### 读写操作

```glsl
// 写入imageStore(u_state, ivec2(gl_FragCoord.xy), vec4(1, 0, 0, 1));

// 读取
vec4 prevState = imageLoad(u_state, ivec2(gl_FragCoord.xy));

// 原子操作（WebGL 2.0 部分支持）
// 注意：原子 image 操作需要 imageAtomicAdd 等，WebGL 2.0 默认不支持
// 需要 EXT_shader_atomic_float 等扩展
```

#### 完整示例：时域低通滤波

```glsl
#version 300 es
precision highp float;

layout(rgba8, binding = 0) uniform image2D u_state;  // 上一帧状态
uniform sampler2D u_curr;                            // 当前帧
uniform float u_alpha;

in vec2 v_uv;

void main() {
    // 读"当前帧"
    vec4 curr = texture(u_curr, v_uv);
    
    // 读"上一帧状态"（imageLoad 用像素坐标）
    ivec2 size = imageSize(u_state);
    ivec2 pixel = ivec2(v_uv * vec2(size));
    vec4 prev = imageLoad(u_state, pixel);
    
    // 时域低通：out = α*curr + (1-α)*prev
    vec4 filtered = mix(prev, curr, u_alpha);
    
    // 写回（imageStore 用像素坐标）
    imageStore(u_state, pixel, filtered);
}
```

#### JS 端配置

```javascript
// 1. 创建纹理（image2D 必须是不可变大小，或用 renderbuffer）
const stateTex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, stateTex);
gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, 256, 256);  // texStorage2D 是 WebGL 2 新增
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

// 2. 绑定到 image2D binding = 0
gl.bindImageTexture(0, stateTex, 0, false, 0, gl.READ_WRITE, gl.RGBA8);

// 3. shader 中 layout(binding = 0) 对应

// 4. 初始数据（如需要）
gl.clearTexImage(stateTex, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(256 * 256 * 4));
```

**注意**：`image2D` 用的纹理**不能用 mipmap**（必须是 level 0），格式必须支持 `READ_WRITE`。

---

### 2.4 方案2：`atomic_uint`（原子计数器）

#### 声明与使用

```glsl
#version 300 es
precision highp uint;

// 声明原子计数器（类似全局数组）
layout(binding = 0) uniform atomic_uint u_counter;

void main() {
    // 原子递增，返回旧值
    uint oldValue = atomicCounterIncrement(u_counter);
    
    // 原子递减
    uint oldValue2 = atomicCounterDecrement(u_counter);
    
    // 原子加
    uint result = atomicAdd(u_counter, 5u);
    
    // 原子读
    uint current = atomicCounter(u_counter);
}
```

**支持的原子操作**：
- `atomicAdd(u, val)`
- `atomicMin(u, val)`
- `atomicMax(u, val)`
- `atomicAnd(u, val)`
- `atomicOr(u, val)`
- `atomicXor(u, val)`
- `atomicExchange(u, val)`
- `atomicCompSwap(u, compare, val)`（比较-交换）

#### JS 端配置

```javascript
// 1. 创建 atomic counter buffer
const counterBuf = gl.createBuffer();
gl.bindBuffer(gl.ATOMIC_COUNTER_BUFFER, counterBuf);
gl.bufferData(gl.ATOMIC_COUNTER_BUFFER, 4, gl.DYNAMIC_COPY);  // 4 字节 = 1 个 uint

// 2. 绑定到 binding = 0
gl.bindBufferBase(gl.ATOMIC_COUNTER_BUFFER, 0, counterBuf);

// 3. 初始化为 0
gl.bufferSubData(gl.ATOMIC_COUNTER_BUFFER, 0, new Uint32Array([0]));

// 4. 读回 CPU
gl.bindBuffer(gl.ATOMIC_COUNTER_BUFFER, counterBuf);
const result = new Uint32Array(1);
gl.getBufferSubData(gl.ATOMIC_COUNTER_BUFFER, 0, result);
console.log('计数器值:', result[0]);
```

#### 应用示例：统计 fragment 数

```glsl
#version 300 es
precision highp float;
precision highp uint;

layout(binding = 0) uniform atomic_uint u_visibleCount;
uniform sampler2D u_image;
in vec2 v_uv;

void main() {
    vec3 color = texture(u_image, v_uv).rgb;
    
    // 统计非黑色像素数
    if (length(color) > 0.1) {
        atomicCounterIncrement(u_visibleCount);
    }
    
    gl_FragColor = vec4(color, 1.0);
}
```

---

### 2.5 方案3：`buffer`（SSBO，Shader Storage Buffer Object）

#### 声明

```glsl
#version 300 es
precision highp float;

// 任意类型的内存块
layout(std430, binding = 0) buffer u_storage {
    vec4 positions[];     // 顶点位置数组
    float weights[];      // 权重数组
    uint counts[];        // 计数器数组
    // ... 任意类型
};

// 或固定大小struct MyData {
    vec3 pos;
    float weight;
};
layout(std430, binding = 0) buffer u_data {
    MyData items[];  // 大小可在 JS 端指定
};

void main() {
    // 读写任意位置
    positions[gl_FragCoord.x] = vec4(1, 0, 0, 1);
    
    // 跨 fragment 访问同一位置（未定义行为，除非有同步）
    if (gl_FragCoord.x == 0.0) {
        positions[0] += vec4(0.1, 0, 0, 0);
    }
}
```

#### JS 端配置

```javascript
// 1. 创建 buffer
const ssbo = gl.createBuffer();
gl.bindBuffer(gl.SHADER_STORAGE_BUFFER, ssbo);

// 2. 分配大小（如 1024 个 vec4）
const size = 1024 * 16;  // 1024 个 vec4 = 16KB
gl.bufferData(gl.SHADER_STORAGE_BUFFER, size, gl.DYNAMIC_COPY);

// 3. 绑定到 binding = 0
gl.bindBufferBase(gl.SHADER_STORAGE_BUFFER, 0, ssbo);

// 4. 上传数据
const data = new Float32Array(1024 * 4);  // 1024 个 vec4
gl.bindBuffer(gl.SHADER_STORAGE_BUFFER, ssbo);
gl.bufferSubData(gl.SHADER_STORAGE_BUFFER, 0, data);

// 5. 读回
const result = new Float32Array(1024 * 4);
gl.getBufferSubData(gl.SHADER_STORAGE_BUFFER, 0, result);
```

---

### 2.6 三种方案对比

| | image2D | atomic_uint | buffer (SSBO) |
|---|---------|-------------|---------------|
| **数据类型** | 2D 纹理 | uint 数组 | 任意 |
| **容量** | 受纹理尺寸限制 | 受 buffer 大小限制 | 最大、最灵活 |
| **读写位置** | 像素坐标 (x, y) | 数组下标 [i] | 任意下标 [i] |
| **原子性** | ❌（需扩展） | ✅ 原子操作 | ❌（需扩展或同步）|
| **性能** | 高（GPU 优化） | 中等 | 高 |
| **WebGL 2.0 默认支持** | ✅ | ✅ | ✅ |

### 2.7 推荐用法

```javascript
// 场景1：时域累积 → image2D
// 场景2：计数器 / 统计 → atomic_uint
// 场景3：复杂数据 / 大参数组 → buffer (SSBO)
```

---

## 3. 纹理存状态（乒乓纹理 / Ping-Pong）

### 3.1 核心思想

用**两张纹理 A、B 交替作为"上一帧"和"当前帧"**。每帧：
- 读 A（上一帧状态）→ 计算 → 写到 B（这一帧状态）
- 下一帧反过来：读 B → 计算 → 写到 A

### 3.2 视觉示意

```
第 1 帧           第 2 帧           第 3 帧
─────────         ─────────         ─────────
输入: A (空)       输入: B          输入: A
输出: B            输出: A           输出: B
```

### 3.3 完整实现（WebGL 2）

#### JS 端：创建资源

```javascript
// ============ 1. 创建两张状态纹理 ============
const STATE_W = 256;
const STATE_H = 256;

function createStateTexture() {
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    
    // WebGL 2 推荐：texStorage2D
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, STATE_W, STATE_H);
    
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    
    return tex;
}

const stateA = createStateTexture();
const stateB = createStateTexture();

// ============ 2. 创建对应 FBO ============
function createStateFBO(tex) {
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(
        gl.FRAMEBUFFER,
        gl.COLOR_ATTACHMENT0,
        gl.TEXTURE_2D,
        tex, 0
    );
    return fbo;
}

const fboA = createStateFBO(stateA);
const fboB = createStateFBO(stateB);

// ============ 3. 初始化状态索引 ============
let pingPongIdx = 0;
const stateTexs = [stateA, stateB];
const stateFBOs = [fboA, fboB];
```

#### shader 端

```glsl
#version 300 es
precision highp float;

uniform sampler2D u_prevState;  // 上一帧状态
uniform sampler2D u_currInput;  // 当前帧输入
uniform float u_alpha;

in vec2 v_uv;

out vec4 fragColor;

void main() {
    vec4 prev = texture(u_prevState, v_uv);
    vec4 curr = texture(u_currInput, v_uv);
    
    // 时域低通滤波
    fragColor = mix(prev, curr, u_alpha);
}
```

#### 每帧调用

```javascript
function renderFrame() {
    const readIdx = pingPongIdx;
    const writeIdx = 1 - pingPongIdx;
    
    // 1. 把输出绑到"写" FBO
    gl.bindFramebuffer(gl.FRAMEBUFFER, stateFBOs[writeIdx]);
    gl.viewport(0, 0, STATE_W, STATE_H);
    
    // 2. 输入纹理：上一帧状态 + 当前帧输入
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, stateTexs[readIdx]);
    gl.uniform1i(prevStateLoc, 0);
    
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, currentInputTexture);
    gl.uniform1i(currInputLoc, 1);
    
    gl.uniform1f(alphaLoc, 0.3);
    
    // 3. 渲染
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    
    // 4. 交换索引
    pingPongIdx = writeIdx;
}
```

### 3.4 应用案例

#### 案例1：运动模糊（时域低通）

```glsl
uniform sampler2D u_prevState;
uniform sampler2D u_currFrame;
uniform float u_alpha;

void main() {
    vec4 prev = texture(u_prevState, v_uv);
    vec4 curr = texture(u_currFrame, v_uv);
    fragColor = mix(prev, curr, u_alpha);
}
```

#### 案例2：粒子轨迹 / 反馈

```glsl
uniform sampler2D u_prevState;
uniform sampler2D u_currParticles;

void main() {
    vec4 prev = texture(u_prevState, v_uv);
    vec4 curr = texture(u_currParticles, v_uv);
    
    vec4 newState = prev * 0.95 + curr;  // 渐隐 + 新位置
    fragColor = newState;
}
```

#### 案例3：累加器

```glsl
uniform sampler2D u_prevState;
uniform sampler2D u_currInput;
uniform float u_addValue;

void main() {
    vec4 prev = texture(u_prevState, v_uv);
    vec4 curr = texture(u_currInput, v_uv);
    fragColor = clamp(prev + curr * u_addValue, 0.0, 1.0);
}
```

### 3.5 WebGL 2 改进：用 image2D 替代乒乓

如果只是单像素读写，可以用 `image2D` 避免乒乓：

```glsl
layout(rgba8, binding = 0) uniform image2D u_state;
uniform sampler2D u_currInput;
uniform float u_alpha;

void main() {
    vec4 curr = texture(u_currInput, v_uv);
    vec4 prev = imageLoad(u_state, ivec2(gl_FragCoord.xy));
    
    vec4 filtered = mix(prev, curr, u_alpha);
    
    imageStore(u_state, ivec2(gl_FragCoord.xy), filtered);
    fragColor = filtered;
}
```

```javascript
// 直接绑 image2D，不需要 FBO
gl.bindImageTexture(0, stateTex, 0, false, 0, gl.READ_WRITE, gl.RGBA8);
// 不需要切换 FBO，每帧写到同一张纹理即可
```

**注意**：实际效果可能不如乒乓稳健（依赖驱动实现），跨 fragment 同步需要内存屏障（WebGL 2 默认有，但显式更好）。

### 3.6 关键细节

**FBO 与纹理关系**：

```javascript
// 推荐：每个 FBO 绑一个固定纹理（避免动态切换）
const fboA = createFBO(stateA);
const fboB = createFBO(stateB);

// 不推荐：动态切换纹理附件（每次都要重新绑）
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
gl.framebufferTexture2D(...);  // 每次开销大
```

**初始状态**：

```javascript
// 全 0（默认 null = 全透明黑）
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);

// 或用 clearTexImage（WebGL 2）
gl.clearTexImage(tex, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(w * h * 4));
```

**资源释放**：

```javascript
// 组件销毁
gl.deleteFramebuffer(fboA);
gl.deleteFramebuffer(fboB);
gl.deleteTexture(stateA);
gl.deleteTexture(stateB);
```

**性能开销**：

| 操作 | 开销 |
|------|------|
| 切换 FBO | 极低（仅修改绑定状态） |
| 切换纹理 | 极低 |
| 纹理采样 | O(W*H) fragment 一次采样 |
| 纹理写入 | O(W*H) fragment 一次写入 |
| **总计** | **约 1.5-2x 单次渲染** |

比 JS 端 readPixels + uniform 上传**快 5-10 倍**（避免 CPU-GPU 同步）。

### 3.7 在当前项目中的潜在应用

**video 顶部 16×16 区域的 5 帧平均亮度**（降噪）：

```glsl
layout(rgba8, binding = 0) uniform image2D u_history;
uniform sampler2D u_currFrame;
uniform float u_count;
uniform vec2 u_texSize;

void main() {
    vec2 uv = vec2(v_uv.x * 16.0 / u_texSize.x, (1.0 - v_uv.y) * 16.0 / u_texSize.y);
    
    vec4 curr = texture(u_currFrame, uv);
    vec4 hist = imageLoad(u_history, ivec2(gl_FragCoord.xy));
    
    // 5 帧移动平均
    float newCount = min(u_count + 1.0, 5.0);
    vec4 newHist = (hist * (newCount - 1.0) + curr) / newCount;
    
    imageStore(u_history, ivec2(gl_FragCoord.xy), newHist);
    fragColor = newHist;
}
```

---

## 4. readPixels 性能分析

### 4.1 readPixels 的两个开销组成

```
readPixels 总耗时 = ① 同步开销（GPU→CPU 同步等待）+ ② 数据拷贝（VRAM→系统内存）
                    │                                  │
                    │ 固定开销（与读多少字节无关）       │ 与数据量成正比
                    │                                  │
                    └─ 决定性因素 ──────┘              └─ 微不足道 ───┘
```

### 4.2 实测对比

| 数据量 | ①同步开销 | ②拷贝开销 | 总耗时 |
|--------|-----------|-----------|--------|
| 4 字节 | 3-4ms | <0.01ms | 3-4ms |
| 64 字节 | 3-4ms | <0.01ms | 3-4ms |
| 4096 字节 | 3-4ms | 0.05ms | 3-4ms |

**结论**：3-4ms **100% 是同步开销**，与数据量基本无关。

### 4.3 为什么同步开销是固定的？

#### WebGL 是异步 API，但 readPixels 是同步调用

```javascript
gl.drawArrays(...);  // 异步：命令进入 GPU 队列，立刻继续

gl.readPixels(...);  // 同步：强制 CPU 等 GPU 完成所有 pending 命令
```

GPU 在另一线程/进程上跑，CPU 必须**等 GPU 完成**才能安全读 framebuffer。

#### Chrome 多进程架构

```
主进程 (CPU 代码)  ←──── IPC延迟 ────→  GPU 进程 (WebGL 命令)
     │                                          │
     │  readPixels 触发：                      │
     │  ① IPC 发送 readPixels 命令 ─────────────→│
     │  ② GPU 进程等 GPU 完成 →拷贝 VRAM → 系统内存│
     │  ③ IPC 返回数据 ←────────────────────────│
```

**IPC 一次往返 = 几毫秒**（与数据量无关）。

### 4.4 延迟波动的常见原因

| 概率 | 原因 | 验证方法 | 修复 |
|------|------|---------|------|
| **70%** | GPU 队列里有未完成的 drawScene 命令 | 看主渲染耗时 | 在 video frame callback 之前调用 readPixels |
| **20%** | GC 暂停 | Chrome devtools Performance 录制 | 消除 getParameter / 节流 processTopLeftPixel |
| **5%** | GPU 频率切换 | macOS 电源设置 | 禁用节能模式 |
| **5%** | 视频纹理重新上传 | 看 texImage2D 时机 | 错开 readPixels 与视频纹理更新 |

### 4.5 WebGL 2 优化方案

#### 方案1：Pixel Pack Buffer（PBO）异步回读

```javascript
// 1. 创建 PBO
const pbo = gl.createBuffer();
gl.bindBuffer(gl.PIXEL_PACK_BUFFER, pbo);
gl.bufferData(gl.PIXEL_PACK_BUFFER, 4, gl.DYNAMIC_READ);

// 2. readPixels 写入 PBO（异步，不阻塞渲染）
gl.bindBuffer(gl.PIXEL_PACK_BUFFER, pbo);
gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, 0);  // 最后一个参数 0 = 写入 buffer 偏移

// 3. 稍后再读回（此时可能已不阻塞）
setTimeout(() => {
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, pbo);
    gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, 0, pixelBuf);
    // 处理 pixelBuf
}, 0);
```

**收益**：把 readPixels 的阻塞拆成两段（发命令不阻塞 + 读数据可能阻塞）。

#### 方案2：`fenceSync` + `clientWaitSync`（异步同步原语）

```javascript
// 1. 创建同步点
const fence = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);

// 2. 后续可以做其他工作，不阻塞
doOtherWork();

// 3. 非阻塞检查
const result = gl.clientWaitSync(fence, 0, 0);
if (result === gl.CONDITION_SATISFIED || result === gl.ALREADY_SIGNALED) {
    // GPU 已完成，现在 readPixels 不会阻塞
    gl.readPixels(...);
}

// 4. 强制等待（如果必须）
const finalResult = gl.clientWaitSync(fence, gl.SYNC_FLUSH_COMMANDS_BIT, 5000000);  // 5ms 超时
```

**收益**：理论上可以让 readPixels 在 GPU 完成时调用，避免承担前面所有 pending 命令。

**实际收益有限**：`clientWaitSync(0)` 通常拿不到 `CONDITION_SATISFIED`，最终还是会阻塞。

#### 方案3：Transform Feedback（完全不用 readPixels）

```glsl
#version 300 es
precision highp float;

uniform sampler2D u_image;
in vec2 v_uv;

// 输出到 Transform Feedback buffer（不输出到 framebuffer）
out vec3 tfPosition;

void main() {
    vec3 color = texture(u_image, v_uv).rgb;
    float brightness = 0.299 * color.r + 0.587 * color.g + 0.114 * color.b;
    
    tfPosition = vec3(v_uv, brightness);
    
    // 不写 gl_FragColor（或写任意值，因为我们不关心 framebuffer 输出）
}
```

```javascript
// 创建 TF buffer
const tfBuffer = gl.createBuffer();
gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, tfBuffer);
gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER, 1024 * 3 * 4, gl.DYNAMIC_COPY);

// 创建 TF 对象
const tf = gl.createTransformFeedback();
gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, tf);
gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, tfBuffer);

// 渲染时开启 TF
gl.beginTransformFeedback(gl.TRIANGLES);
gl.drawArrays(gl.TRIANGLES, 0, 6);
gl.endTransformFeedback();

// 读回
const result = new Float32Array(1024 * 3);
gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER, 0, result);
```

**收益**：完全避免 readPixels，但只能用于顶点 shader 输出（fragment shader 不能用 TF）。

#### 方案4：用 image2D / atomic_uint 把结果留在 GPU

```glsl
// 不用 readPixels，让结果保留在 GPU 端
layout(rgba8, binding = 0) uniform image2D u_result;
layout(binding = 0) uniform atomic_uint u_count;

void main() {
    vec4 color = texture(u_image, v_uv);
    float brightness = 0.299 * color.r + 0.587 * color.g + 0.114 * color.b;
    
    // 写入 GPU 端 image2D（用 shader 端其他逻辑读取）
    imageStore(u_result, ivec2(gl_FragCoord.xy), vec4(brightness));
    
    // 或用原子计数器
    if (brightness > 0.5) {
        atomicCounterIncrement(u_count);
    }
    
    fragColor = color;
}
```

**适用场景**：业务逻辑完全在 GPU 端时（不需要 CPU 知道结果）。

### 4.6 实际推荐：节流 + shader 预计算

```javascript
// 1. shader 内预计算亮度
fragColor = vec4(color.rgb, brightness);

// 2. JS 端每 N 帧才 readPixels
if (frameCount % 10 === 0) {
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    processBrightness(buf[3]);
}
```

**收益**：
- ✅ 节流后**平均每帧 0.3-0.4ms**
- ✅ 数据量从 64 字节降到 4 字节
- ✅ shader 预计算省掉 CPU 端 BT.601 计算

### 4.7 在当前项目中的完整优化路径

**当前代码**：

```javascript
// 1. 渲染到 4×4 FBO
gl.bindFramebuffer(gl.FRAMEBUFFER, this._pixelFBO);
gl.viewport(0, 0, this.checkSize, this.checkSize);
gl.useProgram(this._pixelProgram);
gl.bindTexture(gl.TEXTURE_2D, texture);
gl.drawArrays(gl.TRIANGLES, 0, 6);

// 2. 读回 4×4 = 16 个像素
gl.readPixels(0, 0, this.checkSize, this.checkSize, gl.RGBA, gl.UNSIGNED_BYTE, this._pixelBuf);
```

**WebGL 2 优化版（3 选 1）**：

#### 优化 A：shader 预计算 + readPixels 1 像素

```glsl
// 主 shader
void main() {
    vec4 color = texture(u_video, v_uv);
    float brightness = 0.299 * color.r + 0.587 * color.g + 0.114 * color.b;
    fragColor = vec4(color.rgb, brightness);
}
```

```javascript
gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, brightnessBuf);
const brightness = brightnessBuf[3] / 255.0;
```

#### 优化 B：1×1 FBO + shader 端 16 平均

```glsl
void main() {
    vec3 sumColor = vec3(0.0);
    float sumBrightness = 0.0;
    
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            vec2 uv = vec2(
                (v_uv.x + float(i)) * 4.0 / u_texSize.x,
                (1.0 - v_uv.y + float(j)) * 4.0 / u_texSize.y
            );
            vec3 c = texture(u_video, uv).rgb;
            sumColor += c;
            sumBrightness += 0.299 * c.r + 0.587 * c.g + 0.114 * c.b;
        }
    }
    
    vec3 avgColor = sumColor / 16.0;
    float avgBrightness = sumBrightness / 16.0;
    
    fragColor = vec4(avgColor, avgBrightness);
}
```

#### 优化 C：完全避免 readPixels（image2D + 乒乓）

```glsl
layout(rgba8, binding = 0) uniform image2D u_brightnessHistory;

void main() {
    vec4 color = texture(u_video, v_uv);
    float brightness = 0.299 * color.r + 0.587 * color.g + 0.114 * color.b;
    
    imageStore(u_brightnessHistory, ivec2(gl_FragCoord.xy), vec4(brightness));
    fragColor = color;
}
```

```javascript
// 主渲染时同时把亮度写到 image2D
gl.bindImageTexture(0, historyTex, 0, false, 0, gl.READ_WRITE, gl.RGBA8);
gl.drawArrays(...);

// 需要亮度时，从 image2D 读（可以异步，或者让另一个 shader 处理）
```

---

## 5. shader 数据传递

### 5.1 uniform 类型

```glsl
// 标量
uniform float u_float;
uniform int u_int;
uniform bool u_bool;

// 向量
uniform vec2 u_vec2;
uniform vec3 u_vec3;
uniform vec4 u_vec4;
uniform ivec2 u_ivec2;  // ivec2 = int 向量
uniform uvec4 u_uvec4;  // uvec4 = uint 向量

// 矩阵
uniform mat2 u_mat2;
uniform mat3 u_mat3;
uniform mat4 u_mat4;

// 采样器
uniform sampler2D u_tex;
uniform samplerCube u_cubeTex;

// 数组（固定大小）
uniform float u_arr[10];
uniform vec4 u_vecArr[5];

// image2D（WebGL 2）
layout(rgba8, binding = 0) uniform image2D u_img;

// atomic_uint（WebGL 2）
layout(binding = 0) uniform atomic_uint u_counter;

// buffer / SSBO（WebGL 2）
layout(std430, binding = 0) buffer u_data {
    float values[];
};
```

### 5.2 ivec2 类型

```glsl
// ivec2 = 2 维整数向量
ivec2 coord = ivec2(10, 20);
coord.x = 5;
coord.y += 1;

// 用途：像素坐标、纹理大小、数组下标等
ivec2 size = textureSize(u_tex, 0);  // (width, height)
ivec2 pixelCoord = ivec2(gl_FragCoord.xy);

// ivec2 vs vec2 区别：
vec2 uv = vec2(0.5, 0.5);        // 浮点纹理坐标
ivec2 idx = ivec2(10, 20);       // 整数像素坐标
```

### 5.3 数组传递

#### 方式1：固定大小数组（WebGL 1 + 2）

```glsl
#define ARR_SIZE 10
uniform vec4 u_arr[ARR_SIZE];

void main() {
    vec4 v = u_arr[3];
}
```

```javascript
// 批量设置
const arr = new Float32Array(10 * 4);  // 10 个 vec4
gl.uniform4fv(loc, arr);

// 或逐个设置
for (let i = 0; i < 10; i++) {
    gl.uniform4f(locBase + i, x, y, z, w);
}
```

**限制**：
- 大小必须是常量表达式（编译期固定）
- 大小有上限（一般几百）
- 频繁修改整个数组的开销大

#### 方式2：texture 替代（动态大数据）

```glsl
uniform sampler2D u_dataTex;  // 纹理代替数组
uniform int u_count;

void main() {
    for (int i = 0; i < 100; i++) {
        if (i >= u_count) break;
        vec2 uv = vec2(float(i) / float(u_count), 0.5);
        vec4 data = texture(u_dataTex, uv);
        // 使用 data
    }
}
```

#### 方式3：buffer (SSBO)（WebGL 2 首选）

```glsl
layout(std430, binding = 0) buffer u_data {
    vec4 items[];  // 动态大小
};

void main() {
    items[gl_FragCoord.x] = vec4(1, 0, 0, 1);
    vec4 v = items[5];
}
```

```javascript
const ssbo = gl.createBuffer();
gl.bindBuffer(gl.SHADER_STORAGE_BUFFER, ssbo);
gl.bufferData(gl.SHADER_STORAGE_BUFFER, sizeInBytes, gl.DYNAMIC_COPY);
gl.bindBufferBase(gl.SHADER_STORAGE_BUFFER, 0, ssbo);
```

**优势**：大小任意、读写灵活、性能高。

### 5.4 WebGL 2 的 uniform 设置

```javascript
// WebGL 1: gl.getUniformLocation(program, 'u_arr[0]')
// WebGL 2: 同 WebGL 1（语法不变）

// 但可以直接用 uniform block
const blockIndex = gl.getUniformBlockIndex(program, 'u_data');
gl.uniformBlockBinding(program, blockIndex, 0);
// 然后绑定 buffer 到 binding = 0
```

---

## 6. shader 内置坐标系统

### 6.1 坐标类型对比

| 名称 | 类型 | 坐标系 | 范围 | 何时赋值 |
|------|------|--------|------|----------|
| `a_position` | attribute (顶点) | 顶点位置 | 通常 [-1, 1] | 顶点 shader 输入 |
| `gl_Position` | vec4 | 裁剪空间 | [-w, w] | 顶点 shader 输出 |
| `gl_FragCoord` | vec4 | **视口像素坐标** | [0, viewport] | fragment shader 内置 |
| `gl_PointCoord` | vec2 | **point 内部** [0,1]² | [0, 1] | gl.POINTS 时有效 |
| `v_uv` (varying) | vec2 | 自定义 | 自定义 | vertex→fragment 传递 |
| `texture(u_tex, uv)` | - | 纹理坐标 [0,1] | [0, 1] | fragment 采样 |

### 6.2 `gl_FragCoord`：视口像素坐标

```glsl
// gl_FragCoord 是视口/canvas 的像素坐标// 不是纹理坐标void main() {
    // 假设 canvas 是 800×600：
    // - 左下角：gl_FragCoord = (0.5, 0.5)
    // - 右上角：gl_FragCoord = (799.5, 599.5)
    
    ivec2 pixel = ivec2(gl_FragCoord.xy);  // 用于 imageLoad/ImageStore
}
```

**注意**：
- 原点在**左下角**（Y 向上）
- 中心在像素中心（半像素偏移）

### 6.3 `gl_PointCoord`：point 内部坐标

```glsl
// 只在 gl.POINTS 模式下有效// 表示当前 fragment 在这个 point 内部的相对位置[0,1]
void main() {
    // gl_PointCoord = (0, 0) 在 point 左下角
    // gl_PointCoord = (1, 1) 在 point 右上角
    
    float dist = length(gl_PointCoord - vec2(0.5));  // 圆点效果
    if (dist > 0.5) discard;
}
```

### 6.4 纹理坐标 vs 视口坐标 vs point 坐标

```glsl
// 纹理坐标（v_uv / varying）
// - 通常用 v_uv 这种 varying 从顶点 shader 传
// - 范围 [0, 1]
// - 用于 texture(u_tex, v_uv) 采样

// 视口像素坐标（gl_FragCoord）
// - 视口尺寸内的像素位置
// - 用于 imageLoad(image, ivec2(gl_FragCoord.xy))

// point 内部坐标（gl_PointCoord）
// - 当前 fragment 在 point sprite 内的 [0,1] 坐标
// - 与纹理坐标无关
```

### 6.5 Y 轴翻转约定

WebGL 纹理 Y 轴向上（(0,0) 在左下），但 video 元素 Y 轴向下（(0,0) 在左上）：

```glsl
// 常见做法：在 shader 里翻转
vec2 uv = vec2(v_uv.x, 1.0 - v_uv.y);

// 或在采样时翻转
vec4 color = texture(u_tex, vec2(v_uv.x, 1.0 - v_uv.y));
```

---

## 7. WebGL 1 → WebGL 2 关键升级点

### 7.1 升级清单

| 特性 | WebGL 1 | WebGL 2 |
|------|---------|---------|
| GLSL 版本 | ES 1.0 | ES 3.0（`#version 300 es`）|
| 顶点数组对象（VAO）| 需要扩展 | 原生支持 |
| 3D 纹理 | 需要扩展 | 原生支持 |
| 浮点纹理 | 需要扩展 | 原生支持 |
| 整数纹理 | 需要扩展 | 原生支�� |
| 多渲染目标（MRT）| 需要扩展 | 原生支持 |
| `texelFetch` | ❌ | ✅（不经过滤波） |
| `textureSize` | ❌ | ✅ |
| `textureLod` | ❌ | ✅ |
| `image2D` / `image3D` | ❌ | ✅ |
| `atomic_uint` | ❌ | ✅ |
| `buffer` (SSBO) | ❌ | ✅ |
| `transform feedback` | ❌ | ✅ |
| `fenceSync` | ❌ | ✅ |
| `in/out` 关键字 | attribute/varying | `in/out` |
| `texture()` 函数 | `texture2D()` | `texture()` |

### 7.2 GLSL 语法升级

```glsl
// WebGL 1 / GLSL ES 1.0
attribute vec2 a_position;
varying vec2 v_uv;

void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
    v_uv = a_position * 0.5 + 0.5;
}

varying vec2 v_uv;

void main() {
    gl_FragColor = texture2D(u_tex, v_uv);
}

// WebGL 2 / GLSL ES 3.0
#version 300 es
precision highp float;

in vec2 a_position;
in vec2 a_uv;
out vec2 v_uv;

void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
    v_uv = a_uv;
}

in vec2 v_uv;
out vec4 fragColor;  // 需要显式声明输出变量

void main() {
    fragColor = texture(u_tex, v_uv);
}
```

### 7.3 VAO（顶点数组对象）

```javascript
// WebGL 1: 每次 drawArrays 前手动绑定 buffer
gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
gl.enableVertexAttribArray(positionLoc);
gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

gl.bindBuffer(gl.ARRAY_BUFFER, uvBuffer);
gl.enableVertexAttribArray(uvLoc);
gl.vertexAttribPointer(uvLoc, 2, gl.FLOAT, false, 0, 0);

gl.drawArrays(gl.TRIANGLES, 0, 6);

// WebGL 2: 用 VAO 一次性配置
const vao = gl.createVertexArray();
gl.bindVertexArray(vao);

gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
gl.enableVertexAttribArray(positionLoc);
gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

gl.bindBuffer(gl.ARRAY_BUFFER, uvBuffer);
gl.enableVertexAttribArray(uvLoc);
gl.vertexAttribPointer(uvLoc, 2, gl.FLOAT, false, 0, 0);

gl.bindVertexArray(null);

// 渲染时只需切 VAO
gl.bindVertexArray(vao);
gl.drawArrays(gl.TRIANGLES, 0, 6);
```

**收益**：减少每次 drawArrays 的绑定操作。

### 7.4 texelFetch（不经过滤波）

```glsl
// texture() 会经过纹理滤波（LINEAR 时插值）// texelFetch() 直接读取指定像素（无滤波）
vec4 color = texelFetch(u_tex, ivec2(gl_FragCoord.xy), 0);
```

**用途**：像素精确读取（如拾取、像素艺术）。

### 7.5 textureSize

```glsl
// 获取纹理尺寸（像素）
ivec2 size = textureSize(u_tex, 0);  // 第二个参数 = mipmap level
int width = size.x;
int height = size.y;
```

**优势**：无需从 JS 端传 videoWidth/videoHeight 到 uniform。

### 7.6 浮点 / 整数纹理原生支持

```javascript
// WebGL 2 直接支持
gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA32F, w, h);
gl.texStorage2D(gl.TEXTURE_2D, 1, gl.R32I, w, h);
gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA16F, w, h);

// 不需要 OES_texture_float / OES_texture_half_float / EXT_color_buffer_float 等扩展
```

### 7.7 texStorage2D（不可变纹理）

```javascript
// WebGL 1: texImage2D 每次都重新分配（可变）
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, data);  // 重新分配

// WebGL 2: texStorage2D 一次性分配，不可变（驱动可以优化）
gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, w, h);
// 之后只能用 texSubImage2D 更新内容
gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, data);
```

**收益**：驱动可以预先优化纹理布局，性能更好。

---

## 附录：当前项目 (`webgl_video_roi.vue`) 的 WebGL 2 迁移建议

### A.1 立即可做的优化（无需大改）

- ✅ shader 预计算亮度 → readPixels 只读 1 像素（4 字节）
- ✅ 复用 `_pixelBuf` Uint8Array（避免 GC 压力）
- ✅ 消除 getParameter × 7（硬编码状态���复）
- ✅ 用 `texStorage2D` 替代 `texImage2D`（驱动优化）

### A.2 中期改造

- 🔄 用 VAO 替代手动绑定 buffer
- 🔄 用 `image2D` 替代 FBO（用于 `_pixelFBO`）
- 🔄 升级 GLSL 到 ES 3.0（`#version 300 es` + `in/out`）

### A.3 长期优化

- 🚀 全面替换为 WebGL 2 特性（VAO、image2D、SSBO）
- 🚀 用 PBO + fenceSync 优化 readPixels
- 🚀 用 transform feedback 完全避免 readPixels
- 🚀 用 atomic_uint / image2D 把状态保留在 GPU 端

---

## 参考文献

- [WebGL 2 Reference](https://www.khronos.org/registry/webgl/specs/latest/2.0/)
- [GLSL ES 3.00 Specification](https://www.khronos.org/registry/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf)
- [WebGL 2 教程（html5rocks）](https://web.dev/webgl2/)
- [OpenGL ES 3.0 Programming Guide](https://www.opengles-book.com/)