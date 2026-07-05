from datetime import date, datetime, time, timedelta

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


def test_build_daily_plan_orders_by_priority_then_start_time():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    scheduler = Scheduler()

    # Titles are deliberately alphabetized *backwards* from their times, so
    # this only passes if the tie-break is chronological, not alphabetical.
    zebra_checkup = Task(
        title="Zebra checkup",
        task_type=TaskType.APPOINTMENT,
        duration_minutes=20,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 9, 0),
    )
    ant_grooming = Task(
        title="Ant grooming",
        task_type=TaskType.APPOINTMENT,
        duration_minutes=20,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 14, 0),
    )
    breakfast = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 18, 0),
    )
    pet.add_task(ant_grooming)
    pet.add_task(zebra_checkup)
    pet.add_task(breakfast)

    plan = scheduler.build_daily_plan(pet, date(2026, 7, 5))

    assert [occurrence.task.title for occurrence in plan] == [
        "Breakfast",       # HIGH outranks MEDIUM regardless of its later time
        "Zebra checkup",   # earlier MEDIUM occurrence, despite losing alphabetically
        "Ant grooming",    # later MEDIUM occurrence
    ]


def test_find_next_available_slot_skips_busy_windows():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    scheduler = Scheduler()

    pet.add_task(
        Task(
            title="Morning walk",
            task_type=TaskType.WALK,
            duration_minutes=30,
            priority=Priority.HIGH,
            scheduled_time=datetime(2026, 7, 5, 7, 0),
        )
    )

    # Before the walk starts, a 30-minute slot is free right at window open.
    before = scheduler.find_next_available_slot(
        pet, date(2026, 7, 5), 30, earliest=time(6, 0), latest=time(21, 0)
    )
    assert before == datetime(2026, 7, 5, 6, 0)

    # Once the window opens *inside* the walk, the next slot is right after it ends.
    during = scheduler.find_next_available_slot(
        pet, date(2026, 7, 5), 15, earliest=time(7, 0), latest=time(21, 0)
    )
    assert during == datetime(2026, 7, 5, 7, 30)


def test_find_next_available_slot_collapses_overlapping_busy_windows():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    scheduler = Scheduler()

    pet.add_task(
        Task(
            title="Vet",
            task_type=TaskType.APPOINTMENT,
            duration_minutes=60,
            priority=Priority.MEDIUM,
            scheduled_time=datetime(2026, 7, 5, 10, 0),
        )
    )
    pet.add_task(
        Task(
            title="Groom",
            task_type=TaskType.APPOINTMENT,
            duration_minutes=90,
            priority=Priority.LOW,
            scheduled_time=datetime(2026, 7, 5, 10, 30),
        )
    )

    # The two occurrences overlap (10:00-11:00 and 10:30-12:00) -- the next
    # free slot must be after BOTH end, not right after the first one ends.
    slot = scheduler.find_next_available_slot(
        pet, date(2026, 7, 5), 10, earliest=time(10, 0), latest=time(21, 0)
    )
    assert slot == datetime(2026, 7, 5, 12, 0)


def test_find_next_available_slot_returns_none_when_fully_booked():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    scheduler = Scheduler()

    pet.add_task(
        Task(
            title="All-day appointment",
            task_type=TaskType.APPOINTMENT,
            duration_minutes=600,
            priority=Priority.HIGH,
            scheduled_time=datetime(2026, 7, 5, 8, 0),
        )
    )

    slot = scheduler.find_next_available_slot(
        pet, date(2026, 7, 5), 30, earliest=time(8, 0), latest=time(18, 0)
    )
    assert slot is None


def test_auto_reschedule_missed_weekly_recovers_single_occurrence_without_shifting_series():
    # 2026-07-05 is a Sunday.
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    grooming = Task(
        title="Grooming",
        task_type=TaskType.APPOINTMENT,
        duration_minutes=30,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 9, 0),
        recurrence=Recurrence.WEEKLY,
    )
    pet.add_task(grooming)
    scheduler = Scheduler()

    recovered_date = scheduler.auto_reschedule_missed_weekly(grooming, pet, date(2026, 7, 5))

    assert recovered_date == date(2026, 7, 6)
    # The series anchor is untouched -- only the isolated occurrence moved.
    assert grooming.scheduled_time == datetime(2026, 7, 5, 9, 0)
    assert grooming.occurs_on(date(2026, 7, 12))


def test_auto_reschedule_missed_weekly_shifts_series_when_no_room_before_next_occurrence():
    pet = Pet(name="Biscuit", species="cat", birthdate=date(2021, 6, 1))
    grooming = Task(
        title="Grooming",
        task_type=TaskType.APPOINTMENT,
        duration_minutes=30,
        priority=Priority.MEDIUM,
        scheduled_time=datetime(2026, 7, 5, 9, 0),
        recurrence=Recurrence.WEEKLY,
    )
    pet.add_task(grooming)

    # Block every day between the miss and the next Sunday.
    for offset in range(1, 7):
        day = date(2026, 7, 5) + timedelta(days=offset)
        pet.add_task(
            Task(
                title=f"Busy {offset}",
                task_type=TaskType.APPOINTMENT,
                duration_minutes=1439,
                priority=Priority.LOW,
                scheduled_time=datetime(day.year, day.month, day.day, 0, 1),
            )
        )

    scheduler = Scheduler()
    recovered_date = scheduler.auto_reschedule_missed_weekly(grooming, pet, date(2026, 7, 5))

    assert recovered_date == date(2026, 7, 12)
    # The series anchor WAS shifted this time -- Phase 1 had nowhere to fit.
    assert grooming.scheduled_time.date() == date(2026, 7, 12)


def test_auto_reschedule_missed_weekly_returns_none_when_recurrence_ended():
    pet = Pet(name="Ziggy", species="dog", birthdate=date(2022, 1, 1))
    ending = Task(
        title="Meds",
        task_type=TaskType.MEDICATION,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 9, 0),
        recurrence=Recurrence.WEEKLY,
        recurrence_end_date=date(2026, 7, 5),
    )
    pet.add_task(ending)
    scheduler = Scheduler()

    assert scheduler.auto_reschedule_missed_weekly(ending, pet, date(2026, 7, 5)) is None


def test_auto_reschedule_missed_weekly_rejects_non_weekly_task():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    one_off = Task(
        title="Vet",
        task_type=TaskType.APPOINTMENT,
        duration_minutes=30,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 9, 0),
    )
    pet.add_task(one_off)
    scheduler = Scheduler()

    try:
        scheduler.auto_reschedule_missed_weekly(one_off, pet, date(2026, 7, 5))
        assert False, "expected ValueError"
    except ValueError:
        pass
