"""
Target / run configuration.

Two layers of config: the static *target* (which adapter, which model,
optional base_url override) and the per-run *options* (filters, dry-run,
output paths). We use Pydantic for both so CLI input flows through one
validation surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


AdapterKind = Literal["openrouter", "nvidia", "generic"]


class TargetConfig(BaseModel):
    """Where to send the probes."""
    adapter: AdapterKind
    model: str = Field(min_length=1, max_length=200)
    base_url: Optional[str] = None      # only used by ``generic``
    max_tokens: int = Field(default=600, ge=1, le=4096)
    timeout_s: float = Field(default=60.0, gt=0, le=600)
    verify_tls: bool = True

    @field_validator("base_url")
    @classmethod
    def _strip_trailing_slash(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.rstrip("/")


class RunOptions(BaseModel):
    """How to drive the run."""
    categories: tuple[str, ...] = ()  # empty == all
    tags: tuple[str, ...] = ()        # empty == all
    concurrency: int = Field(default=4, ge=1, le=32)
    record_responses: bool = True
    output_dir: Path = Path("results/runs")
    dry_run: bool = False             # build everything, send nothing
