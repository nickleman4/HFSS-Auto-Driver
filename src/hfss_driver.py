import os
import yaml
import numpy as np
import pyaedt
import psutil

# 全局变量
hfss_app = None

def init_hfss(project_path, version="2023.1"):
    """初始化 HFSS 后台进程"""
    global hfss_app
    print(f"🚀 正在后台启动 HFSS {version}...")
    hfss_app = pyaedt.Hfss(projectname=project_path, 
                           specified_version=version, 
                           non_graphical=True, 
                           new_desktop_session=True)
    pid = hfss_app.odesktop.GetProcessID()
    print(f"✅ HFSS 启动成功！进程 PID: {pid}")

def close_hfss():
    """安全关闭并清理残留进程"""
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

