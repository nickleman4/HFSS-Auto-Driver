import csv

from src.result_writer import ResultWriter


def test_writer_creates_header_and_appends_rows(tmp_path):
    result_csv = tmp_path / "result_farfield.csv"
    writer = ResultWriter(
        result_csv=result_csv,
        metadata_yaml=tmp_path / "run_metadata.yaml",
        columns=["sample_id", "ld", "freq", "theta", "phi", "rEPhi_re", "status", "error_message"],
        write_mode="append",
    )

    writer.write_rows(
        [
            {
                "sample_id": 1,
                "ld": 6.0,
                "freq": "3GHz",
                "theta": 0.0,
                "phi": 0.0,
                "rEPhi_re": 1.25,
                "status": "success",
                "error_message": "",
            }
        ]
    )
    writer.write_rows(
        [
            {
                "sample_id": 2,
                "ld": 6.2,
                "freq": "3GHz",
                "theta": 90.0,
                "phi": 0.0,
                "rEPhi_re": 2.5,
                "status": "success",
                "error_message": "",
            }
        ]
    )

    with result_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows == [
        ["sample_id", "ld", "freq", "theta", "phi", "rEPhi_re", "status", "error_message"],
        ["1", "6.0", "3GHz", "0.0", "0.0", "1.25", "success", ""],
        ["2", "6.2", "3GHz", "90.0", "0.0", "2.5", "success", ""],
    ]


def test_writer_records_failed_sample_with_nan_values(tmp_path):
    result_csv = tmp_path / "result_farfield.csv"
    writer = ResultWriter(
        result_csv=result_csv,
        metadata_yaml=tmp_path / "run_metadata.yaml",
        columns=["sample_id", "ld", "rEPhi_re", "status", "error_message"],
        write_mode="append",
    )

    writer.write_rows(
        [
            {
                "sample_id": 3,
                "ld": 7.1,
                "status": "failed",
                "error_message": "Far field report is empty",
            }
        ]
    )

    with result_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {
            "sample_id": "3",
            "ld": "7.1",
            "rEPhi_re": "nan",
            "status": "failed",
            "error_message": "Far field report is empty",
        }
    ]


def test_writer_saves_metadata_yaml(tmp_path):
    metadata_yaml = tmp_path / "run_metadata.yaml"
    writer = ResultWriter(
        result_csv=tmp_path / "result_farfield.csv",
        metadata_yaml=metadata_yaml,
        columns=["sample_id"],
        write_mode="append",
    )

    writer.write_metadata({"hfss_version": "2023.1", "variable_names": ["ld", "wd"]})

    assert "hfss_version: '2023.1'" in metadata_yaml.read_text(encoding="utf-8")
    assert "- ld" in metadata_yaml.read_text(encoding="utf-8")
