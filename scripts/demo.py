from contextlib import closing
from pathlib import Path

import docker
from vibesandbox.config import Policy
from vibesandbox.reporting import display
from vibesandbox.runners.docker import LABEL
from vibesandbox.service import ExecutionService

service = ExecutionService()
run_ids = []
for filename, status, expected in (
    ("hello.py", "completed", "Hello from VibeSandbox"),
    ("hello.js", "completed", "Node.js"),
    ("timeout.py", "timed_out", ""),
    ("network.py", "completed", "Network connection unavailable"),
    ("readonly.py", "completed", "Root filesystem write denied"),
    ("processes.py", "completed", "Process creation limited"),
    ("failure.py", "failed", "Intentional safe demonstration failure"),
):
    result = service.execute(
        Path("examples") / filename, Policy(timeout=1.0 if filename == "timeout.py" else 5.0)
    )
    display(result)
    run_ids.append(result.run_id)
    assert result.status == status, result.model_dump_json()
    assert expected in result.stdout + result.stderr
    assert result.container_removed is True
with closing(docker.from_env()) as client:
    for run_id in run_ids:
        assert not client.containers.list(all=True, filters={"label": f"{LABEL}.run={run_id}"})
print("All seven scenarios passed; no demo containers remain.")
