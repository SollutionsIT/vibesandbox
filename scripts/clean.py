"""Remove only known generated artifacts under this checkout."""

import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for name in (".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov", "dist", "build"):
    path = root / name
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
(root / ".coverage").unlink(missing_ok=True)
for path in root.rglob("__pycache__"):
    if ".venv" not in path.parts and not path.is_symlink():
        shutil.rmtree(path)
