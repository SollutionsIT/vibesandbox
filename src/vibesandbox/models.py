from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from vibesandbox.config import Policy


class Result(BaseModel):
    run_id: str
    runtime: str | None = None
    source_sha256: str | None = None
    image: str | None = None
    image_id: str | None = None
    policy: Policy
    started_at: datetime
    finished_at: datetime | None = None
    duration: float = 0
    exit_code: int | None = None
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    status: Literal["completed", "failed", "timed_out", "policy_error", "internal_error"] = (
        "internal_error"
    )
    error: str | None = None
    cleanup_error: str | None = None
    container_removed: bool | None = None
    security: dict[str, str] = Field(default_factory=lambda: {"network": "disabled"})
