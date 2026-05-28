from __future__ import annotations

import copy


PART_SUFFIXES = {
    "real": "re",
    "imag": "im",
}


def load_runtime_config(raw_config):
    """Normalize and validate the V1.0 runtime configuration."""
    config = copy.deepcopy(raw_config)
    _require(config, "design_name", "design_name is required")

    outputs = config.setdefault("outputs", {})
    if "farfield" not in outputs:
        raise ValueError("outputs.farfield configuration is required")
    outputs.setdefault("s11", {"enabled": False})

    config.setdefault("simulation", {})
    config["simulation"].setdefault("setup_name", "Setup1")
    config["simulation"].setdefault("sweep_name", "Sweep")
    config["simulation"].setdefault("variable_unit", "mm")

    farfield = outputs["farfield"]
    farfield.setdefault("enabled", True)
    farfield.setdefault("components", ["rEPhi", "rETheta"])
    farfield.setdefault("parts", ["real", "imag"])
    farfield.setdefault("convert_to_si", False)

    frequencies = farfield.get("frequencies")
    if isinstance(frequencies, str):
        farfield["frequencies"] = [frequencies]
    elif isinstance(frequencies, tuple):
        farfield["frequencies"] = list(frequencies)

    if farfield.get("enabled"):
        _require(farfield, "sphere_name", "outputs.farfield.sphere_name is required")
        _require(farfield, "frequencies", "outputs.farfield.frequencies is required")
        _require(farfield, "theta", "outputs.farfield.theta is required")
        _require(farfield, "phi", "outputs.farfield.phi is required")

    output = config.setdefault("output", {})
    output.setdefault("root_dir", "result")
    output.setdefault("run_dir_prefix", "run")
    output.setdefault("result_csv", "result_farfield.csv")
    output.setdefault("s11_csv", "result_s11.csv")
    output.setdefault("metadata_yaml", "run_metadata.yaml")
    output.setdefault("write_mode", "append")

    return config


def generate_range_values(range_config):
    """Generate inclusive floating-point range values from start/stop/step."""
    start = float(range_config["start"])
    stop = float(range_config["stop"])
    step = float(range_config["step"])
    if step <= 0:
        raise ValueError("range step must be greater than 0")
    if stop < start:
        raise ValueError("range stop must be greater than or equal to start")

    values = []
    current = start
    epsilon = step * 1e-9
    while current <= stop + epsilon:
        values.append(round(current, 10))
        current += step
    return values


def build_result_columns(config):
    """Build deterministic result CSV columns for the enabled outputs."""
    columns = ["sample_id", *config["variable_names"]]

    farfield = config["outputs"]["farfield"]
    if farfield.get("enabled"):
        columns.extend(["freq", "theta", "phi"])
        for component in farfield.get("components", []):
            for part in farfield.get("parts", []):
                suffix = PART_SUFFIXES.get(part, part)
                columns.append(f"{component}_{suffix}")

    columns.extend(["status", "error_message"])
    return columns


def build_s11_columns(config):
    """Build deterministic S11 CSV columns."""
    return ["sample_id", *config["variable_names"], "freq", "s11_db", "status", "error_message"]


def _require(mapping, key, message):
    if key not in mapping or mapping[key] in (None, "", []):
        raise ValueError(message)
