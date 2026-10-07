#!/usr/bin/env python3
"""Install the Simplified-Chinese language option into Dust Front RTS (Demo).

The script works on *your own* legally installed copy of the game: it reads the
localization CSVs that ship inside ``resources.assets``, appends a ``Chinese``
column taken from ``translations/zh-CN.json``, and writes the file back with a
surgical patch (all other game data is left byte-identical).

Python 3.8+, standard library only.

    python tools/apply.py                 # auto-detect the game, install
    python tools/apply.py --dry-run       # show what would happen
    python tools/apply.py --game-dir "D:\\SteamLibrary\\steamapps\\common\\Dust Front RTS Demo"
    python tools/restore.py               # undo
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from unitypatch import SerializedFile  # noqa: E402

GAME_NAME = "Dust Front RTS Demo"
ASSET_REL = os.path.join("Dust Front RTS_Data", "resources.assets")
TARGET_ASSETS = (
    "Localization_DUST_FRONT - Main",
    "Localization_DUST_FRONT - Tutorial-locals",
)
DEFAULT_COLUMN = "Chinese"
BACKUP_SUFFIX = ".zh-backup"

STEAM_ROOTS = [
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
    r"C:\Steam",
    r"D:\Steam",
    r"E:\Steam",
    r"F:\Steam",
    r"K:\Steam",
]
LIBRARY_HINTS = [
    r"C:\SteamLibrary", r"D:\SteamLibrary", r"E:\SteamLibrary",
    r"F:\SteamLibrary", r"G:\SteamLibrary", r"Z:\SteamLibrary",
    r"K:\SteamLibrary",
]


# --------------------------------------------------------------- discovery
def _vdf_library_paths(steam_root: str) -> list[str]:
    """Read library folder paths out of Steam's libraryfolders.vdf."""
    vdf = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
    paths = []
    if not os.path.isfile(vdf):
        return paths
    try:
        with open(vdf, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if '"path"' in line:
                    parts = line.split('"')
                    if len(parts) >= 4:
                        paths.append(parts[3].replace("\\\\", "\\"))
    except OSError:
        pass
    return paths


def find_game(explicit: str | None = None) -> str:
    if explicit:
        if os.path.isdir(explicit):
            return explicit
        raise SystemExit(f"[!] game directory not found: {explicit}")

    candidates: list[str] = []
    for root in STEAM_ROOTS:
        candidates += _vdf_library_paths(root)
    candidates += LIBRARY_HINTS
    for steam_root in STEAM_ROOTS:
        candidates.append(os.path.join(steam_root, "steamapps", "common"))

    seen = set()
    for lib in candidates:
        if not lib or lib.lower() in seen:
            continue
        seen.add(lib.lower())
        game = os.path.join(lib, GAME_NAME) if not lib.endswith(GAME_NAME) else lib
        if os.path.isfile(os.path.join(game, ASSET_REL)):
            return game
        # library folder -> steamapps/common/<game>
        game2 = os.path.join(lib, "steamapps", "common", GAME_NAME)
        if os.path.isfile(os.path.join(game2, ASSET_REL)):
            return game2
    raise SystemExit(
        "[!] Could not find the game automatically.\n"
        "    Pass the folder that contains 'Dust Front RTS.exe', e.g.\n"
        r'    python tools/apply.py --game-dir "D:\SteamLibrary\steamapps\common\Dust Front RTS Demo"'
    )


# ------------------------------------------------------------------ csv work
def load_translations(path: str) -> dict[str, str]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"[!] {path} must contain a JSON object of \"file/key\": \"中文\"")
    return {k: v for k, v in data.items() if not k.startswith("__")}


def build_csv(tag: str, raw: str, strings: dict[str, str], column: str):
    """Append (or refresh) the Chinese column. Returns (text, stats)."""
    rows = list(csv.reader(io.StringIO(raw, newline="")))
    if not rows:
        raise SystemExit(f"[!] {tag}: empty CSV")
    header = rows[0]

    # refresh mode: drop a previously added column with the same name
    drop = None
    if header and header[-1] == column and len(header) > 1:
        drop = len(header) - 1
        header = header[:-1]
        rows = [r[:drop] for r in rows]

    if len(header) < 2 or header[0] != "Keys":
        raise SystemExit(f"[!] {tag}: unexpected CSV header {header}")

    out = []
    missing, translated, fallback = [], 0, 0
    for i, row in enumerate(rows):
        if i == 0:
            out.append(row + [column])
            continue
        key = f"{tag}/{row[0]}"
        zh = strings.get(key)
        if zh is None or not zh.strip():
            missing.append(key)
            zh = row[-1]            # fall back to the original text
            fallback += 1
        else:
            translated += 1
        out.append(row + [zh])

    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerows(out)
    text = buf.getvalue()

    # integrity: the original columns must be untouched
    check = list(csv.reader(io.StringIO(text, newline="")))
    if len(check) != len(rows):
        raise SystemExit(f"[!] {tag}: row count changed while rebuilding")
    cols = len(header)          # number of original columns (after a refresh-drop)
    for a, b in zip(rows, check):
        if a[:cols] != b[:cols]:
            raise SystemExit(f"[!] {tag}: original columns were modified (row {a[0]!r})")
    return text, dict(rows=len(rows) - 1, translated=translated,
                      fallback=fallback, missing=missing)


# --------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-dir", help="folder containing 'Dust Front RTS.exe'")
    ap.add_argument("--assets", help="path to Dust Front RTS_Data/resources.assets")
    ap.add_argument("--translations", default=os.path.join(ROOT, "translations", "zh-CN.json"))
    ap.add_argument("--column", default=DEFAULT_COLUMN,
                    help="CSV column name == language name in the in-game dropdown")
    ap.add_argument("--dry-run", action="store_true", help="do not write anything")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    assets = args.assets
    if not assets:
        game = find_game(args.game_dir)
        assets = os.path.join(game, ASSET_REL)
    if not os.path.isfile(assets):
        raise SystemExit(f"[!] asset file not found: {assets}")

    strings = load_translations(args.translations)
    print(f"[*] game asset : {assets}")
    print(f"[*] translations: {args.translations} ({len(strings)} entries)")
    print(f"[*] column name : {args.column!r} (this is what the in-game dropdown shows)")

    sf = SerializedFile(assets)
    found = sf.text_assets()
    todo = {}
    for name in TARGET_ASSETS:
        if name not in found:
            raise SystemExit(f"[!] TextAsset not found in the asset file: {name}\n"
                             "    Is this really the Dust Front RTS demo?")
        todo[name] = found[name]
        print(f"[*] found {name!r} (pathID {found[name][0]}, {len(found[name][1])} chars)")

    new_texts = {}
    total_t = total_f = 0
    for name, (path_id, raw) in todo.items():
        tag = "main" if name.endswith("Main") else "tutorial"
        text, stats = build_csv(tag, raw, strings, args.column)
        new_texts[name] = text
        total_t += stats["translated"]
        total_f += stats["fallback"]
        print(f"    {tag}: {stats['rows']} rows, translated {stats['translated']}, "
              f"fallback {stats['fallback']}, {len(text.encode('utf-8'))} bytes")
        for key in stats["missing"][:10]:
            print(f"      [!] no translation for {key} (kept original text)")
        if len(stats["missing"]) > 10:
            print(f"      [!] ... and {len(stats['missing']) - 10} more")

    if args.dry_run:
        print("[*] dry run: nothing written")
        return 0

    backup = assets + BACKUP_SUFFIX
    already_patched = args.column in (list(todo.values())[0][1].split("\r\n")[0].split(","))
    if not args.no_backup:
        if os.path.isfile(backup):
            print(f"[*] backup already exists, keeping it: {backup}")
        elif already_patched:
            print("[!] asset already patched and no pristine backup exists; "
                  "use Steam 'verify integrity' to restore the original file")
        else:
            shutil.copy2(assets, backup)
            print(f"[*] backup written: {backup}")

    patched = 0
    for name, text in new_texts.items():
        path_id = todo[name][0]
        blob = sf.build_text_asset(name, text.encode("utf-8"))
        sf.replace_object(path_id, blob)
        patched += 1
    sf.save()

    print(f"[*] patched {patched} TextAsset(s); file is now {os.path.getsize(assets)} bytes")
    print(f"[*] translated {total_t} strings"
          + (f", {total_f} fell back to the original text" if total_f else ""))
    print()
    print("Done.  Start the game through Steam and pick CHINESE in the language")
    print("dropdown at the bottom of the start screen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
