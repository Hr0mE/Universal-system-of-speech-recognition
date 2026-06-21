from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from huggingface_hub import list_models

logger = logging.getLogger(__name__)

_HF_CACHE_ROOT = Path.home() / ".cache" / "huggingface" / "hub"

# Bytes per parameter element for each safetensors dtype
_DTYPE_BYTES: dict[str, int] = {
    "F64": 8, "F32": 4, "F16": 2, "BF16": 2,
    "I64": 8, "I32": 4, "I16": 2, "I8": 1, "U8": 1, "BOOL": 1,
}

_MONTH_RU = ["Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"]


def _fmt_created(dt) -> str:
    if dt is None:
        return ""
    try:
        return f"{_MONTH_RU[dt.month - 1]} {dt.year}"
    except Exception:
        return ""


def _extract_size_and_params(safetensors) -> tuple[int, int]:
    """Returns (size_bytes, num_parameters) from a SafeTensorsInfo object."""
    if safetensors is None:
        return 0, 0
    params: dict = getattr(safetensors, "parameters", {}) or {}
    total_params: int = getattr(safetensors, "total", 0) or 0
    size_bytes = sum(count * _DTYPE_BYTES.get(dtype, 2) for dtype, count in params.items())
    return size_bytes, total_params


@dataclass
class CatalogModel:
    repo_id: str
    downloads: int
    languages: list[str]
    pipeline_tag: str
    cached: bool
    likes: int = 0
    size_bytes: int = 0       # estimated from safetensors dtype × param count
    num_parameters: int = 0   # total number of model parameters
    created_month: str = ""   # "Окт 2024" or "" if unknown


def search_models(
    pipeline_tag: str,
    language: str | None = None,
    token: str | None = None,
    limit: int = 20,
) -> list[CatalogModel]:
    """Search HuggingFace for models by task/language. Returns [] on network error."""
    try:
        kwargs: dict = {
            "pipeline_tag": pipeline_tag,
            "sort": "downloads",
            "limit": limit,
            "expand": ["tags", "downloads", "likes", "createdAt", "safetensors"],
        }
        if language:
            kwargs["filter"] = language
        if token:
            kwargs["token"] = token

        results = []
        for model in list_models(**kwargs):
            tags = list(getattr(model, "tags", None) or [])
            langs = [t for t in tags if len(t) == 2 or t.startswith("lang:")]
            downloads = int(getattr(model, "downloads", 0) or 0)
            likes = int(getattr(model, "likes", 0) or 0)
            size_bytes, num_params = _extract_size_and_params(getattr(model, "safetensors", None))
            created_month = _fmt_created(getattr(model, "created_at", None))
            results.append(CatalogModel(
                repo_id=model.id,
                downloads=downloads,
                languages=langs,
                pipeline_tag=pipeline_tag,
                cached=is_cached(model.id),
                likes=likes,
                size_bytes=size_bytes,
                num_parameters=num_params,
                created_month=created_month,
            ))
        return results
    except Exception as exc:
        logger.warning("HF model search failed: %s", exc)
        return []


def is_cached(repo_id: str) -> bool:
    """Check whether a model is **fully** downloaded in the local HuggingFace cache.

    snapshot_download() creates the cache directory immediately on start, so
    checking directory existence alone returns True for partial downloads.
    HuggingFace Hub only writes refs/main after all files are successfully
    downloaded, making it a reliable indicator of a complete snapshot.
    """
    cache_name = "models--" + repo_id.replace("/", "--")
    refs_main = _HF_CACHE_ROOT / cache_name / "refs" / "main"
    return refs_main.is_file() and refs_main.stat().st_size > 0


def list_cached_hf_repos() -> list[str]:
    """Return all fully-downloaded repo_ids from the local HuggingFace cache.

    HuggingFace Hub writes ``refs/main`` only after a complete snapshot download,
    so its presence is a reliable indicator of a finished download.
    """
    if not _HF_CACHE_ROOT.exists():
        return []
    result = []
    for entry in _HF_CACHE_ROOT.iterdir():
        if not entry.name.startswith("models--"):
            continue
        refs_main = entry / "refs" / "main"
        if refs_main.is_file() and refs_main.stat().st_size > 0:
            # "models--openai--whisper-tiny" → "openai/whisper-tiny"
            tail = entry.name[len("models--"):]
            parts = tail.split("--", 1)
            if len(parts) == 2:
                result.append(f"{parts[0]}/{parts[1]}")
    return result


def list_local_models(models_dir: Path) -> list[str]:
    """Return subdirectory names from a local models directory."""
    if not models_dir.exists():
        return []
    return [p.name for p in models_dir.iterdir() if p.is_dir()]
