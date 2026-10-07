#!/usr/bin/env python3
"""Restore the original Dust Front RTS asset file (undo the Chinese patch).

    python tools/restore.py
    python tools/restore.py --game-dir "D:\\...\\Dust Front RTS Demo"

If no backup exists, verify the game files through Steam instead
(Steam -> right click the demo -> Properties -> Installed Files ->
Verify integrity of game files).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from apply import ASSET_REL, BACKUP_SUFFIX, find_game  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir")
    ap.add_argument("--assets")
    args = ap.parse_args()

    assets = args.assets or os.path.join(find_game(args.game_dir), ASSET_REL)
    backup = assets + BACKUP_SUFFIX
    if not os.path.isfile(backup):
        raise SystemExit(
            f"[!] no backup found at {backup}\n"
            "    Use Steam's 'Verify integrity of game files' to restore the game."
        )
    shutil.copy2(backup, assets)
    print(f"[*] restored {assets} from {backup}")
    print("[*] if the game still runs in Chinese, pick ENGLISH/RUSSIAN in the "
          "language dropdown once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
