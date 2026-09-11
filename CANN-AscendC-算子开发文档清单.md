# 华为昇腾 CANN Ascend C 算子开发文档清单

- **目标**：自研算子 / 定制 kernel
- **CANN 版本**：8.x 为主（涵盖 8.0.0 商用 / 8.0.0 社区 alpha / 8.0.RC 系列 / 8.2.RC1 / 8.3.RCX / 8.5.0）
- **生成日期**：2026-09-03
- **来源策略**：官方为主（昇腾社区 docs.hiascend.com、华为企业支持 support.huawei.com），社区/第三方为辅（已注明）

---

## 1. Ascend C 算子开发总览入口（编程模型 / 核函数 / Tiling / 调试 / 调优）

### 官方 — 昇腾社区 docs.hiascend.com

- **Ascend C 算子开发指南（应用软件开发用户指南）— CANN 8.0.RC3 商用版**  
  自研算子的根文档，覆盖编程模型、SP / 算子开发流程、核函数实现、Tiling 设计与性能调优。  
  🔗 https://www.hiascend.com/document/detail/zh/canncommercial/80RC3/developmentguide/opdevg/Ascendcopdevg/atlas_ascendc_10_0006.html

- **创建算子工程 — CANN 8.0.0.alpha003 社区版**  
  同一系列文档在社区版的入口。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/800alpha003/devguide/opdevg/ascendcopdevg/atlas_ascendc_10_0060.html

- **算子基本概念 — CANN 8.5.0.alpha001**  
  Tiling、TilingData、TilingKey、UB、PPosition 等术语解释，入门前必读。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/850alpha001/opdevg/Ascendcopdevg/atlas_ascendc_10_0098.html

### 官方 — 华为企业支持 support.huawei.com

- **Ascend C 算子编程总览**  
  🔗 https://support.huawei.com/enterprise/zh/doc/EDOC1100314802

**适用场景**：第一次接触 Ascend C 自研算子，先读"基本概念"和"开发指南"前两章，建立 Tiling / 核函数 / 流水 / 双缓冲的认知框架。

---

## 2. Ascend C API 参考（算子类 / 向量 / 标量 / TilingData）

### 官方 — 昇腾社区 docs.hiascend.com

- **Ascend C API 列表 — CANN 8.0.0.alpha003 社区版**  
  按类组织的主入口（Kernel / 算子原型 / TilingData / 平台信息 / 调测）。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/800alpha003/apiref/ascendcopapi/atlasascendc_api_07_937.html

- **Ascend C API 列表 — CANN 8.0.0 商用版（英文）**  
  商用版对应英文入口，便于跨版本检索。  
  🔗 https://www.hiascend.com/document/detail/en/canncommercial/800/apiref/ascendcopapi/atlasascendc_api_07_0256.html

- **Ascend C API 列表 — CANN 8.3.RCX**  
  较新版本参考。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/83RC1/API/ascendcopapi/atlasascendc_api_07_81.html

- **基础数据结构和接口列表 — CANN 8.0.0.alpha002**  
  StorageFormat / StorageShape / Tensor / TilingContext / TilingData / TypedContinuousVector 等。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/800alpha002/apiref/basicdataapi/atlasopapi_07_8.html

- **限制 TilingData 结构大小（最佳实践）— CANN 8.0.0 商用版**  
  TilingData 排布正反例；`BEGIN_TILING_DATA_DEF / TILING_DATA_FIELD_DEF / END_TILING_DATA_DEF` 宏规范。  
  🔗 https://www.hiascend.com/document/detail/zh/canncommercial/800/developmentguide/opdevg/ascendcbestP/atlas_ascendc_best_practices_10_0018.html

### 关键 API 族群速览

- **算子原型 / 注册**：`OpDef / OpParamDef / OpAttrDef / OpAICoreDef / OpAICoreConfig / OpMC2Def`
- **Tiling 数据结构**：`TilingDef / TilingData`（通过宏定义并注册到自定义算子）
- **平台信息**：`PlatformAscendC / PlatformAscendCManager`
- **调测**：`GmAlloc / ICPU_RUN_KF / ICPU_SET_TILING_KEY / SetKernelMode`
- **Kernel 基础 API（标量）**：`ScalarCast / ScalarCountLeadingZero / ScalarGetCountOfValue / CountBitsCntSameAsSignBit / ScalarGetSFFValue / ToBfloat16 / ToFloat`
- **Kernel 基础 API（向量）**：
  - 一元：`Exp / Ln / Abs / Reciprocal / Sqrt / Rsqrt / Not / Relu`
  - 二元：`Add / Sub / Mul / Div / Max / Min / And / Or`
  - 融合：`AddRelu / AddReluCast / AddDeqRelu / SubRelu / MulAddDst / MulCast / FusedMulAdd / FusedMulAddRelu`
  - 二元-标量：`Adds / Muls`

**适用场景**：写算子时按类查具体函数签名、参数约束、对齐方式；TilingData 设计阶段先看"限制大小"。

---

## 3. 工程样例仓库（MatMul / Softmax / LayerNorm 等）

### 官方开源仓库 — Ascend samples

- **路径**：`samples/cplusplus/level1_single_api/4_op_dev/1_custom_op/`
- **包含算子**：Add / Conv2d / LeakyRelu / Matmul / Permute / ScatterNdAdd / Upsample 等，每个算子对应 `doc/<Op>_CN.md` + `framework / op_host / op_kernel` 三层工程。
- **仓库入口**：在 Gitee / GitHub 搜 `Ascend samples`（昇腾社区官方），主页 https://gitee.com/ascend/samples
- **文档入口（8.x）**：
  - CANN 8.0.RC1 商用版 — 自定义算子开发样例总览  
    🔗 https://www.hiascend.com/document/detail/zh/canncommercial/80RC1/developmentguide/opdevg/tbeaicpudevg/atlasopdev_10_0153.html
  - CANN 8.5.0.alpha001 社区版 — 自定义算子开发样例  
    🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/850alpha001/opdevg/tbeaicpudevg/atlasopdev_10_0121.html

### 社区（强烈推荐） — AscendC Templates

- **仓库**：https://gitee.com/cold_brew/ascendc-templates
- **来源**：华南理工陆璐教授团队 + 社区维护，分层模板 + 高性能实现样例（典型是 matmul 各种 tile 切法）。
- **目录结构**：`docs / examples / include / scripts`，`examples/00_basic_matmul` 是入门。
- **运行示例**：
  ```bash
  source /usr/local/Ascend/ascend-toolkit/set_env.sh
  bash scripts/build.sh 00_basic_matmul
  cd build/bin
  ./00_basic_matmul 256 512 1024 0
  ```
- **支持**：Atlas 800T A2 / Atlas 200T A2 Box16，CANN 8.0.0.beta1+。
- **Softmax / LayerNorm**：官方 samples 的 level1 路径不一定直接覆盖，需要在仓库里直接搜 `softmax` / `layer_norm`；社区仓里持续在补充新算子模板。

**适用场景**：拿到 Ascend C 工程结构后，挑一个跟目标算子最像的样例改，比从零写快得多。AscendC Templates 适合想做"超过 baseline 性能"的优化版本。

---

## 4. 算子工程编译与注册（msopgen / aclop / ACLLib）

### 官方 — msopgen 自定义算子工程生成

- **工具概述（msOpGen）— CANN 8.0.0.alpha003**  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/800alpha003/devaids/opdev/optool/atlasopdev_16_0029.html

- **简易算子工程（`-f aclnn`，仅 Atlas A2 / 800I A2）— CANN 8.0.0.alpha002**  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/800alpha002/devaids/opdev/optool/atlasopdev_16_0028.html

- **Ascend C 自定义算子开发实践 — CANN 8.5.0 商用版**  
  🔗 https://www.hiascend.com/document/detail/zh/canncommercial/850/devaids/optool/atlasopdev_16_0027.html

- **基于自定义算子工程的算子开发 — CANN 8.0.RC3 商用版**  
  🔗 https://www.hiascend.com/document/detail/zh/canncommercial/80RC3/developmentguide/opdevg/Ascendcopdevg/atlas_ascendc_10_0006.html

- **基于 Kernel 直调工程的算子开发 — CANN 8.0.RC2.alpha002**  
  跳过 op_host 插件层，只跑 kernel（适合极致性能调优场景）。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/80RC2alpha002/devguide/opdevg/ascendcopdevg/atlas_ascendc_10_0005.html

- **Using the msopgen Tool — CANN 8.5.0 商用英文**  
  🔗 https://www.hiascend.com/document/detail/en/canncommercial/850/opdevg/tbeaicpudevg/atlasopdev_10_0022.html

### 官方 — aclop 系列 API（运行时动态注册 / 调用）

- **Operator Execution / aclopRegisterCompileFunc** — 华为企业支持  
  适用于动态 shape 或非内置算子。  
  🔗 https://support.huawei.com/enterprise/en/doc/EDOC1100180746/392ad20/aclopRegisterCompileFunc.htm

### 官方 — MindSpore 集成

- **AOT-Type Custom Operators (Ascend)**  
  MindSpore ≥2.3.0 封装的 `custom_compiler`，可避免手动跑 msopgen。  
  🔗 https://mindspore.cn/docs/en/r2.4.1/model_train/custom_program/operation/op_custom_ascendc.html

### 典型流程

```bash
# 1. 用算子原型 JSON 生成工程
msopgen gen \
    -i $HOME/sample/add_custom.json \
    -c ai_core-Ascend<xxxyy> \
    -lan cpp \
    -out $HOME/sample/AddCustom

# 2. 改 op_host/* 与 op_kernel/*

# 3. 编译
cd AddCustom && ./build.sh

# 4. 部署到 CANN
./build_out/custom_opp_<target>_<version>.run [--install-path="..."]

# 5. 生成并运行 ST 测试
msopst create -i "xxx/AddCustom/op_host/add_custom.cpp" -out ./st
```

**适用场景**：第一次走自定义算子全流程，跟着 msopgen 生成的目录结构改最稳；要嵌入 PyTorch / MindSpore 框架就再叠 aclop 或 custom_compiler 那一层。

---

## 5. CANN 8.x 与 7.x 在 Ascend C 上的差异

⚠️ 没找到华为官方"Changelog / Release Notes"专题页（直接搜 `CANN 8.0 vs 7.x 差异` 0 命中）。以下是基于交叉对比 URL 层级和文档结构的间接推断，建议在 CANN 8.0.0 商用版文档里以"新增内容 / 修订记录"关键字再扫一遍确认：

- **算子开发主路径**：7.x 时期 TBE + Ascend C 并行，Ascend C 已经可用；8.x 主推 Ascend C，新文档更系统化（出现"最佳实践"独立章节、"限制 TilingData 结构大小"等专题）。
- **新硬件亲和**：8.x 主线文档显式区分 Atlas A2 训练系列 / Atlas 800I A2 推理产品；新增简易算子工程（`-f aclnn`）仅在 A2 系列支持。
- **工具链**：msopgen 从 7.x 的"工程模板生成器"演化为 8.x 的多模式（标准工程 / 简易算子工程 / Kernel 直调工程），对应不同芯片自动选择。
- **性能工具**：msProf 在 8.x 引入 `msprof op` 子命令（更专注于算子级 profiling）、`msprof op simulator` 仿真器模式，以及 MindStudio Insight 可视化（8.3.RC 引入）。

---

## 6. 性能调优 / Profiling

### 官方 — msProf 命令行工具

- **简介 / 采集方式对比 — CANN 8.0.0 商用版**  
  msprof CLI vs PyTorch / TensorFlow / AscendCL / Ascend Graph / acl.json / 环境变量六种采集方式对比。  
  🔗 https://www.hiascend.com/document/detail/zh/canncommercial/800/devaids/devtools/profiling/atlasprofiling_16_60.html

- **使用前准备 — CANN 8.0.RC3.alpha003**  
  内存 ≥20G、仿真器路径、blockdim 限制、pem_config_cloud.toml 的 core_ostd_num 等。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/80RC3alpha003/devaids/auxiliarydevtool/atlasopdev_16_0083.html

- **采集 Ascend C 算子性能数据 — 典型案例 — CANN 8.0.RC3 商用��**  
  上板调优、仿真器调优、PyTorch / aclnn 三种调用场景。  
  🔗 https://www.hiascend.com/document/detail/zh/canncommercial/80RC3/devaids/opdev/optool/atlasopdev_16_0116.html

### 官方 — 算子调优最佳实践

- **算子调测总览 — CANN 8.0.RC2.alpha002**  
  上板 vs 仿真两条路。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/80RC2alpha002/devguide/opdevg/ascendcbestP/atlas_ascendc_best_practices_10_0006.html

- **获取性能数据 — CANN 8.0.RC3.alpha003**  
  含"搬运理论耗时"算例（GM 带宽 1.8 TB/s 下的 4096×4096 矩阵示例）。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/80RC3alpha003/devguide/opdevg/ascendcbestP/atlas_ascendc_best_practices_10_0007.html

- **分析性能数据 — CANN 8.0.RC2 商用版**  
  `op_summary_*.csv` 字段含义、瓶颈定位方法。  
  🔗 https://www.hiascend.com/document/detail/zh/canncommercial/80RC2/developmentguide/opdevg/ascendcbestP/atlas_ascendc_best_practices_10_0009.html

- **优化建议总览表 — CANN 8.3.RC1**  
  新增 MindStudio Insight 可视化。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/83RC1/opdevg/ascendcbestP/atlas_ascendc_best_practices_10_00010.html

- **未采集到 AI Core Metrics 数据 — CANN 8.0.RC2.alpha002（排查手册）**  
  多算子未融合 + 自动调优（AOE）的解决方案。  
  🔗 https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/80RC2alpha002/devaids/auxiliarydevtool/atlasprofiling_16_0124.html

### 典型命令速记

```bash
# 上板
msprof op --output=$HOME/projects/output $HOME/projects/MyApp/out/main

# 仿真器
msprof op simulator --soc-version=Ascendxxxyy ascendc_kernels_bbit

# 通用 + AI Core 指标
msprof --application=./add_custom_npu --output=./out \
       --ai-core=on --aic-metrics="PipeUtilization"
```

**适用场景**：算子跑通后用 `msprof op` 抓 AI Core 流水 → 读 `op_summary_*.csv` 定位瓶颈（搬运 / 计算 / 同步等待）→ 对照最佳实践里的优化建议表改。

---

## 推荐阅读顺序（自研算子场景）

1. **算子基本概念**（CANN 8.5.0 那篇术语表）— 建立术语框架。
2. **Ascend C 算子开发指南**（CANN 8.0.RC3 商用版）— 按章节读。
3. **AscendC Templates** 仓库里挑一个最像目标算子的样例 — 先模仿再改造。
4. **msopgen 工具概述 + 创建算子工程** — 用工具生成自己的工程。
5. **Ascend C API 列表** — 当字典查。
6. **限制 TilingData 结构大小** + **最佳实践 / 优化建议表** — 做性能调优。
7. **msProf 算子调优** — 抓流水、定位瓶颈。

---

## 来源一览

- 昇腾社区（CANN 8.0.0.alpha003 社区版入口）：https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/800alpha003/devguide/opdevg/ascendcopdevg/atlas_ascendc_10_0060.html
- 昇腾社区（Ascend C 算子开发指南 — CANN 8.0.RC3 商用）：https://www.hiascend.com/document/detail/zh/canncommercial/80RC3/developmentguide/opdevg/Ascendcopdevg/atlas_ascendc_10_0006.html
- 昇腾社区（Ascend C API 列表 — CANN 8.0.0.alpha003）：https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/800alpha003/apiref/ascendcopapi/atlasascendc_api_07_937.html
- 昇腾社区（限制 TilingData 结构大小 — CANN 8.0.0 商用）：https://www.hiascend.com/document/detail/zh/canncommercial/800/developmentguide/opdevg/ascendcbestP/atlas_ascendc_best_practices_10_0018.html
- 昇腾社区（msProf 简介 — CANN 8.0.0 商用）：https://www.hiascend.com/document/detail/zh/canncommercial/800/devaids/devtools/profiling/atlasprofiling_16_60.html
- 昇腾社区（采集 Ascend C 算子性能数据 — CANN 8.0.RC3 商用）：https://www.hiascend.com/document/detail/zh/canncommercial/80RC3/devaids/opdev/optool/atlasopdev_16_0116.html
- 昇腾社区（优化建议总览表 — CANN 8.3.RC1）：https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/83RC1/opdevg/ascendcbestP/atlas_ascendc_best_practices_10_00010.html
- 华为企业支持（Ascend C 算子编程）：https://support.huawei.com/enterprise/zh/doc/EDOC1100314802
- 华为企业支持（Operator Execution / aclopRegisterCompileFunc）：https://support.huawei.com/enterprise/en/doc/EDOC1100180746/392ad20/aclopRegisterCompileFunc.htm
- AscendC Templates（华南理工陆璐教授团队）：https://gitee.com/cold_brew/ascendc-templates
- MindSpore（AOT-Type Custom Operators Ascend）：https://mindspore.cn/docs/en/r2.4.1/model_train/custom_program/operation/op_custom_ascendc.html