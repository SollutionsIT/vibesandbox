import json
from pathlib import Path

import pytest
from docker.errors import DockerException
from typer.testing import CliRunner

import docker
from vibesandbox.cli import app
from vibesandbox.config import Policy
from vibesandbox.runners.docker import LABEL
from vibesandbox.runtimes import RUNTIMES
from vibesandbox.service import ExecutionService

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def daemon():
    try:
        client = docker.from_env(timeout=3)
        client.ping()
    except DockerException:
        pytest.skip("local Docker daemon unavailable")
    for runtime in RUNTIMES:
        try:
            client.images.get(runtime.image)
        except DockerException:
            pytest.fail("Execution images missing: run make images")
    yield client
    client.close()


def execute(path, daemon, policy=None):
    report = ExecutionService().execute(path.resolve(), policy or Policy())
    assert report.container_removed is True, report.model_dump_json()
    assert not daemon.containers.list(all=True, filters={"label": f"{LABEL}.run={report.run_id}"})
    return report


@pytest.mark.parametrize(
    "name,status,message",
    [
        ("hello.py", "completed", "Hello from VibeSandbox"),
        ("hello.js", "completed", "Node.js"),
        ("network.py", "completed", "Network connection unavailable"),
        ("readonly.py", "completed", "Root filesystem write denied"),
        ("processes.py", "completed", "Process creation limited"),
        ("failure.py", "failed", "Intentional safe demonstration failure"),
        ("timeout.py", "timed_out", ""),
    ],
)
def test_scenarios(daemon, name, status, message):
    report = execute(
        Path("examples") / name, daemon, Policy(timeout=1.0 if name == "timeout.py" else 5.0)
    )
    assert report.status == status, report.model_dump_json()
    assert message in report.stdout + report.stderr
    if name == "timeout.py":
        assert report.timed_out and report.duration < 10


def test_output_flood_is_bounded(daemon, tmp_path):
    path = tmp_path / "output.py"
    path.write_text(
        "import sys\nfor _ in range(1000):\n print('x'*1000)\n print('y'*1000, file=sys.stderr)\n"
    )
    report = execute(path, daemon, Policy(output_bytes=1024))
    assert report.status == "completed"
    assert len(report.stdout) == len(report.stderr) == 1024
    assert report.stdout_truncated and report.stderr_truncated


def test_memory_limit(daemon, tmp_path):
    path = tmp_path / "memory.py"
    path.write_text("data = bytearray(256 * 1024 * 1024)\nprint(len(data))\n")
    report = execute(path, daemon, Policy(memory_mb=32))
    assert report.status == "failed"
    assert report.exit_code == 137 or "MemoryError" in report.stderr


def test_effective_identity_and_source_readonly(daemon, tmp_path):
    path = tmp_path / "identity.py"
    path.write_text("""import os
assert os.getuid() == 65532
status = open('/proc/self/status').read()
assert 'NoNewPrivs:\\t1' in status
assert 'CapEff:\\t0000000000000000' in status
assert 'Seccomp:\\t2' in status
try:
    open('/source/main.py', 'w')
except OSError:
    print('source read-only')
else:
    raise RuntimeError('source writable')
assert not os.path.exists('/var/run/docker.sock')
""")
    report = execute(path, daemon)
    assert report.status == "completed", report.model_dump_json()
    assert "source read-only" in report.stdout


def test_cli_json(daemon):
    output = CliRunner().invoke(app, ["run", "examples/hello.py", "--json"])
    assert output.exit_code == 0, output.stdout
    report = json.loads(output.stdout)
    assert report["status"] == "completed" and report["container_removed"]
