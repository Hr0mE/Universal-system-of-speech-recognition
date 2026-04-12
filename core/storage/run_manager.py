from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import yaml

from core.pipeline.context import Segment
from core.pipeline.state import PipelineState


class RunManager:
    """Owns the on-disk layout of pipeline runs.

    Layout::

        <runs_root>/<run_id>/
            config.yaml                # snapshot of the run configuration
            state.json                 # progress / completed stages
            stage_01_<name>.json       # output of stage 1
            stage_02_<name>.json       # output of stage 2
            ...
    """

    CONFIG_FILENAME = "config.yaml"
    STATE_FILENAME = "state.json"

    def __init__(self, runs_root: Path):
        self.runs_root = runs_root

    def run_dir_for(self, run_id: str) -> Path:
        return self.runs_root / run_id

    def create_run(self, run_id: str) -> Path:
        run_dir = self.run_dir_for(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def save_config(self, run_dir: Path, config: Any) -> Path:
        if is_dataclass(config) and not isinstance(config, type):
            data = asdict(config)
        elif isinstance(config, dict):
            data = config
        else:
            raise TypeError(
                f"Unsupported config type: {type(config).__name__}"
            )

        path = run_dir / self.CONFIG_FILENAME
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return path

    def load_config(self, run_dir: Path) -> dict[str, Any]:
        path = run_dir / self.CONFIG_FILENAME
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def save_state(self, run_dir: Path, state: PipelineState) -> Path:
        path = run_dir / self.STATE_FILENAME
        path.write_text(
            json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def load_state(self, run_dir: Path) -> PipelineState:
        path = run_dir / self.STATE_FILENAME
        data = json.loads(path.read_text(encoding="utf-8"))
        return PipelineState.from_dict(data)

    def save_stage_result(
        self,
        run_dir: Path,
        stage_index: int,
        stage_name: str,
        segments: list[Segment],
    ) -> Path:
        path = run_dir / self._stage_filename(stage_index, stage_name)
        path.write_text(
            json.dumps(
                [s.to_dict() for s in segments],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def load_stage_result(
        self,
        run_dir: Path,
        stage_index: int,
        stage_name: str,
    ) -> list[Segment]:
        path = run_dir / self._stage_filename(stage_index, stage_name)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Segment(**item) for item in raw]

    @staticmethod
    def _stage_filename(stage_index: int, stage_name: str) -> str:
        return f"stage_{stage_index:02d}_{stage_name}.json"
