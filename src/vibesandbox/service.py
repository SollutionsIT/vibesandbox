import hashlib
import secrets
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from docker.errors import DockerException, ImageNotFound

from vibesandbox.config import Policy
from vibesandbox.models import Result
from vibesandbox.runners.docker import DockerRunner
from vibesandbox.runtimes import Runtime, detect
from vibesandbox.source import read_source


class Runner(Protocol):
    def run(self, source: Path, runtime: Runtime, result: Result) -> None: ...


class ExecutionService:
    def __init__(self, runner: Runner | None = None) -> None:
        self.runner = runner if runner is not None else DockerRunner()

    def execute(self, path: Path, policy: Policy) -> Result:
        start = time.monotonic()
        result = Result(run_id=secrets.token_hex(16), policy=policy, started_at=datetime.now(UTC))
        try:
            runtime = detect(path)
            data = read_source(path, policy.source_bytes)
            result.runtime = runtime.name
            result.image = runtime.image
            result.source_sha256 = hashlib.sha256(data).hexdigest()
        except (ValueError, OSError):
            result.status = "policy_error"
            result.error = (
                "Source rejected: use a readable regular .py/.js file without symlinks "
                "or traversal, within the source size limit."
            )
        else:
            try:
                with tempfile.TemporaryDirectory(prefix="vibesandbox-") as directory:
                    snapshot = Path(directory) / "source"
                    snapshot.mkdir(mode=0o755)
                    snapshot.chmod(0o755)
                    target = snapshot / f"main{runtime.extension}"
                    target.write_bytes(data)
                    target.chmod(0o444)
                    self.runner.run(snapshot, runtime, result)
            except ImageNotFound:
                result.error = "Execution image missing; run make images."
                result.status = "internal_error"
            except DockerException:
                result.error = (
                    "Docker operation failed; check the local daemon, image and permissions."
                )
                result.status = "internal_error"
            except ValueError as exc:
                result.error = str(exc)
                result.status = "policy_error"
            except Exception:
                result.error = "Execution failed internally; check Docker availability and retry."
                result.status = "internal_error"
        result.finished_at = datetime.now(UTC)
        result.duration = round(time.monotonic() - start, 6)
        return result
