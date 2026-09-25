import json
import re
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import ValidationError

from vibesandbox.config import load_policy
from vibesandbox.reporting import display
from vibesandbox.service import ExecutionService

app = typer.Typer(no_args_is_help=True, help="Disposable, policy-enforced local code execution.")


@app.callback()
def main() -> None:
    """VibeSandbox: Python and JavaScript sandboxes."""


@app.command()
def run(
    source: Path,
    policy: Annotated[Path | None, typer.Option(help="Resource policy YAML")] = None,
    timeout: Annotated[float | None, typer.Option()] = None,
    memory: Annotated[str | None, typer.Option(help="Memory in MiB, e.g. 256m")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Execute one source file; exit 0 only on completed execution and cleanup."""
    try:
        memory_mb = None
        if memory is not None:
            if not re.fullmatch(r"[0-9]+[mM]", memory):
                raise ValueError("memory must be specified in MiB, for example 256m")
            memory_mb = int(memory[:-1])
        config = load_policy(policy, timeout=timeout, memory_mb=memory_mb)
    except (ValueError, OSError, yaml.YAMLError, ValidationError):
        message = (
            "Invalid policy or resource override; see policies/default.yaml and policy limits."
        )
        if json_output:
            typer.echo(json.dumps({"status": "policy_error", "error": message}))
        else:
            typer.echo(message, err=True)
        raise typer.Exit(2) from None
    result = ExecutionService().execute(source, config)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        display(result)
    raise typer.Exit(0 if result.status == "completed" else 1)
