# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small atomic JSON writer copied in spirit from core fileio: no public host equivalent."""
import json
import os
import tempfile
import time
from pathlib import Path


def write_json(path: Path, data, *, indent=2, sort_keys=True, ensure_ascii=False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as out:
            out.write(json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii) + "\n")
            out.flush()
            os.fsync(out.fileno())
        for attempt in range(8):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.25)
    finally:
        temporary.unlink(missing_ok=True)
