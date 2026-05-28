import pytest

from src.config_loader import build_result_columns, build_s11_columns, generate_range_values, load_runtime_config


def test_missing_farfield_config_has_clear_error():
    raw_config = {
        "project_path": "E:/model.aedt",
        "hfss_version": "2023.1",
        "design_name": "Opti_Result1",
        "variable_names": ["ld", "wd"],
        "simulation": {"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
        "outputs": {"s11": {"enabled": False}},
        "output": {"result_csv": "result_farfield.csv", "metadata_yaml": "run_metadata.yaml"},
    }

    with pytest.raises(ValueError, match="outputs.farfield"):
        load_runtime_config(raw_config)


def test_missing_design_name_has_clear_error():
    raw_config = {
        "project_path": "E:/model.aedt",
        "hfss_version": "2023.1",
        "variable_names": ["ld", "wd"],
        "simulation": {"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
        "outputs": {
            "farfield": {
                "enabled": True,
                "sphere_name": "EH",
                "frequencies": ["3GHz"],
                "theta": {"start": 0, "stop": 0, "step": 1},
                "phi": {"start": 0, "stop": 0, "step": 1},
            }
        },
    }

    with pytest.raises(ValueError, match="design_name"):
        load_runtime_config(raw_config)


def test_single_frequency_is_normalized_to_list():
    raw_config = {
        "project_path": "E:/model.aedt",
        "hfss_version": "2023.1",
        "design_name": "Opti_Result1",
        "variable_names": ["ld", "wd"],
        "simulation": {"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
        "outputs": {
            "s11": {"enabled": False},
            "farfield": {
                "enabled": True,
                "sphere_name": "3D",
                "frequencies": "3GHz",
                "theta": {"start": 0, "stop": 180, "step": 90},
                "phi": {"start": 0, "stop": 90, "step": 90},
                "components": ["rEPhi", "rETheta"],
                "parts": ["real", "imag"],
            },
        },
        "output": {"result_csv": "result_farfield.csv", "metadata_yaml": "run_metadata.yaml"},
    }

    config = load_runtime_config(raw_config)

    assert config["outputs"]["farfield"]["frequencies"] == ["3GHz"]


def test_farfield_convert_to_si_defaults_to_false():
    config = load_runtime_config(
        {
            "project_path": "E:/model.aedt",
            "hfss_version": "2023.1",
            "design_name": "Opti_Result1",
            "variable_names": ["ld"],
            "outputs": {
                "farfield": {
                    "enabled": True,
                    "sphere_name": "EH",
                    "frequencies": ["2.1GHz"],
                    "theta": {"start": 0, "stop": 0, "step": 1},
                    "phi": {"start": 0, "stop": 0, "step": 1},
                }
            },
        }
    )

    assert config["outputs"]["farfield"]["convert_to_si"] is False


def test_farfield_convert_to_si_can_be_enabled():
    config = load_runtime_config(
        {
            "project_path": "E:/model.aedt",
            "hfss_version": "2023.1",
            "design_name": "Opti_Result1",
            "variable_names": ["ld"],
            "outputs": {
                "farfield": {
                    "enabled": True,
                    "sphere_name": "EH",
                    "frequencies": ["2.1GHz"],
                    "theta": {"start": 0, "stop": 0, "step": 1},
                    "phi": {"start": 0, "stop": 0, "step": 1},
                    "convert_to_si": True,
                }
            },
        }
    )

    assert config["outputs"]["farfield"]["convert_to_si"] is True


def test_angle_range_is_inclusive():
    values = generate_range_values({"start": 0, "stop": 180, "step": 90})

    assert values == [0.0, 90.0, 180.0]


def test_result_columns_follow_enabled_farfield_parts():
    config = load_runtime_config(
        {
            "project_path": "E:/model.aedt",
            "hfss_version": "2023.1",
            "design_name": "Opti_Result1",
            "variable_names": ["ld", "wd"],
            "simulation": {"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
            "outputs": {
                "s11": {"enabled": False},
                "farfield": {
                    "enabled": True,
                    "sphere_name": "3D",
                    "frequencies": ["3GHz"],
                    "theta": {"start": 0, "stop": 0, "step": 1},
                    "phi": {"start": 0, "stop": 0, "step": 1},
                    "components": ["rEPhi", "rETheta"],
                    "parts": ["real", "imag"],
                },
            },
            "output": {"result_csv": "result_farfield.csv", "metadata_yaml": "run_metadata.yaml"},
        }
    )

    columns = build_result_columns(config)

    assert columns == [
        "sample_id",
        "ld",
        "wd",
        "freq",
        "theta",
        "phi",
        "rEPhi_re",
        "rEPhi_im",
        "rETheta_re",
        "rETheta_im",
        "status",
        "error_message",
    ]


def test_farfield_result_columns_exclude_s11_when_enabled():
    config = load_runtime_config(
        {
            "project_path": "E:/model.aedt",
            "hfss_version": "2023.1",
            "design_name": "Opti_Result1",
            "variable_names": ["ld"],
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
        }
    )

    columns = build_result_columns(config)

    assert "s11_db" not in columns


def test_s11_columns_are_separate_when_enabled():
    config = load_runtime_config(
        {
            "project_path": "E:/model.aedt",
            "hfss_version": "2023.1",
            "design_name": "Opti_Result1",
            "variable_names": ["ld", "wd"],
            "outputs": {
                "s11": {"enabled": True},
                "farfield": {
                    "enabled": True,
                    "sphere_name": "EH",
                    "frequencies": ["2.1GHz"],
                    "theta": {"start": 0, "stop": 0, "step": 1},
                    "phi": {"start": 0, "stop": 0, "step": 1},
                },
            },
        }
    )

    assert build_s11_columns(config) == [
        "sample_id",
        "ld",
        "wd",
        "freq",
        "s11_db",
        "status",
        "error_message",
    ]


def test_output_defaults_to_result_root_dir():
    config = load_runtime_config(
        {
            "project_path": "E:/model.aedt",
            "hfss_version": "2023.1",
            "design_name": "Opti_Result1",
            "variable_names": ["ld"],
            "outputs": {
                "farfield": {
                    "enabled": True,
                    "sphere_name": "EH",
                    "frequencies": ["3GHz"],
                    "theta": {"start": 0, "stop": 0, "step": 1},
                    "phi": {"start": 0, "stop": 0, "step": 1},
                }
            },
        }
    )

    assert config["output"]["root_dir"] == "result"
    assert config["output"]["run_dir_prefix"] == "run"
    assert config["output"]["result_csv"] == "result_farfield.csv"
    assert config["output"]["s11_csv"] == "result_s11.csv"
    assert config["output"]["metadata_yaml"] == "run_metadata.yaml"
