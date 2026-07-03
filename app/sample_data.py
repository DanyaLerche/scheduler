from __future__ import annotations

from app.models import Group, Lesson, Room, ScheduleDataset, Teacher, TimeSlot


def sample_dataset() -> ScheduleDataset:
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    pairs = [
        ("09:00", "10:30"),
        ("10:45", "12:15"),
        ("13:00", "14:30"),
        ("14:45", "16:15"),
    ]
    timeslots: list[TimeSlot] = []
    order = 1
    for day_index, day in enumerate(days, start=1):
        for pair_index, (start, end) in enumerate(pairs, start=1):
            timeslots.append(
                TimeSlot(
                    id=f"d{day_index}-p{pair_index}",
                    day=day,
                    start=start,
                    end=end,
                    order=order,
                )
            )
            order += 1

    return ScheduleDataset(
        timeslots=timeslots,
        rooms=[
            Room(id="aud-101", name="Ауд. 101", capacity=120, room_type="lecture"),
            Room(id="aud-205", name="Ауд. 205", capacity=40, room_type="practice"),
            Room(id="lab-310", name="Лаб. 310", capacity=28, room_type="lab"),
            Room(id="aud-420", name="Ауд. 420", capacity=60, room_type="any"),
        ],
        teachers=[
            Teacher(id="teacher-ivanov", name="Иванов И.И.", unavailable=["d1-p1", "d5-p4"]),
            Teacher(id="teacher-petrova", name="Петрова А.С.", unavailable=["d3-p3"]),
            Teacher(id="teacher-sidorov", name="Сидоров П.П.", unavailable=["d2-p4"]),
            Teacher(id="teacher-kuznetsova", name="Кузнецова Е.В.", unavailable=["d4-p1"]),
            Teacher(id="teacher-smirnov", name="Смирнов Д.А.", unavailable=[]),
        ],
        groups=[
            Group(id="pi-101", name="ПИ-101", size=28, unavailable=["d5-p4"]),
            Group(id="pi-102", name="ПИ-102", size=26, unavailable=["d1-p1"]),
            Group(id="pi-201", name="ПИ-201", size=22, unavailable=["d3-p4"]),
        ],
        lessons=[
            Lesson(
                id="algorithms",
                subject="Алгоритмы и структуры данных",
                teacher_id="teacher-ivanov",
                group_ids=["pi-101", "pi-102"],
                sessions=2,
                room_type="lecture",
                priority=5,
            ),
            Lesson(
                id="databases",
                subject="Базы данных",
                teacher_id="teacher-petrova",
                group_ids=["pi-101"],
                sessions=2,
                room_type="lab",
                priority=4,
            ),
            Lesson(
                id="web",
                subject="Веб-программирование",
                teacher_id="teacher-sidorov",
                group_ids=["pi-102"],
                sessions=2,
                room_type="lab",
                priority=4,
            ),
            Lesson(
                id="math",
                subject="Дискретная математика",
                teacher_id="teacher-smirnov",
                group_ids=["pi-101", "pi-102"],
                sessions=2,
                room_type="practice",
                priority=4,
            ),
            Lesson(
                id="networks",
                subject="Компьютерные сети",
                teacher_id="teacher-kuznetsova",
                group_ids=["pi-201"],
                sessions=2,
                room_type="lab",
                priority=3,
            ),
            Lesson(
                id="economics",
                subject="Экономика ИТ-проектов",
                teacher_id="teacher-smirnov",
                group_ids=["pi-101", "pi-102", "pi-201"],
                sessions=1,
                room_type="lecture",
                priority=3,
            ),
            Lesson(
                id="project",
                subject="Проектный практикум",
                teacher_id="teacher-sidorov",
                group_ids=["pi-102", "pi-201"],
                sessions=1,
                room_type="practice",
                priority=5,
            ),
            Lesson(
                id="ai",
                subject="Основы искусственного интеллекта",
                teacher_id="teacher-ivanov",
                group_ids=["pi-201"],
                sessions=2,
                room_type="lab",
                priority=3,
            ),
        ],
    )
