from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class UnitEntry:
    index: int
    uid: str
    title: str
    url: str
    duration_minutes: int | None
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ModuleEntry:
    index: int
    uid: str
    title: str
    url: str
    duration_minutes: int | None
    units: list[UnitEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["units"] = [u.to_dict() for u in self.units]
        return data


@dataclass(slots=True)
class LearningPathEntry:
    index: int
    uid: str
    title: str
    url: str
    duration_minutes: int | None
    modules: list[ModuleEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["modules"] = [m.to_dict() for m in self.modules]
        return data


@dataclass(slots=True)
class Manifest:
    source_url: str
    source_uid: str
    source_type: str
    locale: str
    generated_at_utc: str
    course_title: str
    learning_paths: list[LearningPathEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["learning_paths"] = [lp.to_dict() for lp in self.learning_paths]
        return data


@dataclass(slots=True)
class UnitContent:
    learning_path_index: int
    module_index: int
    unit_index: int
    unit_uid: str
    unit_title: str
    url: str
    fetched_at_utc: str
    success: bool
    extracted_title: str
    content: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

