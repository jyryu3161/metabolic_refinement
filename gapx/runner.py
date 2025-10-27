"""High-level runner coordinating GAPx workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config.loader import dump_manifest
from .config.models import RunBundle


@dataclass
class RunResult:
    """Container for GA execution results."""

    bundle: RunBundle
    best_individual: Optional[dict] = None
    started_at: datetime = datetime.utcnow()
    finished_at: Optional[datetime] = None
    manifest_path: Optional[Path] = None


class Runner:
    """Entry point for executing GAPx runs.

    The current implementation acts as a scaffold that records configuration and
    produces deterministic manifests. Integration with COBRApy, GA operators,
    parallel orchestration, and reporting will be added in subsequent milestones.
    """

    def __init__(self, bundle: RunBundle) -> None:
        self.bundle = bundle

    def run(self, resume: bool = False) -> RunResult:
        """Execute a run (stub)."""

        result = RunResult(bundle=self.bundle)
        result.finished_at = datetime.utcnow()

        output_dir = Path(self.bundle.run.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = output_dir / "manifest.json"
        dump_manifest(self.bundle, manifest_path)
        result.manifest_path = manifest_path

        return result

