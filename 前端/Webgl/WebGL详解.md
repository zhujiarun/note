# WebGL 完整详解

> WebGL 1.0 / 2.0 / WebGL 入门到精通参考手册
> 涵盖：上下文、Shader、缓冲、纹理、FrameBuffer、Uniform、绘制流程、扩展、性能优化
> 适合作为浏览器 3D 图形开发的速查手册

---

## 目录

- [一、概述与版本演进](#一概述与版本演进)
- [二、上下文初始化](#二上下文初始化)
- [三、Shader 与 GLSL](#三shader-与-glsl)
- [四、Program 与 Uniform](#四program-与-uniform)
- [五、顶点缓冲对象（VBO）](#五顶点缓冲对象vbo)
- [六、顶点数组对象（VAO）](#六顶点数组对象vao)
- [七、纹理（Texture）](#七纹理texture)
- [八、采样与过滤](#八采样与过滤)
- [九、FrameBuffer 与 Renderbuffer](#九framebuffer-与-renderbuffer)
- [十、绘制流程](#十绘制流程)
- [十一、混合、深度、模板](#十一混合深度深度、模板)
- [十二、WebGL 2.0 新特性](#十二webgl-20-新特性)
- [十三、扩展机制](#十三扩展机制)
- [十四、几何与矩阵工具](#十四几何与矩阵工具)
- [十五、性能优化清单](#十五性能优化清单)
- [十六、典型实战案例](#十六典型实战案例)
- [十七、错误处理与调试](#十七错误处理与调试)
- [十八、与 WebGPU 的对比](#十八与-webgpu-的对比)
- [附录 A：API 速查表](#附录-aapi-速查表)
- [附录 B：参考资源](#附录-b参考资源)

---

## 一、概述与版本演进

### 1.1 什么是 WebGL

WebGL（Web Graphics Library）是一套 JavaScript API，通过 `<canvas>` 元素暴露 GPU 加速的 2D/3D 图形能力，本质上是 **OpenGL ES** 在 Web 上的移植。

**版本演进：**

| 版本 | 基础 | 发布时间 | 现状 |
|------|------|---------|------|
| WebGL 1.0 | OpenGL ES 2.0 | 2011 | 几乎所有浏览器支持，但已停止演进 |
| WebGL 2.0 | OpenGL ES 3.0 | 2017 | 现代浏览器均支持（iOS 15+ / Chrome 56+） |
| WebGL 3.0 | OpenGL ES 3.2 / 提案 | 草案中 | 多数浏览器实现为扩展，未广泛启用 |

### 1.2 WebGL 1.0 vs 2.0 关键差异

| 特性 | WebGL 1.0 | WebGL 2.0 |
|------|-----------|-----------|
| 基础 | OpenGL ES 2.0 | OpenGL ES 3.0 |
| Shader 版本 | GLSL ES 1.00 | GLSL ES 3.00 |
| 3D 纹理 | ❌ | ✓ |
| 整数纹理 | ❌ | ✓ |
| 多重渲染目标（MRT） | 1 个 | 多个 |
| 顶点数组对象（VAO） | 扩展 | 内置 |
| Sampler Object | 纹理参数 | 独立对象 |
| 纹理压缩 | 扩展 | 部分原生支持 |
| Instanced Rendering | 扩展 | 内置 |
| Uniform Buffer Object | ❌ | ✓ |
| Transform Feedback | 扩展 | ✓ |
| Blend Equation Advanced | ❌ | ✓ |
| 像素缓冲对象（PBO） | 扩展 | ✓ |

### 1.3 WebGL 的核心特性

- **状态机 API**：所有状态由全局上下文管理
- **Shader 驱动**：必须用 GLSL 编写 GPU 程序
- **资源显式创建**：Buffer、Texture、Framebuffer 都要手动管理
- **同步执行**：`gl.drawArrays` 立即提交 GPU（与 WebGPU 不同）
- **错误码查询**：`gl.getError()` / `getError` 异步查错

---

## 二、上下文初始化

### 2.1 获取 WebGL 上下文

```js
// 获取 WebGL 2.0 上下文
const canvas = document.querySelector('canvas');
const gl = canvas.getContext('webgl2', {
  alpha: true,
  depth: true,
  stencil: false,
  antialias: true,        // MSAA
  premultipliedAlpha: true,
  preserveDrawingBuffer: false,  // 高性能，但需要 readPixels 时要 true
  powerPreference: 'high-performance',  // 'low-power' | 'high-performance'
  failIfMajorPerformanceCaveat: false,
});

// 降级到 WebGL 1.0
if (!gl) {
  const gl1 = canvas.getContext('webgl');
  // 或 'experimental-webgl'
}

// 退化情况：Canvas 2D
if (!gl) {
  const ctx2d = canvas.getContext('2d');
}
```

### 2.2 Context Attributes 详解

| 属性 | 默认值 | 说明 |
|------|--------|------|
| `alpha` | `true` | 是否提供 alpha 通道 |
| `depth` | `true` | 是否提供深度缓冲（16/24 bit） |
| `stencil` | `false` | 是否提供模板缓冲 |
| `antialias` | `true` | 是否开启 MSAA（4x） |
| `premultipliedAlpha` | `true` | 颜色是否预乘 alpha |
| `preserveDrawingBuffer` | `false` | 渲染后是否保留 buffer（影响性能） |
| `powerPreference` | `'default'` | GPU 选择偏好 |
| `desynchronized` | `false` | 是否降低延迟（实验性） |
| `xrCompatible` | `false` | 是否与 WebXR 兼容 |

### 2.3 上下文状态

```js
// 查询上下文信息
const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
if (debugInfo) {
  console.log('Vendor:', gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL));
  console.log('Renderer:', gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL));
}

// 常用查询
gl.getParameter(gl.VERSION);          // "WebGL 2.0 (OpenGL ES 3.0 Chromium)"
gl.getParameter(gl.SHADING_LANGUAGE_VERSION);  // "WebGL GLSL ES 3.00"
gl.getParameter(gl.MAX_TEXTURE_SIZE);
gl.getParameter(gl.MAX_VERTEX_ATTRIBS);
gl.getParameter(gl.MAX_VIEWPORT_DIMS);
gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS);
gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS);
gl.getParameter(gl.MAX_VARYING_VECTORS);
gl.getParameter(gl.MAX_COMBINED_TEXTURE_IMAGE_UNITS);
gl.getParameter(gl.MAX_RENDERBUFFER_SIZE);
```

### 2.4 上下文丢失与恢复

```js
canvas.addEventListener('webglcontextlost', (e) => {
  e.preventDefault();  // 必须 preventDefault 才能收到恢复事件
  console.warn('WebGL 上下文丢失');
  pauseRendering();
});

canvas.addEventListener('webglcontextrestored', () => {
  console.log('WebGL 上下文恢复');
  // 重新创建所有 WebGL 资源（shader、buffer、texture、framebuffer）
  initResources();
  resumeRendering();
});
```

---

## 三、Shader 与 GLSL

### 3.1 Shader 类型

- **Vertex Shader**：顶点变换（位置、光照、法线变换）
- **Fragment Shader**：像素着色（颜色计算、纹理采样）
- **WebGL 2.0 还有 Geometry / Tessellation / Compute（理论）**：但 WebGL 不支持，WebGPU 才支持 Compute

### 3.2 GLSL ES 1.00（WebGL 1.0）

```glsl
// Vertex shader
attribute vec3 aPosition;
attribute vec3 aNormal;
attribute vec2 aUV;

uniform mat4 uModelViewProjection;
uniform mat4 uModel;
uniform mat3 uNormalMatrix;

varying vec3 vNormal;
varying vec2 vUV;

void main() {
  gl_Position = uModelViewProjection * vec4(aPosition, 1.0);
  vNormal = normalize(uNormalMatrix * aNormal);
  vUV = aUV;
}

// Fragment shader
precision mediump float;

uniform sampler2D uTexture;
uniform vec3 uLightDir;
uniform vec3 uLightColor;

varying vec3 vNormal;
varying vec2 vUV;

void main() {
  vec4 texColor = texture2D(uTexture, vUV);
  float diffuse = max(dot(vNormal, uLightDir), 0.0);
  vec3 color = texColor.rgb * uLightColor * diffuse;
  gl_FragColor = vec4(color, texColor.a);
}
```

### 3.3 GLSL ES 3.00（WebGL 2.0）

```glsl
// 顶点着色器：in/out 替代 attribute/varying
#version 300 es
precision highp float;

in vec3 aPosition;
in vec3 aNormal;
in vec2 aUV;

uniform mat4 uMVP;
uniform mat4 uModel;
uniform mat3 uNormalMatrix;

out vec3 vNormal;
out vec2 vUV;

void main() {
  gl_Position = uMVP * vec4(aPosition, 1.0);
  vNormal = normalize(uNormalMatrix * aNormal);
  vUV = aUV;
}

// Fragment shader
#version 300 es
precision highp float;

uniform sampler2D uTexture;

in vec3 vNormal;
in vec2 vUV;

out vec4 fragColor;

void main() {
  vec4 texColor = texture(uTexture, vUV);
  fragColor = texColor;
}
```

**WebGL 2.0 关键变化：**
- 必须 `#version 300 es`
- `attribute` / `varying` → `in` / `out`
- `gl_FragColor` → 自定义 `out vec4`
- `texture2D` → `texture`
- 新增 `texelFetch`、`textureLod`、`textureGrad` 等

### 3.4 GLSL 内置变量详解

GLSL 内置变量是着色器**无需声明即可直接使用**的特殊变量，由 GPU 在管线阶段填充，或要求你手动赋值。分为**顶点着色器**和**片元着色器**两套。

#### 顶点着色器内置变量

| 变量 | 类型 | 版本 | 是否必须赋值 | 说明 |
|------|------|------|------|------|
| `gl_Position` | vec4 | 1.00+ | ✅ **必须** | 顶点的**裁剪空间**坐标 |
| `gl_PointSize` | float | 1.00+ | ❌ 可选 | 点精灵（POINTS）的像素大小 |
| `gl_VertexID` | int | 3.00+ | 只读 | 当前顶点的索引 |
| `gl_InstanceID` | int | 3.00+ | 只读 | 当前实例的索引（实例渲染时） |

**`gl_Position`：裁剪空间 vs NDC**

`gl_Position` 接收的是**裁剪空间（clip space）**坐标——经过 MVP 矩阵变换但**还没做透视除法**的四维向量。GPU 随后会自动做透视除法，转成 NDC（标准化设备坐标）：

```glsl
gl_Position = uMVP * vec4(aPosition, 1.0);
// (x/w, y/w, z/w) 才是真正的 NDC，由 GPU 自动算
```

**`gl_PointSize`**

只在 `gl.drawArrays(gl.POINTS, ...)` 时生效。默认 1.0 像素：

```glsl
gl_PointSize = 10.0;  // 渲染成 10x10 像素的点
```

**`gl_VertexID` / `gl_InstanceID`**（WebGL 2.0）

```glsl
int vid = gl_VertexID;     // 当前顶点索引（0, 1, 2, ...）
int iid = gl_InstanceID;   // 当前实例索引（实例渲染时）
```

#### 片元着色器内置变量

| 变量 | 类型 | 版本 | 是否必须赋值 | 说明 |
|------|------|------|------|------|
| `gl_FragColor` | vec4 | **1.00 only** | ✅ **必须** | 当前像素的最终颜色 |
| `gl_FragCoord` | vec4 | 1.00+ | 只读 | 当前像素的窗口坐标 |
| `gl_FrontFacing` | bool | 1.00+ | 只读 | 当前像素是否在正面 |
| `gl_PointCoord` | vec2 | 1.00+ | 只读 | 点精灵内的 [0,1]² 坐标 |
| `gl_FragDepth` | float | 扩展/3.00 | 可选 | 自定义深度值 |
| `gl_PrimitiveID` | int | 3.00+ | 只读 | 当前图元 ID |

**`gl_FragColor`（仅 GLSL ES 1.00）**

```glsl
void main() {
  gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);  // 红色
}
```

在 GLSL ES 3.00 中已**移除**，必须改用用户自定义 `out vec4`：

```glsl
#version 300 es
out vec4 fragColor;
void main() {
  fragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
```

**`gl_FragCoord`：窗口坐标（不是 NDC！）**

```glsl
vec4 fc = gl_FragCoord;
// fc.x : 当前像素中心的窗口坐标 x（左下角 (0.5, 0.5)，不是 (0, 0)）
// fc.y : 当前像素中心的窗口坐标 y
// fc.z : 当前像素的深度值 [0, 1]，与深度缓冲比较使用
// fc.w : 1 / 裁剪空间 w（透视除法的倒数）
```

常见用途：

```glsl
// 1. 屏幕空间效果（描边、扫描线、像素化）
float scanline = sin(gl_FragCoord.y * 0.5) * 0.5 + 0.5;
gl_FragColor.rgb *= scanline;

// 2. 屏幕 UV（不需要 varying 传 uv）
vec2 screenUV = gl_FragCoord.xy / uResolution;
```

注意：`gl_FragCoord.y` 的方向取决于视口的 Y 翻转设置（`gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, ...)`）。

**`gl_FrontFacing`：正反面区分**

```glsl
if (gl_FrontFacing) {
  // 正面
} else {
  // 背面（可做背面不同颜色、不同材质）
}
```

配合面剔除 `gl.cullFace(gl.BACK)` 使用——被剔除的片元**不会进入片元着色器**。

**`gl_PointCoord`：点精灵内的 UV**

只在 `POINTS` 模式时有效，范围 `[0, 1]²`，左下角 (0,0)、右上角 (1,1)：

```glsl
void main() {
  // 把点精灵渲染成圆形
  vec2 d = gl_PointCoord - vec2(0.5);
  float r = length(d);
  if (r > 0.5) discard;  // 圆形外的片元丢弃
  gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
```

**`gl_FragDepth`：自定义深度**

默认不需要写（GPU 用 `gl_FragCoord.z`）。如果**必须**自定义深度值（比如 alpha-test 替代）：

```glsl
// WebGL 1.0 需要扩展
#extension GL_EXT_frag_depth : enable
gl_FragDepthEXT = 0.5;

// WebGL 2.0 直接用
gl_FragDepth = 0.5;
```

⚠️ **性能代价**：写入 `gl_FragDepth` 会**禁用 early-Z 优化**（GPU 无法提前丢弃被遮挡的片元）。

**`gl_PrimitiveID`（WebGL 2.0）**

```glsl
int id = gl_PrimitiveID;  // 当前片元属于哪个图元（点/线/三角形）
```

#### 着色器间数据传递：varying / in-out

虽然 `varying` 是用户定义的变量名，但它的**机制是 GLSL 内置的**——顶点着色器写、片元着色器读，由 GPU 自动插值。

**GLSL ES 1.00**：

```glsl
// 顶点着色器
attribute vec3 aPosition;
varying vec3 vNormal;        // 声明
void main() {
  gl_Position = ...;
  vNormal = normalize(uNormalMatrix * aNormal);   // 写
}

// 片元着色器
varying vec3 vNormal;        // 接收同名 varying
void main() {
  // vNormal 已经被 GPU 插值（透视正确插值）
  float light = dot(normalize(vNormal), uLightDir);
}
```

**GLSL ES 3.00**：

```glsl
// 顶点着色器
out vec3 vNormal;            // out 输出
void main() {
  // ...
  vNormal = ...;
}

// 片元着色器
in vec3 vNormal;             // in 输入（同名匹配）
void main() {
  // 使用 vNormal
}
```

#### 总表对照

| 类别 | 变量 | 1.00 | 3.00 |
|------|------|------|------|
| 顶点 | `gl_Position` | ✅ 必须赋值 | ✅ 必须赋值 |
| 顶点 | `gl_PointSize` | ✅ | ✅ |
| 顶点 | `gl_VertexID` | ❌ | ✅ 只读 |
| 顶点 | `gl_InstanceID` | ❌ | ✅ 只读 |
| 片元 | `gl_FragColor` | ✅ 输出 | ❌ 移除，用自定义 `out` |
| 片元 | `gl_FragCoord` | ✅ 只读 | ✅ 只读 |
| 片元 | `gl_FrontFacing` | ✅ 只读 | ✅ 只读 |
| 片元 | `gl_PointCoord` | ✅ 只读 | ✅ 只读 |
| 片元 | `gl_FragDepth` | 扩展 `EXT_frag_depth` | ✅ |
| 片元 | `gl_PrimitiveID` | ❌ | ✅ 只读 |

### 3.5 编译 Shader

```js
function createShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);

  // 检查编译错误
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`Shader 编译失败:\n${log}\n源代码:\n${source}`);
  }

  return shader;
}

// WebGL 1.0
const vertexShader = createShader(gl, gl.VERTEX_SHADER, vertexSource);
const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);

// WebGL 2.0
const vertexShader = createShader(gl, gl.VERTEX_SHADER, '#version 300 es\n' + vertexSource);
```

### 3.6 调试 Shader

```js
// 详细错误日志（Chrome）
const debugShader = gl.createShader(gl.VERTEX_SHADER);
gl.shaderSource(debugShader, source);
gl.compileShader(debugShader);

if (!gl.getShaderParameter(debugShader, gl.COMPILE_STATUS)) {
  const log = gl.getShaderInfoLog(debugShader);
  console.error('编译错误:', log);
}

// 在 Chrome DevTools → Settings → Experiments → "WebGL Inspector"
// 或用 Spectre.js / RenderDoc 抓帧调试
```

---

## 四、Program 与 Uniform

### 4.1 创建与链接 Program

```js
function createProgram(gl, vsSource, fsSource) {
  const vs = createShader(gl, gl.VERTEX_SHADER, vsSource);
  const fs = createShader(gl, gl.FRAGMENT_SHADER, fsSource);

  const program = gl.createProgram();
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(program);
    throw new Error(`Program 链接失败:\n${log}`);
  }

  // 链接后 shader 可以删除
  gl.deleteShader(vs);
  gl.deleteShader(fs);

  return program;
}

// 使用
gl.useProgram(program);
```

### 4.2 获取 Attribute 与 Uniform 位置

```js
const program = createProgram(gl, vsSource, fsSource);

// attribute 位置
const aPositionLoc = gl.getAttribLocation(program, 'aPosition');
const aUVLoc = gl.getAttribLocation(program, 'aUV');

// uniform 位置
const uMVPLoc = gl.getUniformLocation(program, 'uMVP');
const uTextureLoc = gl.getUniformLocation(program, 'uTexture');
```

### 4.3 设置 Uniform

#### 基本类型

```js
gl.uniform1f(loc, 1.5);                // float
gl.uniform2f(loc, 1.5, 2.5);           // vec2
gl.uniform3f(loc, 1.5, 2.5, 3.5);      // vec3
gl.uniform4f(loc, 1.5, 2.5, 3.5, 4.5); // vec4

gl.uniform1i(loc, 0);                  // int / sampler2D

// 整数数组
gl.uniform1iv(loc, [1, 2, 3, 4]);
gl.uniform2iv(loc, [1, 2, 3, 4]);       // 实际是 [x0,y0,x1,y1,...]

// 矩阵
gl.uniformMatrix3fv(loc, false, mat3);
gl.uniformMatrix4fv(loc, false, mat4);

// transpose 必须为 false（WebGL 不支持）
```

#### Uniform Block（WebGL 2.0）

```glsl
// GLSL
layout(std140) uniform TransformUBO {
  mat4 uModel;
  mat4 uView;
  mat4 uProjection;
};
```

```js
// JS
const ubo = gl.createBuffer();
gl.bindBuffer(gl.UNIFORM_BUFFER, ubo);
gl.bufferData(gl.UNIFORM_BUFFER, 192, gl.DYNAMIC_DRAW);  // 3 个 mat4

const blockIndex = gl.getUniformBlockIndex(program, 'TransformUBO');
gl.uniformBlockBinding(program, blockIndex, 0);
gl.bindBufferBase(gl.UNIFORM_BUFFER, 0, ubo);

// 更新数据
gl.bufferSubData(gl.UNIFORM_BUFFER, 0, new Float32Array([
  ...modelMatrix, ...viewMatrix, ...projectionMatrix
]));
```

### 4.4 纹理采样器绑定

```js
// 把纹理单元 0 绑定到 sampler
gl.activeTexture(gl.TEXTURE0);
gl.bindTexture(gl.TEXTURE_2D, texture);
gl.uniform1i(uTextureLoc, 0);  // 告诉 shader 用单元 0

// 多纹理
gl.activeTexture(gl.TEXTURE0);
gl.bindTexture(gl.TEXTURE_2D, diffuseMap);
gl.activeTexture(gl.TEXTURE1);
gl.bindTexture(gl.TEXTURE_2D, normalMap);
gl.uniform1i(uDiffuseLoc, 0);
gl.uniform1i(uNormalLoc, 1);
```

---

## 五、顶点缓冲对象（VBO）

### 5.1 创建与上传

```js
// 创建 buffer
const vbo = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, vbo);

// 上传数据（静态、动态、流式）
gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
// STATIC_DRAW: 上传后不再修改
// DYNAMIC_DRAW: 频繁更新
// STREAM_DRAW: 每帧都重新上传
```

### 5.2 配置顶点属性指针

```js
// 假设顶点格式：position(3f) + normal(3f) + uv(2f) = 8 个 float = 32 字节
gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
gl.enableVertexAttribArray(aPositionLoc);
gl.vertexAttribPointer(
  aPositionLoc,
  3,             // size: vec3
  gl.FLOAT,      // type
  false,         // normalized
  32,            // stride: 一个顶点占 32 字节
  0              // offset
);

gl.enableVertexAttribArray(aNormalLoc);
gl.vertexAttribPointer(aNormalLoc, 3, gl.FLOAT, false, 32, 12);

gl.enableVertexAttribArray(aUVLoc);
gl.vertexAttribPointer(aUVLoc, 2, gl.FLOAT, false, 32, 24);
```

### 5.3 整型属性（WebGL 2.0）

```js
// GLSL
// in uint aMaterialId;
// in ivec2 aBoneIds;

// JS
gl.vertexAttribIPointer(
  loc,
  1,                // size
  gl.UNSIGNED_INT,  // type
  32,               // stride
  24                // offset
);
// WebGL 2.0 用 vertexAttribIPointer 处理整数属性
```

### 5.4 更新缓冲

```js
// 部分更新（推荐）
gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
gl.bufferSubData(gl.ARRAY_BUFFER, offset, newData);

// 重新上传整个 buffer
gl.bufferData(gl.ARRAY_BUFFER, newData, gl.DYNAMIC_DRAW);
```

### 5.5 索引缓冲（IBO/EBO）

```js
const ibo = gl.createBuffer();
gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);

// 绘制时
gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
gl.drawElements(gl.TRIANGLES, indexCount, gl.UNSIGNED_SHORT, 0);
// 或 gl.UNSIGNED_INT（WebGL 2.0 中推荐）
```

**索引类型：**
- `gl.UNSIGNED_BYTE`：最大 256 个顶点
- `gl.UNSIGNED_SHORT`：最大 65536 个顶点（WebGL 1.0 推荐）
- `gl.UNSIGNED_INT`：超过 65536 必须用（需要 `OES_element_index_uint` 扩展）

---

## 六、顶点数组对象（VAO）

VAO 把"顶点属性配置"打包成一个对象，避免重复设置。**WebGL 2.0 内置，WebGL 1.0 需要扩展**。

### 6.1 基本用法（WebGL 2.0）

```js
// 创建 VAO
const vao = gl.createVertexArray();
gl.bindVertexArray(vao);

// 配置顶点属性（一次性）
gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
gl.enableVertexAttribArray(aPositionLoc);
gl.vertexAttribPointer(aPositionLoc, 3, gl.FLOAT, false, 32, 0);
// ... 其它属性

gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);

// 后续绘制只需切换 VAO
gl.bindVertexArray(vao);
gl.drawElements(gl.TRIANGLES, indexCount, gl.UNSIGNED_INT, 0);
```

### 6.2 WebGL 1.0 用扩展

```js
const vaoExt = gl.getExtension('OES_vertex_array_object');

const vao = vaoExt.createVertexArrayOES();
vaoExt.bindVertexArrayOES(vao);
// ... 配置属性
vaoExt.bindVertexArrayOES(null);
```

### 6.3 多个 VAO 切换

```js
const vaoQuad = createQuadVAO();
const vaoCube = createCubeVAO();

function render() {
  // 渲染 quad
  gl.bindVertexArray(vaoQuad);
  gl.drawArrays(gl.TRIANGLES, 0, 6);

  // 渲染 cube
  gl.bindVertexArray(vaoCube);
  gl.drawElements(gl.TRIANGLES, 36, gl.UNSIGNED_INT, 0);
}
```

---

## 七、纹理（Texture）

### 7.1 2D 纹理

```js
// 创建纹理
const texture = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, texture);

// 上传图像数据
gl.texImage2D(
  gl.TEXTURE_2D,
  0,                  // mip level
  gl.RGBA,            // internal format
  gl.RGBA,            // format
  gl.UNSIGNED_BYTE,   // type
  image               // HTMLImageElement / HTMLCanvasElement / ImageData / ImageBitmap
);

// 设置纹理参数（或者用 sampler object）
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

// 生成 mipmap
gl.generateMipmap(gl.TEXTURE_2D);
```

### 7.2 纹理格式

#### WebGL 1.0 支持的格式

| internalFormat | format | type |
|----------------|--------|------|
| `gl.RGBA` | `gl.RGBA` | `gl.UNSIGNED_BYTE` |
| `gl.RGB` | `gl.RGB` | `gl.UNSIGNED_BYTE` |
| `gl.LUMINANCE` | `gl.LUMINANCE` | `gl.UNSIGNED_BYTE` |
| `gl.LUMINANCE_ALPHA` | `gl.LUMINANCE_ALPHA` | `gl.UNSIGNED_BYTE` |
| `gl.ALPHA` | `gl.ALPHA` | `gl.UNSIGNED_BYTE` |

#### WebGL 2.0 新增

| internalFormat | format | type |
|----------------|--------|------|
| `gl.RGBA8` | `gl.RGBA` | `gl.UNSIGNED_BYTE` |
| `gl.RGBA16F` | `gl.RGBA` | `gl.HALF_FLOAT` |
| `gl.RGBA32F` | `gl.RGBA` | `gl.FLOAT` |
| `gl.RGBA8UI` | `gl.RGBA_INTEGER` | `gl.UNSIGNED_BYTE` |
| `gl.R8` | `gl.RED` | `gl.UNSIGNED_BYTE` |
| `gl.RG8` | `gl.RG` | `gl.UNSIGNED_BYTE` |
| `gl.SRGB8_ALPHA8` | `gl.RGBA` | `gl.UNSIGNED_BYTE` |
| `gl.DEPTH_COMPONENT24` | `gl.DEPTH_COMPONENT` | `gl.UNSIGNED_INT` |
| `gl.DEPTH_COMPONENT32F` | `gl.DEPTH_COMPONENT` | `gl.FLOAT` |

### 7.3 立方贴图（Cubemap）

```js
// 6 个面的顺序：+X, -X, +Y, -Y, +Z, -Z
const faces = [posXImage, negXImage, posYImage, negYImage, posZImage, negZImage];

const cubeTex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_CUBE_MAP, cubeTex);

faces.forEach((face, i) => {
  gl.texImage2D(
    gl.TEXTURE_CUBE_MAP_POSITIVE_X + i,
    0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE,
    face
  );
});

gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
gl.generateMipmap(gl.TEXTURE_CUBE_MAP);

// shader 中用 vec3 方向采样
// texture(samplerCube, vec3(x, y, z));
```

### 7.4 3D 纹理（WebGL 2.0）

```js
const tex3D = gl.createTexture();
gl.bindTexture(gl.TEXTURE_3D, tex3D);

// 上传：width × height × depth 的体数据
gl.texImage3D(
  gl.TEXTURE_3D,
  0,                  // mip level
  gl.RGBA8,           // internal format
  width, height, depth,
  0,                  // border (must be 0)
  gl.RGBA,            // format
  gl.UNSIGNED_BYTE,   // type
  volumeData          // Uint8Array
);

gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_R, gl.CLAMP_TO_EDGE);
```

### 7.5 纹理数组（WebGL 2.0）

```js
const texArray = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D_ARRAY, texArray);

gl.texImage3D(
  gl.TEXTURE_2D_ARRAY,
  0, gl.RGBA8, width, height, layerCount,
  0, gl.RGBA, gl.UNSIGNED_BYTE, arrayData
);

// shader: texture(sampler2DArray, vec3(uv, layerIndex));
```

### 7.6 视频纹理（与 WebCodecs 集成）

```js
// 1. 从 VideoFrame 创建纹理
const texture = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, texture);
gl.texImage2D(
  gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE,
  videoFrame  // VideoFrame（实现了 TexImageSource 接口）
);

// 2. 每帧更新
videoFrame.close();  // 关闭上一帧
const newFrame = new VideoFrame(videoElement, { timestamp: ... });
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, newFrame);
```

> **注意**：WebGL 没有 WebGPU 的零拷贝 `importExternalTexture`，但浏览器对 `texImage2D(VideoFrame, ...)` 已经做了 GPU 快速路径优化，性能接近零拷贝。

---

## 八、采样与过滤

### 8.1 纹理参数（旧方式，WebGL 1.0）

```js
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
```

### 8.2 Sampler Object（WebGL 2.0）

```js
// 创建独立的 sampler
const sampler = gl.createSampler();
gl.samplerParameteri(sampler, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
gl.samplerParameteri(sampler, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.samplerParameteri(sampler, gl.TEXTURE_WRAP_S, gl.REPEAT);
gl.samplerParameteri(sampler, gl.TEXTURE_WRAP_T, gl.REPEAT);

// 绑定 sampler 到纹理
gl.bindTexture(gl.TEXTURE_2D, texture);
gl.bindSampler(0, sampler);  // 纹理单元 0

// shader 中
uniform sampler2D uTexture;  // 注意：sampler 和 texture 是分开的
```

### 8.3 常用过滤模式

| 模式 | 用途 |
|------|------|
| `NEAREST` | 像素风 |
| `LINEAR` | 平滑缩放 |
| `NEAREST_MIPMAP_NEAREST` | 块状 + 锐利 mipmap |
| `LINEAR_MIPMAP_NEAREST` | 平滑 + 锐利 mipmap |
| `NEAREST_MIPMAP_LINEAR` | 块状 + 平滑 mipmap（trilinear） |
| `LINEAR_MIPMAP_LINEAR` | 全平滑 |

### 8.4 各向异性过滤（扩展）

```js
const anisoExt = gl.getExtension('EXT_texture_filter_anisotropic') ||
                 gl.getExtension('WEBKIT_EXT_texture_filter_anisotropic');

if (anisoExt) {
  const maxAniso = gl.getParameter(anisoExt.MAX_TEXTURE_MAX_ANISOTROPY_EXT);
  gl.texParameterf(gl.TEXTURE_2D, anisoExt.TEXTURE_MAX_ANISOTROPY_EXT, maxAniso);
  // 8 或 16 都可，值越大纹理越清晰但越慢
}
```

---

## 九、FrameBuffer 与 Renderbuffer

### 9.1 FrameBuffer（离屏渲染目标）

```js
// 创建 FBO
const fbo = gl.createFramebuffer();
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);

// 附加颜色纹理
const colorTex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, colorTex);
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1024, 1024, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, colorTex, 0);

// 附加深度 Renderbuffer
const depthRb = gl.createRenderbuffer();
gl.bindRenderbuffer(gl.RENDERBUFFER, depthRb);
gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, 1024, 1024);
gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, depthRb);

// 检查完整性
const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
if (status !== gl.FRAMEBUFFER_COMPLETE) {
  throw new Error('FBO 不完整: ' + status);
}

// 渲染
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
gl.viewport(0, 0, 1024, 1024);
// ... 绘制

// 渲染回默认 framebuffer
gl.bindFramebuffer(gl.FRAMEBUFFER, null);
```

### 9.2 多渲染目标（MRT，WebGL 2.0）

```glsl
// Fragment shader
#version 300 es
precision highp float;
layout(location = 0) out vec4 gColor;
layout(location = 1) out vec4 gNormal;
layout(location = 2) out vec4 gPosition;

in vec3 vNormal;
in vec3 vWorldPos;

void main() {
  gColor = vec4(1.0, 0.5, 0.0, 1.0);
  gNormal = vec4(normalize(vNormal), 1.0);
  gPosition = vec4(vWorldPos, 1.0);
}
```

```js
const attachments = [
  gl.COLOR_ATTACHMENT0,  // gColor
  gl.COLOR_ATTACHMENT1,  // gNormal
  gl.COLOR_ATTACHMENT2,  // gPosition
];
gl.drawBuffers(attachments);
```

### 9.3 Renderbuffer vs Texture

| 用途 | 选 Renderbuffer | 选 Texture |
|------|----------------|-----------|
| 深度/模板缓冲 | ✓（无法采样） | ✓（需要采样做效果） |
| 颜色缓冲 | ❌（需要采样） | ✓ |

---

## 十、绘制流程

### 10.1 基本流程

```js
// 1. 清除
gl.clearColor(0.0, 0.0, 0.0, 1.0);
gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

// 2. 绑定 program
gl.useProgram(program);

// 3. 设置 uniform
gl.uniformMatrix4fv(uMVPLoc, false, mvpMatrix);
gl.uniform3f(uLightDirLoc, 1.0, 1.0, 1.0);

// 4. 绑定纹理
gl.activeTexture(gl.TEXTURE0);
gl.bindTexture(gl.TEXTURE_2D, diffuseMap);
gl.uniform1i(uDiffuseLoc, 0);

// 5. 绑定 VAO（WebGL 2.0）
gl.bindVertexArray(vao);

// 6. 绘制
gl.drawElements(gl.TRIANGLES, indexCount, gl.UNSIGNED_INT, 0);
```

### 10.2 绘制模式

| 模式 | 说明 |
|------|------|
| `gl.POINTS` | 每个顶点是一个点 |
| `gl.LINES` | 每两个顶点一条线 |
| `gl.LINE_STRIP` | 连线 |
| `gl.LINE_LOOP` | 闭合连线 |
| `gl.TRIANGLES` | 每三个顶点一个三角形（最常用） |
| `gl.TRIANGLE_STRIP` | 三角形带（共享顶点） |
| `gl.TRIANGLE_FAN` | 三角形扇（围绕一个中心） |

### 10.3 Instanced Rendering（WebGL 2.0）

```js
// 1. 实例缓冲
const instanceData = new Float32Array([
  // 100 个实例的 4x4 矩阵（每个矩阵 16 个 float）
  ...matrix1, ...matrix2, // ...
]);
const instanceVbo = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, instanceVbo);
gl.bufferData(gl.ARRAY_BUFFER, instanceData, gl.STATIC_DRAW);

// 2. 配置实例属性
// aInstanceMatrix: mat4（4 个 vec4 属性）
for (let i = 0; i < 4; i++) {
  gl.enableVertexAttribArray(aInstanceMatrixLoc + i);
  gl.vertexAttribPointer(aInstanceMatrixLoc + i, 4, gl.FLOAT, false, 64, i * 16);
  gl.vertexAttribDivisor(aInstanceMatrixLoc + i, 1);  // 每个实例更新一次
}

// 3. 顶点属性 divisor = 0（每个顶点更新）
gl.vertexAttribDivisor(aPositionLoc, 0);

// 4. 绘制
gl.drawElementsInstanced(gl.TRIANGLES, indexCount, gl.UNSIGNED_INT, 0, 100);
```

### 10.4 间接绘制（WebGL 2.0）

```js
// 参数缓冲（GPU 写入后 CPU 端无需再传）
const indirectBuffer = gl.createBuffer();
gl.bindBuffer(gl.DRAW_INDIRECT_BUFFER, indirectBuffer);
gl.bufferData(gl.DRAW_INDIRECT_BUFFER, new Uint32Array([
  indexCount,    // 索引数量
  instanceCount, // 实例数量
  firstIndex,    // 起始索引
  baseVertex,    // 顶点偏移
  firstInstance, // 实例偏移
]), gl.DYNAMIC_DRAW);

gl.drawElementsIndirect(gl.TRIANGLES, gl.UNSIGNED_INT, indirectBuffer, 0);
```

---

## 十一、混合、深度、模板

### 11.1 深度测试

```js
gl.enable(gl.DEPTH_TEST);
gl.depthFunc(gl.LESS);           // 'always' | 'never' | 'less' | 'less-equal' | 'equal' | 'greater' | ...
gl.depthMask(true);              // 是否写入深度缓冲
gl.clearDepth(1.0);
```

### 11.2 混合（Alpha 混合）

```js
gl.enable(gl.BLEND);
gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);  // 正常 alpha 混合
gl.blendEquation(gl.FUNC_ADD);

// 常用预设
gl.blendFunc(gl.ONE, gl.ONE);                // 加法
gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA); // 预乘 alpha
gl.blendFunc(gl.SRC_ALPHA, gl.ONE);           // 加法 alpha
```

### 11.3 模板测试

```js
gl.enable(gl.STENCIL_TEST);
gl.stencilFunc(gl.ALWAYS, 1, 0xFF);  // func, ref, mask
gl.stencilOp(gl.KEEP, gl.KEEP, gl.REPLACE);  // fail, zfail, zpass
gl.clearStencil(0);
```

### 11.4 面剔除

```js
gl.enable(gl.CULL_FACE);
gl.cullFace(gl.BACK);        // 'front' | 'back'
gl.frontFace(gl.CCW);        // 'cw' | 'ccw'
```

### 11.5 视口与裁剪

```js
gl.viewport(0, 0, canvas.width, canvas.height);

// 多个视口
gl.viewport(0, 0, 512, 512);
gl.drawArrays(/* ... */);
gl.viewport(512, 0, 512, 512);
gl.drawArrays(/* ... */);

// 裁剪（用于分屏）
gl.scissor(0, 0, 256, 256);
gl.enable(gl.SCISSOR_TEST);
```

---

## 十二、WebGL 2.0 新特性

### 12.1 必须使用 `#version 300 es`

```glsl
#version 300 es
precision highp float;
in vec3 aPos;
out vec4 fragColor;
void main() { fragColor = vec4(1.0); }
```

### 12.2 实例渲染（Instanced Rendering）

见上文 10.3。

### 12.3 多渲染目标（MRT）

见上文 9.2。

### 12.4 像素缓冲对象（PBO）

```js
// 异步像素上传/下载
const pbo = gl.createBuffer();
gl.bindBuffer(gl.PIXEL_PACK_BUFFER, pbo);
gl.bufferData(gl.PIXEL_PACK_BUFFER, width * height * 4, gl.STATIC_READ);

// 启动 readPixels（异步）
gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, 0);

// GPU 完成后读回
gl.bindBuffer(gl.PIXEL_PACK_BUFFER, pbo);
const data = new Uint8Array(width * height * 4);
// mapped data via getBufferSubData
gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, 0, data);
```

### 12.5 Transform Feedback

```js
// 把顶点 shader 输出写回 buffer（用于 GPU 粒子、模拟）
const tfBuffer = gl.createBuffer();
gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, tfBuffer);
gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER, feedbackData, gl.DYNAMIC_COPY);

gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, tf);
gl.beginTransformFeedback(gl.POINTS);
gl.drawArrays(gl.POINTS, 0, particleCount);
gl.endTransformFeedback();

// tfBuffer 现在包含新位置
```

### 12.6 Uniform Buffer Object（UBO）

见上文 4.3。

### 12.7 整数纹理

```glsl
// shader
uniform usampler2D uMaterialIndexTex;
in vec2 vUV;
flat out int vMaterialId;
void main() {
  vMaterialId = int(texture(uMaterialIndexTex, vUV).r);
}
```

---

## 十三、扩展机制

### 13.1 WebGL 1.0 常用扩展

```js
// 各向异性过滤
const anisoExt = gl.getExtension('EXT_texture_filter_anisotropic');

// 深度纹理
const depthTexExt = gl.getExtension('WEBGL_depth_texture');

// 浮点纹理
const floatTexExt = gl.getExtension('OES_texture_float');
const halfFloatTexExt = gl.getExtension('OES_texture_half_float');

// 线性浮点过滤
const floatLinearExt = gl.getExtension('OES_texture_float_linear');
const halfFloatLinearExt = gl.getExtension('OES_texture_half_float_linear');

// VAO
const vaoExt = gl.getExtension('OES_vertex_array_object');

// 整数索引
const uintIndexExt = gl.getExtension('OES_element_index_uint');

// 纹理压缩
const s3tcExt = gl.getExtension('WEBGL_compressed_texture_s3tc');
const etc1Ext = gl.getExtension('WEBGL_compressed_texture_etc1');
const pvrtcExt = gl.getExtension('WEBGL_compressed_texture_pvrtc');
const atcExt = gl.getExtension('WEBGL_compressed_texture_atc');

// 调试
const debugExt = gl.getExtension('WEBGL_debug_renderer_info');

// 调试着色器
const shaderDebugExt = gl.getExtension('WEBGL_debug_shaders');
```

### 13.2 WebGL 2.0 扩展

```js
// 同步查询（性能分析）
const timerExt = gl.getExtension('EXT_disjoint_timer_query_webgl2');

// 多实例渲染高级
const baseInstanceExt = gl.getExtension('WEBGL_multi_draw_indirect');
```

### 13.3 加载纹理压缩格式

```js
const ext = gl.getExtension('WEBGL_compressed_texture_s3tc');

// 从 KTX / DDS 文件读取压缩数据
const data = await loadKTX('diffuse.ktx');

gl.bindTexture(gl.TEXTURE_2D, tex);
gl.compressedTexImage2D(
  gl.TEXTURE_2D, 0,
  ext.COMPRESSED_RGBA_S3TC_DXT5_EXT,  // 格式
  width, height, 0,
  data
);
```

---

## 十四、几何与矩阵工具

### 14.1 内置矩阵库

WebGL 不自带矩阵库，常见做法是用 **gl-matrix**：

```bash
npm install gl-matrix
```

```js
import { mat4, mat3, vec3, quat } from 'gl-matrix';

// 透视投影
const projection = mat4.create();
mat4.perspective(projection, Math.PI / 3, w/h, 0.1, 100);

// 视图矩阵
const view = mat4.create();
mat4.lookAt(view, [0, 0, 5], [0, 0, 0], [0, 1, 0]);

// 模型矩阵
const model = mat4.create();
mat4.translate(model, model, [0, 0, -3]);
mat4.rotateX(model, model, angle);
mat4.scale(model, model, [1, 1, 1]);

// MVP
const mvp = mat4.create();
mat4.multiply(mvp, projection, view);
mat4.multiply(mvp, mvp, model);

// 传递给 shader
gl.uniformMatrix4fv(uMVPLoc, false, mvp);

// 法线矩阵（model 矩阵的逆转置）
const normalMatrix = mat3.create();
mat3.normalFromMat4(normalMatrix, model);
gl.uniformMatrix3fv(uNormalMatrixLoc, false, normalMatrix);
```

### 14.2 几何数据生成

```js
// 立方体
function createCube() {
  const positions = [
    // 前
    -1, -1,  1,   1, -1,  1,   1,  1,  1,  -1,  1,  1,
    // 后
    -1, -1, -1,  -1,  1, -1,   1,  1, -1,   1, -1, -1,
    // 上
    -1,  1, -1,  -1,  1,  1,   1,  1,  1,   1,  1, -1,
    // 下
    -1, -1, -1,   1, -1, -1,   1, -1,  1,  -1, -1,  1,
    // 左
    -1, -1, -1,  -1, -1,  1,  -1,  1,  1,  -1,  1, -1,
    // 右
     1, -1, -1,   1,  1, -1,   1,  1,  1,   1, -1,  1,
  ];
  // ... normals, uvs, indices
}
```

---

## 十五、性能优化清单

### 15.1 减少 CPU/GPU 状态切换

- ✅ **合并 Mesh**：同材质、同一组 VAO 的 mesh 一起绘制
- ✅ **使用 Instanced Rendering**：同类物体（如粒子、树、草）批量绘制
- ✅ **VAO 切换代替属性重新配置**：减少 `gl.vertexAttribPointer` 调用
- ✅ **批处理 Uniform**：把所有矩阵放到 UBO（WebGL 2.0）
- ❌ **避免每帧重新创建 buffer、texture**

### 15.2 渲染管线优化

```js
// 1. Early-Z（深度前测试）
// 着色器内不要写 gl_FragDepth（除非必要），保留 early-z 优化
gl_FragDepth = gl_FragCoord.z;  // ❌ 禁用 early-z
// 默认使用 gl_FragCoord.z 即可 ✓

// 2. 减少 fragment shader 工作量
// - 简化光照计算
// - 用 mipmap 替代远距离纹理采样
// - 用 LOD bias

// 3. 背面剔除（默认开启）
gl.enable(gl.CULL_FACE);

// 4. 视锥体剔除（CPU 端）
// 计算每个 mesh 的包围盒，与视锥体 6 个平面比较
```

### 15.3 纹理优化

- ✅ **纹理图集**：合并多张小纹理
- ✅ **压缩纹理**：用 DXT/ETC/PVRTC 减少显存
- ✅ **mipmap**：远距离物体自动用低分辨率
- ✅ **分辨率**：不要用超过屏幕尺寸的纹理
- ❌ **避免运行时频繁重新生成 mipmap**

### 15.4 缓冲优化

```js
// 1. 静态 vs 动态
gl.bufferData(ARRAY_BUFFER, staticData, gl.STATIC_DRAW);  // GPU 优化存储
gl.bufferData(ARRAY_BUFFER, dynamicData, gl.DYNAMIC_DRAW);

// 2. 局部更新用 bufferSubData
gl.bufferSubData(ARRAY_BUFFER, offset, newData);

// 3. 不要每帧重传整个 buffer（除非必要）
```

### 15.5 异步读取像素

```js
// 避免主线程同步阻塞
gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, pixels);  // ❌ 阻塞
// 用 PBO（WebGL 2.0）异步读取
```

### 15.6 监控性能

```js
// Chrome DevTools → Performance → 查看 "GPU Process"
// 或用 EXT_disjoint_timer_query_webgl2

const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
const query = gl.createQuery();
gl.beginQuery(ext.TIME_ELAPSED_EXT, query);
// 渲染...
gl.endQuery(ext.TIME_ELAPSED_EXT);

// 异步获取结果
setTimeout(() => {
  const available = gl.getQueryParameter(query, gl.QUERY_RESULT_AVAILABLE);
  if (available) {
    const timeNs = gl.getQueryParameter(query, gl.QUERY_RESULT);
    console.log('GPU 时间:', timeNs / 1_000_000, 'ms');
  }
}, 0);
```

---

## 十六、典型实战案例

### 16.1 渲染旋转立方体

```js
const canvas = document.getElementById('canvas');
const gl = canvas.getContext('webgl2');

// Shader
const vsSource = `#version 300 es
in vec3 aPos;
in vec3 aColor;
out vec3 vColor;
uniform mat4 uMVP;
void main() {
  gl_Position = uMVP * vec4(aPos, 1.0);
  vColor = aColor;
}`;

const fsSource = `#version 300 es
precision highp float;
in vec3 vColor;
out vec4 fragColor;
void main() {
  fragColor = vec4(vColor, 1.0);
}`;

// 立方体数据
const vertices = new Float32Array([
  // 位置           // 颜色
  -1,-1, 1,  1,0,0,
   1,-1, 1,  0,1,0,
   1, 1, 1,  0,0,1,
  -1, 1, 1,  1,1,0,
  // ... 后面
]);

const indices = new Uint16Array([
  0,1,2, 0,2,3,  // 前
  // ...
]);

// 编译
const vs = createShader(gl, gl.VERTEX_SHADER, vsSource);
const fs = createShader(gl, gl.FRAGMENT_SHADER, fsSource);
const program = createProgram(gl, vs, fs);

// VAO
const vao = gl.createVertexArray();
gl.bindVertexArray(vao);

const vbo = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

const aPosLoc = gl.getAttribLocation(program, 'aPos');
gl.enableVertexAttribArray(aPosLoc);
gl.vertexAttribPointer(aPosLoc, 3, gl.FLOAT, false, 24, 0);

const aColorLoc = gl.getAttribLocation(program, 'aColor');
gl.enableVertexAttribArray(aColorLoc);
gl.vertexAttribPointer(aColorLoc, 3, gl.FLOAT, false, 24, 12);

const ibo = gl.createBuffer();
gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);

// Uniform location
const uMVPLoc = gl.getUniformLocation(program, 'uMVP');

// 渲染循环
let angle = 0;
function render() {
  angle += 0.01;

  // MVP
  const projection = mat4.create();
  mat4.perspective(projection, Math.PI / 3, canvas.width / canvas.height, 0.1, 100);
  const view = mat4.create();
  mat4.lookAt(view, [0, 0, 5], [0, 0, 0], [0, 1, 0]);
  const model = mat4.create();
  mat4.rotateY(model, model, angle);
  mat4.rotateX(model, model, angle * 0.5);
  const mvp = mat4.create();
  mat4.multiply(mvp, projection, view);
  mat4.multiply(mvp, mvp, model);

  gl.clearColor(0.0, 0.0, 0.0, 1.0);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

  gl.enable(gl.DEPTH_TEST);

  gl.useProgram(program);
  gl.uniformMatrix4fv(uMVPLoc, false, mvp);
  gl.bindVertexArray(vao);
  gl.drawElements(gl.TRIANGLES, indices.length, gl.UNSIGNED_SHORT, 0);

  requestAnimationFrame(render);
}
render();
```

### 16.2 视频纹理渲染（WebGL 2.0 + WebCodecs）

```js
// 1. 初始化 WebGL 纹理
const videoTexture = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, videoTexture);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

// 2. Shader
const vs = `#version 300 es
in vec2 aPos;
in vec2 aUV;
out vec2 vUV;
void main() {
  gl_Position = vec4(aPos, 0.0, 1.0);
  vUV = aUV;
}`;

const fs = `#version 300 es
precision highp float;
in vec2 vUV;
uniform sampler2D uVideo;
out vec4 fragColor;
void main() {
  fragColor = texture(uVideo, vUV);
}`;

// 3. 全屏 quad
const quadVertices = new Float32Array([
  -1, -1,  0, 1,
   1, -1,  1, 1,
   1,  1,  1, 0,
  -1, -1,  0, 1,
   1,  1,  1, 0,
  -1,  1,  0, 0,
]);

const vao = gl.createVertexArray();
gl.bindVertexArray(vao);
const vbo = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
gl.bufferData(gl.ARRAY_BUFFER, quadVertices, gl.STATIC_DRAW);
gl.enableVertexAttribArray(0);
gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 16, 0);
gl.enableVertexAttribArray(1);
gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 16, 8);

// 4. WebCodecs 解码
const decoder = new VideoDecoder({
  output: (frame) => {
    gl.bindTexture(gl.TEXTURE_2D, videoTexture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, frame.displayWidth, frame.displayHeight, 0,
                  gl.RGBA, gl.UNSIGNED_BYTE, frame);

    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);

    gl.useProgram(program);
    gl.bindVertexArray(vao);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, videoTexture);
    gl.uniform1i(uVideoLoc, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 6);

    frame.close();
  },
  error: console.error,
});
```

### 16.3 后处理：Bloom

```js
// 1. 渲染场景到 FBO
// 2. 提取高亮区域 → FBO2
// 3. 高斯模糊（横 + 纵）→ FBO3
// 4. 合成到屏幕

// 高亮提取 shader
const brightShader = `
in vec2 vUV;
uniform sampler2D uScene;
out vec4 fragColor;
void main() {
  vec3 color = texture(uScene, vUV).rgb;
  float brightness = max(color.r, max(color.g, color.b));
  fragColor = vec4(color * smoothstep(0.7, 1.0, brightness), 1.0);
}`;

// 高斯模糊 shader（横/纵共用，通过 uniform 切换）
const blurShader = `
in vec2 vUV;
uniform sampler2D uTexture;
uniform vec2 uDirection;
uniform vec2 uTexelSize;
out vec4 fragColor;
void main() {
  vec3 color = vec3(0.0);
  float weights[5] = float[5](0.227, 0.194, 0.122, 0.054, 0.016);
  color += texture(uTexture, vUV).rgb * weights[0];
  for (int i = 1; i < 5; i++) {
    vec2 offset = uDirection * uTexelSize * float(i);
    color += texture(uTexture, vUV + offset).rgb * weights[i];
    color += texture(uTexture, vUV - offset).rgb * weights[i];
  }
  fragColor = vec4(color, 1.0);
}`;

// 最终合成
const compositeShader = `
in vec2 vUV;
uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform float uIntensity;
out vec4 fragColor;
void main() {
  vec3 scene = texture(uScene, vUV).rgb;
  vec3 bloom = texture(uBloom, vUV).rgb;
  fragColor = vec4(scene + bloom * uIntensity, 1.0);
}`;
```

### 16.4 GPU 粒子系统（Transform Feedback）

```js
// Vertex Shader：计算下一帧位置
const particleVS = `#version 300 es
in vec3 aPosition;
in vec3 aVelocity;
in float aLife;
uniform float uDeltaTime;
out vec3 vNewPosition;
out vec3 vNewVelocity;
out float vNewLife;
void main() {
  vec3 newPos = aPosition + aVelocity * uDeltaTime;
  float newLife = aLife - uDeltaTime;

  if (newLife < 0.0) {
    newPos = vec3(0.0);  // 重置
    newLife = 1.0;
  }

  vNewPosition = newPos;
  vNewVelocity = aVelocity;
  vNewLife = newLife;

  gl_Position = vec4(0.0);  // 不参与光栅化
  gl_PointSize = 1.0;
}`;

// 1. 创建 particle buffer
const particles = new Float32Array([
  // pos.x, pos.y, pos.z, vel.x, vel.y, vel.z, life
  ...(new Array(1000).fill(0)).flatMap(() => [0, 0, 0, Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5, Math.random()])
]);

const particleBuffer = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, particleBuffer);
gl.bufferData(gl.ARRAY_BUFFER, particles, gl.DYNAMIC_COPY);

// 2. 设置 Transform Feedback
const tf = gl.createTransformFeedback();
gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, tf);
gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, particleBuffer);

const program = createProgram(gl, particleVS, `#version 300 es\nprecision highp float; out vec4 f; void main(){f=vec4(0);}`);
gl.transformFeedbackVaryings(program, ['vNewPosition', 'vNewVelocity', 'vNewLife'], gl.SEPARATE_ATTRIBS);

// 3. 每帧更新
gl.beginTransformFeedback(gl.POINTS);
gl.drawArrays(gl.POINTS, 0, 1000);
gl.endTransformFeedback();
```

---

## 十七、错误处理与调试

### 17.1 错误检测

```js
// 检查错误码
const error = gl.getError();
switch (error) {
  case gl.NO_ERROR: break;
  case gl.INVALID_ENUM: console.error('GL_INVALID_ENUM'); break;
  case gl.INVALID_VALUE: console.error('GL_INVALID_VALUE'); break;
  case gl.INVALID_OPERATION: console.error('GL_INVALID_OPERATION'); break;
  case gl.INVALID_FRAMEBUFFER_OPERATION: console.error('GL_INVALID_FRAMEBUFFER_OPERATION'); break;
  case gl.OUT_OF_MEMORY: console.error('GL_OUT_OF_MEMORY'); break;
  case gl.CONTEXT_LOST_WEBGL: console.error('GL_CONTEXT_LOST'); break;
}

// 调试模式：所有 GL 调用都检查
gl = WebGLDebugUtils.makeDebugContext(gl, (err, func, args) => {
  console.error(`WebGL error in ${func}: ${WebGLDebugUtils.glEnumToString(err)}`);
});
```

### 17.2 Shader 调试

```glsl
// 在 shader 中输出调试
#version 300 es
precision highp float;
in vec2 vUV;
uniform sampler2D uTex;
out vec4 fragColor;

void main() {
  vec3 color = texture(uTex, vUV).rgb;

  // 调试：只显示红色通道
  // fragColor = vec4(color.r, 0.0, 0.0, 1.0);

  // 调试：UV 可视化
  // fragColor = vec4(vUV, 0.0, 1.0);

  fragColor = vec4(color, 1.0);
}
```

### 17.3 性能分析

```js
// 1. Chrome DevTools → Performance → 录制
// 2. WebGL Inspector（Chrome 实验功能）
// 3. Spectre.js（Mac，本地）
// 4. RenderDoc（跨平台，截帧调试）
// 5. EXT_disjoint_timer_query_webgl2（GPU 时间）
```

---

## 十八、与 WebGPU 的对比

### 18.1 API 风格差异

| 维度 | WebGL | WebGPU |
|------|-------|--------|
| API 风格 | 状态机（隐式全局状态） | 显式对象（pipeline、bind group） |
| 着色器语言 | GLSL ES | WGSL |
| 计算着色器 | 无（需 transform feedback / 扩展） | 原生支持 |
| 多线程 | 无 | OffscreenCanvas + Worker |
| 资源所有权 | 隐式 | 显式（usage flag） |
| 错误处理 | GL Error Code | Validation Error + 设备丢失 |
| 零拷贝纹理 | 受限（texImage2D） | 原生支持（importExternalTexture） |
| 命令录制 | 立即模式 | 录制到 CommandEncoder 后批量提交 |

### 18.2 何时用 WebGL，何时用 WebGPU？

| 场景 | 推荐 |
|------|------|
| 移动端广泛兼容性 | WebGL（覆盖 99% 设备） |
| 已有 WebGL 代码库 | 继续 WebGL |
| 需要 WebCodecs 零拷贝 | WebGPU |
| 需要 Compute Shader | WebGPU |
| 需要多线程渲染 | WebGPU |
| 需要显式管线状态 | WebGPU |
| 现代浏览器新项目 | WebGPU + WebGL 降级 |

### 18.3 迁移到 WebGPU

```js
// WebGL 状态 → WebGPU 管线
// WebGL: gl.useProgram + gl.uniformXXX + gl.bindTexture + gl.drawElements
// WebGPU: 创建 Pipeline + BindGroup + 一次性 setBindGroup/setPipeline，可复用
```

---

## 附录 A：API 速查表

| 类别 | API |
|------|-----|
| 上下文 | `getContext('webgl2')`, `getContext('webgl')` |
| 缓冲 | `createBuffer`, `bindBuffer`, `bufferData`, `bufferSubData` |
| 纹理 | `createTexture`, `bindTexture`, `texImage2D`, `texImage3D`, `compressedTexImage2D` |
| Shader | `createShader`, `shaderSource`, `compileShader`, `getShaderParameter` |
| Program | `createProgram`, `attachShader`, `linkProgram`, `useProgram`, `getAttribLocation`, `getUniformLocation` |
| Uniform | `uniform1f/i`, `uniform2f/i`, `uniform3f/i`, `uniform4f/i`, `uniformMatrix3fv`, `uniformMatrix4fv` |
| 顶点属性 | `enableVertexAttribArray`, `vertexAttribPointer`, `vertexAttribIPointer`, `vertexAttribDivisor` |
| VAO | `createVertexArray`, `bindVertexArray` |
| FBO | `createFramebuffer`, `bindFramebuffer`, `framebufferTexture2D`, `checkFramebufferStatus` |
| Renderbuffer | `createRenderbuffer`, `bindRenderbuffer`, `renderbufferStorage` |
| 绘制 | `drawArrays`, `drawElements`, `drawArraysInstanced`, `drawElementsInstanced`, `drawElementsIndirect` |
| 状态 | `enable`, `disable`, `blendFunc`, `depthFunc`, `cullFace`, `viewport`, `clear`, `clearColor` |

## 附录 B：常见错误与解决

| 错误 | 原因 | 解决 |
|------|------|------|
| Shader 编译失败 | GLSL 语法错误 | 查看 `getShaderInfoLog` |
| Program 链接失败 | varyings 不匹配 | 检查 vertex/fragment 的 in/out |
| FRAMEBUFFER_INCOMPLETE_ATTACHMENT | 附件格式不兼容 | 检查纹理格式与 FBO |
| FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT | 没有附件 | 添加 color/depth 附件 |
| INVALID_OPERATION on drawArrays | VAO/Buffer 未绑定 | 确保 bindBuffer → vertexAttribPointer |
| 性能低 | 状态切换频繁 | 用 VAO + 批处理 |
| 黑屏 | 着色器错误或深度问题 | 检查 depthFunc、cullFace |
| 像素模糊 | 纹理过滤设置不对 | 设置 LINEAR mipmap |

## 附录 C：参考资源

- [MDN - WebGL API](https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API)
- [WebGL 2.0 Reference Card](https://www.khronos.org/files/webgl20-reference-guide.pdf)
- [WebGL Fundamentals](https://webglfundamentals.org/)
- [Learn WebGL](https://learnwebgl.brown37.net/)
- [Three.js](https://threejs.org/)（WebGL 包装库）
- [Babylon.js](https://www.babylonjs.com/)（WebGL/WebGPU）
- [regl](https://github.com/regl-project/regl)（函数式 WebGL 包装）
- [gl-matrix](https://github.com/toji/gl-matrix)（矩阵库）

---

*文档版本：2026-08-27*
*涵盖 WebGL 1.0、2.0 与未来草案特性*