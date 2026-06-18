"""Pipeline stage compatibility checker.

Pure function `check_compatibility` scans an ordered list of StageConfig
objects and returns issues for enabled stages whose `requires` tags are not
yet available in the stream at that point.

Non-cascading: each stage's `produces` is added to the available set
regardless of whether that stage itself has unmet requirements — so one
broken stage doesn't trigger a cascade of false warnings downstream.

Stages without a descriptor (unknown stage_id) are treated as always
compatible (no requirements, no contributions).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config.pipeline_config import StageConfig
from core.pipeline.stage import get_stage_descriptor

TAG_LABELS: dict[str, str] = {
    "segments":        "Сегменты аудио",
    "speaker_labels":  "Метки говорящих (диаризация)",
    "language_labels": "Метки языков (определение языка)",
    "transcript":      "Транскрипция (ASR)",
}


@dataclass(frozen=True)
class StageIssue:
    """Indicates that an enabled stage has unmet stream requirements.

    Attributes:
        stage_id: The stage that is incompatible.
        missing_tags: Tags required by the stage that are not yet available.
    """

    stage_id: str
    missing_tags: frozenset[str]


@dataclass(frozen=True)
class StagePortState:
    """Per-stage port snapshot: what the stage needs, adds, and what's in the stream.

    Attributes:
        stage_id: The stage this state describes.
        issue: Non-None when the stage is enabled and has unmet requirements.
        requires: Tags required by this stage.
        produces: Tags this stage declares it produces.
        available_before: Stream tags available immediately before this stage runs.
        available_after: Stream tags available after this stage (= before + produces
            if enabled, = before if disabled — non-cascading rule applies).
    """

    stage_id: str
    issue: StageIssue | None
    requires: frozenset[str]
    produces: frozenset[str]
    available_before: frozenset[str]
    available_after: frozenset[str]


def check_compatibility(stages: list[StageConfig]) -> dict[str, StageIssue]:
    """Return {stage_id: StageIssue} for enabled stages with unmet requirements.

    Args:
        stages: Ordered list of stage configs (execution order matters).

    Returns:
        Mapping of stage_id to StageIssue for each incompatible enabled stage.
        Disabled stages and stages without a descriptor are never included.
    """
    available: set[str] = set()
    issues: dict[str, StageIssue] = {}

    for stage_cfg in stages:
        descriptor = get_stage_descriptor(stage_cfg.stage_id)

        if descriptor is None:
            continue

        if stage_cfg.enabled:
            missing = descriptor.requires - available
            if missing:
                issues[stage_cfg.stage_id] = StageIssue(
                    stage_id=stage_cfg.stage_id,
                    missing_tags=frozenset(missing),
                )
            # Non-cascading: add produces regardless of own compatibility
            available |= descriptor.produces
        # Disabled stages contribute nothing

    return issues


def compute_port_states(stages: list[StageConfig]) -> dict[str, StagePortState]:
    """Return a per-stage port snapshot for every stage that has a descriptor.

    Disabled stages appear in the result but contribute nothing to the stream
    (available_after == available_before for them).  This lets the UI show
    "what this stage would need/provide if you enabled it."
    """
    issues = check_compatibility(stages)
    available: set[str] = set()
    result: dict[str, StagePortState] = {}

    for stage_cfg in stages:
        descriptor = get_stage_descriptor(stage_cfg.stage_id)
        if descriptor is None:
            continue

        available_before = frozenset(available)

        if stage_cfg.enabled:
            available |= descriptor.produces

        result[stage_cfg.stage_id] = StagePortState(
            stage_id=stage_cfg.stage_id,
            issue=issues.get(stage_cfg.stage_id),
            requires=descriptor.requires,
            produces=descriptor.produces,
            available_before=available_before,
            available_after=frozenset(available),
        )

    return result
