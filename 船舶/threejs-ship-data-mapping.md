# Three.js 船舶三维可视化 — 数据接入与映射文档

> 适用场景:在浏览器中以 Three.js 渲染一艘真实船舶,在模拟海面上按真实数据驱动其位置、姿态与动作。
> 目标:把"船舶数据 → 三维场景状态"这条链路完整说清楚,作为前端开发、对接后端、协议选型的依据。

---

## 1. 总览:数据到画面的链路

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 真实船舶数据 │ -> │ 协议解析层   │ -> │ 船舶状态模型 │ -> │ Three.js 渲染 │
│  AIS/NMEA/   │    │ Parser       │    │ ShipState     │    │  Renderer    │
│  自定义API   │    │              │    │ (规范化字段)  │    │              │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
      ↑                                                    ↓
      └─────────────── 控制指令(可选,操船) ────────────────┘
```

数据从最底层的物理量出发,经过规范化后被渲染层消费。**船舶状态模型**是中间的核心数据结构,所有上层(渲染、UI、报警、操船指令)都只面向它,不直接接触底层协议,这样切换数据源不需要改渲染代码。

---

## 2. 数据字段清单

下面按"对三维可视化是否必需"分四档:

- **★ 必备**:不接就动不起来或位置错
- **★★ 推荐**:有才能看到真实运动(横摇、纵摇、风浪)
- **☆☆ 可选**:丰富视觉/物理细节
- **— 辅助**:不直接驱动 3D,只用于 UI/报警

### 2.1 位置与运动(★ 必备)

| 字段       | 英文                        | 单位         | 说明         |
| -------- | ------------------------- | ---------- | ---------- |
| 经度       | Longitude                 | ° (WGS-84) | 正东为正       |
| 纬度       | Latitude                  | ° (WGS-84) | 正北为正       |
| 对地航速     | SOG (Speed Over Ground)   | 节 (kn)     | GPS 给出     |
| 对水航速     | STW (Speed Through Water) | 节          | 计程仪        |
| 航向(对地)   | COG (Course Over Ground)  | ° [0, 360) | 0 = 北,顺时针  |
| 艏向(船首指向) | Heading                   | ° [0, 360) | 陀螺罗经,真航向   |
| 转向率      | ROT (Rate of Turn)        | °/min      | 左舷负、右舷正    |
| 位置精度     | Position Accuracy         | m          | 高精度定位差分/普通 |

### 2.2 姿态(★★ 推荐)

| 字段  | 英文    | 单位  | 说明                 |
| --- | ----- | --- | ------------------ |
| 横摇  | Roll  | °   | 左舷负、右舷正,范围 ±30°    |
| 纵摇  | Pitch | °   | 船首上仰为正,范围 ±10°     |
| 偏航  | Yaw   | °   | 与 Heading 的小偏差,可省略 |
| 升沉  | Heave | m   | 垂直起伏,影响吃水线         |

### 2.3 动力(★★ 推荐,影响可视化细节)

| 字段              | 单位          | 说明          |
| --------------- | ----------- | ----------- |
| 主机转速 RPM        | rpm         | 螺旋桨转速       |
| 螺旋桨螺距 Pitch     | % 或度        | 可调螺距桨       |
| 舵角 Rudder Angle | ° [−35, 35] | 左负右正        |
| 侧推器状态           | bool        | 港口靠泊        |
| 车钟设定            | enum        | 前进/后退/停车/全速 |

### 2.4 环境(★★ 推荐,用于海面/尾浪)

| 字段 | 单位 | 说明 |
|---|---|---|
| 真风速/风向 | m/s、° | 气象站 |
| 视风速/风向 | m/s、° | 船上计算值 |
| 风向相对船首 | ° | 艉风/迎风判断 |
| 浪高/浪向/浪周期 | m、°、s | 涌浪主要参数 |
| 流速/流向 | m/s、° | 海流 |
| 水深 | m | 测深仪 |
| 海水温度、气温 | ℃ | 背景信息 |

### 2.5 船型参数(静态,接入一次即可)

| 字段 | 单位 | 说明 |
|---|---|---|
| 船长 LOA | m | 总长 |
| 船宽 Beam | m | |
| 型深 Depth | m | |
| 吃水 Draft | m | 决定船体在水面下深度 |
| 重心位置 | m | 横摇/纵摇的支点 |
| 船型(散货/集装箱/油轮/...) | enum | 选模型用 |
| IMO 号、MMSI | — | AIS 标识 |

### 2.6 AIS 通信(★ 必备,公共船舶)

| 字段 | 说明 |
|---|---|
| MMSI | 船舶唯一 ID |
| 航行状态 | 0=航行中,1=锚泊,2=失控,3=操限船,4=吃水受限,5=系泊,6=搁浅,7=捕捞,8=帆船 |
| 目的地 + ETA | 文本 + 时间 |
| 船舶类型 | AIS 类型码 |
| 船长/船宽 | 用于相对比例 |

> 周边目标船的 AIS 同样可拉入,作为 AIS 目标层显示在海面上。

### 2.7 报警与设备状态(— 辅助)

主机报警、舵机报警、火灾/进水、漂移、碰撞警告等。**不直接驱动 3D**,但可以叠加在船模上的红色高亮区域。

---

## 3. 数据来源与协议

### 3.1 数据源类型汇总

| 来源 | 适用 | 频率 | 接入难度 |
|---|---|---|---|
| NMEA 0183 串口/IP | 单船设备直连 | 1–10 Hz | 中 |
| NMEA 2000 (CAN) | 现代船舶总线 | 1–100 Hz | 中 |
| AIS 解码 | 公共船舶 | 2–10 秒 | 低(有现成库) |
| 自建平台 API | 公司自有船队 | 可调 | 低 |
| WebSocket 推送 | 实时可视化 | 10–60 Hz | 低 |
| MQTT | IoT 网关 | 可调 | 中 |

### 3.2 NMEA 0183 关键语句

NMEA 0183 是船舶最通用的协议,基于 ASCII 文本,形如 `$XXYYY,field1,field2,...*hh\r\n`。常用语句:

| 语句 | 名称 | 提供字段 |
|---|---|---|
| `RMC` | 推荐最小专用 GNSS 数据 | 经纬度、SOG、COG、时间、磁偏角 |
| `GGA` | GPS 定位数据 | 经纬度、定位质量、高度 |
| `VTG` | 对地航向航速 | COG、SOG、真/磁 |
| `HDT` | 真艏向 | 真航向(陀螺罗经) |
| `HDG` | 磁艏向 | 磁航向、磁偏、偏差 |
| `ROT` | 转向率 | ROT、状态 |
| `VHW` | 对水速度与航向 | STW、Heading |
| `DPT` | 水深 | 深度 |
| `MWV` | 风速风向(视/真) | 风速、风向、参考 |
| `MWD` | 真风向 | 真风向、风速 |
| `VDR` | 流向流速 | 流速、流向 |
| `XDR` | 传感器多源 | 横摇/纵摇/温度等 |
| `ATT` | 姿态 | 横摇、纵摇、艏向 |
| `VWT` | 视风真风 | — |
| `AIVDM` | AIS 消息 | 周围船舶 |

**示例 RMC 语句**:
```
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
       时间    状态 纬度      N/S 经度      E/S  SOG  COG  日期   磁偏
```

**前端解析**:推荐使用 [`nmea-simple`](https://www.npmjs.com/package/nmea-simple)、[`nmea0183-signalk`](https://www.npmjs.com/package/nmea0183-signalk) 或 [`@signalk/nmea0183`](https://www.npmjs.com/package/@signalk/nmea0183)。

```js
import { parseNmeaSentence } from 'nmea-simple';
const data = parseNmeaSentence('$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A');
// data.latitude, data.longitude, data.speedOverGround, data.trackMadeGood
```

### 3.3 NMEA 2000

基于 CAN 总线,二进制格式。每个 PGN(Parameter Group Number)对应一类数据:

- PGN 127250 船艏向
- PGN 127251 转弯率
- PGN 127257 姿态
- PGN 128259 对水速度
- PGN 129025 位置快速更新
- PGN 129026 COG/SOG 快速更新
- PGN 130306 风数据
- PGN 130310 环境参数
- PGN 130311 环境参数(扩展)

**前端接入**:浏览器通常拿不到原生 CAN。需要:
1. 用网关(如 Actisense NGT-1、Yacht Devices YDNU-02)把 NMEA 2000 转成 NMEA 0183 over TCP
2. 或用 [Signal K](https://signalk.org/) 服务端解析后通过 WebSocket 推送
3. Node.js 侧用 [`canboatjs`](https://www.npmjs.com/package/canboatjs) 解析 PGN

### 3.4 AIS

AIS 本身就是 NMEA 0183 的 `!AIVDM` 语句,内容是压缩的 VDM 报文。**AISlib.js / aisdecoder** 等可直接解码,得到目标船的:
- MMSI、IMO、船名、呼号
- 船长、船宽、船舶类型
- 位置、SOG、COG、Heading、ROT
- 航行状态、目的地、ETA

### 3.5 自建平台 API

大多数船队管理平台直接对外提供 REST/GraphQL/WebSocket。**推荐字段命名规范**:使用 Signal K 路径,前端不用管原始协议。

**Signal K 路径示例**:
```
navigation.position              -> { latitude, longitude, altitude }
navigation.speedOverGround       -> m/s
navigation.courseOverGround      -> rad
navigation.headingTrue           -> rad
navigation.rateOfTurn            -> rad/s
navigation.attitude              -> { roll, pitch, yaw }  (rad)
navigation.speedThroughWater     -> m/s
environment.wind.speedApparent   -> m/s
environment.wind.angleApparent   -> rad
environment.wind.speedTrue
environment.wind.angleTrue
environment.depth.belowTransducer-> m
environment.water.temperature
environment.outside.temperature
propulsion.mainEngine.revolutions-> rpm
steering.rudderAngle             -> rad
```

**WebSocket 推送示例**:
```json
{
  "context": "vessels.self",
  "updates": [{
    "timestamp": "2026-08-24T03:12:45.123Z",
    "values": [
      { "path": "navigation.position", "value": { "latitude": 31.234, "longitude": 121.456 } },
      { "path": "navigation.speedOverGround", "value": 12.4 },
      { "path": "navigation.courseOverGround", "value": 1.45 },
      { "path": "navigation.headingTrue", "value": 1.42 },
      { "path": "navigation.attitude", "value": { "roll": -0.03, "pitch": 0.01, "yaw": 1.42 } }
    ]
  }]
}
```

> Signal K 的 `updates` 是 delta(只包含变化的字段),非常适合低带宽推送。Signal K 也支持 HTTPS 请求历史回放(`/signalk/v1/api/vessels/self/history/...`)。

### 3.6 数据频率建议

| 字段 | 推荐刷新率 | 理由 |
|---|---|---|
| 位置 / COG / SOG | 1–10 Hz | 平滑航线 |
| Heading | 5–10 Hz | 转向跟随 |
| ROT | 1–4 Hz | 平滑弧线 |
| Roll / Pitch | 5–10 Hz | 横摇实时感 |
| Wind | 1 Hz | 视觉 |
| 主 RPM / 舵角 | 1–2 Hz | 视觉 |
| AIS 目标 | 2–10 s | 标准间隔 |

---

## 4. 坐标系与坐标转换

Three.js 默认是 **右手系,Y-up,单位米**。真实船舶数据是 **WGS-84 经纬度 + 度数角 + 节/米/秒**。需要做两件事:**地理坐标 → 场景坐标**,**角度 → 三维旋转**。

### 4.1 地理坐标 → 场景坐标(局部 ENU 切平面)

把第一帧(或参考点)的经纬度记作 `(lat0, lon0)`,所有船的相对位置用 **东-北-上(ENU)局部切平面坐标** 算:

```
东向距离 E = (lon - lon0) × cos(lat0) × R_equator × π/180
北向距离 N = (lat - lat0) × R_equator × π/180
```

- `R_equator = 6378137 m`(WGS-84 长半轴)
- `cos(lat0)` 修正经度收敛

**Three.js 场景约定**:常见两种,**任选其一**即可:

| 约定 | X | Y | Z |
|---|---|---|---|
| A(地理一致) | 东 E | 上 U | 北 N |
| B(常用:北-上-东,Z-up 时) | 北 N | 东 E | 上 U |

> 注意 Three.js **Y-up** 还是 **Z-up**。Three.js 默认 Y-up,所以通常:
> - `object.position.set(E, U, -N)` 或 `object.position.set(E, 0, -N)`
> - 即 `x = 东`,`z = -北`(`-N` 是因为 N 朝北,z 朝南)

```js
const R = 6378137;
const toXY = (lat, lon, lat0, lon0) => {
  const east  = (lon - lon0) * Math.cos(lat0 * Math.PI / 180) * R * Math.PI / 180;
  const north = (lat - lat0) * R * Math.PI / 180;
  return { x: east, z: -north };   // Three.js 默认 Y-up
};
```

### 4.2 角度 → 旋转

**Heading**(船首指向):0° = 北,顺时针为正。Three.js 默认 **Z 轴指向+Y** 方向为参考,但常用模型朝向 **-Z**(摄像机默认看向 -Z)。

| 数据 | Three.js | 转换 |
|---|---|---|
| Heading 0°(朝北) | 物体 -Z 朝北 | `rotation.y = π/2 - heading` 或 `heading - π/2`,取决于模型朝向 |
| Heading 顺时针+ | 同向 + | 一致 |

**常用公式**(假设模型默认朝 -Z,即未旋转时船头指向屏幕里):
```js
ship.rotation.y = (90 - headingDeg) * Math.PI / 180;
```
> 当 heading=0(朝北)→ `rotation.y = π/2`,模型 -Z 旋转 π/2 后指向 +X(东),不对;所以另一种约定是:
```js
// 模型默认朝 +X 方向作为船头
ship.rotation.y = -headingRad;
```
> 总之**先固定模型朝向,然后反推公式**。建议在模型加载后立刻调整一次,使"船头朝向"与你的"零度 = +X"对齐,后续代码不再变化。

**Roll / Pitch**:
- Roll(横摇,左舷下沉为负):直接作为 `rotation.z`(绕船体纵轴)
- Pitch(纵摇,船首上仰为正):直接作为 `rotation.x`(绕船体横轴)

> 注意 Three.js 中欧拉旋转的**旋转顺序**(`Euler.order`),默认 `'XYZ'`,建议显式设为 `'ZYX'`(先 heading,再 pitch,再 roll),更符合船舶实际姿态。

```js
ship.rotation.order = 'ZYX';
ship.rotation.set(pitchRad, headingRad, rollRad);  // 注意参数顺序对应 X Y Z
```

### 4.3 速度单位

| 数据 | 内部统一 |
|---|---|
| SOG/STW | 节 → m/s: `× 0.514444` |
| Wind speed | m/s 即可 |
| Heave | m |

```js
const speedMs = sogKnots * 0.514444;
```

### 4.4 时间与插值

**关键**:真实数据更新频率有限(1–10 Hz),但渲染是 60 Hz,**必须插值**。

- 简单做法:对 Heading/位置做线性插值,旋转用 `slerp`。
- 推荐:维护一个**短期缓冲队列**(100–500 ms),渲染时取 `(now - renderDelay)` 对应的数据,并插值。
- 横摇/纵摇/升沉最好用 **低通滤波 + 二阶谐振模型**,避免直接套用高频抖动导致模型穿模。

### 4.5 距离尺度与远裁

真实海面覆盖大尺度(船 → 港口可能几十公里)。Three.js 场景单位是米,数值会很大。

- **局部方案**(推荐):把第一个 AIS 接收点或港口设为场景原点 `(0,0,0)`,只显示半径 5–50 km 范围。
- **LOD 切换**:超过视野范围的对象做降采样。
- **投影相机**:远裁面 `far` 设为 50 000–200 000 m;近裁面 `near` 设为 1 m。

---

## 5. Three.js 映射方案

### 5.1 渲染分层

```
Scene
├─ 水面 Ocean     (ShaderMaterial / Ocean 类库)
├─ 天空 Skybox
├─ 船舶 ShipGroup
│   ├─ Hull       (船体,绕船体重心旋转)
│   ├─ SuperStructure(上层建筑)
│   ├─ Rudder     (舵,绕舵轴转)
│   ├─ Propeller  (螺旋桨,绕推进轴高速转)
│   ├─ Mast       (桅杆,挂旗/天线)
│   └─ Wake       (尾浪,粒子/贴花)
├─ AIS Targets    (其他船,简化模型)
├─ Land / Coastline(陆地,GeoJSON + extrude)
└─ Chart Layer    (电子海图叠加,可选)
```

### 5.2 各字段到 Three.js 的映射

| 数据 | 驱动对象 / 属性 | 备注 |
|---|---|---|
| 位置 (lat, lon) | `ship.position` | 见 4.1 转换 |
| Heading | `ship.rotation.y` | 见 4.2 |
| Roll / Pitch | `ship.rotation.x`, `.z` | 欧拉顺序 ZYX |
| Heave | `ship.position.y` | 直接加到 y 上 |
| COG vs Heading 偏差 | 视觉上可合并(船沿航迹走) | 真实中 COG 是航迹,Heading 是船头 |
| SOG / STW | `ship.position` 增量 | 见下面"位置推进" |
| ROT | `ship.rotation.y` 时间导数 | 也可以直接读数 |
| 舵角 | `rudder.rotation.y` | 视觉细节 |
| 主机 RPM | `propeller.rotation.z` | rpm × 6°/s |
| 真风 | 船旗/烟的方向 + 强度 | 视觉 |
| 涌浪 | 水面 shader 参数 | 浪高/浪向/周期 |
| 吃水 | 船体水下部分裁剪 / 调整船模基线 | 模型分层 |

### 5.3 位置推进方式(两种)

**(A)绝对定位**(默认):每帧用经纬度直接算 ENU。
- 优点:简单,数据缺失/跳变时容易容错
- 缺点:位置可能被插值漂移

**(B)航位推算 + GPS 校正**:用 SOG + Heading 积分推位置,GPS 修正。
- 优点:平滑,真实感强
- 缺点:长时间推算会漂,需要 GPS 校正

可视化场景里 **(A) + 短期插值** 就够。

### 5.4 横摇 / 纵摇的滤波

真实 IMU 噪声大(尤其小船),直接套用会看到模型高频抖。推荐:

```js
class OneEuroFilter {
  // 一阶欧拉滤波,适合实时低延迟去抖
  // 实现见 https://cristal.univ-lille.fr/~casiez/1euro/
}
const rollFilter  = new OneEuroFilter(minCutoff=1.0, beta=0.02);
const pitchFilter = new OneEuroFilter(minCutoff=1.0, beta=0.02);
```

### 5.5 海面与天空

| 视觉 | 数据 |
|---|---|
| 浪高(有效浪高) | 环境:涌浪场 |
| 浪向 | 环境 |
| 海面颜色 | 时间(昼夜)+ 天气 |
| 能见度/雾 | 天气 |
| 风向/风速 | 船旗 + 海面白帽 |
| 雨雪 | 天气 |

**实现**:
- 海面:`three/examples/jsm/objects/Ocean` (Three.js 自带) 或 `three.js/examples/jsm/objects/Water`
- 白帽:`Water` shader 已有,或自己写 normal map
- 太阳/月亮:`Sky` (Preetham model)

### 5.6 尾浪(Wake)与船首浪(Bow Wave)

- 用 `Wake`/`Wakes` 类库或自写 trail
- 根据 SOG/RPM 动态调整浪的强度
- 在船模本地空间下渲染,跟随船体

### 5.7 AIS 目标船显示

- 拉取所有目标船的 AIS
- 距离 > X km 的不进场景(LOD)
- 距离内用简化模型(船长按 AIS 数据放缩)
- 位置同样用经纬度 → ENU 转换
- 同步显示名称、目的地、SOG/COG、CPA/TCPA

---

## 6. 数据层 / 状态层 / 渲染层架构

### 6.1 推荐目录结构(Vue 2 项目适配)

```
src/
├─ data-sources/        # 协议层
│   ├─ NMEA0183Source.js
│   ├─ AISSource.js
│   ├─ SignalKSource.js
│   └─ RestSource.js
├─ parsers/
│   ├─ nmea0183.js
│   └─ signalk.js
├─ models/
│   ├─ ShipState.js        # 规范化状态,所有数据合并到这里
│   └─ AISTarget.js
├─ store/                 # Vuex / Pinia
│   └─ shipStore.js
├─ three/
│   ├─ ShipScene.js        # 场景初始化
│   ├─ Ocean.js
│   ├─ ShipModel.js        # GLTFLoader + 动画
│   ├─ AISTargets.js
│   └─ Wake.js
└─ App.vue
```

### 6.2 ShipState 状态模型(规范化)

```js
class ShipState {
  constructor() {
    // 静态
    this.imo = null;
    this.mmsi = null;
    this.length = 0; this.beam = 0; this.draft = 0;
    // 动态
    this.position = { lat: 0, lon: 0 };        // WGS-84
    this.sog = 0;                              // m/s
    this.stw = 0;                              // m/s
    this.cog = 0;                              // rad, 0 = 北
    this.heading = 0;                          // rad, 0 = 北
    this.rot = 0;                              // rad/s
    this.attitude = { roll: 0, pitch: 0, yaw: 0 }; // rad
    this.heave = 0;                            // m
    // 动力
    this.rpm = 0;
    this.rudderAngle = 0;                      // rad
    // 环境
    this.wind = { speedApparent: 0, angleApparent: 0,
                  speedTrue: 0,     angleTrue: 0 };
    this.depth = null;
    // 时间戳
    this.timestamp = 0;
  }
}
```

### 6.3 数据流(以 Signal K WebSocket 为例)

```
Signal K Server ──WS──► SignalKSource
                            │ 解析 delta
                            ▼
                          ShipState (规范化)
                            │ 推入 Vuex
                            ▼
                          shipStore
                            │ getter 暴露给渲染
                            ▼
   three/ShipModel.update(state)  (requestAnimationFrame 内调用)
                            │
                            ▼
                   THREE.Group rotation/position
```

### 6.4 关键代码:渲染更新循环

```js
import * as THREE from 'three';
import { OneEuroFilter } from 'one-euro-filter';

const REF_LAT = 31.234, REF_LON = 121.456;   // 初始化时锁定
const R = 6378137;
const toXY = (lat, lon) => ({
  x: (lon - REF_LON) * Math.cos(REF_LAT * Math.PI / 180) * R * Math.PI / 180,
  z: -(lat - REF_LAT) * R * Math.PI / 180
});

const rollFilter  = new OneEuroFilter(1.0, 0.02);
const pitchFilter = new OneEuroFilter(1.0, 0.02);
const headingFilter = new OneEuroFilter(0.5, 0.005);

function updateShip(ship, shipState, dt) {
  // 1. 位置
  const { x, z } = toXY(shipState.position.lat, shipState.position.lon);
  ship.position.x = x;
  ship.position.z = z;
  ship.position.y = shipState.heave || 0;

  // 2. 旋转
  const heading = headingFilter(shipState.heading, performance.now());
  const roll    = rollFilter(shipState.attitude.roll, performance.now());
  const pitch   = pitchFilter(shipState.attitude.pitch, performance.now());

  ship.rotation.order = 'ZYX';
  ship.rotation.set(pitch, heading, roll);
}
```

### 6.5 协议层示例:Signal K WebSocket

```js
class SignalKSource {
  constructor(url, onUpdate) {
    this.ws = new WebSocket(url);
    this.onUpdate = onUpdate;
    this.ws.onmessage = (e) => {
      const delta = JSON.parse(e.data);
      this._applyDelta(delta);
    };
  }
  _applyDelta(delta) {
    const patch = {};
    for (const u of delta.updates || []) {
      for (const v of u.values || []) {
        this._setPath(patch, v.path, v.value);
      }
    }
    this.onUpdate(patch);
  }
  _setPath(obj, path, value) {
    // navigation.position -> obj.position
    const map = {
      'navigation.position': 'position',
      'navigation.speedOverGround': 'sog',
      'navigation.speedThroughWater': 'stw',
      'navigation.courseOverGround': 'cog',
      'navigation.headingTrue': 'heading',
      'navigation.rateOfTurn': 'rot',
      'navigation.attitude': 'attitude',
      'environment.wind.speedApparent': 'wind.speedApparent',
      'environment.wind.angleApparent': 'wind.angleApparent',
      'environment.depth.belowTransducer': 'depth',
      'propulsion.*': 'propulsion',
      'steering.rudderAngle': 'rudderAngle'
    };
    const key = map[path] || (path.startsWith('propulsion.') ? 'propulsion' : null);
    if (key) obj[key] = value;
  }
}
```

### 6.6 数据时间同步与乱序

真实数据可能乱序到达(WebSocket 推送、网络抖动)。建议:

- 每条数据带 `timestamp`(UTC 毫秒)
- 在状态层用**最新时间戳获胜**(newer-wins)
- 渲染层使用 `(now - renderDelay)` 历史数据,**renderDelay = 100–300 ms**,这样即使有抖动也看不到跳变

```js
class ShipState {
  patch(partial, timestamp) {
    if (timestamp < this.timestamp) return;   // 旧数据丢弃
    Object.assign(this, partial);
    this.timestamp = timestamp;
  }
}
```

---

## 7. 完整接入清单(Checklist)

按这个清单逐项打勾,接完即用:

### 必备
- [ ] 选定数据源(自家 API / Signal K / NMEA 直连 / AIS)
- [ ] 实现/对接 `ShipState` 数据模型
- [ ] 经纬度 → ENU 转换函数
- [ ] Heading/Roll/Pitch → Three.js 旋转(含 order='ZYX')
- [ ] 节 → m/s 转换
- [ ] 短期数据缓冲 + 插值(避免跳变)

### 推荐
- [ ] Roll/Pitch 低通滤波(One Euro)
- [ ] Heave 叠加到 ship.position.y
- [ ] 海面 shader 参数由真实浪高/浪向驱动
- [ ] 舵角联动舵模型旋转
- [ ] RPM 联动螺旋桨旋转
- [ ] AIS 目标船显示层

### 可选
- [ ] 历史回放(Signal K `/history/...` 或自家 API)
- [ ] 多船队管理(多船切换)
- [ ] 电子海图叠加(GeoJSON/ENC)
- [ ] 报警层(火灾/进水/碰撞高亮)
- [ ] 操船控制回写(从 3D 操作船舶,把车钟/舵角写回真实)

---

## 8. 参考资源

### 协议与规范
- **NMEA 0183 标准** - https://www.nmea.org/
- **NMEA 2000 / J1939 PGN 列表** - https://www.nmea.org/Assets/20190613%20amendment%20engine%20add%20-%20public%20review%20copy.pdf
- **ITU-R M.1371 AIS** - AIS 技术规范
- **Signal K 规范** - https://signalk.org/specification/

### 前端解析库
- `nmea-simple` - NMEA 0183 解析
- `@signalk/nmea0183` - Signal K 团队 NMEA 0183 解析
- `canboatjs` - NMEA 2000 解析
- `ais-format` / `ais-decode` - AIS 解码

### Three.js 资源
- `three/examples/jsm/objects/Ocean` - 海面
- `three/examples/jsm/objects/Water` - 另一种水面
- `three/examples/jsm/objects/Sky` - 天空
- `three/examples/jsm/loaders/GLTFLoader` - 船体模型
- `three/examples/jsm/controls/OrbitControls` - 视角

### 滤波
- `one-euro-filter` - 横摇/纵摇去抖
- Signal K 自带 history service - 数据回放

---

## 9. 常见问题

**Q1:模型默认朝向不一致,heading 怎么都对不上?**
A:在 GLTFLoader 加载完后,先确定模型的"船头方向"。一般做法是在 Blender 里把船头对齐到模型的 +X 轴(或 -Z 轴),然后用 `rotation.y = -headingRad` 或 `(90 - headingDeg) * π / 180`,二选一固定下来,后面不要改。

**Q2:经纬度坐标太大,场景抖?**
A:一定用局部 ENU,不要把整个地球坐标塞进 Three.js。一旦相对参考点的偏移超过 ~50 km,重置参考点,避免浮点精度损失。

**Q3:数据有跳变 / 缺失?**
A:数据层做时间戳过滤(`timestamp < this.timestamp` 丢弃);渲染层加 `renderDelay` 历史插值;信号丢失时降级为根据最后 SOG/Heading 推算。

**Q4:横摇很抖,看起来像癫痫?**
A:用 One Euro Filter 或卡尔曼滤波,调 `minCutoff`(越小越平滑)和 `beta`(越大越跟手)。小船浪大可调到 `minCutoff=0.5, beta=0.01`。

**Q5:多艘船怎么同步?**
A:每艘船一个 `ShipState` 实例 + 一个 `ShipModel` 实例,数据层独立。共享 `Ocean` 和 `Sky`,不复制。

**Q6:海面 shader 需要哪些数据?**
A:`Ocean` 主要用 `windSpeed`(m/s)、`windDirection`(rad)。如有涌浪场(浪高/浪向/浪周期),可叠加多组 Gerstner 波浪。

**Q7:历史回放怎么做?**
A:Signal K 提供 `/signalk/v1/api/vessels/<urn>/history/...` 端点,按时间窗口查。请求格式见 Signal K 文档。

---

> 文档结束。版本 v1.0,2026-08-24。
