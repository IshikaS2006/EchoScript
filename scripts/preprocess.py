#!/usr/bin/env python3
"""EchoScript preprocessing: raw recordings -> clean 16 kHz clips + manifest.

Steps
1. Build groups: recordings sharing a folder or a user_id stay together.
2. For each recording: resample 44.1 kHz -> 16 kHz mono, cut into segments
   using transcript timestamps.
3. Drop segments labelled REDACTED (label is a placeholder, not the speech).
4. Clean text: NFC normalize, "_" and "-" -> space, strip , . । ! :
   (spellings, digits and word boundaries are left untouched).
5. Write clips + manifest.csv, split train/val by group (seed 42).

Run from anywhere:
    python scripts/preprocess.py            # skips if manifest already exists
    python scripts/preprocess.py --force    # rebuild
    python scripts/preprocess.py --limit 3 --out-dir data_clean_test --force
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SRC_SR = 44100
TARGET_SR = 16000
VAL_FRACTION = 0.1
SEED = 42


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("_", " ")
    text = re.sub(r"[,.।!:\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_groups(df: pd.DataFrame) -> dict:
    """Union-find: rows sharing a folder or a user_id end up in one group."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, r in df.iterrows():
        parent[find(f"f{r.folder}")] = find(f"u{r.user_id}")
    return {u: find(f"u{u}") for u in df.user_id.unique()}


def process_recording(uid, group, clips_dir: Path, counts: dict) -> list[dict]:
    audio, sr = sf.read(DATA / "audios" / f"{uid}_audio.wav", dtype="float32")
    if sr != SRC_SR:
        raise ValueError(f"{uid}: expected {SRC_SR} Hz, got {sr}")
    audio = resample_poly(audio, 160, 441).astype("float32")  # 44.1k -> 16k

    segs = json.load(open(DATA / "transcripts" / f"{uid}_transcript.json", encoding="utf-8"))
    rows = []
    for i, s in enumerate(segs):
        if "REDACTED" in s["text"]:
            counts["redacted"] += 1
            continue
        text = clean(s["text"])
        if not text:
            counts["empty"] += 1
            continue
        a, b = int(s["start"] * TARGET_SR), min(int(s["end"] * TARGET_SR), len(audio))
        if b <= a:
            counts["zero_length"] += 1
            continue
        name = f"{uid}_{i:04d}.wav"
        sf.write(clips_dir / name, audio[a:b], TARGET_SR, subtype="PCM_16")
        rows.append(dict(clip=name, text=text, text_raw=s["text"],
                         duration=(b - a) / TARGET_SR, user_id=uid, group=group))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rebuild even if manifest exists")
    ap.add_argument("--limit", type=int, default=None, help="only process the first N user_ids (testing)")
    ap.add_argument("--out-dir", default="data_clean", help="output folder, relative to project root")
    args = ap.parse_args()

    out = ROOT / args.out_dir
    if (out / "manifest.csv").exists() and not args.force:
        print(f"{out / 'manifest.csv'} already exists. Use --force to rebuild.")
        return
    clips_dir = out / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA / "NewData.csv")
    df["folder"] = df.rec_url_gcp.str.extract(r"upload_goai/(\d+)/")[0]
    group_of = build_groups(df)

    uids = sorted(group_of)
    if args.limit:
        uids = uids[: args.limit]

    counts = {"redacted": 0, "empty": 0, "zero_length": 0}
    rows = []
    for n, uid in enumerate(uids, 1):
        rows += process_recording(uid, group_of[uid], clips_dir, counts)
        print(f"[{n}/{len(uids)}] {uid}", end="\r", flush=True)
    print()

    m = pd.DataFrame(rows)

    # split by group so no speaker or conversation crosses train/val
    rng = np.random.default_rng(SEED)
    groups = np.array(sorted(m.group.unique()))
    val_groups = set(rng.choice(groups, size=round(len(groups) * VAL_FRACTION), replace=False))
    m["split"] = np.where(m.group.isin(val_groups), "val", "train")
    m.to_csv(out / "manifest.csv", index=False, encoding="utf-8-sig")

    print("dropped redacted / empty-after-clean / zero-length:",
          counts["redacted"], counts["empty"], counts["zero_length"])
    print("clips:", len(m), "| hours:", round(m.duration.sum() / 3600, 2))
    print(m.groupby("split").agg(
        clips=("clip", "size"),
        hours=("duration", lambda x: round(x.sum() / 3600, 2)),
        speakers=("user_id", "nunique"),
        groups=("group", "nunique")))
    overlap = set(m[m.split == "val"].user_id) & set(m[m.split == "train"].user_id)
    print("val/train speaker overlap:", overlap)


if __name__ == "__main__":
    main()