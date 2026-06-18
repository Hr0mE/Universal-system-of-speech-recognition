"""Постобработка и экспорт результатов транскрибации.

Предоставляет :func:`build_meeting_report` для группировки сегментов по спикерам
и функции :func:`export_json` / :func:`export_txt` для сохранения отчётов.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.pipeline.context import Segment


def _fmt_time(seconds: float) -> str:
    """Форматирует время в секундах как ``MM:SS`` или ``H:MM:SS``.

    Args:
        seconds (float): Время в секундах.

    Returns:
        str: Отформатированная строка времени.
    """
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


@dataclass
class SpeakerGroup:
    """Группа сегментов одного говорящего.

    Attributes:
        speaker_id (str | None): Идентификатор говорящего или ``None``.
        total_duration (float): Суммарное время речи говорящего в секундах.
        segments (list[Segment]): Список сегментов этого говорящего.
    """

    speaker_id: str | None
    total_duration: float
    segments: list[Segment]

    def to_dict(self) -> dict:
        """Сериализует группу говорящего в словарь.

        Returns:
            dict: Словарь с полями группы и сегментов.
        """
        return {
            "speaker_id": self.speaker_id,
            "total_duration": self.total_duration,
            "segments": [
                {
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "language": seg.language,
                    "text": seg.text,
                }
                for seg in self.segments
            ],
        }


@dataclass
class MeetingReport:
    """Отчёт о встрече: транскрибация, сгруппированная по говорящим.

    Attributes:
        run_id (str): Идентификатор запуска pipeline.
        audio_path (str): Путь к исходному аудиофайлу.
        duration_s (float): Длительность записи в секундах.
        speakers (list[SpeakerGroup]): Список групп по говорящим в хронологическом порядке.
    """

    run_id: str
    audio_path: str
    duration_s: float
    speakers: list[SpeakerGroup]

    def to_dict(self) -> dict:
        """Сериализует отчёт в словарь для экспорта в JSON.

        Returns:
            dict: Словарь с метаданными и списком групп говорящих.
        """
        return {
            "run_id": self.run_id,
            "audio_path": self.audio_path,
            "duration_s": self.duration_s,
            "speakers": [g.to_dict() for g in self.speakers],
        }


def build_meeting_report(result) -> MeetingReport:
    """Группирует сегменты TranscriptionResult по говорящим в MeetingReport.

    Args:
        result: Объект :class:`TranscriptionResult` с сегментами.

    Returns:
        MeetingReport: Отчёт с группами по говорящим в хронологическом порядке.
    """
    groups: dict[str | None, list[Segment]] = {}
    for seg in result.segments:
        groups.setdefault(seg.speaker_id, []).append(seg)

    speaker_list: list[SpeakerGroup] = []
    for spk_id, segs in sorted(groups.items(), key=lambda kv: kv[1][0].start_time):
        total_dur = round(sum(s.duration for s in segs), 3)
        speaker_list.append(SpeakerGroup(
            speaker_id=spk_id,
            total_duration=total_dur,
            segments=segs,
        ))

    return MeetingReport(
        run_id=result.run_id,
        audio_path=str(result.audio_path),
        duration_s=round(result.duration_s, 3),
        speakers=speaker_list,
    )


def export_json(report: MeetingReport, path: Path) -> None:
    """Сохраняет отчёт в JSON-файл.

    Args:
        report (MeetingReport): Отчёт для экспорта.
        path (Path): Путь к выходному файлу.
    """
    path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_txt(report: MeetingReport, path: Path) -> None:
    """Сохраняет отчёт в виде читаемого текстового файла.

    Args:
        report (MeetingReport): Отчёт для экспорта.
        path (Path): Путь к выходному файлу.
    """
    lines = [
        f"Meeting: {report.run_id}",
        f"Audio: {report.audio_path}",
        f"Duration: {_fmt_time(report.duration_s)}",
        "",
    ]
    for grp in report.speakers:
        spk = grp.speaker_id or "Unknown"
        lines.append(f"{spk}  ({_fmt_time(grp.total_duration)} total):")
        for seg in grp.segments:
            lang = f"[{seg.language}] " if seg.language else ""
            text = seg.text or ""
            lines.append(f"  {_fmt_time(seg.start_time)} – {_fmt_time(seg.end_time)}  {lang}{text}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
