"""Shared TinyDB handle (one per path).

Multiple TinyDB instances on the same file each cache the file in memory and
rewrite the whole file on insert — two handles lose each other's writes. All
stores must go through get_db().
"""

from pathlib import Path

from tinydb import TinyDB

from app.core.config import settings

_cache: dict[str, TinyDB] = {}


def get_db() -> TinyDB:
    path = settings.tinydb_path
    if path not in _cache:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        _cache[path] = TinyDB(path)
    return _cache[path]
