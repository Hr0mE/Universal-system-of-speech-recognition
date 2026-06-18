"""Высокоуровневый API транскрибации аудио.

Предоставляет функции :func:`transcribe` и :func:`resume_transcription`,
скрывающие детали pipeline за единым вызовом.  Результат возвращается
в виде датакласса :class:`TranscriptionResult`.
"""

from __future__ import annotations

import json
import secrets
import threading
import wave
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.config.pipeline_config import PipelineConfig, default_pipeline_config
from core.events.bus import EventBus
from core.models import default_registry
from core.pipeline.context import PipelineCancelled, PipelineContext, Segment

__all__ = [
    "TranscriptionResult",
    "transcribe",
    "resume_transcription",
    "find_resumable_run",
    "load_run_result",
    "save_run_result",
    "PipelineCancelled",
]
from core.pipeline.engine import PipelineEngine
from core.pipeline.registry import StageRegistry
from core.pipeline.stage import Stage
from core.pipeline.stages import (
    ASRStage,
    DiarizationStage,
    FixedWindowSegmentationStage,
    LanguageDetectionStage,
    MinDurationFilterStage,
)
from core.storage.run_manager import RunManager
from plugins import setup_plugins


@dataclass
class TranscriptionResult:
    """Результат транскрибации одного аудиофайла.

    Attributes:
        segments (list[Segment]): Список транскрибированных сегментов
            с текстом, языком и идентификатором говорящего.
        run_id (str): Уникальный идентификатор запуска pipeline.
        run_dir (Path): Путь к директории с артефактами запуска.
        audio_path (Path): Путь к исходному аудиофайлу.
        duration_s (float): Длительность аудио в секундах.
    """

    segments: list[Segment]
    run_id: str
    run_dir: Path
    audio_path: Path = field(default_factory=Path)
    duration_s: float = 0.0


def generate_run_id() -> str:
    """Генерирует уникальный идентификатор запуска pipeline.

    Returns:
        str: Строка вида ``run_YYYYMMDD_HHMMSS_<hex6>``.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)
    return f"run_{timestamp}_{suffix}"


def read_wav_duration(path: Path) -> float:
    """Возвращает длительность WAV-файла в секундах.

    Args:
        path (Path): Путь к WAV-файлу.

    Returns:
        float: Длительность в секундах.

    Raises:
        ValueError: Если файл содержит нулевую частоту дискретизации.
    """
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate == 0:
            raise ValueError(f"Invalid sample rate in {path}")
        return frames / float(rate)


def build_stages_from_pipeline(
    pipeline_config: PipelineConfig,
    registry,
) -> list[Stage]:
    """Строит стадии pipeline из :class:`PipelineConfig`, уважая порядок и enabled.

    Включает только те этапы, у которых ``enabled=True``.
    """
    import logging as _log

    stages: list[Stage] = []
    for stage_cfg in pipeline_config.stages:
        if not stage_cfg.enabled:
            continue
        sid = stage_cfg.stage_id
        p = stage_cfg.params
        if sid == "segmentation":
            stages.append(FixedWindowSegmentationStage(
                window_seconds=float(p.get("window_seconds", 30.0))
            ))
        elif sid == "min_duration_filter":
            stages.append(MinDurationFilterStage(
                min_seconds=float(p.get("min_seconds", 0.3))
            ))
        elif sid == "diarization":
            diar = registry.create_diarization(stage_cfg.model_name, **p)
            stages.append(DiarizationStage(model=diar))
        elif sid == "language_detection":
            lid = registry.create_language(stage_cfg.model_name, **p)
            stages.append(LanguageDetectionStage(model=lid))
        elif sid == "asr":
            asr_model = registry.create_asr(stage_cfg.model_name, **p)
            lang_models = {}
            for lang, spec in stage_cfg.lang_model_map.items():
                mn = spec.get("model_name", stage_cfg.model_name)
                lp = {k: v for k, v in spec.items() if k != "model_name"}
                lang_models[lang] = registry.create_asr(mn, **lp)
            stages.append(ASRStage(model=asr_model, lang_models=lang_models or None))
        else:
            _log.getLogger(__name__).warning(
                "build_stages_from_pipeline: неизвестный stage_id %r — пропускаем", sid
            )
    return stages


def transcribe(
    audio_path: str | Path,
    models_config: PipelineConfig | None = None,
    *,
    runs_dir: Path = Path("runs"),
    window_seconds: float = 30.0,
    event_bus: EventBus | None = None,
    stop_requested: threading.Event | None = None,
) -> TranscriptionResult:
    """Транскрибирует WAV-файл и возвращает сегменты с текстом, языком и спикером.

    Args:
        audio_path (str | Path): Путь к WAV-файлу.
        models_config (PipelineConfig | None): Конфигурация пайплайна или ``None``
            (используется :func:`default_pipeline_config`).
        runs_dir (Path): Директория для хранения артефактов запуска.
        window_seconds (float): Длина окна сегментации (передаётся для совместимости,
            фактически берётся из ``PipelineConfig``).
        event_bus (EventBus | None): Опциональная шина событий.
        stop_requested (threading.Event | None): Событие для отмены pipeline.

    Returns:
        TranscriptionResult: Результат с сегментами, run_id и метаданными.

    Raises:
        FileNotFoundError: Если аудиофайл не найден.
        ValueError: Если файл не является WAV-форматом.
        TypeError: Если ``models_config`` не является ``PipelineConfig`` или ``None``.
    """
    audio_path = Path(audio_path).expanduser().resolve()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if audio_path.suffix.lower() != ".wav":
        raise ValueError(
            f"Only .wav is supported at this stage (got: {audio_path.suffix})"
        )

    if isinstance(models_config, PipelineConfig):
        pipeline_cfg = models_config
    elif models_config is None:
        pipeline_cfg = default_pipeline_config()
    else:
        raise TypeError(
            f"models_config must be PipelineConfig or None, got {type(models_config).__name__}"
        )

    duration = read_wav_duration(audio_path)
    run_id = generate_run_id()

    registry = default_registry()
    setup_plugins(registry, StageRegistry())

    stages = build_stages_from_pipeline(pipeline_cfg, registry)

    run_manager = RunManager(runs_root=runs_dir)
    run_dir = run_manager.create_run(run_id)

    from core.config.config import RunConfig

    config = RunConfig(
        audio_path=str(audio_path),
        audio_duration=duration,
        window_seconds=window_seconds,
        stages=[s.name for s in stages],
        models=pipeline_cfg.to_dict(),
    )
    run_manager.save_config(run_dir, config)

    context = PipelineContext(
        run_id=run_id,
        audio_path=audio_path,
        run_dir=run_dir,
        audio_duration=duration,
        stop_requested=stop_requested or threading.Event(),
    )

    engine = PipelineEngine(
        stages=stages,
        run_manager=run_manager,
        event_bus=event_bus,
    )
    segments = engine.run(context)

    result_path = run_dir / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "audio_path": str(audio_path),
                "duration_s": duration,
                "segments": [s.to_dict() for s in segments],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return TranscriptionResult(
        segments=segments,
        run_id=run_id,
        run_dir=run_dir,
        audio_path=audio_path,
        duration_s=duration,
    )


def find_resumable_run(runs_dir: Path, audio_path: str) -> Path | None:
    """Возвращает директорию последнего прерванного запуска для указанного аудиофайла.

    Ищет запуски с хотя бы одной завершённой стадией, которые не имеют статуса
    ``completed``.

    Args:
        runs_dir (Path): Корневая директория со всеми запусками.
        audio_path (str): Строковый путь к аудиофайлу (сравнивается с config.yaml).

    Returns:
        Path | None: Последняя по имени директория прерванного запуска или ``None``.
    """
    if not runs_dir.exists():
        return None
    import yaml as _yaml
    candidates: list[Path] = []
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        config_file = run_dir / "config.yaml"
        state_file  = run_dir / "state.json"
        if not (config_file.exists() and state_file.exists()):
            continue
        try:
            cfg        = _yaml.safe_load(config_file.read_text(encoding="utf-8"))
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            if (
                cfg.get("audio_path") == audio_path
                and state_data.get("status") != "completed"
                and state_data.get("last_stage_index", 0) > 0
            ):
                candidates.append(run_dir)
        except Exception:
            pass
    return sorted(candidates)[-1] if candidates else None


def resume_transcription(
    run_dir: Path,
    models_config: PipelineConfig | None = None,
    *,
    event_bus: EventBus | None = None,
    stop_requested: threading.Event | None = None,
) -> TranscriptionResult:
    """Возобновляет прерванный запуск с последней завершённой стадии.

    Args:
        run_dir (Path): Директория существующего запуска с state.json и config.yaml.
        models_config (PipelineConfig | None): Конфигурация пайплайна или ``None``
            (используется :func:`default_pipeline_config`).
        event_bus (EventBus | None): Опциональная шина событий.
        stop_requested (threading.Event | None): Событие для отмены из другого потока.

    Returns:
        TranscriptionResult: Результат с полным набором сегментов (включая ранее
            вычисленные стадии).

    Raises:
        TypeError: Если ``models_config`` не является ``PipelineConfig`` или ``None``.
    """
    run_manager = RunManager(runs_root=run_dir.parent)
    state       = run_manager.load_state(run_dir)
    config_data = run_manager.load_config(run_dir)
    audio_path  = Path(config_data["audio_path"])
    duration    = float(config_data.get("audio_duration", 0.0))

    if state.last_stage_index > 0 and state.completed_stages:
        segments = run_manager.load_stage_result(
            run_dir, state.last_stage_index, state.completed_stages[-1]
        )
    else:
        segments = []

    if isinstance(models_config, PipelineConfig):
        pipeline_cfg = models_config
    elif models_config is None:
        pipeline_cfg = default_pipeline_config()
    else:
        raise TypeError(
            f"models_config must be PipelineConfig or None, got {type(models_config).__name__}"
        )

    registry = default_registry()
    setup_plugins(registry, StageRegistry())
    stages = build_stages_from_pipeline(pipeline_cfg, registry)
    context = PipelineContext(
        run_id=run_dir.name,
        audio_path=audio_path,
        run_dir=run_dir,
        audio_duration=duration,
        stop_requested=stop_requested or threading.Event(),
    )
    engine       = PipelineEngine(stages=stages, run_manager=run_manager, event_bus=event_bus)
    new_segments = engine.run(context, initial_segments=segments, state=state)

    result_path = run_dir / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "run_id":      run_dir.name,
                "audio_path":  str(audio_path),
                "duration_s":  duration,
                "segments":    [s.to_dict() for s in new_segments],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return TranscriptionResult(
        segments=new_segments,
        run_id=run_dir.name,
        run_dir=run_dir,
        audio_path=audio_path,
        duration_s=duration,
    )


def save_run_result(result: TranscriptionResult) -> None:
    """Перезаписывает result.json обновлёнными данными результата.

    Args:
        result (TranscriptionResult): Результат транскрибации (возможно, отредактированный).
    """
    data = {
        "run_id": result.run_id,
        "audio_path": str(result.audio_path),
        "duration_s": result.duration_s,
        "segments": [s.to_dict() for s in result.segments],
    }
    path = result.run_dir / "result.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_run_result(run_dir: Path) -> TranscriptionResult | None:
    """Восстанавливает :class:`TranscriptionResult` из директории запуска.

    Сначала читает ``result.json``; при его отсутствии делает откат к последнему
    файлу ``stage_*.json``, что позволяет открыть запуски, созданные до введения
    сохранения result.json.

    Args:
        run_dir (Path): Директория запуска с артефактами.

    Returns:
        TranscriptionResult | None: Восстановленный результат или ``None``, если
            данные отсутствуют или повреждены.
    """
    from core.pipeline.context import Segment
    import yaml as _yaml

    result_path = run_dir / "result.json"
    if result_path.exists():
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
            segments = [Segment(**s) for s in data["segments"]]
            return TranscriptionResult(
                segments=segments,
                run_id=data["run_id"],
                run_dir=run_dir,
                audio_path=Path(data["audio_path"]),
                duration_s=float(data["duration_s"]),
            )
        except Exception:
            pass

    # Fallback: reconstruct from the last stage file (ASR output)
    stage_files = sorted(run_dir.glob("stage_*.json"))
    if not stage_files:
        return None
    try:
        raw = json.loads(stage_files[-1].read_text(encoding="utf-8"))
        segments = [Segment(**s) for s in raw]

        # Best-effort: read audio metadata from config.yaml
        audio_path = run_dir
        duration_s = 0.0
        config_path = run_dir / "config.yaml"
        if config_path.exists():
            cfg = _yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            audio_path = Path(cfg.get("audio_path", str(run_dir)))
            duration_s = float(cfg.get("audio_duration", 0.0))

        return TranscriptionResult(
            segments=segments,
            run_id=run_dir.name,
            run_dir=run_dir,
            audio_path=audio_path,
            duration_s=duration_s,
        )
    except Exception:
        return None
