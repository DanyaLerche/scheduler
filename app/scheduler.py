from __future__ import annotations

import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from app.models import (
    AlgorithmName,
    AlgorithmStats,
    Group,
    Lesson,
    Room,
    ScheduleDataset,
    ScheduleEntry,
    ScheduleResult,
    TimeSlot,
    UnscheduledLesson,
    ValidationConflict,
)


ALGORITHM_TITLES: dict[AlgorithmName, str] = {
    "greedy": "Жадный алгоритм",
    "sequential": "Последовательный перебор",
    "random": "Случайный порядок",
}


@dataclass(frozen=True)
class SchedulingTask:
    id: str
    lesson: Lesson
    session_index: int
    group_size: int


@dataclass(frozen=True)
class Candidate:
    slot: TimeSlot
    room: Room
    room_waste: int


@dataclass
class SchedulingContext:
    dataset: ScheduleDataset
    slots_by_id: dict[str, TimeSlot] = field(init=False)
    rooms_by_id: dict[str, Room] = field(init=False)
    teachers_by_id: dict[str, object] = field(init=False)
    groups_by_id: dict[str, Group] = field(init=False)
    lessons_by_id: dict[str, Lesson] = field(init=False)
    sorted_slots: list[TimeSlot] = field(init=False)
    sorted_rooms: list[Room] = field(init=False)

    def __post_init__(self) -> None:
        self.slots_by_id = {slot.id: slot for slot in self.dataset.timeslots}
        self.rooms_by_id = {room.id: room for room in self.dataset.rooms}
        self.teachers_by_id = {teacher.id: teacher for teacher in self.dataset.teachers}
        self.groups_by_id = {group.id: group for group in self.dataset.groups}
        self.lessons_by_id = {lesson.id: lesson for lesson in self.dataset.lessons}
        self.sorted_slots = sorted(
            self.dataset.timeslots, key=lambda slot: (slot.order, slot.day, slot.start, slot.id)
        )
        self.sorted_rooms = sorted(
            self.dataset.rooms, key=lambda room: (room.capacity, room.room_type, room.name, room.id)
        )


@dataclass
class ScheduleState:
    occupied_rooms: dict[tuple[str, str], str] = field(default_factory=dict)
    occupied_teachers: dict[tuple[str, str], str] = field(default_factory=dict)
    occupied_groups: dict[tuple[str, str], str] = field(default_factory=dict)
    lesson_days: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    teacher_day_load: Counter[tuple[str, str]] = field(default_factory=Counter)
    group_day_load: Counter[tuple[str, str]] = field(default_factory=Counter)
    slot_load: Counter[str] = field(default_factory=Counter)


def generate_schedule(
    dataset: ScheduleDataset, algorithm: AlgorithmName = "greedy", seed: int = 42
) -> ScheduleResult:
    started_at = time.perf_counter()
    context = SchedulingContext(dataset)
    tasks = _build_tasks(context)
    rng = random.Random(seed)

    if algorithm == "greedy":
        tasks = sorted(tasks, key=lambda task: _task_hardness(context, task))
    elif algorithm == "random":
        rng.shuffle(tasks)

    state = ScheduleState()
    entries: list[ScheduleEntry] = []
    unscheduled: list[UnscheduledLesson] = []

    for task in tasks:
        candidates = _candidate_pairs(context, task)
        if algorithm == "greedy":
            candidates.sort(key=lambda candidate: _candidate_score(state, task, candidate))
        elif algorithm == "sequential":
            candidates.sort(key=lambda candidate: (candidate.slot.order, candidate.room.capacity))
        else:
            rng.shuffle(candidates)

        entry = _place_first_available(context, state, task, candidates)
        if entry is None:
            unscheduled.append(_unscheduled_item(context, task, candidates))
            continue

        _reserve(state, task, entry)
        entries.append(entry)

    conflicts = validate_schedule(dataset, entries)
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)
    stats = AlgorithmStats(
        algorithm=algorithm,
        title=ALGORITHM_TITLES[algorithm],
        scheduled_count=len(entries),
        unscheduled_count=len(unscheduled),
        conflict_count=len(conflicts),
        utilization_percent=_utilization_percent(dataset, entries),
        elapsed_ms=elapsed_ms,
    )
    return ScheduleResult(
        algorithm=algorithm,
        title=ALGORITHM_TITLES[algorithm],
        entries=entries,
        unscheduled=unscheduled,
        conflicts=conflicts,
        stats=stats,
    )


def compare_algorithms(dataset: ScheduleDataset, seed: int = 42) -> list[ScheduleResult]:
    return [
        generate_schedule(dataset, "greedy", seed),
        generate_schedule(dataset, "sequential", seed),
        generate_schedule(dataset, "random", seed),
    ]


def validate_schedule(
    dataset: ScheduleDataset, entries: list[ScheduleEntry]
) -> list[ValidationConflict]:
    context = SchedulingContext(dataset)
    conflicts: list[ValidationConflict] = []
    room_usage: dict[tuple[str, str], ScheduleEntry] = {}
    teacher_usage: dict[tuple[str, str], ScheduleEntry] = {}
    group_usage: dict[tuple[str, str], ScheduleEntry] = {}

    for entry in entries:
        slot = context.slots_by_id.get(entry.timeslot_id)
        room = context.rooms_by_id.get(entry.room_id)
        lesson = context.lessons_by_id.get(entry.lesson_id)
        teacher = context.teachers_by_id.get(entry.teacher_id)

        if slot is None:
            conflicts.append(
                ValidationConflict(
                    type="unknown_timeslot",
                    message=f"Занятие {entry.id}: неизвестный слот {entry.timeslot_id}.",
                    entry_ids=[entry.id],
                )
            )
            continue
        if room is None:
            conflicts.append(
                ValidationConflict(
                    type="unknown_room",
                    message=f"Занятие {entry.id}: неизвестная аудитория {entry.room_id}.",
                    entry_ids=[entry.id],
                )
            )
            continue
        if lesson is None:
            conflicts.append(
                ValidationConflict(
                    type="unknown_lesson",
                    message=f"Занятие {entry.id}: неизвестное занятие {entry.lesson_id}.",
                    entry_ids=[entry.id],
                )
            )
            continue
        if teacher is None:
            conflicts.append(
                ValidationConflict(
                    type="unknown_teacher",
                    message=f"Занятие {entry.id}: неизвестный преподаватель {entry.teacher_id}.",
                    entry_ids=[entry.id],
                )
            )
            continue

        group_size = _group_size(context, entry.group_ids)
        if room.capacity < group_size:
            conflicts.append(
                ValidationConflict(
                    type="room_capacity",
                    message=(
                        f"Занятие {entry.id}: аудитория {room.name} вмещает {room.capacity}, "
                        f"а требуется {group_size} мест."
                    ),
                    entry_ids=[entry.id],
                )
            )
        if not _room_matches(lesson.room_type, room.room_type):
            conflicts.append(
                ValidationConflict(
                    type="room_type",
                    message=(
                        f"Занятие {entry.id}: нужен тип {lesson.room_type}, "
                        f"но выбрана аудитория типа {room.room_type}."
                    ),
                    entry_ids=[entry.id],
                )
            )
        if entry.timeslot_id in teacher.unavailable:
            conflicts.append(
                ValidationConflict(
                    type="teacher_unavailable",
                    message=f"Занятие {entry.id}: преподаватель {teacher.name} недоступен.",
                    entry_ids=[entry.id],
                )
            )

        _check_single_resource(
            conflicts,
            room_usage,
            (room.id, slot.id),
            entry,
            "room_busy",
            f"Аудитория {room.name} занята в слоте {slot.day} {slot.start}.",
        )
        _check_single_resource(
            conflicts,
            teacher_usage,
            (teacher.id, slot.id),
            entry,
            "teacher_busy",
            f"Преподаватель {teacher.name} занят в слоте {slot.day} {slot.start}.",
        )

        for group_id in entry.group_ids:
            group = context.groups_by_id.get(group_id)
            if group is None:
                conflicts.append(
                    ValidationConflict(
                        type="unknown_group",
                        message=f"Занятие {entry.id}: неизвестная группа {group_id}.",
                        entry_ids=[entry.id],
                    )
                )
                continue
            if entry.timeslot_id in group.unavailable:
                conflicts.append(
                    ValidationConflict(
                        type="group_unavailable",
                        message=f"Занятие {entry.id}: группа {group.name} недоступна.",
                        entry_ids=[entry.id],
                    )
                )
            _check_single_resource(
                conflicts,
                group_usage,
                (group.id, slot.id),
                entry,
                "group_busy",
                f"Группа {group.name} занята в слоте {slot.day} {slot.start}.",
            )

    return conflicts


def _build_tasks(context: SchedulingContext) -> list[SchedulingTask]:
    tasks: list[SchedulingTask] = []
    for lesson in context.dataset.lessons:
        group_size = _group_size(context, lesson.group_ids)
        for session_index in range(1, lesson.sessions + 1):
            tasks.append(
                SchedulingTask(
                    id=f"{lesson.id}-{session_index}",
                    lesson=lesson,
                    session_index=session_index,
                    group_size=group_size,
                )
            )
    return tasks


def _task_hardness(context: SchedulingContext, task: SchedulingTask) -> tuple[int, int, int, str, int]:
    candidate_count = len(_candidate_pairs(context, task))
    return (
        candidate_count,
        -task.lesson.priority,
        -task.group_size,
        task.lesson.id,
        task.session_index,
    )


def _candidate_pairs(context: SchedulingContext, task: SchedulingTask) -> list[Candidate]:
    candidates: list[Candidate] = []
    teacher = context.teachers_by_id[task.lesson.teacher_id]
    groups = [context.groups_by_id[group_id] for group_id in task.lesson.group_ids]

    for slot in context.sorted_slots:
        if slot.id in teacher.unavailable:
            continue
        if any(slot.id in group.unavailable for group in groups):
            continue
        for room in context.sorted_rooms:
            if room.capacity < task.group_size:
                continue
            if not _room_matches(task.lesson.room_type, room.room_type):
                continue
            candidates.append(
                Candidate(slot=slot, room=room, room_waste=room.capacity - task.group_size)
            )
    return candidates


def _candidate_score(
    state: ScheduleState, task: SchedulingTask, candidate: Candidate
) -> tuple[int, int, int, int, int, int, str]:
    same_lesson_day = int(candidate.slot.day in state.lesson_days[task.lesson.id])
    teacher_day_load = state.teacher_day_load[(task.lesson.teacher_id, candidate.slot.day)]
    max_group_day_load = max(
        state.group_day_load[(group_id, candidate.slot.day)] for group_id in task.lesson.group_ids
    )
    return (
        same_lesson_day,
        max_group_day_load,
        teacher_day_load,
        candidate.room_waste,
        state.slot_load[candidate.slot.id],
        candidate.slot.order,
        candidate.room.id,
    )


def _place_first_available(
    context: SchedulingContext,
    state: ScheduleState,
    task: SchedulingTask,
    candidates: list[Candidate],
) -> ScheduleEntry | None:
    for candidate in candidates:
        slot_id = candidate.slot.id
        if (candidate.room.id, slot_id) in state.occupied_rooms:
            continue
        if (task.lesson.teacher_id, slot_id) in state.occupied_teachers:
            continue
        if any((group_id, slot_id) in state.occupied_groups for group_id in task.lesson.group_ids):
            continue
        return _entry_from_candidate(context, task, candidate)
    return None


def _entry_from_candidate(
    context: SchedulingContext, task: SchedulingTask, candidate: Candidate
) -> ScheduleEntry:
    teacher = context.teachers_by_id[task.lesson.teacher_id]
    groups = [context.groups_by_id[group_id] for group_id in task.lesson.group_ids]
    return ScheduleEntry(
        id=task.id,
        lesson_id=task.lesson.id,
        subject=task.lesson.subject,
        session_index=task.session_index,
        teacher_id=task.lesson.teacher_id,
        teacher=teacher.name,
        group_ids=task.lesson.group_ids,
        groups=[group.name for group in groups],
        room_id=candidate.room.id,
        room=candidate.room.name,
        timeslot_id=candidate.slot.id,
        day=candidate.slot.day,
        start=candidate.slot.start,
        end=candidate.slot.end,
    )


def _reserve(state: ScheduleState, task: SchedulingTask, entry: ScheduleEntry) -> None:
    slot_id = entry.timeslot_id
    state.occupied_rooms[(entry.room_id, slot_id)] = entry.id
    state.occupied_teachers[(entry.teacher_id, slot_id)] = entry.id
    for group_id in entry.group_ids:
        state.occupied_groups[(group_id, slot_id)] = entry.id
        state.group_day_load[(group_id, entry.day)] += 1
    state.lesson_days[entry.lesson_id].add(entry.day)
    state.teacher_day_load[(entry.teacher_id, entry.day)] += 1
    state.slot_load[slot_id] += 1


def _unscheduled_item(
    context: SchedulingContext, task: SchedulingTask, candidates: list[Candidate]
) -> UnscheduledLesson:
    if not candidates:
        compatible_rooms = [
            room
            for room in context.sorted_rooms
            if room.capacity >= task.group_size and _room_matches(task.lesson.room_type, room.room_type)
        ]
        reason = (
            "нет аудитории нужного типа и вместимости"
            if not compatible_rooms
            else "преподаватель или группа недоступны во всех подходящих слотах"
        )
    else:
        reason = "все подходящие слоты заняты аудиторией, преподавателем или группой"

    return UnscheduledLesson(
        id=task.id,
        lesson_id=task.lesson.id,
        subject=task.lesson.subject,
        session_index=task.session_index,
        reason=reason,
    )


def _group_size(context: SchedulingContext, group_ids: list[str]) -> int:
    return sum(context.groups_by_id[group_id].size for group_id in group_ids if group_id in context.groups_by_id)


def _room_matches(required: str, actual: str) -> bool:
    return required == "any" or actual == "any" or required == actual


def _check_single_resource(
    conflicts: list[ValidationConflict],
    usage: dict[tuple[str, str], ScheduleEntry],
    key: tuple[str, str],
    entry: ScheduleEntry,
    conflict_type: str,
    message: str,
) -> None:
    previous = usage.get(key)
    if previous is None:
        usage[key] = entry
        return
    conflicts.append(
        ValidationConflict(
            type=conflict_type,
            message=message,
            entry_ids=[previous.id, entry.id],
        )
    )


def _utilization_percent(dataset: ScheduleDataset, entries: list[ScheduleEntry]) -> float:
    capacity = len(dataset.timeslots) * len(dataset.rooms)
    if capacity == 0:
        return 0
    return round(len(entries) / capacity * 100, 1)
