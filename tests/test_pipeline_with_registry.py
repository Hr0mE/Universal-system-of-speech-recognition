from __future__ import annotations

from pathlib import Path

from core.config.models_config import ModelsConfig, load_models_config
from core.models import default_registry
from core.models.base import ASRModel
from core.models.registry import ModelRegistry
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.engine import PipelineEngine
from core.pipeline.stages import (
    ASRStage,
    FixedWindowSegmentationStage,
    LanguageDetectionStage,
)


def _build_stages(window_seconds, models_config: ModelsConfig, registry: ModelRegistry):
    asr = registry.create_asr(
        models_config.asr.name, **models_config.asr.params
    )
    lid = registry.create_language(
        models_config.language_detection.name,
        **models_config.language_detection.params,
    )
    return [
        FixedWindowSegmentationStage(window_seconds=window_seconds),
        LanguageDetectionStage(model=lid),
        ASRStage(model=asr),
    ]


def test_pipeline_runs_end_to_end_via_registry(run_manager, context, tmp_path: Path):
    yaml_path = tmp_path / "models.yaml"
    yaml_path.write_text(
        "asr: dummy\n"
        "language_detection:\n"
        "  name: dummy\n"
        "  params:\n"
        "    language: ru\n",
        encoding="utf-8",
    )
    cfg = load_models_config(yaml_path)
    registry = default_registry()

    stages = _build_stages(20.0, cfg, registry)
    engine = PipelineEngine(stages=stages, run_manager=run_manager)
    result = engine.run(context)

    assert len(result) == 3
    assert all(s.language == "ru" for s in result)
    assert all(s.text and s.text.startswith("[dummy asr") for s in result)


def test_swapping_model_in_yaml_changes_pipeline_output(
    run_manager, context, tmp_path: Path
):
    """Stage 6 acceptance: swap model = edit YAML; pipeline code is untouched."""

    class ShoutASR(ASRModel):
        name = "shout"

        def transcribe(self, segment: Segment, context: PipelineContext) -> str:
            return "HELLO"

    registry = default_registry()
    registry.register_asr("shout", ShoutASR)

    yaml_dummy = tmp_path / "dummy.yaml"
    yaml_dummy.write_text(
        "asr: dummy\nlanguage_detection: dummy\n", encoding="utf-8"
    )
    yaml_shout = tmp_path / "shout.yaml"
    yaml_shout.write_text(
        "asr: shout\nlanguage_detection: dummy\n", encoding="utf-8"
    )

    def run_with(path: Path, ctx: PipelineContext):
        cfg = load_models_config(path)
        stages = _build_stages(30.0, cfg, registry)
        return PipelineEngine(stages=stages, run_manager=run_manager).run(ctx)

    ctx_a = PipelineContext(
        run_id="run_a",
        audio_path=context.audio_path,
        run_dir=run_manager.create_run("run_a"),
        audio_duration=context.audio_duration,
    )
    ctx_b = PipelineContext(
        run_id="run_b",
        audio_path=context.audio_path,
        run_dir=run_manager.create_run("run_b"),
        audio_duration=context.audio_duration,
    )

    result_dummy = run_with(yaml_dummy, ctx_a)
    result_shout = run_with(yaml_shout, ctx_b)

    assert all(s.text and s.text.startswith("[dummy") for s in result_dummy)
    assert all(s.text == "HELLO" for s in result_shout)


def test_unknown_model_name_in_config_raises_keyerror(tmp_path: Path):
    yaml_path = tmp_path / "models.yaml"
    yaml_path.write_text(
        "asr: nonexistent\nlanguage_detection: dummy\n", encoding="utf-8"
    )
    cfg = load_models_config(yaml_path)
    registry = default_registry()

    import pytest

    with pytest.raises(KeyError, match="nonexistent"):
        registry.create_asr(cfg.asr.name, **cfg.asr.params)
