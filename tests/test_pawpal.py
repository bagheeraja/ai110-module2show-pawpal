from datetime import date, datetime, timedelta

from pawpal_system import Pet, Priority, Recurrence, Scheduler, Task, TaskType


def test_mark_complete_changes_task_status():
    task = Task(
        title="Morning walk",
        task_type=TaskType.WALK,
        duration_minutes=20,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 8, 0),
    )

    assert not task.is_complete_on(date(2026, 7, 5))

    task.mark_complete()

    assert task.is_complete_on(date(2026, 7, 5))


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    task = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 7, 30),
    )

    assert len(pet.tasks) == 0

    pet.add_task(task)

    assert len(pet.tasks) == 1


def test_next_occurrence_date_daily_is_timedelta_of_one_day():
    task = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 7, 30),
        recurrence=Recurrence.DAILY,
    )

    assert task.next_occurrence_date(date(2026, 7, 5)) == date(2026, 7, 6)


def test_next_occurrence_date_weekly_matches_anchor_weekday():
    # 2026-07-05 is a Sunday.
    task = Task(
        title="Vet checkup",
        task_type=TaskType.APPOINTMENT,
        duration_minutes=30,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 14, 0),
        recurrence=Recurrence.WEEKLY,
    )

    assert task.next_occurrence_date(date(2026, 7, 5)) == date(2026, 7, 12)
    # From a non-anchor weekday mid-week, it should still land on the next Sunday.
    assert task.next_occurrence_date(date(2026, 7, 8)) == date(2026, 7, 12)


def test_next_occurrence_date_none_when_recurrence_none_or_end_date_exceeded():
    one_off = Task(
        title="Flea medication",
        task_type=TaskType.MEDICATION,
        duration_minutes=5,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 9, 0),
    )
    assert one_off.next_occurrence_date(date(2026, 7, 5)) is None

    ending_daily = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 7, 30),
        recurrence=Recurrence.DAILY,
        recurrence_end_date=date(2026, 7, 5),
    )
    assert ending_daily.next_occurrence_date(date(2026, 7, 5)) is None


def test_mark_complete_returns_next_occurrence_date():
    task = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 7, 30),
        recurrence=Recurrence.DAILY,
    )

    next_date = task.mark_complete(date(2026, 7, 5))

    assert task.is_complete_on(date(2026, 7, 5))
    assert next_date == date(2026, 7, 6)


def test_sort_by_time_returns_chronological_order():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    scheduler = Scheduler()

    evening_walk = Task(
        title="Evening walk",
        task_type=TaskType.WALK,
        duration_minutes=20,
        priority=Priority.LOW,
        scheduled_time=datetime(2026, 7, 5, 18, 0),
    )
    breakfast = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 7, 30),
    )
    midday_meds = Task(
        title="Midday medication",
        task_type=TaskType.MEDICATION,
        duration_minutes=5,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 12, 0),
    )
    pet.add_task(evening_walk)
    pet.add_task(breakfast)
    pet.add_task(midday_meds)

    occurrences = pet.get_tasks_for_date(date(2026, 7, 5))
    sorted_occurrences = scheduler.sort_by_time(occurrences)

    assert [occurrence.task.title for occurrence in sorted_occurrences] == [
        "Breakfast",
        "Midday medication",
        "Evening walk",
    ]


def test_daily_recurrence_marks_today_complete_without_completing_tomorrow():
    task = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 7, 30),
        recurrence=Recurrence.DAILY,
    )

    next_date = task.mark_complete(date(2026, 7, 5))

    # Marking today's occurrence complete produces tomorrow's occurrence date,
    # but doesn't retroactively mark tomorrow as complete too.
    assert next_date == date(2026, 7, 6)
    assert task.is_complete_on(date(2026, 7, 5))
    assert not task.is_complete_on(date(2026, 7, 6))
    assert task.occurs_on(date(2026, 7, 6))


def test_detect_conflicts_flags_overlapping_duplicate_times():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    scheduler = Scheduler()

    walk = Task(
        title="Walk",
        task_type=TaskType.WALK,
        duration_minutes=30,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 8, 0),
    )
    vet_visit = Task(
        title="Vet visit",
        task_type=TaskType.APPOINTMENT,
        duration_minutes=30,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 8, 0),
    )
    pet.add_task(walk)
    pet.add_task(vet_visit)

    occurrences = pet.get_tasks_for_date(date(2026, 7, 5))
    conflicts = scheduler.detect_conflicts(occurrences)

    assert len(conflicts) == 1
    conflict_titles = {occurrence.task.title for occurrence in conflicts[0]}
    assert conflict_titles == {"Walk", "Vet visit"}


def test_detect_conflicts_ignores_back_to_back_tasks():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    scheduler = Scheduler()

    morning_walk = Task(
        title="Morning walk",
        task_type=TaskType.WALK,
        duration_minutes=30,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 8, 0),
    )
    breakfast = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=15,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 8, 30),
    )
    pet.add_task(morning_walk)
    pet.add_task(breakfast)

    occurrences = pet.get_tasks_for_date(date(2026, 7, 5))
    conflicts = scheduler.detect_conflicts(occurrences)

    assert conflicts == []
