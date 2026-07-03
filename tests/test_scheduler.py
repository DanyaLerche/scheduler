from app.sample_data import sample_dataset
from app.scheduler import compare_algorithms, generate_schedule, validate_schedule


def test_greedy_sample_schedule_has_no_conflicts() -> None:
    dataset = sample_dataset()
    result = generate_schedule(dataset, "greedy")
    expected_lessons = sum(lesson.sessions for lesson in dataset.lessons)

    assert result.stats.scheduled_count == expected_lessons
    assert result.stats.unscheduled_count == 0
    assert result.stats.conflict_count == 0
    assert result.conflicts == []


def test_greedy_respects_teacher_and_group_unavailability() -> None:
    dataset = sample_dataset()
    result = generate_schedule(dataset, "greedy")
    teachers = {teacher.id: teacher for teacher in dataset.teachers}
    groups = {group.id: group for group in dataset.groups}

    for entry in result.entries:
        assert entry.timeslot_id not in teachers[entry.teacher_id].unavailable
        for group_id in entry.group_ids:
            assert entry.timeslot_id not in groups[group_id].unavailable


def test_validator_detects_resource_conflicts() -> None:
    dataset = sample_dataset()
    result = generate_schedule(dataset, "greedy")
    first, second = result.entries[0], result.entries[1]
    conflicting_second = second.model_copy(
        update={
            "timeslot_id": first.timeslot_id,
            "day": first.day,
            "start": first.start,
            "end": first.end,
            "room_id": first.room_id,
            "room": first.room,
            "teacher_id": first.teacher_id,
            "teacher": first.teacher,
            "group_ids": first.group_ids,
            "groups": first.groups,
        }
    )

    conflicts = validate_schedule(dataset, [first, conflicting_second])
    conflict_types = {conflict.type for conflict in conflicts}

    assert "room_busy" in conflict_types
    assert "teacher_busy" in conflict_types
    assert "group_busy" in conflict_types


def test_comparison_runs_three_algorithms() -> None:
    dataset = sample_dataset()
    results = compare_algorithms(dataset)

    assert [result.algorithm for result in results] == ["greedy", "sequential", "random"]
    assert all(result.stats.conflict_count == 0 for result in results)
