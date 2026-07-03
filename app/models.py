from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


RoomType = Literal["any", "lecture", "practice", "lab"]
AlgorithmName = Literal["greedy", "sequential", "random"]


class TimeSlot(BaseModel):
    id: str = Field(min_length=1)
    day: str = Field(min_length=1)
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    order: int = 0


class Room(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    room_type: RoomType = "any"


class Teacher(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    unavailable: list[str] = Field(default_factory=list)


class Group(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    size: int = Field(gt=0)
    unavailable: list[str] = Field(default_factory=list)


class Lesson(BaseModel):
    id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    teacher_id: str = Field(min_length=1)
    group_ids: list[str] = Field(min_length=1)
    sessions: int = Field(default=1, ge=1, le=30)
    room_type: RoomType = "any"
    priority: int = Field(default=3, ge=1, le=5)


class ScheduleDataset(BaseModel):
    timeslots: list[TimeSlot] = Field(min_length=1)
    rooms: list[Room] = Field(min_length=1)
    teachers: list[Teacher] = Field(min_length=1)
    groups: list[Group] = Field(min_length=1)
    lessons: list[Lesson] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "ScheduleDataset":
        self._ensure_unique("timeslots", [item.id for item in self.timeslots])
        self._ensure_unique("rooms", [item.id for item in self.rooms])
        self._ensure_unique("teachers", [item.id for item in self.teachers])
        self._ensure_unique("groups", [item.id for item in self.groups])
        self._ensure_unique("lessons", [item.id for item in self.lessons])

        slot_ids = {item.id for item in self.timeslots}
        teacher_ids = {item.id for item in self.teachers}
        group_ids = {item.id for item in self.groups}

        for teacher in self.teachers:
            self._ensure_known_slots("teacher", teacher.id, teacher.unavailable, slot_ids)
        for group in self.groups:
            self._ensure_known_slots("group", group.id, group.unavailable, slot_ids)
        for lesson in self.lessons:
            if lesson.teacher_id not in teacher_ids:
                raise ValueError(f"lesson {lesson.id} references unknown teacher {lesson.teacher_id}")
            missing_groups = [group_id for group_id in lesson.group_ids if group_id not in group_ids]
            if missing_groups:
                raise ValueError(
                    f"lesson {lesson.id} references unknown groups: {', '.join(missing_groups)}"
                )

        return self

    @staticmethod
    def _ensure_unique(collection: str, ids: list[str]) -> None:
        duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
        if duplicates:
            raise ValueError(f"{collection} has duplicate ids: {', '.join(duplicates)}")

    @staticmethod
    def _ensure_known_slots(
        owner_type: str, owner_id: str, slots: list[str], known_slots: set[str]
    ) -> None:
        missing = [slot_id for slot_id in slots if slot_id and slot_id not in known_slots]
        if missing:
            raise ValueError(
                f"{owner_type} {owner_id} references unknown unavailable slots: {', '.join(missing)}"
            )


class ScheduleEntry(BaseModel):
    id: str
    lesson_id: str
    subject: str
    session_index: int
    teacher_id: str
    teacher: str
    group_ids: list[str]
    groups: list[str]
    room_id: str
    room: str
    timeslot_id: str
    day: str
    start: str
    end: str


class UnscheduledLesson(BaseModel):
    id: str
    lesson_id: str
    subject: str
    session_index: int
    reason: str


class ValidationConflict(BaseModel):
    type: str
    message: str
    entry_ids: list[str] = Field(default_factory=list)


class AlgorithmStats(BaseModel):
    algorithm: AlgorithmName
    title: str
    scheduled_count: int
    unscheduled_count: int
    conflict_count: int
    utilization_percent: float
    elapsed_ms: float


class ScheduleResult(BaseModel):
    algorithm: AlgorithmName
    title: str
    entries: list[ScheduleEntry]
    unscheduled: list[UnscheduledLesson]
    conflicts: list[ValidationConflict]
    stats: AlgorithmStats


class ScheduleOptions(BaseModel):
    seed: int = 42
    include_comparison: bool = True


class ScheduleRequest(BaseModel):
    dataset: ScheduleDataset
    options: ScheduleOptions = Field(default_factory=ScheduleOptions)


class ScheduleResponse(BaseModel):
    greedy: ScheduleResult
    comparisons: list[AlgorithmStats]
