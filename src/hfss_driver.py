import numpy as np

try:
    from .config_loader import PART_SUFFIXES, generate_range_values
except ImportError:
    from config_loader import PART_SUFFIXES, generate_range_values

# 全局变量
hfss_app = None

def init_hfss(project_path, design_name, version="2023.1"):
    """初始化 HFSS 后台进程"""
    import pyaedt

    global hfss_app
    print(f"🚀 正在后台启动 HFSS {version}...")
    hfss_app = pyaedt.Hfss(projectname=project_path,
                           designname=design_name,
                           specified_version=version,
                           non_graphical=True,
                           new_desktop_session=True)
    pid = hfss_app.odesktop.GetProcessID()
    print(f"✅ HFSS 启动成功！进程 PID: {pid}")

def close_hfss():
    """安全关闭并清理残留进程"""
    import psutil

    global hfss_app
    if hfss_app:
        print("🧹 正在清理进程...")
        try:
            pid = hfss_app.odesktop.GetProcessID()
            hfss_app.release_desktop(close_projects=True, close_desktop=True)
            if psutil.pid_exists(pid):
                psutil.Process(pid).terminate()
                print(f"🔫 已强杀残留进程 (PID: {pid})")
        except Exception:
            pass
        finally:
            hfss_app = None
            print("✅ 清理完毕！")

def run_farfield_simulation(x, var_names, simulation_config, farfield_config, s11_config=None):
    """Modify variables, solve the setup, and extract configured far-field rE data."""
    global hfss_app
    if hfss_app is None:
        raise RuntimeError("❌ 错误：未启动 HFSS 实例！")

    try:
        variable_unit = simulation_config.get("variable_unit", "mm")
        _set_design_variables(x, var_names, variable_unit)

        setup_name = simulation_config.get("setup_name")
        if setup_name is None:
            setup_name = hfss_app.setups[0].name
        sweep_name = simulation_config.get("sweep_name")
        if sweep_name is None:
            sweep_name = hfss_app.setups[0].sweeps[0].name
        hfss_app.analyze_setup(setup_name)

        s11_rows = []
        if s11_config and s11_config.get("enabled"):
            s11_values = _extract_s11_values(setup_name, sweep_name)
            s11_rows = _build_s11_rows(farfield_config["frequencies"], s11_values)

        rows = _extract_farfield_rows(setup_name, sweep_name, farfield_config)
        return {"status": "success", "error_message": "", "rows": rows, "s11_rows": s11_rows}
    except Exception as e:
        print(f"❌ 远场仿真报错拦截 (尺寸 x={x})。错误详情: {e}")
        return {"status": "failed", "error_message": str(e), "rows": []}


def run_hfss_simulation(x, var_names, num_freq_points):
    """
    终极版核心功能：动态修改 N 个参数 -> 求解 -> 提取数据
    x: 具体的尺寸数值列表 (例如 [6.0, 1.0, 2.5])
    var_names: 从 yaml 读取的变量名列表 (例如 ["Length", "Width", "Feed_X"])
    """
    global hfss_app
    if hfss_app is None:
        raise RuntimeError("❌ 错误：未启动 HFSS 实例！")

    penalty_s11 = np.zeros(num_freq_points)

    try:
        # 【核心升级】利用 zip 函数，动态将变量名和数值一一对应并修改
        for name, val in zip(var_names, x):
            hfss_app[name] = f"{val}mm"  # 假设单位都是毫米

        setup_name = hfss_app.setups[0].name
        hfss_app.analyze_setup(setup_name)

        sweep_name = hfss_app.setups[0].sweeps[0].name
        solution_str = f"{setup_name} : {sweep_name}"
        
        report = hfss_app.post.get_solution_data(expressions="dB(S(1,1))", 
                                                 setup_sweep_name=solution_str)
        
        if report is None:
            print(f"⚠️ 警告：未提取到数据 (尺寸 x={x})，返回惩罚值。")
            return None, penalty_s11

        freqs = np.array(report.primary_sweep_values) 
        s11_values = np.array(report.data_real())
        return freqs, s11_values

    except Exception as e:
        print(f"❌ 仿真报错拦截 (尺寸 x={x})。错误详情: {e}")
        return None, penalty_s11


def _set_design_variables(x, var_names, variable_unit):
    for name, val in zip(var_names, x):
        hfss_app[name] = f"{val}{variable_unit}"


def _extract_farfield_rows(setup_name, sweep_name, farfield_config):
    solution_str = f"{setup_name} : {sweep_name}"
    sphere_name = farfield_config["sphere_name"]
    frequencies = farfield_config["frequencies"]
    theta_values = generate_range_values(farfield_config["theta"])
    phi_values = generate_range_values(farfield_config["phi"])
    components = farfield_config.get("components", ["rEPhi", "rETheta"])
    parts = farfield_config.get("parts", ["real", "imag"])
    convert_to_si = farfield_config.get("convert_to_si", False)

    rows = []
    for freq in frequencies:
        for theta in theta_values:
            for phi in phi_values:
                row = {"freq": freq, "theta": theta, "phi": phi}
                for component in components:
                    real_value, imag_value = _get_farfield_complex_value(
                        component=component,
                        setup_sweep_name=solution_str,
                        sphere_name=sphere_name,
                        freq=freq,
                        theta=theta,
                        phi=phi,
                        convert_to_si=convert_to_si,
                    )
                    values = {"real": real_value, "imag": imag_value}
                    for part in parts:
                        suffix = PART_SUFFIXES.get(part, part)
                        row[f"{component}_{suffix}"] = values[part]
                rows.append(row)
    return rows


def _build_s11_rows(frequencies, s11_values):
    return [
        {"freq": freq, "s11_db": s11_values.get(_frequency_key(freq), np.nan)}
        for freq in frequencies
    ]


def _extract_s11_values(setup_name, sweep_name):
    solution_str = f"{setup_name} : {sweep_name}"
    report = hfss_app.post.get_solution_data(
        expressions="dB(S(1,1))",
        setup_sweep_name=solution_str,
    )
    if report is None:
        raise RuntimeError(f"No S11 data for {solution_str}")

    freqs = list(report.primary_sweep_values)
    values = np.array(report.data_real(), dtype=float).flatten()
    return {_frequency_key(freq): float(value) for freq, value in zip(freqs, values)}


def _get_farfield_complex_value(component, setup_sweep_name, sphere_name, freq, theta, phi, convert_to_si=False):
    report = hfss_app.post.get_solution_data(
        expressions=component,
        setup_sweep_name=setup_sweep_name,
        domain="Sweep",
        variations={
            "Freq": [freq],
            "Theta": [f"{_format_degree(theta)}deg"],
            "Phi": [f"{_format_degree(phi)}deg"],
        },
        report_category="Far Fields",
        context=sphere_name,
    )
    if report is None:
        raise RuntimeError(
            f"No far-field data for {component} at Freq={freq}, Theta={theta}, Phi={phi}"
        )

    real_values = report.data_real(convert_to_SI=convert_to_si)
    imag_values = report.data_imag(convert_to_SI=convert_to_si) if hasattr(report, "data_imag") else [0.0]
    return float(real_values[0]), float(imag_values[0])


def _format_degree(value):
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return str(value)


def _frequency_key(value):
    if isinstance(value, (int, float, np.integer, np.floating)):
        ghz = float(value)
    else:
        text = str(value).strip().lower()
        numeric = "".join(ch for ch in text if ch.isdigit() or ch in ".-+eE")
        ghz = float(numeric)
        if "mhz" in text:
            ghz /= 1000.0
        elif "khz" in text:
            ghz /= 1_000_000.0
        elif "hz" in text and "ghz" not in text:
            ghz /= 1_000_000_000.0
    return f"{ghz:.12g}"
