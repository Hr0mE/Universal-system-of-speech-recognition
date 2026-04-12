from __future__ import annotations

import argparse
import logging
import secrets
import sys
import wave
from datetime import datetime
from pathlib import Path

from core.pipeline.context import PipelineContext
from core.pipeline.engine import PipelineEngine
from core.pipeline.stages import DummyStage, FixedWindowSegmentationStage

logger = logging.getLogger("pipeline")


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="USSR diplom — local meeting transcription pipeline",
    )
    parser.add_argument("audio", type=Path, help="Path to input WAV file")
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    audio_path: Path = args.audio.expanduser().resolve()
    if not audio_path.exists():
        logger.error("Audio file not found: %s", audio_path)
        return 2
    if audio_path.suffix.lower() != ".wav":
        logger.error(
            "Only .wav is supported at this stage (got: %s)", audio_path.suffix
        )
        return 2

    duration = read_wav_duration(audio_path)
    run_id = generate_run_id()
    run_dir = args.runs_dir.expanduser().resolve() / run_id

    context = PipelineContext(
        run_id=run_id,
        audio_path=audio_path,
        run_dir=run_dir,
        audio_duration=duration,
    )
    logger.info(
        "run_id=%s | audio=%s | duration=%.2fs", run_id, audio_path, duration
    )

    engine = PipelineEngine(
        stages=[
            DummyStage(),
            FixedWindowSegmentationStage(window_seconds=args.window),
        ]
    )

    segments = engine.run(context)
    logger.info(
        "Pipeline complete. %d segments saved under %s", len(segments), run_dir
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
