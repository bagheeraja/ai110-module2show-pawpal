"""Terminal testing ground for pawpal_system.py -- not the final UI.

Creates an owner with two pets and a handful of tasks, then prints
today's schedule to verify the backend logic works end to end.
"""

from datetime import date, datetime, time

from pawpal_system import Owner, Pet, Priority, Recurrence, Scheduler, Task, TaskType

TODAY = date.today()


def at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(TODAY, time(hour, minute))


def main() -> None:
    owner = Owner(name="Jordan Ames", email="jordan@example.com")

    mochi = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    biscuit = Pet(name="Biscuit", species="cat", birthdate=date(2021, 6, 1))
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    # Added out of chronological order on purpose, to exercise sort_by_time.
    biscuit.add_task(
        Task(
            title="Vet checkup",
            task_type=TaskType.APPOINTMENT,
            duration_minutes=30,
            priority=Priority.MEDIUM,
            scheduled_time=at(14, 0),
        )
    )
    mochi.add_task(
        Task(
            title="Morning walk",
            task_type=TaskType.WALK,
            duration_minutes=20,
            priority=Priority.HIGH,
            scheduled_time=at(8, 0),
        )
    )
    biscuit.add_task(
        Task(
            title="Flea medication",
            task_type=TaskType.MEDICATION,
            duration_minutes=5,
            priority=Priority.MEDIUM,
            scheduled_time=at(9, 0),
        )
    )
    # Deliberately overlaps Mochi's Morning walk (8:00-8:20) to demonstrate conflict detection.
    mochi.add_task(
        Task(
            title="Photo session",
            task_type=TaskType.APPOINTMENT,
            duration_minutes=15,
            priority=Priority.LOW,
            scheduled_time=at(8, 0),
        )
    )
    breakfast = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=at(7, 30),
        recurrence=Recurrence.DAILY,
    )
    mochi.add_task(breakfast)

    scheduler = Scheduler()
    plan = scheduler.build_daily_plan_for_owner(owner, TODAY)

    def print_occurrences(occurrences) -> None:
        for occurrence in occurrences:
            start = occurrence.start_time.strftime("%I:%M %p")
            print(
                f"{start}  {occurrence.pet.name:<8} {occurrence.task.title:<18} "
                f"[{occurrence.task.priority.name}]"
            )

    print(f"Today's Schedule -- {TODAY.isoformat()} (priority order)")
    print("=" * 40)
    print_occurrences(plan)

    print("\nSorted by time")
    print("=" * 40)
    print_occurrences(scheduler.sort_by_time(plan))

    print("\nMochi's tasks only")
    print("=" * 40)
    print_occurrences(scheduler.filter_occurrences(plan, pet_name="Mochi"))

    print("\nNot-yet-completed tasks")
    print("=" * 40)
    print_occurrences(scheduler.filter_occurrences(plan, completed=False))

    warnings = scheduler.get_conflict_warnings(plan)
    if warnings:
        print("\nConflicts detected:")
        for warning in warnings:
            print(f"  {warning}")

    next_date = breakfast.mark_complete(TODAY)
    print(
        f"\nMarked '{breakfast.title}' complete for {TODAY.isoformat()} -- "
        f"next occurrence: {next_date.isoformat() if next_date else 'none'}"
    )


if __name__ == "__main__":
    main()
