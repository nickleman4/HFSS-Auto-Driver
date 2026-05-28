from __future__ import annotations

import csv
from pathlib import Path

import yaml


class ResultWriter:
    """Append V1.0 simulation rows and metadata to disk."""

    def __init__(self, result_csv, metadata_yaml, columns, write_mode="append"):
        self.result_csv = Path(result_csv)
        self.metadata_yaml = Path(metadata_yaml)
        self.columns = list(columns)
        self.write_mode = write_mode
        self._overwrite_prepared = False

    def write_metadata(self, metadata):
        self.metadata_yaml.parent.mkdir(parents=True, exist_ok=True)
        with self.metadata_yaml.open("w", encoding="utf-8") as f:
            yaml.safe_dump(metadata, f, allow_unicode=True, sort_keys=False)

    def write_rows(self, rows):
        rows = list(rows)
        if not rows:
            return

        self.result_csv.parent.mkdir(parents=True, exist_ok=True)
        self._prepare_overwrite()
        write_header = not self.result_csv.exists() or self.result_csv.stat().st_size == 0

        with self.result_csv.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.columns, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            for row in rows:
                writer.writerow(self._complete_row(row))

    def _prepare_overwrite(self):
        if self.write_mode != "overwrite" or self._overwrite_prepared:
            return
        if self.result_csv.exists():
            self.result_csv.unlink()
        self._overwrite_prepared = True

    def _complete_row(self, row):
        completed = {}
        for column in self.columns:
            value = row.get(column, "nan")
            completed[column] = value
        return completed
