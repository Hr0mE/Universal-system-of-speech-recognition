"""Plugin для регистрации TransformersASR в реестре моделей."""

from core.models.transformers_asr import TransformersASR
from core.models.registry import ModelRegistry
from core.pipeline.registry import StageRegistry


def register(model_registry: ModelRegistry, stage_registry: StageRegistry) -> None:
    """Регистрирует TransformersASR в реестре моделей."""
    model_registry.register_asr("transformers-asr", TransformersASR)
