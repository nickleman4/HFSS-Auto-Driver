import os
import yaml
import numpy as np
from hfss_driver import init_hfss, close_hfss, run_hfss_simulation

if __name__ == "__main__":
    print("===================================")
    print("   HFSS 自动化仿真主控程序 V3.0")
    print("===================================")

    # 1. 读取 YAML 配置文件
    yaml_path = "config.yaml"
    if not os.path.exists(yaml_path):
        print("❌ 找不到 config.yaml 文件，请检查！")
        exit()
        
    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    project_path = config["project_path"]
    version = config["hfss_version"]
    num_points = config["num_freq_points"]
    var_names = config["variable_names"]
    
    # 2. 从外部 CSV 文件读取要跑的尺寸数据
    input_csv = "input_data.csv"
    if not os.path.exists(input_csv):
        print(f"❌ 找不到输入数据文件 {input_csv}，请检查！")
        exit()
        
    print(f"📄 正在读取输入数据: {input_csv}...")
    # skiprows=1 表示跳过第一行的表头 (ld, wd)
    dataset_x = np.loadtxt(input_csv, delimiter=",", skiprows=1)
    
    # 防止只跑一组数据时 numpy 把二维数组降维成一维
    if dataset_x.ndim == 1:
        dataset_x = dataset_x.reshape(1, -1)
        
    print(f"✅ 成功加载 {len(dataset_x)} 组待仿真尺寸。")
    
    # 3. 开始执行自动化流程
    all_results = []
    global_freqs = None 
    
    if os.path.exists(project_path):
        # 启动后台
        init_hfss(project_path, version=version)
        
        # 遍历读取到的每一组尺寸
        for i, x in enumerate(dataset_x):
            print(f"\n---> 正在计算第 {i+1}/{len(dataset_x)} 组，输入尺寸: {x}")
            
            freqs, s11_array = run_hfss_simulation(x, var_names, num_points) 
            
            if freqs is not None and global_freqs is None:
                global_freqs = freqs
            
            row_data = np.concatenate((x, s11_array))
            all_results.append(row_data)
            
        # 彻底关闭进程
        close_hfss()
        
        # 4. 生成表头并保存结果
        var_header = ",".join(var_names)
        if global_freqs is not None:
            # 【Bug已修复】：去掉了 /1e9，直接保留两位小数加上 GHz
            freq_header = ",".join([f"{f:.2f}GHz" for f in global_freqs])
            header_str = f"{var_header},{freq_header}"
        else:
            header_str = f"{var_header}," + ",".join([f"Freq_{i+1}" for i in range(num_points)])
            
        save_path = "result_data.csv"
        np.savetxt(save_path, np.array(all_results), delimiter=",", header=header_str, comments="", fmt="%.6f")
        print(f"\n🎉 全部仿真圆满完成！结果已导出至: {os.path.abspath(save_path)}")
        
    else:
        print(f"🤷‍♂️ 找不到指定的 aedt 文件，请检查路径: {project_path}")