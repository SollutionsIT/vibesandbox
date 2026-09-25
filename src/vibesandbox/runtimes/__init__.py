"""Runtime registry: orchestration has no language-specific branches."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Runtime:
    name: str
    extension: str
    image: str
    interpreter: tuple[str, ...]

    def command(self) -> list[str]:
        return [*self.interpreter, f"/source/main{self.extension}"]


RUNTIMES = (
    Runtime("python", ".py", "vibesandbox-python:0.1.0", ("python", "-I", "-B", "-u")),
    Runtime("node", ".js", "vibesandbox-node:0.1.0", ("node", "--max-old-space-size=64")),
)


def detect(path: Path) -> Runtime:
    for runtime in RUNTIMES:
        if path.suffix == runtime.extension:
            return runtime
    raise ValueError("unsupported source extension; use .py or .js")
