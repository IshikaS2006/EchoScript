#!/usr/bin/env python3
"""Rewrite ASR dataset URLs to the new upload_goai format.

Example conversion:
https://storage.googleapis.com/joshtalks-data-collection/hq_data/hi/967179/825780_transcription.json
->
https://storage.googleapis.com/upload_goai/967179/825780_transcription.json
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse

NEW_BASE = "https://storage.googleapis.com/upload_goai"
DEFAULT_URL_COLUMNS = ["rec_url_gcp", "transcription_url_gcp", "metadata_url_gcp"]


def transform_url(url: str, new_base: str = NEW_BASE) -> str:
    """Convert an old GCS URL to the new upload_goai format.

    Keeps only the last two path parts: <parent_id>/<filename>.
    """
    raw = (url or "").strip()
    if not raw:
        return raw

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return raw

    parent_id, filename = parts[-2], parts[-1]
    return f"{new_base.rstrip('/')}/{parent_id}/{filename}"


def infer_url_columns(fieldnames: list[str]) -> list[str]:
    lowered = {name.lower(): name for name in fieldnames}

    # Prefer the expected audio/transcript/metadata columns.
    selected = [lowered[c] for c in DEFAULT_URL_COLUMNS if c in lowered]
    if "metadata_url" in lowered and lowered["metadata_url"] not in selected:
        selected.append(lowered["metadata_url"])
    if selected:
        return selected

    # Fallback: any column that appears to contain URL data.
    return [name for name in fieldnames if "url" in name.lower()]


def rewrite_csv(input_csv: Path, output_csv: Path, columns: list[str] | None) -> tuple[int, int]:
    with input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not fieldnames:
        raise ValueError("Input CSV has no header row.")

    selected_columns = columns or infer_url_columns(fieldnames)
    missing = [c for c in selected_columns if c not in fieldnames]
    if missing:
        raise ValueError(f"Columns not found in CSV header: {missing}")

    updated_cells = 0
    for row in rows:
        for col in selected_columns:
            before = row.get(col, "")
            after = transform_url(before)
            if before != after:
                row[col] = after
                updated_cells += 1

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows), updated_cells


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rewrite ASR CSV URLs to upload_goai format")
    parser.add_argument("--input", "-i", required=True, help="Input CSV path")
    parser.add_argument(
        "--output",
        "-o",
        help="Output CSV path (default: NewData.csv in input file directory)",
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        help="Columns to rewrite. Default: auto-detect URL columns.",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite the input CSV instead of writing a new file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input)
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    if args.inplace:
        output_csv = input_csv
    elif args.output:
        output_csv = Path(args.output)
    else:
        output_csv = input_csv.with_name("NewData.csv")

    rows, updated_cells = rewrite_csv(input_csv, output_csv, args.columns)
    print(f"Rows processed: {rows}")
    print(f"URL cells updated: {updated_cells}")
    print(f"Output: {output_csv}")


if __name__ == "__main__":
    main()
