import csv
from pathlib import Path
from typing import Any


def _is_null_like(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip() == ""


def summarize_csv(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        column_names = reader.fieldnames or []
        null_counts = {column_name: 0 for column_name in column_names}
        row_count = 0

        for row in reader:
            row_count += 1
            for column_name in column_names:
                if _is_null_like(row.get(column_name)):
                    null_counts[column_name] += 1

    return {
        "row_count": row_count,
        "column_count": len(column_names),
        "column_names": column_names,
        "null_counts": null_counts,
    }
