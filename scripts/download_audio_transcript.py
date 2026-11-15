#!/usr/bin/env python3
"""Download audio, transcript, and metadata files from an ASR CSV.

Saves files into three separate folders:
- audios/
- transcripts/
- metadata/

Naming pattern:
- <user_id>_audio.<ext>
- <user_id>_transcript.<ext>
- <user_id>_metadata.<ext>
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def extension_from_url(url: str, default_ext: str) -> str:
    path = urlparse((url or "").strip()).path
    suffix = Path(path).suffix
    return suffix if suffix else default_ext


def safe_download(url: str, destination: Path, timeout: int = 60) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as response:
        data = response.read()

    with destination.open("wb") as f:
        f.write(data)


def canonical_target_path(base_dir: Path, base_name: str, ext: str) -> Path:
    return base_dir / f"{base_name}{ext}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download audio, transcript, and metadata files from CSV")
    parser.add_argument("--input", "-i", required=True, help="Input CSV path")
    parser.add_argument(
        "--audio-column",
        default="rec_url_gcp",
        help="CSV column containing audio URLs (default: rec_url_gcp)",
    )
    parser.add_argument(
        "--transcript-column",
        default="transcription_url_gcp",
        help="CSV column containing transcript URLs (default: transcription_url_gcp)",
    )
    parser.add_argument(
        "--metadata-column",
        default="metadata_url_gcp",
        help="CSV column containing metadata URLs (default: metadata_url_gcp)",
    )
    parser.add_argument(
        "--user-id-column",
        default="user_id",
        help="CSV column for user ID (default: user_id)",
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        help="Output root directory (default: current directory)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds (default: 60)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input)
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    out_root = Path(args.out_dir)
    if not out_root.is_absolute():
        # Keep outputs in the same project directory as the input CSV by default.
        out_root = input_csv.parent / out_root

    audio_dir = out_root / "audios"
    transcript_dir = out_root / "transcripts"
    metadata_dir = out_root / "metadata"
    audio_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    success_audio = 0
    success_transcript = 0
    success_metadata = 0
    skipped_audio = 0
    skipped_transcript = 0
    skipped_metadata = 0
    failed = 0

    with input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
        total_rows = len(rows)

        required = [
            args.user_id_column,
            args.audio_column,
            args.transcript_column,
            args.metadata_column,
        ]
        missing = [col for col in required if col not in fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        for idx, row in enumerate(rows, start=1):
            user_id = str(row.get(args.user_id_column, "")).strip()
            audio_url = str(row.get(args.audio_column, "")).strip()
            transcript_url = str(row.get(args.transcript_column, "")).strip()
            metadata_url = str(row.get(args.metadata_column, "")).strip()

            print(f"[PROGRESS] {idx}/{total_rows} rows processed", end="\r", flush=True)

            if not user_id:
                print(f"[WARN] Row {idx}: user_id missing, skipping")
                failed += 1
                continue

            try:
                if audio_url:
                    audio_ext = extension_from_url(audio_url, ".wav")
                    audio_target = canonical_target_path(audio_dir, f"{user_id}_audio", audio_ext)
                    if audio_target.exists():
                        skipped_audio += 1
                    else:
                        safe_download(audio_url, audio_target, timeout=args.timeout)
                        success_audio += 1
                else:
                    print(f"[WARN] Row {idx}: audio URL missing")

                if transcript_url:
                    transcript_ext = extension_from_url(transcript_url, ".json")
                    transcript_target = canonical_target_path(
                        transcript_dir,
                        f"{user_id}_transcript",
                        transcript_ext,
                    )
                    if transcript_target.exists():
                        skipped_transcript += 1
                    else:
                        safe_download(transcript_url, transcript_target, timeout=args.timeout)
                        success_transcript += 1
                else:
                    print(f"[WARN] Row {idx}: transcript URL missing")

                if metadata_url:
                    metadata_ext = extension_from_url(metadata_url, ".json")
                    metadata_target = canonical_target_path(
                        metadata_dir,
                        f"{user_id}_metadata",
                        metadata_ext,
                    )
                    if metadata_target.exists():
                        skipped_metadata += 1
                    else:
                        safe_download(metadata_url, metadata_target, timeout=args.timeout)
                        success_metadata += 1
                else:
                    print(f"[WARN] Row {idx}: metadata URL missing")

            except (HTTPError, URLError, OSError) as exc:
                failed += 1
                print(f"\n[ERROR] Row {idx}, user_id={user_id}: {exc}")

    print()
    print("Download complete")
    print(f"Rows processed: {total_rows}/{total_rows}")
    print(f"Audio files downloaded: {success_audio}")
    print(f"Audio files skipped (already exists): {skipped_audio}")
    print(f"Transcript files downloaded: {success_transcript}")
    print(f"Transcript files skipped (already exists): {skipped_transcript}")
    print(f"Metadata files downloaded: {success_metadata}")
    print(f"Metadata files skipped (already exists): {skipped_metadata}")
    print(f"Rows with errors: {failed}")
    print(f"Output folder: {out_root.resolve()}")


if __name__ == "__main__":
    main()
