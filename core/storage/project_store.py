"""Хранилище метаданных проектов.

Каждый проект сохраняется как отдельный JSON-файл в директории projects/.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.domain.project import Project


class ProjectStore:
    """Хранилище метаданных проектов: каждый проект — отдельный JSON-файл.

    Файлы именуются ``{project_id}.json`` и хранятся в ``projects_dir``.
    """

    def __init__(self, projects_dir: Path) -> None:
        """Инициализирует хранилище и создаёт директорию при необходимости.

        Args:
            projects_dir (Path): Директория для хранения JSON-файлов проектов.
        """
        self.projects_dir = projects_dir
        projects_dir.mkdir(parents=True, exist_ok=True)

    def save(self, project: Project) -> None:
        """Сохраняет или обновляет проект в файл ``{project_id}.json``.

        Args:
            project (Project): Проект для сохранения.
        """
        path = self.projects_dir / f"{project.project_id}.json"
        path.write_text(
            json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_all(self) -> list[Project]:
        """Загружает все проекты, отсортированные по дате создания (новые первыми).

        Повреждённые файлы игнорируются.

        Returns:
            list[Project]: Список всех проектов.
        """
        projects: list[Project] = []
        for f in self.projects_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                projects.append(Project.from_dict(data))
            except Exception:
                pass
        projects.sort(key=lambda p: p.created_at, reverse=True)
        return projects

    def load(self, project_id: str) -> Project | None:
        """Загружает проект по идентификатору.

        Args:
            project_id (str): Идентификатор проекта.

        Returns:
            Project | None: Объект проекта или ``None``, если не найден или повреждён.
        """
        path = self.projects_dir / f"{project_id}.json"
        if not path.exists():
            return None
        try:
            return Project.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return None

    def delete(self, project_id: str) -> None:
        """Удаляет файл проекта.

        Args:
            project_id (str): Идентификатор проекта для удаления.
        """
        (self.projects_dir / f"{project_id}.json").unlink(missing_ok=True)
