"""Хранилище именованных пресетов конфигурации пайплайна."""

from __future__ import annotations

import json
from pathlib import Path

from core.domain.pipeline_preset import PipelinePreset


class PipelinePresetStore:
    """Хранилище пресетов: каждый пресет — отдельный JSON-файл.

    Файлы именуются ``{preset_id}.json`` и хранятся в ``presets_dir``.
    Директория создаётся при необходимости.
    """

    def __init__(self, presets_dir: Path) -> None:
        self.presets_dir = presets_dir

    def save(self, preset: PipelinePreset) -> None:
        """Сохраняет или обновляет пресет в файл ``{preset_id}.json``."""
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        path = self.presets_dir / f"{preset.preset_id}.json"
        path.write_text(
            json.dumps(preset.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, preset_id: str) -> PipelinePreset | None:
        """Загружает пресет по идентификатору или возвращает ``None``."""
        path = self.presets_dir / f"{preset_id}.json"
        if not path.exists():
            return None
        try:
            return PipelinePreset.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return None

    def load_all(self) -> list[PipelinePreset]:
        """Загружает все пресеты, отсортированные по ``created_at`` убывающе.

        Повреждённые файлы молча пропускаются.
        """
        if not self.presets_dir.exists():
            return []
        presets: list[PipelinePreset] = []
        for f in self.presets_dir.glob("*.json"):
            try:
                presets.append(PipelinePreset.from_dict(json.loads(f.read_text(encoding="utf-8"))))
            except Exception:
                pass
        presets.sort(key=lambda p: p.created_at, reverse=True)
        return presets

    def delete(self, preset_id: str) -> None:
        """Удаляет файл пресета. Не бросает исключение, если пресет не найден."""
        (self.presets_dir / f"{preset_id}.json").unlink(missing_ok=True)

    def load_ordered(self) -> list[PipelinePreset]:
        """Загружает пресеты в пользовательском порядке из order.json.

        Пресеты, отсутствующие в order.json, добавляются в конец.
        """
        all_presets = {p.preset_id: p for p in self.load_all()}
        order = self._read_order()
        ordered = [all_presets[pid] for pid in order if pid in all_presets]
        seen = {p.preset_id for p in ordered}
        ordered += [p for p in all_presets.values() if p.preset_id not in seen]
        return ordered

    def save_order(self, preset_ids: list[str]) -> None:
        """Сохраняет пользовательский порядок пресетов в order.json."""
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        (self.presets_dir / "order.json").write_text(
            json.dumps(preset_ids, ensure_ascii=False),
            encoding="utf-8",
        )

    def _read_order(self) -> list[str]:
        path = self.presets_dir / "order.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def save_selection(self, active_id: str | None, saved_id: str | None) -> None:
        """Сохраняет последнее выбранное состояние чипов в selection.json."""
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        (self.presets_dir / "selection.json").write_text(
            json.dumps({"active_id": active_id, "saved_id": saved_id}, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_selection(self) -> tuple[str | None, str | None]:
        """Загружает последнее выбранное состояние из selection.json."""
        path = self.presets_dir / "selection.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("active_id"), data.get("saved_id")
        except Exception:
            return None, None
