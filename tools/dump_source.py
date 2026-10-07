#!/usr/bin/env python3
"""Dump the game's original localization CSVs to a local (git-ignored) file.

Handy when translating: it shows the original Russian/English text next to each
key.  The output is *not* meant to be committed - it contains the game's own
text, which stays in your game folder.

    python tools/dump_source.py                 # -> source-reference.csv (git-ignored)
    python tools/dump_source.py --assets PATH --out file.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from apply import ASSET_REL, find_game  # noqa: E402
from unitypatch import SerializedFile   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets")
    ap.add_argument("--out", default="source-reference.csv")
    args = ap.parse_args()

    assets = args.assets or os.path.join(find_game(None), ASSET_REL)
    sf = SerializedFile(assets)
    rows = []
    for name, (_, text) in sorted(sf.text_assets().items()):
        if not name.startswith("Localization_DUST_FRONT"):
            continue
        tag = "main" if name.endswith("Main") else "tutorial"
        for i, row in enumerate(csv.reader(io.StringIO(text, newline=""))):
            if i == 0:
                continue
            rows.append([f"{tag}/{row[0]}"] + row[1:] + [""])

    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "russian", "english", "chinese"])
        w.writerows(rows)
    print(f"[*] wrote {len(rows)} rows to {args.out} (do not commit this file)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
