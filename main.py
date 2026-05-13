from __future__ import annotations

import argparse
import logging
import secrets
import sys
import wave
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from core.config.config import RunConfig
from core.config.models_config import ModelsConfig, load_models_config
from core.events.bus import EventBus
from core.events.events import (
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
from core.pipeline.stage import Stage
from core.pipeline.stages import (
    ASRStage,
    DiarizationStage,
    FixedWindowSegmentationStage,
    LanguageDetectionStage,
    MinDurationFilterStage,
)
from core.pipeline.state import PipelineState
from core.storage.run_manager import RunManager

DEFAULT_MODELS_CONFIG = Path("configs/models.yaml")

logger = logging.getLogger("pipeline")


def attach_logging_subscriber(bus: EventBus) -> None:
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

    bus.subscribe(PipelineStarted, on_pipeline_started)
    bus.subscribe(StageStarted, on_stage_started)
    bus.subscribe(StageFinished, on_stage_finished)
    bus.subscribe(StageSkipped, on_stage_skipped)
    bus.subscribe(PipelineFinished, on_pipeline_finished)
    bus.subscribe(PipelineFailed, on_pipeline_failed)


def generate_run_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)
    return f"run_{timestamp}_{suffix}"


def read_wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate == 0:
            raise ValueError(f"Invalid sample rate in {path}")
        return frames / float(rate)


def build_stages(
    window_seconds: float,
    models_config: ModelsConfig,
    registry: ModelRegistry,
) -> list[Stage]:
    asr = registry.create_asr(
        models_config.asr.name, **models_config.asr.params
    )
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
        first_stages: list[Stage] = [
            DiarizationStage(model=diar),
            MinDurationFilterStage(),
        ]
    else:
        first_stages = [FixedWindowSegmentationStage(window_seconds=window_seconds)]

    return [
        *first_stages,
        LanguageDetectionStage(model=lid),
        ASRStage(model=asr, lang_models=lang_models or None),
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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


def prepare_fresh_run(
    args: argparse.Namespace,
    run_manager: RunManager,
    registry: ModelRegistry,
) -> tuple[PipelineContext, list[Stage], PipelineState | None, list | None]:
    audio_path: Path = args.audio.expanduser().resolve()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if audio_path.suffix.lower() != ".wav":
        raise ValueError(
            f"Only .wav is supported at this stage (got: {audio_path.suffix})"
        )

    models_config_path = args.models_config.expanduser().resolve()
    if not models_config_path.exists():
        raise FileNotFoundError(
            f"Models config not found: {models_config_path}"
        )
    models_config = load_models_config(models_config_path)

    duration = read_wav_duration(audio_path)
    run_id = generate_run_id()
    stages = build_stages(args.window, models_config, registry)

    config = RunConfig(
        audio_path=str(audio_path),
        audio_duration=duration,
        window_seconds=args.window,
        stages=[s.name for s in stages],
        models=models_config.to_dict(),
    )

    run_dir = run_manager.create_run(run_id)
    config_path = run_manager.save_config(run_dir, config)
    logger.info("Config snapshot → %s", config_path)

    context = PipelineContext(
        run_id=run_id,
        audio_path=audio_path,
        run_dir=run_dir,
        audio_duration=duration,
    )
    logger.info(
        "run_id=%s | audio=%s | duration=%.2fs",
        run_id,
        audio_path,
        duration,
    )
    return context, stages, None, None


def prepare_resume_run(
    args: argparse.Namespace,
    run_manager: RunManager,
    registry: ModelRegistry,
) -> tuple[PipelineContext, list[Stage], PipelineState, list]:
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
        last_name = state.completed_stages[-1]
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
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    run_manager = RunManager(runs_root=args.runs_dir.expanduser().resolve())
    registry = default_registry()

    try:
        if args.resume:
            context, stages, state, initial_segments = prepare_resume_run(
                args, run_manager, registry
            )
        else:
            context, stages, state, initial_segments = prepare_fresh_run(
                args, run_manager, registry
            )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        logger.error("%s", exc)
        return 2

    bus = EventBus()
    attach_logging_subscriber(bus)

    engine = PipelineEngine(
        stages=stages, run_manager=run_manager, event_bus=bus
    )
    engine.run(context, initial_segments=initial_segments, state=state)

    logger.info("Artifacts under %s", context.run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
