"""Minimal, dependency-free patcher for Unity serialized asset files (format v22).

Why a custom patcher?
---------------------
We only need to change the two ``TextAsset`` objects that hold the game's
localization CSV files.  Instead of rebuilding the whole asset file (which is
risky and requires a heavyweight library), this patcher:

1. serializes the changed object into a fresh blob,
2. appends that blob at the end of the file,
3. repoints the object-table entry (byteStart / byteSize),
4. updates the header file size.

Every other byte of the original file is left untouched, so the game keeps
reading a perfectly valid asset file.

Object table entry layout (serialized format version >= 22, little endian):
    align4
    int64  pathID
    int64  byteStart   (relative to header.dataOffset)
    uint32 byteSize
    int32  typeID

No third-party modules are required: Python 3.8+ standard library only.
"""
from __future__ import annotations

import os
import struct

ALIGN = 4


def align(n: int, a: int = ALIGN) -> int:
    return (n + a - 1) & ~(a - 1)


class SerializedFile:
    """A Unity serialized (.assets) file we can surgically edit."""

    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as fh:
            self.data = bytearray(fh.read())
        d = self.data
        if len(d) < 50:
            raise ValueError("file too small to be a Unity serialized file")
        self.version = struct.unpack_from(">I", d, 8)[0]
        self.metadata_size = struct.unpack_from(">I", d, 20)[0]
        self.file_size = struct.unpack_from(">q", d, 24)[0]
        self.data_offset = struct.unpack_from(">q", d, 32)[0]
        if self.version < 22:
            raise ValueError(
                f"unsupported serialized file version {self.version}; "
                "this tool expects version >= 22 (Unity 2019.3+)"
            )
        if self.file_size != len(d):
            raise ValueError("header file size does not match the actual file size")
        self.entries: dict[int, int] = {}          # pathID -> entry offset
        self.entry_info: dict[int, tuple] = {}     # pathID -> (byte_start, size, type_id)
        self._scan_entries()

    # ------------------------------------------------------------------ table
    def _scan_entries(self) -> None:
        d = self.data
        p = 50
        end = self.data_offset
        while p < end - 24:
            p = align(p, 4)
            path_id = struct.unpack_from("<q", d, p)[0]
            byte_start = struct.unpack_from("<q", d, p + 8)[0]
            byte_size = struct.unpack_from("<I", d, p + 16)[0]
            type_id = struct.unpack_from("<i", d, p + 20)[0]
            if (0 < path_id < (1 << 62) and 0 <= byte_start and byte_size > 0
                    and self.data_offset + byte_start + byte_size <= self.file_size
                    and 0 <= type_id < 4096):
                self.entries[path_id] = p
                self.entry_info[path_id] = (byte_start, byte_size, type_id)
            p += 24

    def object_bytes(self, path_id: int) -> bytes:
        byte_start, byte_size, _ = self.entry_info[path_id]
        off = self.data_offset + byte_start
        return bytes(self.data[off:off + byte_size])

    # ------------------------------------------------------- object building
    @staticmethod
    def _put_string(buf: bytearray, s: str) -> None:
        raw = s.encode("utf-8")
        buf += struct.pack("<i", len(raw)) + raw
        buf += b"\x00" * (align(len(buf)) - len(buf))

    def build_text_asset(self, name: str, script: bytes) -> bytes:
        """Serialize a TextAsset (m_Name + m_Script) the way Unity does."""
        buf = bytearray()
        self._put_string(buf, name)
        buf += struct.pack("<i", len(script)) + script
        buf += b"\x00" * (align(len(buf)) - len(buf))
        return bytes(buf)

    # ---------------------------------------------------------------- patch
    def replace_object(self, path_id: int, blob: bytes) -> None:
        new_off = align(len(self.data), 16)
        self.data += b"\x00" * (new_off - len(self.data))
        self.data += blob
        entry = self.entries[path_id]
        struct.pack_into("<q", self.data, entry + 8, new_off - self.data_offset)
        struct.pack_into("<I", self.data, entry + 16, len(blob))
        self.entry_info[path_id] = (new_off - self.data_offset, len(blob),
                                    self.entry_info[path_id][2])
        struct.pack_into(">q", self.data, 24, len(self.data))
        self.file_size = len(self.data)

    def save(self, dest: str | None = None) -> str:
        dest = dest or self.path
        tmp = dest + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(self.data)
        os.replace(tmp, dest)
        return dest

    # ---------------------------------------------------------------- read
    def text_assets(self) -> dict[str, tuple[int, str]]:
        """Return {name: (pathID, text)} for every TextAsset we can parse."""
        found: dict[str, tuple[int, str]] = {}
        for path_id in list(self.entry_info):
            try:
                blob = self.object_bytes(path_id)
                name, text, consumed = self._parse_text_asset(blob)
            except Exception:
                continue
            if consumed != len(blob) or not name:
                continue
            found[name] = (path_id, text)
        return found

    @staticmethod
    def _parse_text_asset(blob: bytes) -> tuple[str, str, int]:
        p = 0
        name_len = struct.unpack_from("<i", blob, p)[0]
        p += 4
        if not 0 < name_len < 4096 or p + name_len > len(blob):
            raise ValueError("bad name length")
        name = blob[p:p + name_len].decode("utf-8")
        p = align(p + name_len)
        script_len = struct.unpack_from("<i", blob, p)[0]
        p += 4
        if not 0 <= script_len or p + script_len > len(blob):
            raise ValueError("bad script length")
        text = blob[p:p + script_len].decode("utf-8")
        p = align(p + script_len)
        return name, text, p
