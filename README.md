HFSS Automated Simulation Framework (v0.1)
1. 项目简介
适用于天线参数化扫描、代理模型（Surrogate Model）训练数据集生成以及结合启发式算法的全局优化任务。

3. 目录结构
Plaintext
HFSS-Auto-Driver/
├── config.yaml          # 全局配置文件（工程路径、版本、变量声明）
├── input_data.csv       # 输入数据矩阵（待仿真的参数组合）
├── hfss_driver.py       # 核心驱动模块（基于 PyAEDT 的底层封装）
├── main_loop.py         # 主控程序（执行批量调度与数据持久化）
├── requirements.txt     # Python 环境依赖清单
└── README.md            # 项目说明文档

4. 环境配置
本项目需在已安装 Ansys Electronics Desktop (AEDT) 的本地或工作站环境中运行。

测试环境：Ansys HFSS 2023 R1, Python 3.10.
配置环境在python3.10 pip install -r requirements.txt

5. 使用说明
5.1 模型准备
确保待仿真的 HFSS 模型文件（.aedt）已配置好参数化变量（Project Variable 或 Design Variable），并设置了可用的求解设置（Setup）与扫频项（Sweep）。运行脚本前需确保关闭该模型的 GUI 界面。

5.2 参数配置 (config.yaml)
编辑配置文件，设置正确的绝对路径、HFSS 版本号、扫频点数以及需要修改的变量名称列表：

project_path: "E:/Hfss_prj/test/test1/antenna1.aedt"
hfss_version: "2023.1"
num_freq_points: 151
variable_names:
  - ld
  - wd

5.3 数据准备 (input_data.csv)
根据 config.yaml 中的变量顺序，在 CSV 文件中输入样本矩阵（第一行为表头）：

ld,wd
6.0,1.0
6.2,1.1

5.4 运行仿真
在终端执行主控脚本：

python main_loop.py

6. 常见错误排查 (Troubleshooting)
错误提示: Project is locked. Close or remove the lock before proceeding.

原因: 当前 .aedt 文件正被其他 HFSS 进程占用。

解决方案: 确保前台未打开该模型；在任务管理器中结束残留的 ansysedt.exe 进程；手动删除同目录下的 .lock 隐藏文件。

输出结果异常: 生成的数据行为全零数组。

原因: 输入尺寸导致几何模型干涉（如部件重叠），或网格剖分失败，触发了容错机制的预设惩罚值。

解决方案: 检查输入样本的数据边界，确保其在合理的物理意义域内。