"""Resource policy; isolation controls are deliberately not configurable."""

import math
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    timeout: float = Field(default=5.0, ge=0.1, le=60)
    memory_mb: int = Field(default=128, ge=32, le=1024)
    cpus: float = Field(default=0.5, ge=0.1, le=2)
    pids: int = Field(default=32, ge=16, le=128)
    tmpfs_mb: int = Field(default=16, ge=1, le=64)
    output_bytes: int = Field(default=65536, ge=256, le=1048576)
    source_bytes: int = Field(default=1048576, ge=1, le=1048576)

    @field_validator("timeout", "cpus")
    @classmethod
    def finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("must be finite")
        return value


def load_policy(path: Path | None = None, **overrides: object) -> Policy:
    data = {} if path is None else yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("policy must be a YAML mapping")
    return Policy.model_validate({**data, **{k: v for k, v in overrides.items() if v is not None}})
