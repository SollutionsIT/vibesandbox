"""Read a bounded regular file without following symlinks in any path component."""

import os
import stat
from pathlib import Path


def read_source(path: Path, limit: int) -> bytes:
    if ".." in path.parts:
        raise ValueError("parent traversal is not allowed")
    absolute = Path(os.path.abspath(path))
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("source must be a regular file")
            data = source.read(limit + 1)
            if len(data) > limit:
                raise ValueError("source exceeds policy size limit")
            return data
    finally:
        os.close(directory)
