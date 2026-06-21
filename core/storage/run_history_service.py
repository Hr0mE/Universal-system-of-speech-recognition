"""Сервис истории запусков pipeline.

Читает метаданные из файлов runs/ без загрузки полных данных сегментов.
Используется экраном истории запусков в GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def _run_created_at(run_id: str) -> str:
    """Извлекает ISO-метку времени из run_id вида ``run_20240605_143022_abc123``.

    Args:
        run_id (str): Идентификатор запуска.

    Returns:
        str: ISO-строка времени или пустая строка при ошибке разбора.
    """
    parts = run_id.split("_")
    if len(parts) >= 3:
        try:
            dt = datetime.strptime(f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S")
            return dt.isoformat(timespec="seconds")
        except ValueError:
            pass
    return ""


def _load_yaml_safe(path: Path) -> dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _load_json_safe(path: Path) -> dict[str, Any]:
    import json
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@dataclass
class RunSummary:
    """Сводка запуска pipeline для отображения в истории запусков.

    Attributes:
        run_id (str): Идентификатор запуска.
        created_at (str): Дата создания в формате ISO 8601.
        status (str): Статус: ``completed``, ``failed``, ``stopped``, ``running`` или ``pending``.
        audio_name (str): Имя файла аудио (без пути).
        audio_path (str): Абсолютный путь к аудиофайлу.
        audio_duration (float): Длительность аудио в секундах.
        asr_model (str): Описание ASR-модели (например, ``"faster-whisper / tiny"``).
        diarization (bool): Использовалась ли диаризация.
        has_result (bool): Есть ли результат для открытия в ResultScreen.
        is_resumable (bool): Можно ли возобновить этот запуск.
        last_stage_index (int): 1-based индекс последней завершённой стадии (0 = ничего).
        completed_stages (list[str]): Имена завершённых стадий из state.json.
        stages (list[str]): Ожидаемые стадии пайплайна из config.yaml.
    """

    run_id: str
    created_at: str
    status: str
    audio_name: str
    audio_path: str
    audio_duration: float
    asr_model: str
    diarization: bool
    has_result: bool
    is_resumable: bool
    last_stage_index: int
    completed_stages: list[str]
    stages: list[str] = field(default_factory=list)


class RunHistoryService:
    """Сервис истории запусков: читает метаданные без загрузки сегментов."""

    def load_all(self, runs_dir: Path, *, limit: int | None = None) -> list[RunSummary]:
        """Загружает сводки запусков из директории.

        Args:
            runs_dir (Path): Корневая директория запусков (например, ``Path("runs")``).
            limit: Максимальное число записей. ``None`` — загрузить все.
                   При наличии лимита отбираются новейшие записи по имени папки
                   (timestamp закодирован в run_id) без чтения файлов.

        Returns:
            list[RunSummary]: Список сводок, отсортированных по дате (новые первыми).
        """
        if not runs_dir.exists():
            return []

        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]

        # Pre-sort by timestamp in dir name — no file reads needed
        run_dirs.sort(key=lambda d: _run_created_at(d.name), reverse=True)

        if limit is not None:
            run_dirs = run_dirs[:limit]

        summaries: list[RunSummary] = []
        for run_dir in run_dirs:
            summary = self._load_summary(run_dir)
            if summary:
                summaries.append(summary)

        summaries.sort(key=lambda s: s.created_at, reverse=True)
        return summaries

    def _load_summary(self, run_dir: Path) -> RunSummary | None:
        run_id = run_dir.name
        if not run_id.startswith("run_"):
            return None

        config = _load_yaml_safe(run_dir / "config.yaml")
        state = _load_json_safe(run_dir / "state.json")

        audio_path_str = config.get("audio_path", "")
        audio_name = Path(audio_path_str).name if audio_path_str else run_id
        audio_duration = float(config.get("audio_duration", 0.0))

        # stages list saved directly in config.yaml under "stages" key
        stages: list[str] = config.get("stages") or []

        models: dict = config.get("models", {}) or {}
        asr_name = ""
        asr_size = ""
        # New format: models = PipelineConfig.to_dict() → {"version": 1, "stages": [...]}
        if "stages" in models:
            for stage in models.get("stages", []):
                if isinstance(stage, dict) and stage.get("stage_id") == "asr":
                    asr_name = stage.get("model_name", "")
                    asr_size = (stage.get("params") or {}).get("model_size", "")
                    break
        else:
            # Old format: models = {"asr": {"name": ..., "params": {...}}, ...}
            asr_info = models.get("asr") or {}
            asr_name = asr_info.get("name", "")
            asr_size = (asr_info.get("params") or {}).get("model_size", "")
        asr_model = f"{asr_name} / {asr_size}" if asr_size else asr_name

        diarization = "diarization" in stages

        status = state.get("status", "pending")
        last_stage_index = int(state.get("last_stage_index", 0))
        completed_stages: list[str] = state.get("completed_stages", [])

        has_result = (run_dir / "result.json").exists() or bool(
            list(run_dir.glob("stage_*.json"))
        )
        is_resumable = (
            status not in ("completed", "running")
            and last_stage_index > 0
            and bool(audio_path_str)
        )

        return RunSummary(
            run_id=run_id,
            created_at=_run_created_at(run_id),
            status=status,
            audio_name=audio_name,
            audio_path=audio_path_str,
            audio_duration=audio_duration,
            asr_model=asr_model,
            diarization=diarization,
            has_result=has_result,
            is_resumable=is_resumable,
            last_stage_index=last_stage_index,
            completed_stages=completed_stages,
            stages=stages,
        )
