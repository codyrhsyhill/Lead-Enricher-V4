"""CSV convenience helpers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence


REQUIRED_MASTER_COLUMNS = {
    "lead_id",
    "business_name",
    "postcode",
}


class SchemaMismatchError(RuntimeError):
    """Raised when an input CSV does not meet the minimum schema requirements."""


def read_csv_rows(path: Path) -> List[dict]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return rows


def ensure_master_schema(rows: Sequence[dict]) -> None:
    if not rows:
        raise SchemaMismatchError("Master CSV is empty; expected at least one row.")
    missing = REQUIRED_MASTER_COLUMNS - set(rows[0].keys())
    if missing:
        raise SchemaMismatchError(
            f"Master CSV missing required columns: {', '.join(sorted(missing))}"
        )


def write_csv_rows(path: Path, rows: Iterable[dict], *, fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    tmp_path.replace(path)


def iter_batches(rows: Sequence[dict], batch_size: int) -> Iterator[list[dict]]:
    for index in range(0, len(rows), batch_size):
        yield list(rows[index : index + batch_size])
