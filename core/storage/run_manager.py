"""Менеджер хранилища запусков pipeline.

Владеет файловой структурой директорий запусков и предоставляет API для
сохранения/загрузки конфигурации, состояния и результатов стадий.
"""

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
        """Инициализирует менеджер с указанием корневой директории запусков.

        Args:
            runs_root (Path): Корневая директория (например, ``Path("runs")``).
        """
        self.runs_root = runs_root

    def run_dir_for(self, run_id: str) -> Path:
        """Возвращает путь к директории конкретного запуска.

        Args:
            run_id (str): Идентификатор запуска.

        Returns:
            Path: Путь ``runs_root / run_id``.
        """
        return self.runs_root / run_id

    def create_run(self, run_id: str) -> Path:
        """Создаёт директорию для нового запуска.

        Args:
            run_id (str): Идентификатор запуска.

        Returns:
            Path: Путь к созданной директории.
        """
        run_dir = self.run_dir_for(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def save_config(self, run_dir: Path, config: Any) -> Path:
        """Сохраняет конфигурацию запуска в ``config.yaml``.

        Args:
            run_dir (Path): Директория запуска.
            config (Any): Dataclass или словарь с конфигурацией.

        Returns:
            Path: Путь к сохранённому файлу.

        Raises:
            TypeError: Если тип конфигурации не поддерживается.
        """
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
        """Загружает конфигурацию запуска из ``config.yaml``.

        Args:
            run_dir (Path): Директория запуска.

        Returns:
            dict[str, Any]: Словарь с конфигурацией.
        """
        path = run_dir / self.CONFIG_FILENAME
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def save_state(self, run_dir: Path, state: PipelineState) -> Path:
        """Сохраняет состояние pipeline в ``state.json``.

        Args:
            run_dir (Path): Директория запуска.
            state (PipelineState): Текущее состояние.

        Returns:
            Path: Путь к сохранённому файлу.
        """
        path = run_dir / self.STATE_FILENAME
        path.write_text(
            json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def load_state(self, run_dir: Path) -> PipelineState:
        """Загружает состояние pipeline из ``state.json``.

        Args:
            run_dir (Path): Директория запуска.

        Returns:
            PipelineState: Восстановленное состояние.
        """
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
        """Сохраняет результат стадии в JSON-файл ``stage_NN_<name>.json``.

        Args:
            run_dir (Path): Директория запуска.
            stage_index (int): 1-based индекс стадии.
            stage_name (str): Имя стадии.
            segments (list[Segment]): Список сегментов для сохранения.

        Returns:
            Path: Путь к сохранённому файлу.
        """
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
        """Загружает результат стадии из ``stage_NN_<name>.json``.

        Args:
            run_dir (Path): Директория запуска.
            stage_index (int): 1-based индекс стадии.
            stage_name (str): Имя стадии.

        Returns:
            list[Segment]: Список восстановленных сегментов.
        """
        path = run_dir / self._stage_filename(stage_index, stage_name)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Segment(**item) for item in raw]

    @staticmethod
    def _stage_filename(stage_index: int, stage_name: str) -> str:
        """Формирует имя файла чекпоинта стадии.

        Args:
            stage_index (int): 1-based индекс стадии.
            stage_name (str): Имя стадии.

        Returns:
            str: Строка вида ``"stage_01_segmentation.json"``.
        """
        return f"stage_{stage_index:02d}_{stage_name}.json"
