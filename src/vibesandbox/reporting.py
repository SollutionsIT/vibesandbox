from rich.console import Console
from rich.text import Text

from vibesandbox.models import Result


def display(result: Result) -> None:
    console = Console()
    console.print("VibeSandbox", style="bold cyan")
    for key, value in {
        "Run ID": result.run_id,
        "Runtime": result.runtime,
        "Status": result.status,
        "Exit code": result.exit_code,
        "Duration": f"{result.duration:.3f}s (total orchestration)",
        "Memory limit": f"{result.policy.memory_mb} MiB",
        "Network": "disabled (policy)",
        "Container removed": result.container_removed,
    }.items():
        console.print(f"{key}: {value}", markup=False)
    for label, value in (("stdout", result.stdout), ("stderr", result.stderr)):
        if value:
            console.print(f"\n{label}:")
            # Escape control characters from untrusted output before terminal rendering.
            safe = "".join(c if c in "\n\t" or c.isprintable() else repr(c)[1:-1] for c in value)
            console.print(Text(safe))
    if result.stdout_truncated or result.stderr_truncated:
        console.print("Output truncated at policy capture limit.")
    for error in (result.error, result.cleanup_error):
        if error:
            console.print(error, markup=False, style="red")
