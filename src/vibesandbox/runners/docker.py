"""Bounded capture and disposable Docker lifecycle."""

import contextlib
import threading
import time
from pathlib import Path
from typing import Any

from docker.errors import NotFound
from docker.types import LogConfig, Mount, Ulimit

import docker
from vibesandbox.config import Policy
from vibesandbox.models import Result
from vibesandbox.runtimes import Runtime

LABEL = "io.sollutions.vibesandbox"


def container_options(
    source: Path, runtime: Runtime, policy: Policy, run_id: str
) -> dict[str, Any]:
    return {
        "image": runtime.image,
        "command": runtime.command(),
        "entrypoint": [],
        "name": f"vibesandbox-{run_id}",
        "labels": {LABEL: "true", f"{LABEL}.run": run_id},
        "user": "65532:65532",
        "working_dir": "/tmp",
        "network_mode": "none",
        "network_disabled": True,
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "privileged": False,
        "mem_limit": f"{policy.memory_mb}m",
        "memswap_limit": f"{policy.memory_mb}m",
        "nano_cpus": int(policy.cpus * 1_000_000_000),
        "pids_limit": policy.pids,
        "tmpfs": {"/tmp": f"rw,noexec,nosuid,nodev,size={policy.tmpfs_mb}m,mode=1777"},
        "shm_size": "1m",
        "mounts": [Mount(target="/source", source=str(source), type="bind", read_only=True)],
        "environment": {"HOME": "/tmp", "LANG": "C.UTF-8"},
        "ulimits": [Ulimit(name="nofile", soft=128, hard=128), Ulimit(name="core", soft=0, hard=0)],
        "log_config": LogConfig(type="none"),
        "stdin_open": False,
        "tty": False,
        "detach": True,
    }


class Capture:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.buffers = [bytearray(), bytearray()]
        self.truncated = [False, False]
        self.error = False

    def consume(self, stream: Any) -> None:
        try:
            for pair in stream:
                for index, chunk in enumerate(pair):
                    if chunk:
                        remaining = self.limit - len(self.buffers[index])
                        self.buffers[index].extend(chunk[:remaining])
                        self.truncated[index] |= len(chunk) > remaining
        except Exception:
            self.error = True

    def apply(self, result: Result) -> None:
        result.stdout, result.stderr = (b.decode("utf-8", "replace") for b in self.buffers)
        result.stdout_truncated, result.stderr_truncated = self.truncated


class DockerRunner:
    def run(self, source: Path, runtime: Runtime, result: Result) -> None:
        client: Any = None
        container: Any = None
        stream: Any = None
        thread: threading.Thread | None = None
        capture = Capture(result.policy.output_bytes)
        name = f"vibesandbox-{result.run_id}"
        create_attempted = False
        try:
            client = docker.from_env(timeout=3)
            if client.api.base_url != "http+docker://localhost":
                raise ValueError("only a local Unix-socket Docker daemon is supported")
            info = client.info()
            if info.get("OSType") != "linux" or not all(
                info.get(key) for key in ("MemoryLimit", "SwapLimit", "CpuCfsQuota", "PidsLimit")
            ):
                raise ValueError("Docker must provide Linux memory, swap, CPU and PID controls")
            if not any("seccomp" in opt for opt in info.get("SecurityOptions", [])):
                raise ValueError("Docker default seccomp support is required")
            image = client.images.get(runtime.image)
            result.image_id = image.id
            options = container_options(source, runtime, result.policy, result.run_id)
            options["image"] = image.id
            create_attempted = True
            container = client.containers.create(**options)
            stream = container.attach(stream=True, stdout=True, stderr=True, demux=True)
            thread = threading.Thread(target=capture.consume, args=(stream,), daemon=True)
            thread.start()
            container.start()
            deadline = time.monotonic() + result.policy.timeout
            while True:
                container.reload()
                state = container.attrs["State"]
                if not state["Running"]:
                    result.exit_code = state["ExitCode"]
                    result.status = "completed" if result.exit_code == 0 else "failed"
                    break
                if time.monotonic() >= deadline:
                    result.timed_out = True
                    result.status = "timed_out"
                    container.kill()
                    container.wait(timeout=3)
                    container.reload()
                    result.exit_code = container.attrs["State"]["ExitCode"]
                    break
                time.sleep(0.025)
            thread.join(timeout=3)
            if thread.is_alive() or capture.error:
                raise RuntimeError("output capture did not complete")
        finally:
            if client is not None and create_attempted:
                # A lost create response may still have created the named container.
                for attempt in range(3):
                    try:
                        target = container if container is not None else client.containers.get(name)
                        target.remove(force=True, v=True)
                        result.container_removed = True
                        break
                    except NotFound:
                        result.container_removed = True
                        break
                    except Exception:
                        if attempt == 2:
                            result.container_removed = False
                            result.cleanup_error = (
                                f"Could not remove {name}; run docker rm -f {name}"
                            )
                            result.status = "internal_error"
                        else:
                            time.sleep(0.1)
            if stream is not None:
                # SDK close may shutdown an already disconnected socket after normal EOF.
                with contextlib.suppress(OSError):
                    stream.close()
                # Docker SDK retains the HTTP response; release it even after EOF.
                with contextlib.suppress(OSError, ValueError):
                    stream._response.close()
            if thread is not None:
                thread.join(timeout=3)
            capture.apply(result)
            if client is not None:
                client.close()
