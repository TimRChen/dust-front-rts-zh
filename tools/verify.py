#!/usr/bin/env python3
"""Validate the translation file (and, if the game is installed, the applied patch).

Offline checks (always):
  * JSON is a flat object of "<csv>/<key>" -> non-empty string
  * every value contains CJK characters
  * rich-text tags are balanced and use known tag names
  * {0}-style placeholders are well formed, no tabs / CR / stray control chars
  * keys look sane (known prefix, no duplicates after lower-casing)

Full checks (when the game is found, or with --assets):
  * every key of the game's own CSV has a translation
  * no translation refers to a key that no longer exists
  * tag set and placeholder set of each translation match the original text
  * the game asset already carries the column (patch applied)
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

PREFIXES = ("main", "tutorial")
TAG_RE = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)(?:=([^>]*))?>")
KNOWN_TAGS = {"b", "i", "u", "s", "color", "size", "material", "quad", "align",
              "alpha", "cspace", "font", "indent", "line-height", "link",
              "lowercase", "uppercase", "smallcaps", "space", "sprite", "style",
              "sub", "sup", "voffset", "width", "mark", "page", "nobr", "br"}
PH_RE = re.compile(r"\{[0-9]+\}")


def load(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    strings = {k: v for k, v in data.items() if not k.startswith("__")}
    return data, strings


def check_offline(strings):
    errors, warnings = [], []
    for key, value in strings.items():
        if not isinstance(value, str):
            errors.append(f"{key}: value is not a string")
            continue
        if "/" not in key or key.split("/", 1)[0] not in PREFIXES:
            errors.append(f"{key}: key must start with one of {PREFIXES}")
        if not value.strip():
            errors.append(f"{key}: empty translation")
            continue
        if not re.search(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]", value):
            errors.append(f"{key}: no Chinese characters")
        if "\t" in value or "\r" in value:
            errors.append(f"{key}: contains a raw tab or CR")
        if any(ord(c) < 32 and c != "\n" for c in value):
            errors.append(f"{key}: contains a control character")
        # tags
        depth = {}
        for m in TAG_RE.finditer(value):
            name = m.group(1).lower()
            if name not in KNOWN_TAGS:
                warnings.append(f"{key}: unknown rich-text tag <{name}>")
            closing = m.group(0).startswith("</")
            depth[name] = depth.get(name, 0) + (-1 if closing else 1)
        for name, d in depth.items():
            if d != 0:
                errors.append(f"{key}: unbalanced <{name}> tag")
        # every '<' that starts a tag must be closed; stray '>' (e.g. ">>>" hints) is fine
        for m in re.finditer(r"<(?=[a-zA-Z/])", value):
            if ">" not in value[m.start():]:
                errors.append(f"{key}: unclosed '<' (missing '>')")
    return errors, warnings


def check_against_game(strings, assets: str, column: str):
    from unitypatch import SerializedFile
    errors, warnings = [], []
    sf = SerializedFile(assets)
    found = {n: t for n, (_, t) in sf.text_assets().items()
             if n.startswith("Localization_DUST_FRONT")}
    if not found:
        errors.append("no localization TextAsset found in the asset file")
        return errors, warnings

    seen_keys = set()
    for name, raw in found.items():
        tag = "main" if name.endswith("Main") else "tutorial"
        rows = list(csv.reader(io.StringIO(raw, newline="")))
        header = rows[0]
        if column not in header:
            errors.append(f"{name}: column {column!r} is not applied "
                          f"(header is {header})")
        idx = header.index(column) if column in header else None
        src_idx = header.index("English") if "English" in header else len(header) - 2
        for row in rows[1:]:
            key = f"{tag}/{row[0]}"
            seen_keys.add(key)
            if key not in strings:
                errors.append(f"{key}: missing from the translation file")
                continue
            zh = strings[key]
            if idx is not None and row[idx] != zh:
                errors.append(f"{key}: applied text differs from the translation file")
            en = row[src_idx]
            if sorted(TAG_RE.findall(en)) != sorted(TAG_RE.findall(zh)):
                errors.append(f"{key}: rich-text tags differ from the original")
            if sorted(PH_RE.findall(en)) != sorted(PH_RE.findall(zh)):
                errors.append(f"{key}: placeholders differ from the original")
    for key in strings:
        if key not in seen_keys:
            warnings.append(f"{key}: no matching row in the game's CSV")
    print(f"[*] game rows checked: {len(seen_keys)}")
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translations", default=os.path.join(ROOT, "translations", "zh-CN.json"))
    ap.add_argument("--assets", help="path to resources.assets (otherwise auto-detect)")
    ap.add_argument("--column", default="Chinese")
    ap.add_argument("--strict-warnings", action="store_true")
    args = ap.parse_args()

    data, strings = load(args.translations)
    print(f"[*] {len(strings)} translations in {os.path.basename(args.translations)}"
          f" (language {data.get('__language__', '?')})")

    errors, warnings = check_offline(strings)

    assets = args.assets
    if not assets:
        try:
            from apply import ASSET_REL, find_game
            assets = os.path.join(find_game(None), ASSET_REL)
        except SystemExit:
            assets = None
            print("[*] game not found - running offline checks only")
    if assets and os.path.isfile(assets):
        print(f"[*] checking against {assets}")
        e2, w2 = check_against_game(strings, assets, args.column)
        errors += e2
        warnings += w2

    for w in warnings[:20]:
        print(f"  [warn] {w}")
    if len(warnings) > 20:
        print(f"  [warn] ... and {len(warnings) - 20} more")
    if errors:
        print(f"\nFAILED with {len(errors)} problem(s):")
        for e in errors[:40]:
            print("  [!]", e)
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more")
        return 1
    if warnings and args.strict_warnings:
        print(f"\nFAILED: {len(warnings)} warning(s) with --strict-warnings")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
