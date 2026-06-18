"""Датаклассы событий pipeline.

Все события наследуют :class:`PipelineEvent` и передаются через
:class:`EventBus`.  Они иммутабельны (``frozen=True``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineEvent:
    """Базовый класс всех событий pipeline.

    Attributes:
        run_id (str): Идентификатор запуска, породившего событие.
    """

    run_id: str


@dataclass(frozen=True)
class PipelineStarted(PipelineEvent):
    """Публикуется при старте pipeline.

    Attributes:
        audio_path (Path): Путь к обрабатываемому аудиофайлу.
        total_stages (int): Общее количество стадий.
        resume_after (int): Индекс стадии, после которой выполняется resume (0 — новый запуск).
    """

    audio_path: Path
    total_stages: int
    resume_after: int


@dataclass(frozen=True)
class PipelineFinished(PipelineEvent):
    """Публикуется при успешном завершении pipeline.

    Attributes:
        segments_count (int): Количество сегментов в финальном результате.
    """

    segments_count: int


@dataclass(frozen=True)
class PipelineFailed(PipelineEvent):
    """Публикуется при падении pipeline с исключением.

    Attributes:
        error (str): Строковое представление исключения (repr).
    """

    error: str


@dataclass(frozen=True)
class StageStarted(PipelineEvent):
    """Публикуется перед запуском стадии.

    Attributes:
        stage_index (int): 1-based индекс стадии.
        stage_name (str): Имя стадии.
    """

    stage_index: int
    stage_name: str


@dataclass(frozen=True)
class StageFinished(PipelineEvent):
    """Публикуется после успешного завершения стадии.

    Attributes:
        stage_index (int): 1-based индекс стадии.
        stage_name (str): Имя стадии.
        segments_count (int): Количество сегментов на выходе стадии.
        artifact (Path | None): Путь к сохранённому артефакту или ``None``.
    """

    stage_index: int
    stage_name: str
    segments_count: int
    artifact: Path | None = None


@dataclass(frozen=True)
class StageSkipped(PipelineEvent):
    """Публикуется при пропуске стадии во время resume.

    Attributes:
        stage_index (int): 1-based индекс пропущенной стадии.
        stage_name (str): Имя стадии.
    """

    stage_index: int
    stage_name: str


@dataclass(frozen=True)
class ProgressUpdated(PipelineEvent):
    """Публикуется ASR-стадией для обновления прогресса обработки сегментов.

    Attributes:
        stage_index (int): Индекс текущей стадии.
        stage_name (str): Имя стадии.
        current (int): Количество обработанных сегментов.
        total (int): Общее количество сегментов.
        message (str): Опциональное сообщение для отображения в UI.
    """

    stage_index: int
    stage_name: str
    current: int
    total: int
    message: str = ""


@dataclass(frozen=True)
class ModelDownloadStarted(PipelineEvent):
    """Публикуется при начале загрузки модели из HuggingFace Hub.

    Attributes:
        model_name (str): Внутреннее имя модели в реестре.
        repo_id (str): Идентификатор репозитория на HuggingFace Hub.
    """

    model_name: str
    repo_id: str


@dataclass(frozen=True)
class ModelDownloadFinished(PipelineEvent):
    """Публикуется при завершении загрузки модели.

    Attributes:
        model_name (str): Внутреннее имя модели в реестре.
        repo_id (str): Идентификатор репозитория на HuggingFace Hub.
    """

    model_name: str
    repo_id: str


@dataclass(frozen=True)
class HFDownloadStarted(PipelineEvent):
    """Публикуется при начале загрузки файлов с HuggingFace Hub.

    Attributes:
        repo_id (str): Идентификатор репозитория на HuggingFace Hub.
    """

    repo_id: str


@dataclass(frozen=True)
class HFDownloadProgress(PipelineEvent):
    """Публикуется для обновления прогресса загрузки с HuggingFace Hub.

    Attributes:
        repo_id (str): Идентификатор репозитория на HuggingFace Hub.
        downloaded_bytes (int): Количество загруженных байт.
        total_bytes (int): Общий размер загрузки в байтах.
    """

    repo_id: str
    downloaded_bytes: int
    total_bytes: int


@dataclass(frozen=True)
class HFDownloadFinished(PipelineEvent):
    """Публикуется при завершении загрузки с HuggingFace Hub.

    Attributes:
        repo_id (str): Идентификатор репозитория на HuggingFace Hub.
    """

    repo_id: str
