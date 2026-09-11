# WebGPU 完整详解

> W3C WebGPU 规范详细参考手册
> 面向 GPU 编程的下一代 Web 图形与计算 API
> 涵盖：设备初始化、渲染管线、计算管线、缓冲、纹理、着色器、命令队列、性能调优、与 WebCodecs 互操作

---

## 目录

- [一、概述与定位](#一概述与定位)
- [二、设备初始化与适配器](#二设备初始化与适配器)
- [三、WGSL 着色器语言](#三wgsl-着色器语言)
- [四、缓冲（Buffer）](#四缓冲buffer)
- [五、纹理（Texture）](#五纹理texture)
- [六、采样器（Sampler）](#六采样器sampler)
- [七、绑定组（BindGroup）](#七绑定组bindgroup)
- [八、渲染管线（RenderPipeline）](#八渲染管线renderpipeline)
- [九、计算管线（ComputePipeline）](#九计算管线computepipeline)
- [十、命令编码器与渲染流程](#十命令编码器与渲染流程)
- [十一、Canvas 配置与展示](#十一canvas-配置与展示)
- [十二、查询与时间戳](#十二查询与时间戳)
- [十三、错误处理与验证](#十三错误处理与验证)
- [十四、性能调优](#十四性能调优)
- [十五、与 WebCodecs 的互操作](#十五与-webcodecs-的互操作)
- [十六、高级特性](#十六高级特性)
- [十七、典型实战案例](#十七典型实战案例)
- [十八、浏览器支持与降级](#十八浏览器支持与降级)

---

## 一、概述与定位

### 1.1 什么是 WebGPU

WebGPU 是 W3C 制定的**下一代 Web 图形与计算 API**，目标是提供：

1. **现代 GPU 硬件能力的直接访问**：计算着色器、显式管线对象、零拷贝纹理
2. **统一的图形 + 计算 API**：取代 WebGL2 + WebGL2 Compute 的分裂
3. **多线程友好的资源模型**：基于显式资源所有权和命令编码
4. **可预测的性能**：命令录制 → 提交 → GPU 执行，CPU/GPU 完全解耦

它是 **Vulkan / Metal / DirectX 12** 在 Web 上的对应物，而不是 WebGL 的简单升级。

### 1.2 与 WebGL 的对比

| 维度 | WebGL | WebGPU |
|------|-------|--------|
| API 风格 | 状态机（全局状态） | 显式对象（pipeline、bind group） |
| 着色器 | GLSL ES | WGSL（类 Rust） |
| 计算着色器 | 无（需 transform feedback / 扩展） | 原生支持 |
| 多线程 | 无 | OffscreenCanvas + Worker |
| 资源所有权 | 隐式 | 显式（GPUBufferUsage / GPUTextureUsage） |
| 错误处理 | GL Error Code | Validation Error + 设备丢失 |
| 零拷贝纹理 | 受限（texImage2D） | 原生支持（importExternalTexture） |
| 命令录制 | 立即模式 | 录制到 CommandEncoder 后批量提交 |
| 性能天花板 | 中 | 高（更接近原生 GPU API） |
| 浏览器支持 | 几乎 100% | Chrome 113+/Safari 17+/Firefox 130+ |

### 1.3 核心架构

```
┌─────────────────────────────────────────────┐
│             JavaScript / Web App            │
└──────────────────┬──────────────────────────┘
                   │ 录制命令
┌──────────────────▼──────────────────────────┐
│       CommandEncoder / PassEncoder           │
│       （CPU 端构建命令流）                     │
└──────────────────┬──────────────────────────┘
                   │ submit
┌──────────────────▼──────────────────────────┐
│              GPU Queue                       │
│       （异步执行，可能跨线程）                  │
└──────────────────┬──────────────────────────┘
                   │ 调用 GPU 驱动
┌──────────────────▼──────────────────────────┐
│       底层图形 API（Vulkan/Metal/DX12）       │
└─────────────────────────────────────────────┘
```

---

## 二、设备初始化与适配器

### 2.1 基础流程

```js
// 1. 请求适配器（GPU 抽象）
const adapter = await navigator.gpu.requestAdapter();

// 2. 请求逻辑设备（GPU 操作上下文）
const device = await adapter.requestDevice();

// 3. 配置 Canvas（如果是渲染到屏幕）
const canvas = document.querySelector('canvas');
const context = canvas.getContext('webgpu');
context.configure({
  device,
  format: navigator.gpu.getPreferredCanvasFormat(),
  alphaMode: 'opaque',  // 或 'premultiplied'
});

// 4. 监听设备丢失（关键！）
device.lost.then((info) => {
  console.error('设备丢失:', info.reason, info.message);
  // 需要重建所有资源
});
```

### 2.2 适配器（Adapter）

`GPUAdapter` 描述一个具体的 GPU 实现。

```js
const adapter = await navigator.gpu.requestAdapter({
  powerPreference: 'high-performance',  // 'low-power' | 'high-performance'
  forceFallbackAdapter: false,           // 强制软渲染（仅调试）
});

if (!adapter) {
  throw new Error('不支持 WebGPU');
}

// 查询适配器信息
const info = await adapter.requestAdapterInfo();
console.log(info.vendor, info.architecture, info.device);
```

### 2.3 设备（Device）

`GPUDevice` 是所有 GPU 操作的主入口。

```js
const device = await adapter.requestDevice({
  requiredFeatures: [
    'shader-f16',           // 半精度浮点（性能优化）
    'texture-compression-bc',  // BC 压缩纹理
    'timestamp-query',      // 时间戳查询
  ],
  requiredLimits: {
    maxStorageBufferBindingSize: 128 * 1024 * 1024,  // 默认 128MB
    maxComputeWorkgroupStorageSize: 16384,
  },
});

// 设备错误监控
device.onuncapturederror = (event) => {
  console.error('Uncaptured error:', event.error);
  event.preventDefault();
};

// 设备丢失（GPU 重启、驱动崩溃等）
device.lost.then((info) => {
  console.error(`GPU lost: ${info.reason} - ${info.message}`);
  // reason: 'unknown' | 'destroyed' | 'device-lost' | 'device-removed'
  // 必须重建整个 GPU 上下文
});
```

### 2.4 特性与限制

```js
// 查询已启用特性
device.features;  // Set<GPUSupportedFeature>

// 查询限制
device.limits.maxBindGroups;               // 最大绑定组数
device.limits.maxComputeWorkgroupSizeX;    // 计算工作组最大尺寸
device.limits.maxTextureDimension2D;       // 2D 纹理最大尺寸
device.limits.maxUniformBufferBindingSize; // uniform buffer 最大
device.limits.maxStorageBufferBindingSize; // storage buffer 最大

// 适配器的特性（申请设备之前可以查）
adapter.features.has('shader-f16');  // true/false
```

**常用特性：**

| 特性 | 作用 |
|------|------|
| `shader-f16` | 支持 f16 类型（半精度） |
| `shader-f64` | 支持 f64（双精度） |
| `texture-compression-bc` | BC 系列压缩纹理 |
| `texture-compression-etc2` | ETC2 压缩纹理 |
| `texture-compression-astc` | ASTC 压缩纹理 |
| `timestamp-query` | GPU 时间戳 |
| `pipeline-statistics-query` | 管线统计 |
| `depth-clip-control` | 深度裁剪控制 |
| `bgra8unorm-storage` | BGRA 存储纹理 |
| `rg11b10ufloat-renderable` | 渲染 RG11B10 格式 |

---

## 三、WGSL 着色器语言

WGSL（WebGPU Shading Language）是 WebGPU 的官方着色器语言，语法类似 Rust。

### 3.1 基本结构

```wgsl
// 顶点着色器
struct VertexIn {
  @location(0) position: vec3f,
  @location(1) color: vec4f,
  @location(2) uv: vec2f,
}

struct VertexOut {
  @builtin(position) pos: vec4f,
  @location(0) color: vec4f,
  @location(1) uv: vec2f,
}

@vertex
fn vs_main(in: VertexIn) -> VertexOut {
  var out: VertexOut;
  out.pos = vec4f(in.position, 1.0);
  out.color = in.color;
  out.uv = in.uv;
  return out;
}

// 片元着色器
@group(0) @binding(0) var mySampler: sampler;
@group(0) @binding(1) var myTexture: texture_2d<f32>;

@fragment
fn fs_main(in: VertexOut) -> @location(0) vec4f {
  let texColor = textureSample(myTexture, mySampler, in.uv);
  return texColor * vec4f(in.color, 1.0);
}
```

### 3.2 内置属性（@builtin）

```wgsl
// 顶点输入
@builtin(vertex_index)         index: u32
@builtin(instance_index)       instIdx: u32

// 顶点输出 / 片元输入
@builtin(position)             pos: vec4f  // 裁剪空间

// 片元输出
@builtin(frag_depth)           depth: f32
@builtin(sample_mask)          mask: u32  // 多采样

// 计算着色器
@builtin(local_invocation_id)  lid: vec3u
@builtin(local_invocation_index) idx: u32
@builtin(workgroup_id)         wid: vec3u
@builtin(num_workgroups)       num: vec3u
@builtin(global_invocation_id) gid: vec3u
```

### 3.3 类型系统

#### 标量类型

```wgsl
// 布尔
let b: bool = true;

// 整数（32-bit）
let i: i32 = -42;
let u: u32 = 42;

// 浮点
let f: f32 = 3.14;
// f16 需要 shader-f16 特性
let h: f16 = 1.5;
```

#### 向量类型

```wgsl
let v2: vec2f = vec2f(1.0, 2.0);
let v3: vec3f = vec3f(1.0, 2.0, 3.0);
let v4: vec4f = vec4f(1.0, 2.0, 3.0, 4.0);

// 分量访问
let x = v4.x;     // 单分量
let xy = v4.xy;   // swizzle
let rgb = v4.rgb; // 颜色命名
```

#### 矩阵类型

```wgsl
// 列主序矩阵
let m: mat3x3f = mat3x3f(
  vec3f(1.0, 0.0, 0.0),  // 第一列
  vec3f(0.0, 1.0, 0.0),  // 第二列
  vec3f(0.0, 0.0, 1.0)   // 第三列
);

// 矩阵乘法
let result: vec3f = m * vec3f(1.0, 2.0, 3.0);
```

#### 数组

```wgsl
// 固定大小数组
var arr: array<f32, 4> = array(1.0, 2.0, 3.0, 4.0);
arr[2] = 99.0;

// 运行时数组（必须在 storage buffer 中）
struct Data {
  count: u32,
  values: array<f32>,  // 末尾
}
```

### 3.4 控��流

```wgsl
fn conditional(x: f32) -> f32 {
  var result: f32;
  if (x > 0.0) {
    result = x;
  } else if (x < 0.0) {
    result = -x;
  } else {
    result = 0.0;
  }
  return result;
}

fn loop(arr: ptr<function, array<f32, 4>>) {
  for (var i: i32 = 0; i < 4; i = i + 1) {
    (*arr)[i] = (*arr)[i] * 2.0;
  }

  // while 循环
  var i: i32 = 0;
  loop {  // 无限循环，需要 break
    if (i >= 4) { break; }
    i = i + 1;
  }

  // continue / breakif
  for (var i: i32 = 0; i < 10; i = i + 1) {
    if (i == 5) { continue; }
    if (i == 8) { break; }
  }
}
```

### 3.5 内存地址空间

WGSL 有 4 个内存地址空间：

| 地址空间 | 说明 | 用途 |
|---------|------|------|
| `function` | 函数栈 | 局部变量 |
| `private` | 模块级 | 模块私有变量 |
| `workgroup` | 工作组共享 | 并行计算共享数据 |
| `storage` | 显存 | 大数组、纹理采样 |
| `uniform` | 显存（只读优化） | uniform 缓冲 |

```wgsl
// 函数内变量（function space）
fn foo() {
  var local: f32 = 0.0;
}

// 模块私有变量（private space）
var<private> counter: u32 = 0;

// 工作组共享（需要 compute shader）
var<workgroup> sharedData: array<f32, 64>;

@compute @workgroup_size(64)
fn cs_main(@builtin(local_invocation_id) lid: vec3u) {
  sharedData[lid.x] = f32(lid.x);
  workgroupBarrier();  // 同步
  let val = sharedData[(lid.x + 1u) % 64u];
}

// 存储缓冲（storage space）
struct UBO {
  mvp: mat4x4f,
  time: f32,
}
@group(0) @binding(0) var<uniform> ubo: UBO;
```

### 3.6 常用数学函数

```wgsl
// 向量函数
let length = length(v);       // 向量长度
let dot = dot(a, b);          // 点积
let cross = cross(a, b);      // 叉积
let norm = normalize(v);      // 归一化
let reflected = reflect(v, n);// 反射
let refracted = refract(v, n, eta); // 折射

// 数值函数
let a = abs(x);
let b = sign(x);
let c = floor(x);
let d = ceil(x);
let e = round(x);
let f = fract(x);          // 小数部分
let g = clamp(x, 0.0, 1.0);
let h = mix(a, b, t);       // 线性插值
let i = step(edge, x);      // 阶跃
let j = smoothstep(e0, e1, x);

// 三角函数
let s = sin(x);
let c = cos(x);
let t = tan(x);
let as = asin(x);
let ac = acos(x);
let at = atan2(y, x);

// 类型转换
let i = i32(f);             // float → int
let u = u32(i);             // int → uint
let f = f32(u);             // uint → float
```

### 3.7 纹理采样函数

```wgsl
// 2D 纹理
let c = textureSample(tex, samp, uv);
let c2 = textureSampleLevel(tex, samp, uv, lod);  // 指定 mipmap
let cs = textureSampleBias(tex, samp, uv, bias);   // LOD bias
let ccmp = textureSampleCompare(depthTex, samp, uv, compareValue); // 深度比较
let clod = textureLoad(tex, coord, lod);  // 直接加载（不采样）

// 多级 mipmap
let mipLevel = textureNumLevels(tex);

// Cubemap
let c = textureSample(cubeTex, samp, dir);

// 3D 纹理
let c = textureSample(tex3d, samp, vec3f(u, v, w));

// 纹理数组
let c = textureSample(texArray, samp, uv, arrayIndex);
```

---

## 四、缓冲（Buffer）

`GPUBuffer` 是 GPU 显存中的线性数据块。

### 4.1 创建缓冲

```js
// 顶点缓冲
const vertexBuffer = device.createBuffer({
  size: vertices.byteLength,
  usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
  mappedAtCreation: true,  // 立即映射用于初始化
});

new Float32Array(vertexBuffer.getMappedRange()).set(vertices);
vertexBuffer.unmap();

// 索引缓冲
const indexBuffer = device.createBuffer({
  size: indices.byteLength,
  usage: GPUBufferUsage.INDEX | GPUBufferUsage.COPY_DST,
  mappedAtCreation: true,
});
new Uint32Array(indexBuffer.getMappedRange()).set(indices);
indexBuffer.unmap();

// Uniform 缓冲
const uniformBuffer = device.createBuffer({
  size: 256,  // 必须是 16 的倍数
  usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
});

// Storage 缓冲（计算着色器用）
const storageBuffer = device.createBuffer({
  size: 1024 * 1024,
  usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
});
```

### 4.2 使用标志（Usage Flags）

```js
GPUBufferUsage.VERTEX          // 顶点数据
GPUBufferUsage.INDEX           // 索引数据
GPUBufferUsage.UNIFORM         // uniform 缓冲
GPUBufferUsage.STORAGE         // storage 缓冲（读写）
GPUBufferUsage.INDIRECT        // 间接绘制参数
GPUBufferUsage.COPY_SRC        // 可作为 copy 源
GPUBufferUsage.COPY_DST        // 可作为 copy 目标
GPUBufferUsage.MAP_READ        // 可读回 CPU
GPUBufferUsage.MAP_WRITE        // 可从 CPU 写入
GPUBufferUsage.QUERY_RESOLVE   // 查询结果
```

**可以组合多个标志**：`usage: VERTEX | COPY_DST | COPY_SRC`

### 4.3 数据更新

```js
// 写入数据（推荐方式）
device.queue.writeBuffer(buffer, offset, data, dataOffset, size);

// 异步映射（适合大块数据传输）
await buffer.mapAsync(GPUMapMode.WRITE, offset, size);
const array = new Float32Array(buffer.getMappedRange(offset, size));
array.set(newData);
buffer.unmap();

// 读回数据
await buffer.mapAsync(GPUMapMode.READ);
const result = new Uint8Array(buffer.getMappedRange());
buffer.unmap();
```

### 4.4 数据拷贝

```js
const cmd = device.createCommandEncoder();

// GPU 内部缓冲之间拷贝
cmd.copyBufferToBuffer(srcBuffer, srcOffset, dstBuffer, dstOffset, size);

// 缓冲 → 纹理
cmd.copyBufferToTexture(
  { buffer, offset: 0, bytesPerRow, rowsPerImage: height },
  { texture, mipLevel: 0, origin: { x: 0, y: 0, z: 0 } },
  { width, height, depthOrArrayLayers: 1 }
);

// 纹理 → 缓冲
cmd.copyTextureToBuffer(
  { texture, mipLevel: 0, origin: { x: 0, y: 0, z: 0 } },
  { buffer, offset: 0, bytesPerRow, rowsPerImage: height },
  { width, height, depthOrArrayLayers: 1 }
);

// 图像 → 纹理
cmd.copyExternalImageToTexture(
  { source: imageBitmap, origin: { x: 0, y: 0 } },
  { texture, mipLevel: 0, origin: { x: 0, y: 0, z: 0 } },
  { width, height, depthOrArrayLayers: 1 }
);

device.queue.submit([cmd.finish()]);
```

---

## 五、纹理（Texture）

`GPUTexture` 是 GPU 显存中的二维/三维图像数据。

### 5.1 创建纹理

```js
// 普通 2D 纹理
const texture = device.createTexture({
  size: { width: 1920, height: 1080, depthOrArrayLayers: 1 },
  format: 'rgba8unorm',
  usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.RENDER_ATTACHMENT,
  mipLevelCount: 1,
  sampleCount: 1,           // 多采样（MSAA）
  dimension: '2d',          // '1d' | '2d' | '3d' | '2d-array' | 'cube' | 'cube-array'
  format: 'rgba8unorm',     // 见下表
  viewFormats: [],          // 额外视图格式
});

// 立方贴图（cubemap）
const cubemap = device.createTexture({
  size: { width: 512, height: 512, depthOrArrayLayers: 6 },
  format: 'rgba8unorm',
  usage: GPUTextureUsage.TEXTURE_BINDING,
  dimension: '2d-array',  // cubemap 是 2d-array + 6 层
});

// 3D 纹理（体积数据、医学影像）
const volumeTex = device.createTexture({
  size: { width: 256, height: 256, depthOrArrayLayers: 64 },
  format: 'rgba8unorm',
  usage: GPUTextureUsage.TEXTURE_BINDING,
  dimension: '3d',
});
```

### 5.2 常用纹理格式

| 类别 | 格式 |
|------|------|
| 8-bit RGBA | `rgba8unorm`, `rgba8unorm-srgb`, `bgra8unorm` |
| 8-bit RGB | `rg8unorm`, `rgb10a2unorm` |
| 16-bit float | `rgba16float`, `rg16float`, `r16float` |
| 32-bit float | `rgba32float`, `rg32float`, `r32float` |
| 深度 | `depth16unorm`, `depth24plus`, `depth32float`, `depth24plus-stencil8` |
| HDR | `rgba16float` + `rgba32float` |
| 压缩 BC | `bc1-rgba-unorm`, `bc2-rgba-unorm`, `bc7-rgba-unorm` |

### 5.3 纹理视图（TextureView）

纹理必须通过 `createView()` 才能在 shader 中使用：

```js
// 默认视图
const view = texture.createView();

// 自定义视图
const mipView = texture.createView({
  format: 'rgba8unorm-srgb',
  dimension: '2d',
  baseMipLevel: 0,
  mipLevelCount: 4,
  baseArrayLayer: 0,
  arrayLayerCount: 1,
  aspect: 'all',  // 'all' | 'depth-only' | 'stencil-only'
});
```

### 5.4 mipmap 生成

```js
// 方法 1：自己生成（兼容性好）
for (let i = 1; i < texture.mipLevelCount; i++) {
  const cmd = device.createCommandEncoder();
  cmd.copyTextureToTexture(
    { texture, mipLevel: i - 1 },
    { texture, mipLevel: i },
    {
      width: Math.max(1, texture.width >> i),
      height: Math.max(1, texture.height >> i),
    }
  );
  device.queue.submit([cmd.finish()]);
}

// 方法 2：用渲染管线一次性生成（更快）
// 需要单独的小渲染管线，目标纹理是下一个 mip
```

---

## 六、采样器（Sampler）

`GPUSampler` 定义纹理采样方式。

### 6.1 创建采样器

```js
const sampler = device.createSampler({
  // 地址模式（UV 超出 [0,1] 时）
  addressModeU: 'clamp-to-edge',  // 'clamp-to-edge' | 'repeat' | 'mirror-repeat'
  addressModeV: 'clamp-to-edge',
  addressModeW: 'clamp-to-edge',

  // 过滤模式
  magFilter: 'linear',    // 'linear' | 'nearest'
  minFilter: 'linear',
  mipmapFilter: 'linear', // 'linear' | 'nearest'

  // LOD
  lodMinClamp: 0,
  lodMaxClamp: 32,

  // 各向异性（需要 feature）
  maxAnisotropy: 16,

  // 比较采样（深度贴图）
  compare: 'less-equal',  // 'never' | 'less' | 'equal' | ...
});
```

### 6.2 常用采样器组合

```js
// 平铺纹理（用于重复图案）
const repeatSampler = device.createSampler({
  addressModeU: 'repeat',
  addressModeV: 'repeat',
  magFilter: 'linear',
  minFilter: 'linear',
});

// 像素风
const nearestSampler = device.createSampler({
  addressModeU: 'clamp-to-edge',
  addressModeV: 'clamp-to-edge',
  magFilter: 'nearest',
  minFilter: 'nearest',
});

// 阴影贴图
const shadowSampler = device.createSampler({
  compare: 'less-equal',
  magFilter: 'linear',
  minFilter: 'linear',
});
```

---

## 七、绑定组（BindGroup）

`BindGroup` 把多个资源绑定到一个组里，shader 通过 `@group(N) @binding(M)` 访问。

### 7.1 BindGroupLayout

```js
// 定义绑定组布局（在管线中）
const bindGroupLayout = device.createBindGroupLayout({
  entries: [
    {
      binding: 0,
      visibility: GPUShaderStage.FRAGMENT,
      sampler: { type: 'filtering' },  // 普通采样器
    },
    {
      binding: 1,
      visibility: GPUShaderStage.FRAGMENT,
      texture: { sampleType: 'float' },  // 浮点纹理
    },
    {
      binding: 2,
      visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT,
      buffer: { type: 'uniform' },  // uniform 缓冲
    },
    {
      binding: 3,
      visibility: GPUShaderStage.COMPUTE,
      buffer: { type: 'storage' },  // storage 缓冲
    },
  ],
});
```

### 7.2 创建绑定组

```js
const bindGroup = device.createBindGroup({
  layout: bindGroupLayout,
  entries: [
    { binding: 0, resource: sampler },
    { binding: 1, resource: textureView },
    { binding: 2, resource: { buffer: uniformBuffer } },
    { binding: 3, resource: { buffer: storageBuffer, offset: 0, size: 1024 } },
  ],
});
```

### 7.3 自动布局（推荐）

如果管线使用 `'auto'` 布局，则可以从管线推断布局：

```js
const pipeline = device.createRenderPipeline({
  layout: 'auto',  // 自动推断
  // ... 其它参数
});

const layout = pipeline.getBindGroupLayout(0);  // 获取自动生成的 layout
const bindGroup = device.createBindGroup({
  layout,
  entries: [...],
});
```

---

## 八、渲染管线（RenderPipeline）

### 8.1 基础配置

```js
const pipeline = device.createRenderPipeline({
  layout: 'auto',  // 或 device.createPipelineLayout({ bindGroupLayouts: [...] })

  vertex: {
    module: device.createShaderModule({ code: vertexShaderWGSL }),
    entryPoint: 'vs_main',
    buffers: [  // 顶点缓冲布局
      {
        arrayStride: 8 * 4,  // 每个顶点 8 个 float = 32 字节
        attributes: [
          { shaderLocation: 0, offset: 0, format: 'float32x3' },   // position
          { shaderLocation: 1, offset: 12, format: 'float32x3' },  // normal
          { shaderLocation: 2, offset: 24, format: 'float32x2' },  // uv
        ],
      },
    ],
  },

  primitive: {
    topology: 'triangle-list',  // 'point-list' | 'line-list' | 'line-strip' | 'triangle-list' | 'triangle-strip'
    stripIndexFormat: undefined,
    frontFace: 'ccw',           // 'ccw' | 'cw'
    cullMode: 'back',           // 'none' | 'front' | 'back'
    unclippedDepth: false,
  },

  depthStencil: {
    format: 'depth24plus',
    depthWriteEnabled: true,
    depthCompare: 'less',
  },

  multisample: {
    count: 4,  // MSAA 4x
  },

  fragment: {
    module: device.createShaderModule({ code: fragmentShaderWGSL }),
    entryPoint: 'fs_main',
    targets: [
      {
        format: navigator.gpu.getPreferredCanvasFormat(),
        blend: {
          color: { srcFactor: 'src-alpha', dstFactor: 'one-minus-src-alpha' },
          alpha: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha' },
        },
        writeMask: GPUColorWrite.ALL,  // GPUColorWrite.RED | .GREEN | .BLUE | .ALPHA
      },
    ],
  },
});
```

### 8.2 顶点缓冲格式

```wgsl
// WGSL 端：
struct VertexIn {
  @location(0) position: vec3f,
  @location(1) normal: vec3f,
  @location(2) uv: vec2f,
}

// JS 端 format：
'float32x2', 'float32x3', 'float32x4',
'sint32x2', 'sint32x3', 'sint32x4',
'uint32x2', 'uint32x3', 'uint32x4',
'unorm8x4', 'snorm8x4',
```

### 8.3 混合模式

```js
blend: {
  color: {
    srcFactor: 'src-alpha',
    dstFactor: 'one-minus-src-alpha',
    operation: 'add',
  },
  alpha: {
    srcFactor: 'one',
    dstFactor: 'one-minus-src-alpha',
    operation: 'add',
  },
}

// 常用组合：
// 正常 alpha 混合：
//   srcFactor: 'src-alpha', dstFactor: 'one-minus-src-alpha'
// 加法混合：
//   srcFactor: 'one', dstFactor: 'one'
// 预乘 alpha：
//   srcFactor: 'one', dstFactor: 'one-minus-src-alpha'
// 完全不混合（覆盖）：
//   blend: undefined
```

### 8.4 深度与模板

```js
depthStencil: {
  format: 'depth24plus-stencil8',
  depthWriteEnabled: true,
  depthCompare: 'less-equal',  // 'always' | 'never' | 'less' | 'less-equal' | ...
  depthBias: 0,
  depthBiasSlopeScale: 0,
  depthBiasClamp: 0,
  stencilFront: { compare: 'always', failOp: 'keep', depthFailOp: 'keep', passOp: 'keep' },
  stencilBack: { compare: 'always', failOp: 'keep', depthFailOp: 'keep', passOp: 'keep' },
  stencilReadMask: 0xFFFFFFFF,
  stencilWriteMask: 0xFFFFFFFF,
}
```

---

## 九、计算管线（ComputePipeline）

### 9.1 基础计算着色器

```wgsl
@group(0) @binding(0) var<storage, read_write> data: array<f32>;

@compute @workgroup_size(64)
fn cs_main(@builtin(global_invocation_id) gid: vec3u) {
  let i = gid.x;
  if (i >= arrayLength(&data)) { return; }
  data[i] = data[i] * 2.0;
}
```

### 9.2 创建计算管线

```js
const computePipeline = device.createComputePipeline({
  layout: 'auto',
  compute: {
    module: device.createShaderModule({ code: computeShaderWGSL }),
    entryPoint: 'cs_main',
  },
});
```

### 9.3 调度计算

```js
const cmd = device.createCommandEncoder();
const pass = cmd.beginComputePass({
  timestampWrites: {  // 可选，时间戳查询
    querySet,
    beginningOfPassWriteIndex: 0,
    endOfPassWriteIndex: 1,
  },
});

pass.setPipeline(computePipeline);
pass.setBindGroup(0, computeBindGroup);
pass.dispatchWorkgroups(
  Math.ceil(dataSize / 64),  // x 维度
  1,                          // y
  1                           // z
);

pass.end();

device.queue.submit([cmd.finish()]);
```

### 9.4 工作组与同步

```wgsl
// 工作组大小（必须是 [1, 256]）
@compute @workgroup_size(8, 1, 1)  // 8 个线程
fn main() { /* ... */ }

// 工作组共享内存
var<workgroup> shared: array<f32, 64>;

@compute @workgroup_size(64)
fn main(@builtin(local_invocation_index) idx: u32) {
  shared[idx] = f32(idx);

  // 同步：所有线程达到此点才能继续
  workgroupBarrier();

  if (idx == 0u) {
    let sum = shared[0] + shared[1] + shared[2];  // 现在可以安全访问
  }
}

// 存储屏障（确保写入可见）
storageBarrier();
textureBarrier();
```

### 9.5 共享内存限制

- 工作组大小：maxComputeWorkgroupSizeX/Y/Z（通常 256）
- 工作组内线程总数：maxComputeInvocationsPerWorkgroup（通常 256）
- 共享内存：maxComputeWorkgroupStorageSize（通常 16-32 KB）

---

## 十、命令编码器与渲染流程

### 10.1 完整渲染流程

```js
// 1. 创建命令编码器
const commandEncoder = device.createCommandEncoder();

// 2. 开始渲染 pass
const renderPass = commandEncoder.beginRenderPass({
  colorAttachments: [
    {
      view: context.getCurrentTexture().createView(),
      clearValue: { r: 0.0, g: 0.0, b: 0.0, a: 1.0 },
      loadOp: 'clear',       // 'clear' | 'load'
      storeOp: 'store',      // 'store' | 'discard'
    },
  ],
  depthStencilAttachment: {
    view: depthTextureView,
    depthClearValue: 1.0,
    depthLoadOp: 'clear',
    depthStoreOp: 'store',
  },
  timestampWrites: { /* 时间戳 */ },
});

// 3. 设置管线、绑定、绘制
renderPass.setPipeline(renderPipeline);
renderPass.setBindGroup(0, bindGroup);
renderPass.setVertexBuffer(0, vertexBuffer);
renderPass.setIndexBuffer(indexBuffer, 'uint32');
renderPass.drawIndexed(indexCount, 1, 0, 0, 0);

// 4. 结束 pass
renderPass.end();

// 5. 提交
device.queue.submit([commandEncoder.finish()]);
```

### 10.2 多 pass 渲染（后处理）

```js
const cmd = device.createCommandEncoder();

// Pass 1：场景渲染到 off-screen 纹理
const scenePass = cmd.beginRenderPass({
  colorAttachments: [{
    view: sceneTextureView,
    clearValue: { r: 0, g: 0, b: 0, a: 1 },
    loadOp: 'clear',
    storeOp: 'store',
  }],
});
scenePass.setPipeline(scenePipeline);
scenePass.setBindGroup(0, sceneBG);
scenePass.drawIndexed(sceneIndexCount);
scenePass.end();

// Pass 2：��处理（模糊、调色等）→ 输出到 canvas
const postPass = cmd.beginRenderPass({
  colorAttachments: [{
    view: context.getCurrentTexture().createView(),
    loadOp: 'clear',
    storeOp: 'store',
  }],
});
postPass.setPipeline(postPipeline);
postPass.setBindGroup(0, postBG);  // 包含 sceneTexture
postPass.draw(6);  // 全屏 quad
postPass.end();

device.queue.submit([cmd.finish()]);
```

### 10.3 间接绘制

```js
// 间接绘制参数缓冲（GPU 生成）
const indirectBuffer = device.createBuffer({
  size: 20,  // sizeof(IndirectDrawIndexed)
  usage: GPUBufferUsage.INDIRECT | GPUBufferUsage.STORAGE,
});

// GPU 写入参数后，无需 CPU 介入即可绘制
renderPass.drawIndexedIndirect(indirectBuffer, 0);
```

### 10.4 提交与异步

```js
// 同步提交
device.queue.submit([cmd.finish()]);

// 链式提交（多个 command buffer 按顺序执行）
device.queue.submit([cmd1.finish(), cmd2.finish()]);

// 等待完成
device.queue.onSubmittedWorkDone().then(() => {
  console.log('GPU 已完成所有提交的工作');
});
```

---

## 十一、Canvas 配置与展示

### 11.1 配置 Canvas Context

```js
const canvas = document.querySelector('canvas');
const context = canvas.getContext('webgpu');

context.configure({
  device,
  format: navigator.gpu.getPreferredCanvasFormat(),
  alphaMode: 'opaque',  // 'opaque' | 'premultiplied'
  colorSpace: 'srgb',
  usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.COPY_SRC,
});

// 获取当前纹理（每帧需要重新调用）
const currentTexture = context.getCurrentTexture();
const view = currentTexture.createView();
```

### 11.2 OffscreenCanvas + Worker

```js
// 主线程
const offscreen = canvas.transferControlToOffscreen();
worker.postMessage({ canvas: offscreen }, [offscreen]);

// Worker
self.onmessage = (e) => {
  const canvas = e.data.canvas;
  const context = canvas.getContext('webgpu');
  context.configure({ device, format: navigator.gpu.getPreferredCanvasFormat() });

  // 在 worker 中渲染
  requestAnimationFrame(render);
};

function render() {
  const cmd = device.createCommandEncoder();
  const pass = cmd.beginRenderPass({
    colorAttachments: [{
      view: context.getCurrentTexture().createView(),
      loadOp: 'clear',
      storeOp: 'store',
    }],
  });
  pass.setPipeline(pipeline);
  pass.setBindGroup(0, bg);
  pass.draw(3);
  pass.end();
  device.queue.submit([cmd.finish()]);

  requestAnimationFrame(render);
}
```

---

## 十二、查询与时间戳

### 12.1 时间戳查询

```js
const querySet = device.createQuerySet({
  type: 'timestamp',
  count: 2,  // 每帧 2 个时间戳
});

const queryBuffer = device.createBuffer({
  size: 2 * 8,  // 每个时间戳 8 字节（i64 + u64，但实际用 BigInt64Array）
  usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC,
});

const cmd = device.createCommandEncoder();
const pass = cmd.beginComputePass({
  timestampWrites: {
    querySet,
    beginningOfPassWriteIndex: 0,
    endOfPassWriteIndex: 1,
  },
});
pass.setPipeline(pipeline);
pass.dispatchWorkgroups(/* ... */);
pass.end();

// 解析到缓冲
cmd.resolveQuerySet(querySet, 0, 2, queryBuffer, 0);

// 读回
await queryBuffer.mapAsync(GPUMapMode.READ);
const timestamps = new BigUint64Array(queryBuffer.getMappedRange());
// timestamps[0] = GPU 时间戳开始
// timestamps[1] = GPU 时间戳结束
const durationNs = Number(timestamps[1] - timestamps[0]);
queryBuffer.unmap();
```

### 12.2 管线统计

```js
const querySet = device.createQuerySet({
  type: 'pipeline-statistics',
  count: 1,
  pipelineStatistics: ['vertex-shader-invocations', 'clipper-invocations', 'fragment-shader-invocations'],
});
```

---

## 十三、错误处理与验证

### 13.1 错误层级

WebGPU 错误分为三个层级：

1. **编译时错误**：shader 语法错误 → `createShaderModule()` 抛错
2. **验证错误**：参数错误（错的尺寸、错的 usage） → 设备错误回调
3. **运行时错误**：GPU 执行错误 → 设备错误回调

### 13.2 错误监控

```js
// 验证错误（未捕获）
device.onuncapturederror = (event) => {
  console.error('WebGPU Error:', event.error);
  event.preventDefault();
};

// Shader 编译错误
try {
  const module = device.createShaderModule({ code: shaderCode });
} catch (e) {
  console.error('Shader 编译失败:', e);
}

// 编译信息（异步）
const module = device.createShaderModule({ code: shaderCode });
const info = await module.getCompilationInfo();
if (info.messages.length > 0) {
  info.messages.forEach(msg => {
    console.warn(`[${msg.type}] ${msg.lineNum}:${msg.linePos} - ${msg.message}`);
  });
}

// Pipeline 编译错误（异步）
const pipeline = device.createRenderPipeline({ /* ... */ });
// 如果有错误，会通过 device.onuncapturederror 报告
```

### 13.3 设备丢失恢复

```js
device.lost.then((info) => {
  console.error(`设备丢失: ${info.reason} - ${info.message}`);
  showError('GPU 设备丢失，请刷新页面');

  // 实际生产中需要：
  // 1. 销毁所有资源
  // 2. 重新请求 adapter
  // 3. 重新创建 device
  // 4. 重新上传所有纹理、缓冲
  // 5. 重新创建所有 pipeline、bind group
});
```

### 13.4 调试技巧

```js
// 1. 开启验证层（开发环境）
// Chrome：chrome://flags/#enable-webgpu-developer-features
// 或启动参数：--enable-features=WebGPUValidation

// 2. 使用 Chrome 的 WebGPU Inspector
// chrome://gpu 页可看到 WebGPU 详细信息

// 3. RenderDoc / SpectreJS 抓帧
// Mac 上 SpectreJS 最方便

// 4. Label 资源（调试用）
const buffer = device.createBuffer({
  /* ... */
  label: 'vertexBuffer-quad',
});
```

---

## 十四、性能调优

### 14.1 渲染管线优化

- ✅ **尽量减少管线切换**：状态变化（pipeline、bind group）是 GPU 同步点
- ✅ **合并小 draw call**：用 InstancedRender 或 MultiDrawIndirect
- ✅ **使用索引绘制**：减少顶点处理
- ✅ **减少纹理绑定切换**：一次绑定多张纹理
- ❌ **避免在每一帧重新创建 pipeline、bind group**

### 14.2 内存优化

```js
// 1. 复用缓冲
const reusableBuffer = device.createBuffer({ size: 1_000_000, usage: ... });

// 2. Ring buffer 上传数据
const UPLOAD_BUFFER_SIZE = 16 * 1024 * 1024;
const uploadBuffer = device.createBuffer({ size: UPLOAD_BUFFER_SIZE, usage: COPY_SRC | COPY_DST });
const fence = 0;  // 当前写入位置

// 3. 异步映射避免阻塞
await buffer.mapAsync(GPUMapMode.WRITE);
// 写入...
buffer.unmap();
```

### 14.3 计算着色器优化

```wgsl
// 1. 合理的 workgroup size
// GPU 通常在 32-128 之间效率最高（一个 warp/wavefront）
@compute @workgroup_size(64)  // 通常 64 或 128 较好

// 2. 合并内存访问（coalesced access）
// 让相邻线程访问相邻内存地址
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3u) {
  let i = gid.x;
  data[i] = data[i] * 2.0;  // 相邻线程访问相邻地址 ✓
}

// 3. 避免分支发散
// 同一 warp 内线程走不同分支会序列化执行
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x % 2u == 0u) {
    // ... 分支 A
  } else {
    // ... 分支 B（分支发散！）
  }
}

// 4. 使用向量类型
let v = vec4f(data[i], data[i+1], data[i+2], data[i+3]);  // 比 4 次标量读取快
```

### 14.4 帧时间预算

| 目标 | 单帧预算 | 备注 |
|------|---------|------|
| VR 90Hz | 11.1ms | GPU + CPU + 系统 |
| 60Hz 普通 | 11.1ms | GPU + CPU |
| 30Hz 省电 | 33ms | 移动设备 |

使用时间戳查询定位 GPU 瓶颈。

---

## 十五、与 WebCodecs 的互操作

详见配套文档《WebCodecs API 详解》，这里只列出关键路径：

### 15.1 VideoFrame → 外部纹理

```js
const videoFrame = decoder.output;  // VideoFrame
const externalTexture = device.importExternalTexture({
  source: videoFrame,
  colorSpace: 'srgb',
});

@group(0) @binding(0) var samp: sampler;
@group(0) @binding(1) var videoTex: texture_external;

@fragment
fn fs(in: VSOut) -> @location(0) vec4f {
  return textureSample(videoTex, samp, in.uv);
}
```

### 15.2 外部纹理 → 普通纹理（用于多 pass）

```js
const ext = device.importExternalTexture({ source: videoFrame });
const cmd = device.createCommandEncoder();
cmd.copyExternalTextureToTexture(
  { source: ext },
  { texture: renderTexture },
  { width: videoFrame.displayWidth, height: videoFrame.displayHeight }
);
device.queue.submit([cmd.finish()]);
```

---

## 十六、高级特性

### 16.1 Push Constants（暂不支持）

WebGPU 当前不支持传统意义的 push constant，需要用 uniform buffer 模拟。

### 16.2 Bindless Rendering

```wgsl
@group(0) @binding(0) var textures: binding_array<texture_2d<f32>, 1024>;
@group(0) @binding(1) var<storage> materialIds: array<u32>;
```

适用于需要大量纹理切换的场景（地形、森林、粒子等）。

### 16.3 Mesh Shader（实验）

WebGPU 还未正式支持 Mesh Shader，但底层 API 已支持。

### 16.4 渲染到多视图（VR/XR）

```js
const renderPass = cmd.beginRenderPass({
  colorAttachments: [
    { view: leftEyeView, /* ... */ },
    { view: rightEyeView, /* ... */ },
  ],
});
```

### 16.5 体积渲染（Volume Rendering）

3D 纹理 + raymarching shader：

```wgsl
@group(0) @binding(0) var volumeTex: texture_3d<f32>;
@group(0) @binding(1) var transferFunc: texture_1d<f32>;

@fragment
fn fs_main(in: VSOut) -> @location(0) vec4f {
  var rayDir = normalize(/* ... */);
  var rayPos = vec3f(0.5);
  var color = vec4f(0.0);

  for (var i: i32 = 0; i < 128; i = i + 1) {
    let density = textureSampleLevel(volumeTex, samp, rayPos, 0.0).r;
    let c = textureSample(transferFunc, samp, vec2f(density, 0.5));
    color.rgb += c.rgb * c.a * (1.0 - color.a);
    color.a += c.a * (1.0 - color.a);
    rayPos += rayDir * 0.01;
  }
  return color;
}
```

### 16.6 Compute Shader 模拟粒子系统

```wgsl
struct Particle {
  position: vec3f,
  velocity: vec3f,
  life: f32,
}

@group(0) @binding(0) var<storage, read_write> particles: array<Particle>;

@compute @workgroup_size(64)
fn update(@builtin(global_invocation_id) gid: vec3u) {
  let i = gid.x;
  if (i >= arrayLength(&particles)) { return; }

  var p = particles[i];
  p.position += p.velocity * 0.016;
  p.life -= 0.016;

  if (p.life < 0.0) {
    p.position = vec3f(0.0);
    p.life = 1.0;
  }

  particles[i] = p;
}
```

---

## 十七、典型实战案例

### 17.1 全屏视频渲染（VideoFrame → WebGPU）

```js
// 初始化
const adapter = await navigator.gpu.requestAdapter();
const device = await adapter.requestDevice();
const canvas = document.querySelector('canvas');
const ctx = canvas.getContext('webgpu');
ctx.configure({ device, format: navigator.gpu.getPreferredCanvasFormat() });

// Shader
const shader = device.createShaderModule({
  code: `
    struct VSOut { @builtin(position) pos: vec4f, @location(0) uv: vec2f };
    @vertex fn vs(@builtin(vertex_index) i: u32) -> VSOut {
      var p = vec2f(0, 0);
      if (i == 1u) { p = vec2f(2, 0); }
      if (i == 2u) { p = vec2f(0, 2); }
      var o: VSOut;
      o.pos = vec4f(p - 1, 0, 1);
      o.uv = p * 0.5;
      return o;
    }
    @group(0) @binding(0) var samp: sampler;
    @group(0) @binding(1) var tex: texture_external;
    @fragment fn fs(in: VSOut) -> @location(0) vec4f {
      return textureSample(tex, samp, in.uv);
    }
  `,
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
        clearValue: { r: 0, g: 0, b: 0, a: 1 },
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

decoder.configure({
  codec: 'avc1.640028',
  codedWidth: 1920,
  codedHeight: 1080,
  hardwareAcceleration: 'prefer-hardware',
});

// 喂数据
// decoder.decode(chunk);
```

### 17.2 图像卷积（Compute Shader）

```wgsl
@group(0) @binding(0) var inputTex: texture_2d<f32>;
@group(0) @binding(1) var outputTex: texture_storage_2d<rgba8unorm, write>;
@group(0) @binding(2) var<uniform> params: vec2f;

@compute @workgroup_size(8, 8)
fn gaussianBlur(@builtin(global_invocation_id) gid: vec3u) {
  let texSize = vec2i(textureDimensions(inputTex));
  let coord = vec2i(gid.xy);

  var sum = vec4f(0.0);
  var count = 0.0;
  for (var dy: i32 = -2; dy <= 2; dy = dy + 1) {
    for (var dx: i32 = -2; dx <= 2; dx = dx + 1) {
      let p = coord + vec2i(dx, dy);
      if (all(p >= vec2i(0) && p < texSize)) {
        sum += textureLoad(inputTex, p, 0);
        count += 1.0;
      }
    }
  }

  textureStore(outputTex, coord, sum / count);
}
```

### 17.3 后处理（多 pass）

```js
const sceneTexture = device.createTexture({
  size: { width: canvas.width, height: canvas.height },
  format: navigator.gpu.getPreferredCanvasFormat(),
  usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.TEXTURE_BINDING,
});

function renderFrame() {
  const cmd = device.createCommandEncoder();

  // Pass 1: 场景
  const scenePass = cmd.beginRenderPass({
    colorAttachments: [{
      view: sceneTexture.createView(),
      loadOp: 'clear',
      storeOp: 'store',
    }],
    depthStencilAttachment: { /* 深度 */ },
  });
  scenePass.setPipeline(scenePipeline);
  scenePass.setBindGroup(0, sceneBG);
  scenePass.drawIndexed(/* ... */);
  scenePass.end();

  // Pass 2: 色调映射 + Bloom
  const postPass = cmd.beginRenderPass({
    colorAttachments: [{
      view: ctx.getCurrentTexture().createView(),
      loadOp: 'clear',
      storeOp: 'store',
    }],
  });
  postPass.setPipeline(postPipeline);
  postPass.setBindGroup(0, postBG);  // 包含 sceneTexture
  postPass.draw(3);
  postPass.end();

  device.queue.submit([cmd.finish()]);
}
```

---

## 十八、浏览器支持与降级

### 18.1 当前支持

| 浏览器 | 版本 |
|--------|------|
| Chrome / Edge | 113+（2023-05）稳定 |
| Firefox | 130+（2024-09）默认开启 |
| Safari | 17+（2023-09）macOS 14+/iOS 17+ |
| 国产浏览器 | 跟随 Chromium 内核 |

### 18.2 能力探测

```js
async function detectWebGPU() {
  if (!('gpu' in navigator)) return false;

  try {
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) return false;

    // 检查必要特性
    const requiredFeatures = [];
    if (adapter.features.has('shader-f16')) {
      requiredFeatures.push('shader-f16');
    }

    const device = await adapter.requestDevice({ requiredFeatures });
    device.destroy();  // 测试完释放
    return true;
  } catch (e) {
    return false;
  }
}
```

### 18.3 降级到 WebGL2

```js
async function createRenderer(canvas) {
  if ('gpu' in navigator) {
    try {
      const adapter = await navigator.gpu.requestAdapter();
      const device = await adapter.requestDevice();
      return new WebGPURenderer(device, canvas);
    } catch (e) {
      console.warn('WebGPU 不可用，降级到 WebGL2');
    }
  }

  // Fallback
  const gl = canvas.getContext('webgl2');
  return new WebGL2Renderer(gl);
}
```

---

## 附录 A：完整 API 速查表

| API | 作用 |
|-----|------|
| `navigator.gpu` | 入口 |
| `GPUAdapter` | GPU 适配器 |
| `GPUDevice` | GPU 设备 |
| `GPUBuffer` | GPU 缓冲 |
| `GPUTexture` | GPU 纹理 |
| `GPUTextureView` | 纹理视图 |
| `GPUSampler` | 采样器 |
| `GPUBindGroup` | 绑定组 |
| `GPUBindGroupLayout` | 绑定组布局 |
| `GPURenderPipeline` | 渲染管线 |
| `GPUComputePipeline` | 计算管线 |
| `GPUShaderModule` | 着色器模块 |
| `GPUCommandEncoder` | 命令编码器 |
| `GPURenderPassEncoder` | 渲染 pass |
| `GPUComputePassEncoder` | 计算 pass |
| `GPUQueue` | 命令队列 |
| `GPUCanvasContext` | Canvas 上下文 |
| `GPUQuerySet` | 查询集 |
| `GPUPipelineLayout` | 管线布局 |

## 附录 B：与 WebGL 关键概念对照

| WebGPU 概念 | WebGL 对应 |
|------------|-----------|
| GPUBuffer + VERTEX | gl.createBuffer + gl.bufferData + gl.vertexAttribPointer |
| GPUTexture + 视图 | gl.createTexture + gl.texImage2D |
| GPUSampler | gl.createSampler (WebGL2) / gl.texParameteri |
| RenderPipeline | 顶点数组 + 编译 program + 状态设置（几十个 gl.XXX） |
| BindGroup | gl.activeTexture + gl.bindTexture + gl.uniformXXX |
| CommandEncoder + submit | gl.drawArrays / gl.drawElements（立即执行） |
| WGSL | GLSL ES |
| ComputePipeline | 无（需 transform feedback 或扩展）|

## 附录 C：参考资源

- [W3C WebGPU 规范](https://www.w3.org/TR/webgpu/)
- [WGSL 规范](https://www.w3.org/TR/WGSL/)
- [MDN - WebGPU API](https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API)
- [Chrome for Developers - WebGPU](https://developer.chrome.com/docs/web-platform/webgpu)
- [WebGPU Fundamentals](https://webgpufundamentals.org/)
- [WebGPU Samples](https://github.com/webgpu/webgpu-samples)
- [Three.js WebGPU](https://threejs.org/docs/#manual/en/introduction/WebGPU)

---

*文档版本：2026-08-27*
*适用于 W3C WebGPU Candidate Recommendation 规范*