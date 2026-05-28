import csv
import re

import yaml

from src import main_driver


def test_run_batch_writes_each_sample_immediately(tmp_path, monkeypatch):
    project_path = tmp_path / "antenna.aedt"
    project_path.write_text("", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    input_csv = tmp_path / "input_data.csv"
    result_csv = tmp_path / "result_farfield.csv"
    metadata_yaml = tmp_path / "run_metadata.yaml"

    config_path.write_text(
        yaml.safe_dump(
            {
                "project_path": str(project_path),
                "hfss_version": "2023.1",
                "design_name": "Opti_Result1",
                "simulation": {"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
                "variable_names": ["ld", "wd"],
                "outputs": {
                    "s11": {"enabled": False},
                    "farfield": {
                        "enabled": True,
                        "sphere_name": "3D",
                        "frequencies": ["3GHz"],
                        "theta": {"start": 0, "stop": 0, "step": 1},
                        "phi": {"start": 0, "stop": 0, "step": 1},
                        "components": ["rEPhi"],
                        "parts": ["real", "imag"],
                    },
                },
                "output": {
                    "root_dir": str(tmp_path / "result"),
                    "run_dir_prefix": "run",
                    "result_csv": "result_farfield.csv",
                    "metadata_yaml": "run_metadata.yaml",
                    "write_mode": "append",
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    input_csv.write_text("ld,wd\n6.0,1.0\n6.2,1.1\n", encoding="utf-8")

    calls = {"init": [], "close": 0, "sim": []}

    monkeypatch.setattr(
        main_driver,
        "init_hfss",
        lambda path, design_name, version: calls["init"].append((path, design_name, version)),
    )
    monkeypatch.setattr(main_driver, "close_hfss", lambda: calls.__setitem__("close", calls["close"] + 1))

    def fake_run_farfield_simulation(x, var_names, simulation_config, farfield_config, s11_config=None):
        calls["sim"].append((list(x), var_names, simulation_config, farfield_config, s11_config))
        return {
            "status": "success",
            "error_message": "",
            "rows": [{"freq": "3GHz", "theta": 0.0, "phi": 0.0, "rEPhi_re": x[0], "rEPhi_im": x[1]}],
        }

    monkeypatch.setattr(main_driver, "run_farfield_simulation", fake_run_farfield_simulation)

    exit_code = main_driver.run_batch(config_path=config_path, input_csv=input_csv)

    assert exit_code == 0
    assert calls["init"] == [(str(project_path), "Opti_Result1", "2023.1")]
    assert calls["close"] == 1
    assert len(calls["sim"]) == 2

    run_dirs = sorted((tmp_path / "result").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert re.match(r"run_\d{8}_\d{6}", run_dir.name)
    result_csv = run_dir / "result_farfield.csv"
    metadata_yaml = run_dir / "run_metadata.yaml"
    assert (run_dir / "config.yaml").read_text(encoding="utf-8") == config_path.read_text(encoding="utf-8")
    assert (run_dir / "input_data.csv").read_text(encoding="utf-8") == input_csv.read_text(encoding="utf-8")

    with result_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {
            "sample_id": "1",
            "ld": "6.0",
            "wd": "1.0",
            "freq": "3GHz",
            "theta": "0.0",
            "phi": "0.0",
            "rEPhi_re": "6.0",
            "rEPhi_im": "1.0",
            "status": "success",
            "error_message": "",
        },
        {
            "sample_id": "2",
            "ld": "6.2",
            "wd": "1.1",
            "freq": "3GHz",
            "theta": "0.0",
            "phi": "0.0",
            "rEPhi_re": "6.2",
            "rEPhi_im": "1.1",
            "status": "success",
            "error_message": "",
        },
    ]
    assert "project_path" in metadata_yaml.read_text(encoding="utf-8")


def test_run_batch_writes_failed_sample_row(tmp_path, monkeypatch):
    project_path = tmp_path / "antenna.aedt"
    project_path.write_text("", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    input_csv = tmp_path / "input_data.csv"
    result_csv = tmp_path / "result_farfield.csv"

    config_path.write_text(
        yaml.safe_dump(
            {
                "project_path": str(project_path),
                "hfss_version": "2023.1",
                "design_name": "Opti_Result1",
                "simulation": {"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
                "variable_names": ["ld"],
                "outputs": {
                    "farfield": {
                        "enabled": True,
                        "sphere_name": "3D",
                        "frequencies": ["3GHz"],
                        "theta": {"start": 0, "stop": 0, "step": 1},
                        "phi": {"start": 0, "stop": 0, "step": 1},
                        "components": ["rEPhi"],
                        "parts": ["real"],
                    }
                },
                "output": {"root_dir": str(tmp_path / "result")},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    input_csv.write_text("ld\n7.1\n", encoding="utf-8")

    monkeypatch.setattr(main_driver, "init_hfss", lambda path, design_name, version: None)
    monkeypatch.setattr(main_driver, "close_hfss", lambda: None)
    monkeypatch.setattr(
        main_driver,
        "run_farfield_simulation",
        lambda x, var_names, simulation_config, farfield_config, s11_config=None: {
            "status": "failed",
            "error_message": "No far-field data",
            "rows": [],
        },
    )

    exit_code = main_driver.run_batch(config_path=config_path, input_csv=input_csv)

    assert exit_code == 0
    run_dir = next((tmp_path / "result").iterdir())
    result_csv = run_dir / "result_farfield.csv"
    with result_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {
            "sample_id": "1",
            "ld": "7.1",
            "freq": "nan",
            "theta": "nan",
            "phi": "nan",
            "rEPhi_re": "nan",
            "status": "failed",
            "error_message": "No far-field data",
        }
    ]


def test_run_batch_passes_enabled_s11_config_and_writes_separate_s11_file(tmp_path, monkeypatch):
    project_path = tmp_path / "antenna.aedt"
    project_path.write_text("", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    input_csv = tmp_path / "input_data.csv"

    config_path.write_text(
        yaml.safe_dump(
            {
                "project_path": str(project_path),
                "hfss_version": "2023.1",
                "design_name": "Opti_Result1",
                "simulation": {"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
                "variable_names": ["L"],
                "outputs": {
                    "s11": {"enabled": True},
                    "farfield": {
                        "enabled": True,
                        "sphere_name": "EH",
                        "frequencies": ["2.1GHz"],
                        "theta": {"start": 0, "stop": 0, "step": 1},
                        "phi": {"start": 0, "stop": 0, "step": 1},
                        "components": ["rEPhi"],
                        "parts": ["real"],
                    },
                },
                "output": {"root_dir": str(tmp_path / "result")},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    input_csv.write_text("L\n6.0\n", encoding="utf-8")

    captured_s11_config = []
    monkeypatch.setattr(main_driver, "init_hfss", lambda path, design_name, version: None)
    monkeypatch.setattr(main_driver, "close_hfss", lambda: None)

    def fake_run_farfield_simulation(x, var_names, simulation_config, farfield_config, s11_config=None):
        captured_s11_config.append(s11_config)
        return {
            "status": "success",
            "error_message": "",
            "rows": [{"freq": "2.1GHz", "theta": 0.0, "phi": 0.0, "rEPhi_re": 1.5}],
            "s11_rows": [{"freq": "2.1GHz", "s11_db": -12.25}],
        }

    monkeypatch.setattr(main_driver, "run_farfield_simulation", fake_run_farfield_simulation)

    exit_code = main_driver.run_batch(config_path=config_path, input_csv=input_csv)

    assert exit_code == 0
    assert captured_s11_config == [{"enabled": True}]
    run_dir = next((tmp_path / "result").iterdir())
    with (run_dir / "result_farfield.csv").open(newline="", encoding="utf-8") as f:
        farfield_rows = list(csv.DictReader(f))
    assert "s11_db" not in farfield_rows[0]

    with (run_dir / "result_s11.csv").open(newline="", encoding="utf-8") as f:
        s11_rows = list(csv.DictReader(f))
    assert s11_rows == [
        {
            "sample_id": "1",
            "L": "6.0",
            "freq": "2.1GHz",
            "s11_db": "-12.25",
            "status": "success",
            "error_message": "",
        }
    ]
