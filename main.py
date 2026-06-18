"""CLI-точка входа приложения транскрибации.

Запускает pipeline транскрибации в режиме командной строки.
Для GUI-режима используйте ``python gui.py``.

Примеры:
    Транскрибировать файл::

        python main.py audio.wav

    Возобновить прерванный запуск::

        python main.py --resume run_20240605_143022_abc123
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from core.api.transcribe import transcribe
from core.export import build_meeting_report, export_json, export_txt
from core.config.models_config import ModelsConfig
from core.events.bus import EventBus
from core.events.events import (
    ModelDownloadFinished,
    ModelDownloadStarted,
    PipelineFailed,
    PipelineFinished,
    PipelineStarted,
    StageFinished,
    StageSkipped,
    StageStarted,
)
from core.models import default_registry
from core.models.registry import ModelRegistry
from core.pipeline.context import PipelineContext
from core.pipeline.engine import PipelineEngine
from core.pipeline.registry import StageRegistry
from core.pipeline.stage import Stage
from core.pipeline.state import PipelineState
from core.storage.run_manager import RunManager
from plugins import setup_plugins
from core.pipeline.stages import (
    ASRStage,
    DiarizationStage,
    FixedWindowSegmentationStage,
    LanguageDetectionStage,
    MinDurationFilterStage,
)

DEFAULT_MODELS_CONFIG = Path("configs/models.yaml")


def build_stages(
    window_seconds: float,
    models_config: ModelsConfig,
    registry: ModelRegistry,
) -> list[Stage]:
    """Собирает список стадий pipeline из ModelsConfig (используется только CLI)."""
    asr = registry.create_asr(models_config.asr.name, **models_config.asr.params)
    lid = registry.create_language(
        models_config.language_detection.name,
        **models_config.language_detection.params,
    )
    lang_models = {}
    if models_config.asr_per_language:
        for lang, spec in models_config.asr_per_language.items():
            lang_models[lang] = registry.create_asr(spec.name, **spec.params)
    if models_config.diarization:
        diar = registry.create_diarization(
            models_config.diarization.name, **models_config.diarization.params
        )
        first_stages: list[Stage] = [DiarizationStage(model=diar), MinDurationFilterStage()]
    else:
        first_stages = [FixedWindowSegmentationStage(window_seconds=window_seconds)]
    return [
        *first_stages,
        LanguageDetectionStage(model=lid),
        ASRStage(model=asr, lang_models=lang_models or None),
    ]

logger = logging.getLogger("pipeline")


def attach_logging_subscriber(bus: EventBus) -> None:
    """Подписывает функции логирования на все события pipeline.

    Args:
        bus (EventBus): Шина событий для подписки.
    """
    def on_pipeline_started(event: PipelineStarted) -> None:
        logger.info(
            "Pipeline started: run_id=%s | audio=%s | stages=%d | resume_after=%d",
            event.run_id,
            event.audio_path,
            event.total_stages,
            event.resume_after,
        )

    def on_stage_started(event: StageStarted) -> None:
        logger.info("Stage start: [%d] %s", event.stage_index, event.stage_name)

    def on_stage_finished(event: StageFinished) -> None:
        logger.info(
            "Stage done:  [%d] %s (segments=%d) → %s",
            event.stage_index,
            event.stage_name,
            event.segments_count,
            event.artifact.name if event.artifact else "—",
        )

    def on_stage_skipped(event: StageSkipped) -> None:
        logger.info(
            "Stage skip:  [%d] %s (already completed)",
            event.stage_index,
            event.stage_name,
        )

    def on_pipeline_finished(event: PipelineFinished) -> None:
        logger.info(
            "Pipeline finished: run_id=%s | segments=%d",
            event.run_id,
            event.segments_count,
        )

    def on_pipeline_failed(event: PipelineFailed) -> None:
        logger.error(
            "Pipeline FAILED: run_id=%s | %s", event.run_id, event.error
        )

    def on_model_download_started(event: ModelDownloadStarted) -> None:
        logger.info(
            "Downloading model: %s (%s)...", event.model_name, event.repo_id
        )

    def on_model_download_finished(event: ModelDownloadFinished) -> None:
        logger.info("Model ready: %s", event.model_name)

    bus.subscribe(PipelineStarted, on_pipeline_started)
    bus.subscribe(StageStarted, on_stage_started)
    bus.subscribe(StageFinished, on_stage_finished)
    bus.subscribe(StageSkipped, on_stage_skipped)
    bus.subscribe(PipelineFinished, on_pipeline_finished)
    bus.subscribe(PipelineFailed, on_pipeline_failed)
    bus.subscribe(ModelDownloadStarted, on_model_download_started)
    bus.subscribe(ModelDownloadFinished, on_model_download_finished)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разбирает аргументы командной строки.

    Args:
        argv (list[str] | None): Список аргументов или ``None`` для sys.argv.

    Returns:
        argparse.Namespace: Разобранные аргументы.
    """
    parser = argparse.ArgumentParser(
        description="USSR diplom — local meeting transcription pipeline",
    )
    parser.add_argument(
        "audio",
        type=Path,
        nargs="?",
        help="Path to input WAV file (omit when using --resume)",
    )
    parser.add_argument(
        "--window",
        type=float,
        default=30.0,
        help="Segmentation window in seconds (default: 30)",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("runs"),
        help="Root directory for runs (default: ./runs)",
    )
    parser.add_argument(
        "--models-config",
        type=Path,
        default=DEFAULT_MODELS_CONFIG,
        help=f"Path to models YAML (default: {DEFAULT_MODELS_CONFIG})",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="RUN_ID",
        help="Resume a previous run from its last completed stage",
    )
    args = parser.parse_args(argv)

    if args.resume is None and args.audio is None:
        parser.error("audio path is required (or pass --resume RUN_ID)")

    return args


def prepare_resume_run(
    args: argparse.Namespace,
    run_manager: RunManager,
    registry: ModelRegistry,
) -> tuple[PipelineContext, list[Stage], PipelineState, list]:
    """Подготавливает данные для возобновления прерванного запуска.

    Args:
        args (argparse.Namespace): Разобранные аргументы CLI (использует ``args.resume``).
        run_manager (RunManager): Менеджер запусков для чтения конфигурации и состояния.
        registry (ModelRegistry): Реестр моделей для создания стадий.

    Returns:
        tuple: Кортеж ``(context, stages, state, initial_segments)``.

    Raises:
        FileNotFoundError: Если директория запуска или аудиофайл не существуют.
        ValueError: Если конфигурация неполна или список стадий изменился.
    """
    run_id = args.resume
    run_dir = run_manager.run_dir_for(run_id)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run not found: {run_dir}")

    cfg = run_manager.load_config(run_dir)
    state = run_manager.load_state(run_dir)

    audio_path = Path(cfg["audio_path"])
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file from run {run_id} no longer exists: {audio_path}"
        )
    duration = float(cfg["audio_duration"])
    window_seconds = float(cfg["window_seconds"])
    models_data = cfg.get("models") or {}
    if not models_data:
        raise ValueError(
            f"Run {run_id} has no models snapshot in config — cannot resume"
        )
    models_config = ModelsConfig.from_dict(models_data)
    stages = build_stages(window_seconds, models_config, registry)

    saved_stage_names = cfg.get("stages", [])
    rebuilt_stage_names = [s.name for s in stages]
    if saved_stage_names and saved_stage_names != rebuilt_stage_names:
        raise ValueError(
            f"Pipeline stage list changed since run {run_id} was created.\n"
            f"  Saved:   {saved_stage_names}\n"
            f"  Current: {rebuilt_stage_names}"
        )

    initial_segments: list = []
    if state.last_stage_index > 0:
        last_name = state.completed_stages[state.last_stage_index - 1]
        initial_segments = run_manager.load_stage_result(
            run_dir, state.last_stage_index, last_name
        )

    context = PipelineContext(
        run_id=run_id,
        audio_path=audio_path,
        run_dir=run_dir,
        audio_duration=duration,
    )
    logger.info(
        "Resuming run_id=%s | %d stage(s) done | %d segments loaded",
        run_id,
        state.last_stage_index,
        len(initial_segments),
    )
    return context, stages, state, initial_segments


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI-приложения.

    Args:
        argv (list[str] | None): Аргументы командной строки или ``None`` для sys.argv.

    Returns:
        int: Код выхода (0 — успех, 2 — ошибка).
    """
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    bus = EventBus()
    attach_logging_subscriber(bus)

    try:
        if args.resume:
            run_manager = RunManager(runs_root=args.runs_dir.expanduser().resolve())
            registry = default_registry()
            stage_registry = StageRegistry()
            setup_plugins(registry, stage_registry)
            if len(stage_registry) > 0:
                logger.warning(
                    "Plugin(s) registered %d stage(s) via StageRegistry %s, "
                    "but build_stages() does not yet consume StageRegistry — "
                    "these stages will be ignored until config-driven pipeline is implemented.",
                    len(stage_registry),
                    stage_registry.list(),
                )
            context, stages, state, initial_segments = prepare_resume_run(
                args, run_manager, registry
            )
            engine = PipelineEngine(stages=stages, run_manager=run_manager, event_bus=bus)
            engine.run(context, initial_segments=initial_segments, state=state)
            logger.info("Artifacts under %s", context.run_dir)
        else:
            result = transcribe(
                args.audio,
                runs_dir=args.runs_dir.expanduser().resolve(),
                window_seconds=args.window,
                event_bus=bus,
            )
            report = build_meeting_report(result)
            export_json(report, result.run_dir / "result.json")
            export_txt(report, result.run_dir / "result.txt")
            logger.info("Artifacts under %s", result.run_dir)
            logger.info("Exported: %s", result.run_dir / "result.json")
    except (FileNotFoundError, ValueError, KeyError) as exc:
        logger.error("%s", exc)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
