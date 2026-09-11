# YOLO11 在 Mac M1 上的练手指南

适用场景：Apple Silicon (M1/M2/M3/M4) Mac，用 venv 隔离环境，跑通 YOLO11 训练全流程。

## 一、环境准备

### 1.1 创建虚拟环境

在项目目录下执行：

```bash
python3 -m venv yolo_env
```

### 1.2 激活环境

```bash
source yolo_env/bin/activate
```

激活成功后，命令行前面会出现 `(yolo_env)` 提示符。所有后续安装和训练命令都在这个环境里执行。

退出环境：

```bash
deactivate
```

### 1.3 安装依赖包

```bash
pip install --upgrade pip
pip install torch torchvision ultralytics
```

### 1.4 验证 MPS（GPU 加速）

```bash
python3 -c "import torch; print(torch.backends.mps.is_available())"
```

输出 `True` 即可用 GPU 训练。如果输出 `False`，说明 PyTorch 没识别到 MPS，需要重装 PyTorch。

## 二、数据集准备

### 2.1 数据结构

YOLO 格式标准目录结构：

```
dataset/
├── images/
│   ├── train/        # 训练集图片
│   └── val/          # 验证集图片
├── labels/
│   ├── train/        # 训练集标注（每张图对应一个同名 .txt）
│   └── val/          # 验证集标注
└── data.yaml         # 数据集配置文件
```

### 2.2 data.yaml 示例

```yaml
path: /绝对路径/dataset
train: images/train
val: images/val

nc: 2                     # 类别数量
names: ['cat', 'dog']     # 类别名称，顺序要和标注文件里的 class id 对应
```

### 2.3 标注文件格式

每张图对应一个同名 `.txt` 文件，每行一个目标：

```
<class_id> <x_center> <y_center> <width> <height>
```

坐标都是**归一化的**（0~1 之间）。例：

```
0 0.5 0.5 0.3 0.4
1 0.7 0.3 0.2 0.2
```

### 2.4 获取练手数据集（不用自己标）

- **Roboflow Universe**：https://universe.roboflow.com ，搜 yolo，下载 YOLO 格式 zip
- **Ultralytics 官方示例**：内置扑克牌、交通标志等小数据集

## 三、训练

### 3.1 最小训练脚本

新建 `train.py`：

```python
from ultralytics import YOLO

# 加载预训练权重（首次运行会自动下载）
model = YOLO('yolo11n.pt')

results = model.train(
    data='path/to/data.yaml',   # 换成你的 data.yaml 绝对路径
    epochs=50,                   # 练手 50 轮够了
    imgsz=640,                   # 输入尺寸
    batch=8,                     # M1 8GB 内存用 8，16GB 用 16
    device='mps',                # 关键：用 MPS 加速
    project='runs',
    name='exp'
)
```

### 3.2 命令行方式

不用写脚本也可以：

```bash
yolo detect train data=data.yaml model=yolo11n.pt epochs=50 imgsz=640 batch=8 device=mps
```

### 3.3 M1 推荐配置

| 内存   | batch | 可用模型        |
| ---- | ----- | ----------- |
| 8GB  | 4-8   | yolo11n/s   |
| 16GB | 8-16  | yolo11n/s/m |
| 32GB | 16-32 | yolo11n~l   |

## 四、训练结果

训练完成后，在 `runs/exp/` 下会生成：

- `weights/best.pt`：验证集上表现最好的权重
- `weights/last.pt`：最后一轮的权重
- `results.png`：训练曲线（loss、mAP 等）
- `confusion_matrix.png`：混淆矩阵
- `labels.jpg`：数据集标签分布

## 五、测试与推理

### 5.1 单张图片测试

新建 `predict.py`：

```python
from ultralytics import YOLO

model = YOLO('runs/exp/weights/best.pt')
results = model.predict('test.jpg', save=True, conf=0.5)
```

结果会保存在 `runs/exp/predict/`。

### 5.2 批量测试整个文件夹

```python
results = model.predict('images_folder/', save=True)
```

### 5.3 验证集评估

```bash
yolo detect val model=runs/exp/weights/best.pt data=data.yaml device=mps
```

会输出 mAP50、mAP50-95、precision、recall 等指标。

## 六、模型导出

### 6.1 导出为 ONNX（通用）

```python
model = YOLO('runs/exp/weights/best.pt')
model.export(format='onnx')
```

### 6.2 导出为 CoreML（部署到 Mac/iPhone）

```python
model.export(format='coreml')
```

生成 `.mlpackage`，可在 macOS/iOS 用 Neural Engine 推理。

## 七、常见问题

### 7.1 pip 安装报错 externally-managed-environment

说明用了 Homebrew 管理的 Python，必须用 venv 或加 `--break-system-packages`。venv 是首选。

### 7.2 mps 不可用

```bash
python3 -c "import torch; print(torch.__version__)"
```

确保 PyTorch 版本 >= 2.0。如果还不行，重装：

```bash
pip install --upgrade torch torchvision
```

### 7.3 训练时报 OOM（内存不足）

把 `batch` 调小（4 或 2），或者把 `imgsz` 降到 320。

### 7.4 MPS 部分算子不支持

设置环境变量自动回退到 CPU：

```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

### 7.5 训练很慢

- 确认是否真的用了 MPS（看日志里有没有 `Apple MPS`）
- 把 `workers` 设为 0 或 2（MPS 多进程有时出问题）
- 模型换更小的（yolo11n）

## 八、快速启动清单

每次新终端要训练时：

```bash
cd /path/to/your/project
source yolo_env/bin/activate          # 激活环境
python3 -c "import torch; print(torch.backends.mps.is_available())"   # 可选，验证 MPS
python3 train.py                       # 跑训练
```

练完想关掉：

```bash
deactivate                            # 退出虚拟环境
```