"""Audit a hash-pinned export of uv.lock without mutating the environment."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="vibesandbox-audit-") as directory:
    requirements = Path(directory) / "requirements.txt"
    subprocess.run(
        [
            os.environ.get("UV", "uv"),
            "export",
            "--frozen",
            "--all-groups",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--cache-dir",
            str(Path(directory) / "cache"),
            "--require-hashes",
            "--disable-pip",
            "-r",
            str(requirements),
        ],
        check=True,
    )
