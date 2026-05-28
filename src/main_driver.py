import csv
import os
import shutil
from pathlib import Path
from datetime import datetime

import yaml

try:
    from .config_loader import build_result_columns, build_s11_columns, load_runtime_config
    from .hfss_driver import close_hfss, init_hfss, run_farfield_simulation
    from .result_writer import ResultWriter
except ImportError:
    from config_loader import build_result_columns, build_s11_columns, load_runtime_config
    from hfss_driver import close_hfss, init_hfss, run_farfield_simulation
    from result_writer import ResultWriter


def run_batch(config_path="config.yaml", input_csv="input_data.csv"):
    print("===================================")
    print("   HFSS 自动化远场数据集生成程序 V1.0")
    print("===================================")

    config_path = Path(config_path)
    input_csv = Path(input_csv)
    if not config_path.exists():
        print(f"❌ 找不到配置文件: {config_path}")
        return 1
    if not input_csv.exists():
        print(f"❌ 找不到输入数据文件: {input_csv}")
        return 1

    with config_path.open("r", encoding="utf-8") as f:
        config = load_runtime_config(yaml.safe_load(f))

    project_path = config["project_path"]
    if not os.path.exists(project_path):
        print(f"🤷‍♂️ 找不到指定的 aedt 文件，请检查路径: {project_path}")
        return 1

    var_names = config["variable_names"]
    samples = read_input_samples(input_csv, var_names)
    print(f"✅ 成功加载 {len(samples)} 组待仿真尺寸。")

    run_dir = create_run_directory(config["output"])
    snapshot_run_inputs(config_path, input_csv, run_dir)

    columns = build_result_columns(config)
    writer = ResultWriter(
        result_csv=run_dir / config["output"]["result_csv"],
        metadata_yaml=run_dir / config["output"]["metadata_yaml"],
        columns=columns,
        write_mode=config["output"].get("write_mode", "append"),
    )
    metadata = dict(config)
    metadata["run_dir"] = str(run_dir)
    writer.write_metadata(metadata)

    s11_writer = None
    if config["outputs"].get("s11", {}).get("enabled"):
        s11_writer = ResultWriter(
            result_csv=run_dir / config["output"]["s11_csv"],
            metadata_yaml=run_dir / config["output"]["metadata_yaml"],
            columns=build_s11_columns(config),
            write_mode=config["output"].get("write_mode", "append"),
        )

    try:
        init_hfss(project_path, design_name=config["design_name"], version=config["hfss_version"])
        for sample_id, x in enumerate(samples, start=1):
            print(f"\n---> 正在计算第 {sample_id}/{len(samples)} 组，输入尺寸: {x}")
            simulation_result = run_farfield_simulation(
                x=x,
                var_names=var_names,
                simulation_config=config["simulation"],
                farfield_config=config["outputs"]["farfield"],
                s11_config=config["outputs"].get("s11"),
            )
            writer.write_rows(build_sample_rows(sample_id, var_names, x, simulation_result))
            if s11_writer:
                s11_writer.write_rows(build_s11_sample_rows(sample_id, var_names, x, simulation_result))
    finally:
        close_hfss()

    print(f"\n🎉 全部仿真完成！结果已导出至: {os.path.abspath(run_dir / config['output']['result_csv'])}")
    return 0


def create_run_directory(output_config):
    root_dir = Path(output_config["root_dir"])
    prefix = output_config.get("run_dir_prefix", "run")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root_dir / f"{prefix}_{timestamp}"
    suffix = 1
    while run_dir.exists():
        run_dir = root_dir / f"{prefix}_{timestamp}_{suffix}"
        suffix += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def snapshot_run_inputs(config_path, input_csv, run_dir):
    shutil.copy2(config_path, run_dir / "config.yaml")
    shutil.copy2(input_csv, run_dir / "input_data.csv")


def read_input_samples(input_csv, var_names):
    samples = []
    with Path(input_csv).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [name for name in var_names if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"input_data.csv 缺少参数列: {', '.join(missing)}")
        for row in reader:
            samples.append([float(row[name]) for name in var_names])
    return samples


def build_sample_rows(sample_id, var_names, x, simulation_result):
    base = {"sample_id": sample_id}
    base.update({name: float(value) for name, value in zip(var_names, x)})

    status = simulation_result.get("status", "failed")
    error_message = simulation_result.get("error_message", "")
    farfield_rows = simulation_result.get("rows", [])

    if status != "success" or not farfield_rows:
        failed_row = dict(base)
        failed_row.update({"status": "failed", "error_message": error_message})
        return [failed_row]

    rows = []
    for farfield_row in farfield_rows:
        row = dict(base)
        row.update(farfield_row)
        row.update({"status": "success", "error_message": ""})
        rows.append(row)
    return rows


def build_s11_sample_rows(sample_id, var_names, x, simulation_result):
    base = {"sample_id": sample_id}
    base.update({name: float(value) for name, value in zip(var_names, x)})

    status = simulation_result.get("status", "failed")
    error_message = simulation_result.get("error_message", "")
    s11_rows = simulation_result.get("s11_rows", [])

    if status != "success" or not s11_rows:
        failed_row = dict(base)
        failed_row.update({"status": "failed", "error_message": error_message})
        return [failed_row]

    rows = []
    for s11_row in s11_rows:
        row = dict(base)
        row.update(s11_row)
        row.update({"status": "success", "error_message": ""})
        rows.append(row)
    return rows


if __name__ == "__main__":
    raise SystemExit(run_batch())
