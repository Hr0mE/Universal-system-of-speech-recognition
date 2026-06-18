"""Tests for pipeline stage compatibility checker.

Spec criteria covered:
  AC-1  check_compatibility([]) returns {}
  AC-2  enabled stage with unmet requires → in result with correct missing_tags
  AC-3  enabled stage with prior enabled producer → NOT in result
  AC-4  disabled stage does not contribute produces
  AC-5  stage with requires={} never in result
  AC-6  StageIssue.missing_tags contains exactly the unavailable tags
  EC-1  unknown stage_id (no descriptor) → always compatible
  EC-2  all stages disabled → {}
  EC-3  incompatible stage still contributes its produces (no cascade)
  ERR-1 disabled stage that would be incompatible → NOT in result
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.config.pipeline_config import StageConfig
from core.pipeline.compatibility import StageIssue, check_compatibility
from core.pipeline.port_types import SEGMENTS, SPEAKER_LABELS, TRANSCRIPT
from core.pipeline.stage import StageDescriptor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(stage_id: str, enabled: bool = True) -> StageConfig:
    return StageConfig(stage_id=stage_id, enabled=enabled, model_name="")


def _desc(stage_id: str, requires: set[str], produces: set[str]) -> StageDescriptor:
    return StageDescriptor(
        stage_id=stage_id,
        display_name=stage_id,
        requires=frozenset(requires),
        produces=frozenset(produces),
    )


def _patch_descriptors(mapping: dict[str, StageDescriptor]):
    """Context manager: replaces get_stage_descriptor for the duration of the test."""
    return patch(
        "core.pipeline.compatibility.get_stage_descriptor",
        side_effect=lambda sid: mapping.get(sid),
    )


# ---------------------------------------------------------------------------
# AC-1: empty input
# ---------------------------------------------------------------------------

def test_ac1_empty_list_returns_empty_dict():
    result = check_compatibility([])
    assert result == {}


# ---------------------------------------------------------------------------
# AC-2: enabled stage with unmet requires → issue emitted
# ---------------------------------------------------------------------------

def test_ac2_unmet_requires_yields_issue():
    cfg = _cfg("asr")
    desc = _desc("asr", requires={SEGMENTS}, produces={TRANSCRIPT})
    with _patch_descriptors({"asr": desc}):
        result = check_compatibility([cfg])
    assert "asr" in result
    assert isinstance(result["asr"], StageIssue)
    assert result["asr"].stage_id == "asr"
    assert SEGMENTS in result["asr"].missing_tags


# ---------------------------------------------------------------------------
# AC-3: prior enabled producer satisfies requires → no issue
# ---------------------------------------------------------------------------

def test_ac3_prior_producer_satisfies_requires():
    seg_cfg = _cfg("segmentation")
    asr_cfg = _cfg("asr")
    seg_desc = _desc("segmentation", requires=set(), produces={SEGMENTS})
    asr_desc = _desc("asr", requires={SEGMENTS}, produces={TRANSCRIPT})
    with _patch_descriptors({"segmentation": seg_desc, "asr": asr_desc}):
        result = check_compatibility([seg_cfg, asr_cfg])
    assert "asr" not in result
    assert "segmentation" not in result


# ---------------------------------------------------------------------------
# AC-4: disabled stage does not contribute produces
# ---------------------------------------------------------------------------

def test_ac4_disabled_stage_does_not_contribute_produces():
    seg_cfg = _cfg("segmentation", enabled=False)
    asr_cfg = _cfg("asr", enabled=True)
    seg_desc = _desc("segmentation", requires=set(), produces={SEGMENTS})
    asr_desc = _desc("asr", requires={SEGMENTS}, produces={TRANSCRIPT})
    with _patch_descriptors({"segmentation": seg_desc, "asr": asr_desc}):
        result = check_compatibility([seg_cfg, asr_cfg])
    assert "asr" in result, "asr should fail because segmentation is disabled"


# ---------------------------------------------------------------------------
# AC-5: stage with empty requires never in result
# ---------------------------------------------------------------------------

def test_ac5_empty_requires_never_in_result():
    cfg = _cfg("segmentation")
    desc = _desc("segmentation", requires=set(), produces={SEGMENTS})
    with _patch_descriptors({"segmentation": desc}):
        result = check_compatibility([cfg])
    assert "segmentation" not in result


# ---------------------------------------------------------------------------
# AC-6: missing_tags contains exactly the unavailable tags
# ---------------------------------------------------------------------------

def test_ac6_missing_tags_exact():
    cfg = _cfg("diarization")
    desc = _desc("diarization", requires={SEGMENTS, SPEAKER_LABELS}, produces={SEGMENTS})
    with _patch_descriptors({"diarization": desc}):
        result = check_compatibility([cfg])
    assert "diarization" in result
    assert result["diarization"].missing_tags == frozenset({SEGMENTS, SPEAKER_LABELS})


def test_ac6_partial_missing_tags():
    seg_cfg = _cfg("segmentation")
    dia_cfg = _cfg("diarization")
    seg_desc = _desc("segmentation", requires=set(), produces={SEGMENTS})
    # diarization requires SEGMENTS (available) + SPEAKER_LABELS (not available)
    dia_desc = _desc("diarization", requires={SEGMENTS, SPEAKER_LABELS}, produces={SEGMENTS})
    with _patch_descriptors({"segmentation": seg_desc, "diarization": dia_desc}):
        result = check_compatibility([seg_cfg, dia_cfg])
    assert "diarization" in result
    assert result["diarization"].missing_tags == frozenset({SPEAKER_LABELS})


# ---------------------------------------------------------------------------
# EC-1: unknown stage_id → always compatible (no descriptor = no requirements)
# ---------------------------------------------------------------------------

def test_ec1_unknown_stage_always_compatible():
    cfg = _cfg("unknown_stage")
    with _patch_descriptors({}):
        result = check_compatibility([cfg])
    assert "unknown_stage" not in result


# ---------------------------------------------------------------------------
# EC-2: all stages disabled → {}
# ---------------------------------------------------------------------------

def test_ec2_all_disabled_returns_empty():
    cfgs = [_cfg("asr", enabled=False), _cfg("segmentation", enabled=False)]
    asr_desc = _desc("asr", requires={SEGMENTS}, produces={TRANSCRIPT})
    seg_desc = _desc("segmentation", requires=set(), produces={SEGMENTS})
    with _patch_descriptors({"asr": asr_desc, "segmentation": seg_desc}):
        result = check_compatibility(cfgs)
    assert result == {}


# ---------------------------------------------------------------------------
# EC-3: incompatible stage still contributes its produces (no cascade)
# ---------------------------------------------------------------------------

def test_ec3_incompatible_stage_contributes_produces():
    # Stage A requires X (not available) → issue. Produces Y.
    # Stage B requires Y → should NOT get an issue (A still added Y).
    a_cfg = _cfg("stage_a")
    b_cfg = _cfg("stage_b")
    a_desc = _desc("stage_a", requires={"x_tag"}, produces={"y_tag"})
    b_desc = _desc("stage_b", requires={"y_tag"}, produces=set())
    with _patch_descriptors({"stage_a": a_desc, "stage_b": b_desc}):
        result = check_compatibility([a_cfg, b_cfg])
    assert "stage_a" in result, "stage_a should be flagged (missing x_tag)"
    assert "stage_b" not in result, "stage_b should not cascade-fail"


# ---------------------------------------------------------------------------
# ERR-1: disabled stage that would be incompatible → NOT in result
# ---------------------------------------------------------------------------

def test_err1_disabled_incompatible_stage_not_in_result():
    cfg = _cfg("asr", enabled=False)
    desc = _desc("asr", requires={SEGMENTS}, produces={TRANSCRIPT})
    with _patch_descriptors({"asr": desc}):
        result = check_compatibility([cfg])
    assert "asr" not in result
