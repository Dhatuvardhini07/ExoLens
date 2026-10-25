from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from exolens.models.result import AnalysisResult


def result_to_dict(result: AnalysisResult) -> dict[str, Any]:
    return result.model_dump(mode="json", exclude_none=False)


def write_json(result: AnalysisResult, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.model_dump_json(indent=2, exclude_none=False) + "\n", encoding="utf-8")
    return output


def write_csv(result: AnalysisResult, path: str | Path) -> Path:
    """Write a one-row flattened summary; nested structures are JSON columns."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    row = result_to_dict(result)
    flat: dict[str, Any] = {}

    def flatten(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                flatten(nested, f"{prefix}.{key}" if prefix else key)
        elif isinstance(value, list):
            flat[prefix] = json.dumps(value, ensure_ascii=False)
        else:
            flat[prefix] = value

    flatten(row)
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat))
        writer.writeheader()
        writer.writerow(flat)
    return output
