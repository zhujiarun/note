# 船舶横摇、纵摇、升沉 — 深度技术文档

> 本文专门讲船舶在波浪中的三个主要运动:**横摇 (Roll)**、**纵摇 (Pitch)**、**升沉 (Heave)**,适合做三维可视化或操船仿真时查阅。
> 配套文档:[Three.js 船舶数据接入与映射](threejs-ship-data-mapping.md)

---

## 1. 在船舶六自由度中的位置

船舶在水中是个刚体,有 **6 个自由度(DOF)**。这正好对应 Three.js 里 `Object3D.position`(平动) 和 `rotation`(转动):

```
              ↑  Z (Heave 升沉)
              │
              │         Yaw 偏航(绕 Z,船首左右)
              │        ╱
              │      ╱
              │    ╱  _______船首→
              │  ● ──→  X (Surge 纵荡,前进后退)
             ╱   ╲
            ╱     ╲
           ╱       Pitch 纵摇(绕 Y,船首上下点头)
         Y (Sway 横荡,左右平移)
       Roll 横摇(绕 X,左右摇晃)
```

| 自由度 | 英文 | 类型 | 本文是否展开 |
|---|---|---|---|
| Surge 纵荡 | surge | 平动 | — |
| Sway 横荡 | sway | 平动 | — |
| **Heave 升沉** | **heave** | **平动** | **✔** |
| **Roll 横摇** | **roll** | **转动** | **✔** |
| **Pitch 纵摇** | **pitch** | **转动** | **✔** |
| Yaw 偏航 | yaw | 转动 | — (见配套文档) |

可视化场景里,**横摇 + 纵摇 + 升沉** 是肉眼最有感、最影响画面真实感的三项,所以本文重点讲。

---

## 2. 横摇 Roll

### 2.1 定义

船绕自身**纵轴(船首—船尾连线,即 surge 方向 X 轴)** 转动。

```
俯视:             横视:
  船尾●──→船首        ___船首___
   ╲                ╱           ╲
    ╲   平静       ╱   波峰     ╲
     ╲___         ╱     __      ╲
   水线水平       ╲___╱   ╲_____╱
                  左舷下沉(负 Roll)
```

### 2.2 符号约定(必须先确认)

**没有统一标准**,不同协议、不同船厂、不同 IMU 厂商定义都不完全一致。常见两种:

| 约定 | 右舷下沉时 | NMEA `ATT` | Signal K |
|---|---|---|---|
| A(航海常见) | Roll > 0 | 是 | 是 |
| B(航空常见) | Roll < 0 | — | — |

**右舷下沉** 指你面朝船首时,**右手边**那侧船舷下沉。

> 强烈建议:接入数据时先在静态条件下(船停泊、水面平静)读一个值,人工给船施加一次"右舷下沉",看读数变化方向,从而确认符号。**这套确认要在协议层做完**,不���留给渲染层猜。

### 2.3 数学描述

#### 单自由度线性横摇方程(经典)

忽略耦合,横摇近似为带阻尼的二阶振荡:

```
I_xx · θ̈ + B_θ · θ̇ + K_θ · θ = M_wave(t)
```

| 符号 | 含义 |
|---|---|
| `θ` | 横摇角(rad) |
| `I_xx` | 绕纵轴转动惯量 |
| `B_θ` | 阻尼系数 |
| `K_θ` | 复原力矩系数(由 GM 提供) |
| `M_wave(t)` | 波浪激励力矩 |

**固有横摇周期(经典公式)**:

```
T_roll = 2π · √(I_xx / (ρg · ∇ · GM))
```

或者工程上常用的简化式:

```
T_roll ≈ 0.8 · B / √GM        (B = 船宽 m, GM = 初稳性高 m)
```

- 集装箱船:B=32m, GM=1.0m → T_roll ≈ 25.6 s
- 散货船:B=23m, GM=0.6m → T_roll ≈ 23.7 s
- 油轮:B=46m, GM=2.0m → T_roll ≈ 26.0 s
- 小型渔船:B=4m, GM=0.5m → T_roll ≈ 4.5 s

**这是个共振周期**。当波浪遭遇周期(encounter period)接近它时,横摇会急剧放大,这就是著名的**谐摇(resonance)**。

### 2.4 物理成因

1. **波浪从舷侧打过来(beam sea)** — 横摇振幅最大,可超过 ±20°
2. **斜浪(quartering sea)** — 既有横摇又有纵摇
3. **操舵(turning)** — 离心力引发横倾
4. **货物移动** — 自由液面、移载导致横倾变化
5. **风压侧力** — 横风施加横倾力矩

### 2.5 共振与"谐摇"红线

**这是船舶安全最关键的运动之一。**

- 当 T_wave ≈ T_roll 时,即使波浪很小,横摇也会越摇越大
- 大型船舶横摇周期长(20–30 s),只有大洋长涌才能激发谐摇
- 小型船舶(渔船、游艇)横摇周期短(3–8 s),**普通风浪就能谐摇**
- 经验红线:**单幅横摇 > 30°** 视为危险

### 2.6 典型振幅与海况关系

| 道格拉斯海况 | 有义浪高 Hs (m) | 横摇单幅(大型船) | 横摇单幅(小型船) |
|---|---|---|---|
| 1 微浪 | 0.0–0.1 | < 0.5° | < 2° |
| 2 小浪 | 0.1–0.5 | 0.5–2° | 2–5° |
| 3 中浪 | 0.5–1.25 | 2–4° | 5–10° |
| 4 大浪 | 1.25–2.5 | 4–8° | 10–20° |
| 5 巨浪 | 2.5–4.0 | 8–15° | 20–30° |
| 6 狂涛 | 4.0–6.0 | 15–25° | > 30°(倾覆风险) |

> 小型船(渔船、游艇)没有减摇装置,**单幅 30°+ 很常见**;大型集装箱船/油轮通常装有减摇鳍,实船横摇可控制在 ±5° 内。

### 2.7 传感器来源

| 传感器 | 提供 |
|---|---|
| **IMU**(惯性测量单元) | 横摇、纵摇、艏向(Roll/Pitch/Yaw) |
| **VRU / MRU**(姿态参考/运动参考单元) | 横摇、纵摇、升沉,精度高 |
| **陀螺罗经 + 倾角仪** | 艏向 + 横摇(老式组合) |
| **GNSS + 多天线** | 艏向,精度低但能给出航向 |

常用型号:
- **MRU**:Kongsberg MRU 5/7000、Seapath、Ixblue PHINS
- **VRU**:VectorNav VN-100/VN-200、Sparton AHRS
- **低成本 IMU**:Xsens MTi 系列、InvenSense BMI088、ADIS16505

### 2.8 数据格式

#### NMEA 0183 ATT

```
$--ATT,x.x,x.x,x.x,x.x,x.x,x.x,x.x,x.x*hh
       roll pitch heave   rollSt  pitchSt heaveSt  reserved  reserved
```

例:`$IIATT,12.3,-2.1,0.8,A,A,A,0,0*5C`
- Roll = +12.3°(右舷下沉 12.3°)
- Pitch = -2.1°(船首下沉 2.1°)
- Heave = +0.8 m
- 状态:全部 `A` = valid

#### NMEA 2000 PGN 127257 Attitude

| 字段 | 类型 | 单位 | 说明 |
|---|---|---|---|
| Yaw | i32 | 1e-4 rad | — |
| Pitch | i16 | 1e-4 rad | — |
| Roll | i16 | 1e-4 rad | — |

更新率典型 1–10 Hz。

#### Signal K

```json
{
  "path": "navigation.attitude",
  "value": {
    "roll": -0.2144,      // rad, 负值表示左舷下沉(按 Signal K 约定)
    "pitch": 0.0366,
    "yaw": 1.4238
  }
}
```

> Signal K 默认右舷下沉为**正**(与 NMEA `ATT` 一致)。

---

## 3. 纵摇 Pitch

### 3.1 定义

船绕**横轴(左舷—右舷连线,即 sway 方向 Y 轴)** 转动,船首在垂直面里上下"点头"。

```
侧视(看船的左舷):
                ___
               /   \___            ← 船首上仰(正 Pitch)
   船尾●_____/         \____●船首
            \_____      /
                  \____/          ← 船首下沉(负 Pitch)
```

### 3.2 符号约定

**船首上仰为正**(头部抬起来) 是主流约定:
- NMEA `ATT`:船首上仰为正
- Signal K:船首上仰为正
- 航空:机头上仰为正

`pitch > 0` → 船首抬起(船被浪从船尾抬起)
`pitch < 0` → 船首扎下去(船首遭遇浪峰后扎进浪谷)

### 3.3 数学描述

纵摇同样近似为带阻尼的二阶振荡,但**激励**主要来自船首—船尾方向的浪(头浪 / 顺浪)。

```
I_yy · φ̈ + B_φ · φ̇ + K_φ · φ = M_wave(t)
```

**固有纵摇周期**:

```
T_pitch ≈ 2π · √(I_yy / (ρg · ∇ · GM_L))
```

`GM_L` 是纵向稳性高,通常 **远大于 GM**(横向稳性高),所以:

- 纵摇周期通常 **比横摇周期短**:
  - 大型船舶纵摇周期 6–12 s,横摇 20–30 s
  - 小型船舶纵摇周期 2–5 s,横摇 3–8 s

这就是为什么 **头浪时船会"扎浪"**——头浪遭遇周期 4–6 s,正好接近纵摇周期。

### 3.4 物理成因

1. **顶浪(head sea)** — 船首直接遭遇波浪,纵摇最严重
2. **斜顶浪(bowing sea)** — 同时激发纵摇和横摇
3. **船尾下沉(Squat)** — 高速航行时船尾下沉、船首上仰(不是波浪导致,是流体动力)
4. **加速度变化** — 加速/减速引发船首俯仰
5. **压载/油水舱变化** — 重心前后移动,改变配平角

### 3.5 典型振幅

| 海况 | 顶浪纵摇单幅(大型船) | 顶浪纵摇单幅(小型船) |
|---|---|---|
| 微浪 | < 0.3° | < 1° |
| 中浪 | 1–3° | 3–6° |
| 大浪 | 3–6° | 6–10° |
| 巨浪 | 6–10° | 10–15° |
| 狂涛 | 10–15° | 15–25° |

> 船首**砰击(slamming)** 是纵摇的直接后果。当船首在波谷中被抬起又落下,落回水面瞬间产生巨大冲击力,可达数百吨。这会损坏船首结构、引发"弓震"。

### 3.6 与速度的关系

**静态**纵摇(船静止在波浪里)与速度无关。**动态**纵摇(航行中)会:

- **顶浪**:速度越高,遭遇周期越短 → 越接近谐摇 → 纵摇放大
- **顺浪**:速度越高,遭遇周期越长 → 远离谐摇 → 纵摇减小
- **斜浪**:取决于浪向

**遭遇周期公式**(重要):

```
T_e = T_w / |1 - (V / g) · cos(μ) · T_w|
```

- `T_w` 真实波浪周期
- `V` 船速
- `g` 重力加速度 9.81
- `μ` 浪向与船首的夹角

> 当 `μ = 90°`(横浪),`cos(μ) = 0`,`T_e = T_w`(船速不影响遭遇周期)
> 当 `μ = 0°`(顶浪),`T_e` 减小 → 短周期激励纵摇
> 当 `μ = 180°`(顺浪),`T_e` 增大 → 长周期

### 3.7 数据格式

与横摇共用同一字段(`ATT` / PGN 127257 / `navigation.attitude`),仅取 `pitch` 这一项。

---

## 4. 升沉 Heave

### 4.1 定义

船舶**重心**(或测量点)**沿垂直方向的平动**。只有上下,没有转动。

```
侧视:
  ●船首
   ╲___
      ╲___         ╱
   ____╲___╱     ╱        ___  ← 波浪下,船整体上下浮动
              ___╱
   ___      ___╱
       ╲___╱
           ╲___
  ●船首
```

`heave > 0` = 重心上抬
`heave < 0` = 重心下沉

### 4.2 与横摇/纵摇的本质区别

| | 横摇/纵摇 | 升沉 |
|---|---|---|
| 类型 | 转动 | 平动 |
| 度数 | 角度 rad | 长度 m |
| 周期 | 6–30 s | 3–10 s |
| 主要激励 | 力矩 | 力 |

升沉是**力的累积效应**:船体本身有浮力,波浪给一个附加浮力,船在浮力—重力—阻尼下做受迫振动。

### 4.3 数学描述

```
m · z̈ + c · ż + ρgA_w · z = F_wave(t)
```

| 符号 | 含义 |
|---|---|
| `z` | 升沉位移(m) |
| `m` | 船舶质量 |
| `c` | 阻尼系数 |
| `ρgA_w` | 静水��原刚度(水线面面积 A_w 提供) |
| `F_wave(t)` | 波浪力 |

**升沉固有周期**:

```
T_heave ≈ 2π · √(m / (ρg · A_w))
```

典型值:
- 大型船舶:**6–12 s**(水线面面积大,刚度大,周期短)
- 小型船舶:**1–3 s**

### 4.4 物理成因

1. **波浪通过** — 船随波面起伏
2. **载荷变化** — 燃油/压载水/货物进出
3. **潮汐** — 整体水位变化(慢周期,与波浪升沉不同)
4. **砰击导致的瞬时下沉** — 船首砰击瞬间船整体下沉
5. **尾滑行(squat & settlement)** — 高速时船整体下沉

### 4.5 典型振幅

| 海况 | 升沉单幅(大型船) | 升沉单幅(小型船) |
|---|---|---|
| 微浪 | < 0.2 m | < 0.1 m |
| 中浪 | 0.5–1.0 m | 0.2–0.5 m |
| 大浪 | 1.0–2.0 m | 0.5–1.0 m |
| 巨浪 | 2.0–3.0 m | 1.0–2.0 m |
| 狂涛 | 3.0–5.0 m | > 2.0 m |

> 升沉比横摇/纵摇的物理感觉更"硬",因为它是直接平动,频率高时船会被剧烈颠簸。

### 4.6 测量方法

这是三者中**最难测量**的,因为传统陀螺仪只能测姿态,不能测平动。

| 方法 | 精度 | 备注 |
|---|---|---|
| **MRU 专用 heave 算法** | ±5 cm @ 95% | 主流方案,MRU 厂商有自己的算法 |
| **GNSS 双天线 + RTK** | 分米级 | 不适合高频升沉 |
| **加速度积分 + 滤波** | 漂移问题 | 必须用高通滤波切断低频 |
| **压力传感器(底部)** | cm 级 | 适合小型船,海底静压参考 |
| **雷达高度计** | cm 级 | 直升机舰载系统常用 |

**MRU 的 heave 输出算法**(核心思想):

```
真实 heave = 低频位移(加速度二次积分 + 重力补偿) - 高频噪声
            = 实时低通后的加速度积分 + 高通补偿项
```

这是 GNSS 与加速度计融合的经典问题,各家厂商算法细节保密。

### 4.7 数据格式

#### NMEA 0183 ATT

```
$IIATT,12.3,-2.1,0.8,A,A,A,0,0*5C
                 ↑
                heave = 0.8 m
```

> 注意 `ATT` 的 heave 字段单位是**米**,精度通常 0.1 m。

#### NMEA 2000

PGN 127257 没有 heave,需要看其他 PGN,或者船厂自定义。Signal K 通常把 heave 单独放在:

```json
{ "path": "navigation.heave", "value": 0.8 }
```

#### Signal K

```json
{ "path": "navigation.heave", "value": 0.8 }   // 单位 m,正为上
```

---

## 5. 三者的耦合与综合

### 5.1 它们不是独立的

真实情况下,横摇、纵摇、升沉**互相耦合**:

- 大幅横摇会改变水线面形状 → 升沉响应变化
- 升沉的非线性(砰击)是横摇的非线性激励源
- **谐摇常常与升沉耦合**——升沉"喂"给横摇
- 操纵(舵)同时影响偏航、横摇、横荡

> 仿真要做到极致,需要 6-DOF 耦合求解。但**可视化场景下分别独立渲染已经够用**,因为我们不是做操船仿真,是做"看着真实"。

### 5.2 数据时序要求

三者**采样时刻必须一致**,否则会出现视觉割裂(船在翻滚但上下不动,或上下颠簸但不转)。

- 同一帧内,3 个字段的 `timestamp` 偏差应 < 50 ms
- 多数 MRU 一次性输出 roll/pitch/heave,自带时间戳
- 如果数据来自多个源(IMU + 计程仪),需要在数据层做时间对齐

### 5.3 海况与振幅的工程估算

没有真实数据时,可用**海况 → 振幅**的查表估算:

```js
// 道格拉斯海况 1-6 → 估算横摇、纵摇、升沉振幅
function estimateMotion(seaState, shipType = 'large') {
  const table = {
    large: [
      { roll: 0.5, pitch: 0.3, heave: 0.2 },  // 1
      { roll: 2,   pitch: 1,   heave: 0.5 },  // 2
      { roll: 4,   pitch: 2,   heave: 1.0 },  // 3
      { roll: 8,   pitch: 4,   heave: 1.5 },  // 4
      { roll: 15,  pitch: 7,   heave: 2.5 },  // 5
      { roll: 25,  pitch: 12,  heave: 4.0 },  // 6
    ],
    small: [
      { roll: 2,   pitch: 1,   heave: 0.1 },
      { roll: 5,   pitch: 3,   heave: 0.3 },
      { roll: 10,  pitch: 5,   heave: 0.5 },
      { roll: 20,  pitch: 8,   heave: 0.8 },
      { roll: 30,  pitch: 12,  heave: 1.5 },
      { roll: 40,  pitch: 18,  heave: 2.5 },
    ],
  };
  return table[shipType][seaState - 1];
}
```

> 这是**没有真实数据时的兜底方案**。正式接入真实船舶数据后,**不要用这个**,以免把误差引入产品。

---

## 6. Three.js 实现细节

### 6.1 轴向映射(关键!)

假设 Three.js 场景 Y-up,**船模局部坐标系**定义为:
- +X = 船尾 → 船首(船头朝 +X)
- +Y = 上
- +Z = 右舷(从船尾向船首看)

那么:

```
Roll  (右舷下沉为正)   →  绕 +X 旋转?  视约定
                         (如果 Roll > 0 = 右舷下沉,且物体 +Z 是右舷,
                          那么 Roll 应该绕 +X 负方向旋转,
                          即 rotation.x = -roll)

Pitch (船首上仰为正)    →  绕 +Z 旋转(因为 +Z 是右舷,即横轴)
                         rotation.z = +pitch

Heave (上抬为正)        →  position.y = +heave
```

如果你模型的"船头朝向"不是 +X 而是 -Z(Three.js 默认加载朝向),需要先 `ship.rotation.y = Math.PI / 2`(或其他角度)对齐,或用 parent group 包一层做适配。

**约定死了之后,代码就这么写(船头朝 +X 约定)**:

```js
ship.rotation.order = 'YXZ';   // 见 6.3 解释
ship.rotation.set(pitch, heading, roll);
ship.position.set(x, heave, z);
```

> **必须明确记录你的约定**,在多人协作的代码里这是 P0 文档。

### 6.2 旋转中心(支点)

Three.js 默认 `rotation` 绕物体**局部原点(0,0,0)**。船体模型的"局部原点"很少正好在船体几何中心,通常在:

- 船底中点(Blender 导出常用)
- 重心处
- 船首某点

横摇 / 纵摇的旋转**必须围绕船体几何中心**,否则船会"点头越点越远"或"摇头越摇越偏"。

**做法**:
1. 在建模阶段,把模型对齐到"重心在原点"
2. 或者:`THREE.Group` 包一层,Group 原点放在重心,船模子节点偏移
3. 加载后用 `Box3.getCenter()` 算出几何中心,然后 `geometry.translate(-cx, -cy, -cz)`

```js
loader.load('ship.glb', (gltf) => {
  const model = gltf.scene;
  // 让模型重心作为局部原点
  const box = new THREE.Box3().setFromObject(model);
  const center = box.getCenter(new THREE.Vector3());
  model.position.sub(center);    // 子节点位移
  shipGroup.add(model);
});
```

### 6.3 欧拉旋转顺序

船舶姿态是三种转动的复合,Three.js 默认 `XYZ` 顺序**对船舶姿态是错的**:

- `XYZ`:先 Roll → Pitch → Heading —— 错!这样 Roll 后 X 轴变斜了,后续的 Pitch 是绕斜轴
- **`ZYX`**:先 Heading → Pitch → Roll(假设 Z=航向轴,X=横摇轴,Y=纵摇轴)—— **航海通常用这个**,但要先按你的轴向约定调整
- **`YXZ`**:先 Y(Pitch)→ X(Roll)→ Z(Heading) —— **航空常用**,适合船头朝 +X 的约定

**如果你用船头朝 +X + +Y上 + +Z 右舷 的约定,推荐 `YXZ`**:

```js
ship.rotation.order = 'YXZ';
ship.rotation.set(roll, pitch, heading);   // 注意参数是 (X=roll, Y=pitch, Z=heading)
```

**经验法则**:
- **航向(Heading)一定要最后旋转**(避免在倾斜的坐标系里做航向变换)
- **横摇/纵摇(细节运动)先做**
- 顺序 = `XYZ → X=Roll, Y=Pitch, Z=Heading` 时,order = `'YXZ'`

### 6.4 滤波策略

真实 IMU 数据有噪声,**直接套用**会看到船模高频抖动。推荐:

#### One Euro Filter(推荐)

法国 INRIA 的 Casiez 等人提出,对姿态这种**有噪声 + 需要跟手**的信号效果很好:

```js
import { OneEuroFilter } from 'one-euro-filter';

const rollFilter   = new OneEuroFilter(1.0, 0.02);  // (minCutoff, beta)
const pitchFilter  = new OneEuroFilter(1.0, 0.02);
const heaveFilter  = new OneEuroFilter(0.5, 0.01);

function tick(state, now) {
  const t = now / 1000;
  return {
    roll:  rollFilter.filter(state.roll, t),
    pitch: pitchFilter.filter(state.pitch, t),
    heave: heaveFilter.filter(state.heave, t),
  };
}
```

参数调整:
- `minCutoff` 越小越平滑、越延迟
- `beta` 越大越跟手、越抖

经验值:
- 平静海况:`minCutoff=0.5, beta=0.005`(平滑优先)
- 大浪:`minCutoff=1.5, beta=0.05`(跟手优先)

#### 二阶低通(更简单)

```js
class Lowpass {
  constructor(alpha = 0.2) { this.alpha = alpha; this.y = 0; }
  filter(x) { return this.y = this.y + this.alpha * (x - this.y); }
}
```

### 6.5 与海面 shader 的关系

横摇/纵摇/升沉 + 海面波浪是**两个独立的运动**:
- **船体**:跟着数据动
- **海面**:自己渲染波浪

如果数据给出的升沉/横摇**与海面波浪不一致**,会看到船模漂浮在波浪之上或之下。两种处理:

**(A)忽略**(推荐)
- 海面波浪是装饰,船按真实数据动
- 视觉上船"破浪",轻微穿模但不明显
- 简单,不容易错

**(C)真实耦合**(最复杂)
- 把船模的升沉 / 横摇 / 纵摇作为约束,海面波浪基于船的位置"重定位"
- 用 Gerstner 波浪叠加时,船所在位置采样波高,然后修正 heave
- 实现难度大,通常不必要

**最常见的做法**:海面波浪用真实的浪高/浪向/浪周期(从数据拿),船的姿态独立按数据渲染。两者频率接近即可,不需要严格一致。

### 6.6 与锚泊 / 停车状态的差异

- **航行中**:全量横摇/纵摇/升沉,数据齐全
- **锚泊中**:横摇/纵摇仍然有,但升沉和摇晃幅度更小
- **靠泊中**:所有运动都很小,甚至为零(船固定在码头)
- **拖船 / 被拖**:运动是被动的,主要靠拖船给出

可视化场景中,**航行状态**判断可以靠 `navigation.speedOverGround` 或 AIS `navigationStatus`,据此选择不同的数据通道或衰减。

### 6.7 限幅与异常保护

真实数据可能给出**不合理的值**(传感器故障、电缆松动、强冲击):

```js
const SAFE = {
  roll:  45 * Math.PI / 180,   // ±45°
  pitch: 20 * Math.PI / 180,   // ±20°
  heave: 10,                   // ±10 m
};

function clamp(v, max) {
  if (!Number.isFinite(v)) return 0;
  return Math.max(-max, Math.min(max, v));
}

function sanitize(state) {
  return {
    ...state,
    roll:  clamp(state.roll,  SAFE.roll),
    pitch: clamp(state.pitch, SAFE.pitch),
    heave: clamp(state.heave, SAFE.heave),
  };
}
```

---

## 7. 完整代码模板

下面是推荐的结构,放在你的 Three.js 项目里:

```js
// ShipMotion.js
import * as THREE from 'three';
import { OneEuroFilter } from 'one-euro-filter';

const DEG = Math.PI / 180;

export class ShipMotionController {
  constructor(shipGroup) {
    this.ship = shipGroup;
    this.ship.rotation.order = 'YXZ';   // 锁定旋转顺序

    // 滤波器
    this.rollFilter  = new OneEuroFilter(1.0, 0.02);
    this.pitchFilter = new OneEuroFilter(1.0, 0.02);
    this.heaveFilter = new OneEuroFilter(0.5, 0.01);

    // 平滑变量
    this.smooth = { roll: 0, pitch: 0, heave: 0 };

    // 安全阈值
    this.SAFE_ROLL  = 45 * DEG;
    this.SAFE_PITCH = 20 * DEG;
    this.SAFE_HEAVE = 10;
  }

  apply(rawState, nowSec) {
    // 1. 异常保护
    const roll  = this._clamp(rawState.roll,  this.SAFE_ROLL);
    const pitch = this._clamp(rawState.pitch, this.SAFE_PITCH);
    const heave = this._clamp(rawState.heave, this.SAFE_HEAVE);

    // 2. 滤波
    this.smooth.roll  = this.rollFilter.filter(roll,  nowSec);
    this.smooth.pitch = this.pitchFilter.filter(pitch, nowSec);
    this.smooth.heave = this.heaveFilter.filter(heave, nowSec);

    // 3. 写入船体
    //    约定:船头朝 +X, +Y 上, +Z 右舷
    //    rotation.order = 'YXZ',参数顺序 = (X, Y, Z) = (roll, pitch, heading)
    this.ship.rotation.x = this.smooth.roll;
    this.ship.rotation.y = this.smooth.pitch;
    // heading 由位置推进时单独设置,这里先不覆盖
    this.ship.position.y = this.smooth.heave;
  }

  applyHeading(headingRad) {
    this.ship.rotation.z = headingRad;
  }

  _clamp(v, max) {
    if (!Number.isFinite(v)) return 0;
    return Math.max(-max, Math.min(max, v));
  }
}
```

```js
// main.js 使用示例
import { ShipMotionController } from './ShipMotionController';

const shipGroup = new THREE.Group();
scene.add(shipGroup);

const motion = new ShipMotionController(shipGroup);

function animate() {
  const now = performance.now() / 1000;
  const shipState = store.getLatestShipState();   // 你的状态层

  // 位置(经纬度 → ENU,见配套文档)
  shipGroup.position.x = shipState.enu.x;
  shipGroup.position.z = shipState.enu.z;

  // 航向
  motion.applyHeading(shipState.heading);

  // 横摇/纵摇/升沉
  motion.apply(shipState, now);

  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}
```

---

## 8. 常见陷阱 Checklist

- [ ] **轴向约定没文档化** — 团队协作时不同人有不同假设,导致 3 个月后看代码混乱
- [ ] **模型几何中心没对齐原点** — 横摇看起来像"绕远处一个点转",很怪
- [ ] **欧拉顺序错了** — 默认 `XYZ` 用于船的姿态是错的,必须显式 `YXZ`/`ZYX`
- [ ] **没滤波** — 高频 IMU 噪声让船模看起来像癫痫
- [ ] **数据缺失没降级** — 缺数据时船模瞬移到 0,体验割裂
- [ ] **没限幅** — 坏数据(如 pitch=999°)把船模翻个底朝天
- [ ] **时间戳不对齐** — roll 来自 IMU, heave 来自另一个源,时间错开 200 ms,船看起来"飘"
- [ ] **船模 Z-fighting 水线** — heave 太小时船底与水面重合,闪烁
- [ ] **单位忘了换算** — IMU 给的是度/弧度、heave 是米/英尺,搞错单位船模消失或剧烈跳

---

## 9. 参考资源

- **船舶运动学** - Fossen, T. I. *Handbook of Marine Craft Hydrodynamics and Motion Control*
- **IMO 稳性规则** - IMO IS Code 2008
- **DNV 船舶运动手册** - DNV-RP-H103
- **One Euro Filter 论文** - Casiez et al., *1€ Filter: A Simple Speed-based Low Pass Filter for Noisy Input in Interactive Systems*, CHI 2012
- **WebGL/Ocean shader** - Evan Wallace 的 WebGL Water 源码
- **NMEA 0183 ATT / NMEA 2000 PGN 127257** 协议规范

---

> 文档结束。版本 v1.0,2026-08-24。
> 与 [Three.js 船舶数据接入与映射](threejs-ship-data-mapping.md) 配套使用。