"""Plugin для регистрации TransformersLID в реестре моделей."""

from core.models.transformers_lid import TransformersLID
from core.models.registry import ModelRegistry
from core.pipeline.registry import StageRegistry


def register(model_registry: ModelRegistry, stage_registry: StageRegistry) -> None:
    """Регистрирует TransformersLID в реестре моделей."""
    model_registry.register_language("transformers-lid", TransformersLID)
