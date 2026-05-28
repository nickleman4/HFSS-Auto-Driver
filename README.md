# HFSS-Auto V1.0

HFSS-Auto 用于批量修改 HFSS 结构参数、自动求解，并导出可用于神经网络训练的远场 `rE` 数据集。

V1.0 的默认输出不再是单条 S11 扫频曲线，而是长表格式的远场数据：

```text
sample_id,ld,wd,freq,theta,phi,rEPhi_re,rEPhi_im,rETheta_re,rETheta_im,status,error_message
```

每一行对应一个结构样本在某个 `freq + theta + phi` 采样点上的远场复数分量。
当 `outputs.s11.enabled: true` 时，程序会额外生成独立的 `result_s11.csv`：

```text
sample_id,ld,wd,freq,s11_db,status,error_message
```

## 目录结构

```text
config.yaml              # 运行配置
input_data.csv           # 结构参数输入
result_farfield.csv      # V1.0 默认远场输出
result_s11.csv           # 可选 S11 输出
run_metadata.yaml        # 本次运行配置快照
src/main_driver.py       # 批处理主入口
src/hfss_driver.py       # HFSS/PyAEDT 封装
src/config_loader.py     # 配置解析与列生成
src/result_writer.py     # CSV/metadata 增量写入
tests/                   # 离线单元测试
```

## 环境

需要在已安装 Ansys Electronics Desktop 的机器上运行真实仿真。

已知目标环境：

```text
Ansys HFSS 2023 R1
Python 3.10
pyaedt==0.6.73
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 配置

`config.yaml` 示例：

```yaml
project_path: "E:/Hfss_prj/test/test1/antenna1.aedt"
hfss_version: "2023.1"
design_name: "Opti_Result1"

simulation:
  setup_name: "Setup1"
  sweep_name: "Sweep"
  variable_unit: "mm"

variable_names:
  - ld
  - wd

outputs:
  s11:
    enabled: true

  farfield:
    enabled: true
    convert_to_si: true
    sphere_name: "3D"
    frequencies:
      - "3GHz"
    theta:
      start: 0
      stop: 180
      step: 5
    phi:
      start: 0
      stop: 360
      step: 5
    components:
      - rEPhi
      - rETheta
    parts:
      - real
      - imag

output:
  root_dir: "result"
  run_dir_prefix: "run"
  result_csv: "result_farfield.csv"
  s11_csv: "result_s11.csv"
  metadata_yaml: "run_metadata.yaml"
  write_mode: "append"
```

注意：

- `variable_names` 必须与 HFSS 工程变量名一致。
- `design_name` 必须与工程树中的 Design 名称一致，例如 `Opti_Result1`。
- `input_data.csv` 的表头顺序应与 `variable_names` 一致。
- `sphere_name` 必须与 HFSS 工程中的 Infinite Sphere / Far Field Setup 名称一致。
- `frequencies` 使用显式频点，例如 `"3GHz"`。
- `convert_to_si: true` 会让远场 rE 调用 `data_real(convert_to_SI=True)` 和 `data_imag(convert_to_SI=True)`，用于测试是否能与 HFSS GUI 表格显示单位对齐。

## 输入数据

`input_data.csv` 示例：

```csv
ld,wd
6.0,1.0
6.2,1.1
```

## 运行

```bash
python src/main_driver.py
```

程序会：

1. 读取 `config.yaml` 和 `input_data.csv`。
2. 启动 HFSS。
3. 对每个结构样本修改变量并求解指定 setup。
4. 按配置频点和 theta/phi 网格提取 `rEPhi`、`rETheta` 的实部/虚部。
5. 每次运行自动创建 `result/run_YYYYMMDD_HHMMSS/`。
6. 如果启用 S11，按同一频点提取 `s11_db` 并写入独立的 `result_s11.csv`。
7. 每个样本完成后立即追加写入本次运行目录下的 `result_farfield.csv`。
8. 复制本次 `config.yaml`、`input_data.csv`，并写入 `run_metadata.yaml` 作为配置快照。

## 失败样本

如果某个样本求解或提取失败，程序仍会写入一行失败记录：

```text
sample_id,结构参数,status=failed,error_message
```

远场数值列填充为 `nan`，不再使用全零惩罚值，避免污染训练数据。

## 验证

离线单元测试不需要启动 HFSS：

```bash
pytest -q
```

真实 HFSS 集成验证建议先使用小网格：

```yaml
frequencies:
  - "3GHz"
theta:
  start: 0
  stop: 180
  step: 90
phi:
  start: 0
  stop: 90
  step: 90
```

期望输出行数：

```text
样本数 × 频点数 × theta点数 × phi点数
```

然后抽查 HFSS GUI 报告中的远场数值是否与 CSV 一致。
