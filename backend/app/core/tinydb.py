"""Shared TinyDB handle (one per path).

All stores must go through get_db(): two handles on the same file are
last-writer-wins (every operation rewrites the whole file).

Concurrency safety has two layers:

- db_lock(): every TinyDB access (read or write) runs under one reentrant
  lock. TinyDB table operations each read the whole database, mutate it in
  memory, and rewrite the file, so without the lock two concurrent
  operations lose each other's writes (last writer wins). The lock also
  keeps a reader from holding a file handle open while a writer
  os.replace()'s the file — Windows denies that replace (PermissionError,
  WinError 5).

- AtomicJSONStorage (below): TinyDB's JSONStorage keeps one file handle
  open and shares its cursor between read() and write(). Under FastAPI's
  threadpool a concurrent write (seek(0) + dump + truncate) can move the
  cursor out from under a reader's seek(0) + read(), which then reads from
  EOF and raises JSONDecodeError (500), and interleaved writes can leave a
  longer doc's tail behind a shorter one (permanent "Extra data"
  corruption). Atomic storage opens a fresh handle per operation and writes
  to a temp file that is os.replace()'d into place, so readers always see
  either the old or the new complete file, and a crash mid-write can never
  leave a truncated file.
"""

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

from tinydb import TinyDB
from tinydb.storages import Storage

from app.core.config import settings

_cache: dict[str, TinyDB] = {}
_lock = threading.RLock()


@contextmanager
def db_lock():
    """Serialize all TinyDB access (see module docstring)."""
    with _lock:
        yield


class AtomicJSONStorage(Storage):
    """JSON file storage that is safe for concurrent reads and writes."""

    def __init__(self, path: str) -> None:
        self._path = path

    def read(self) -> dict | None:
        try:
            with open(self._path, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except FileNotFoundError:
            return None

    def write(self, data: dict) -> None:
        directory = os.path.dirname(self._path) or "."
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                json.dump(data, fp)
            os.replace(tmp, self._path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def get_db() -> TinyDB:
    path = settings.tinydb_path
    if path not in _cache:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        _cache[path] = TinyDB(path, storage=AtomicJSONStorage)
    return _cache[path]
