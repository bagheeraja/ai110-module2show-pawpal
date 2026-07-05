"""PawPal+ logic layer.

This module holds the backend classes for PawPal+: Owner, Pet, Task, the
supporting enums, and the Scheduler. This is a skeleton generated from the
UML in diagrams/uml.mmd -- method bodies are stubs and will be filled in
during the implementation pass.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum, auto


class TaskType(Enum):
    FEEDING = auto()
    WALK = auto()
    MEDICATION = auto()
    APPOINTMENT = auto()


class Priority(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class Recurrence(Enum):
    NONE = auto()
    DAILY = auto()
    WEEKLY = auto()


@dataclass
class Task:
    """A task *template*.

    ``scheduled_time`` is the anchor for the task: for a one-off task it is
    the actual occurrence; for a recurring task it supplies the time-of-day
    (and, for WEEKLY, the weekday) that every generated occurrence reuses.
    Completion is tracked per calendar date in ``completed_dates`` rather
    than as a single bool, so marking one occurrence of a recurring task
    done doesn't silently complete the whole series.

    A 0-minute duration is rejected -- every task must occupy some real time
    to be schedulable/conflict-checkable. If ``scheduled_time + duration``
    crosses midnight, the occurrence is considered to belong to *both* the
    start date and the rollover (end) date, so it shows up on both days'
    plans -- see ``occurs_on``.
    """

    title: str
    task_type: TaskType
    duration_minutes: int
    priority: Priority
    scheduled_time: datetime
    recurrence: Recurrence = Recurrence.NONE
    recurrence_end_date: date | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    completed_dates: set[date] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be greater than 0")

    def mark_complete(self, occurrence_date: date | None = None) -> None:
        """Mark the occurrence on ``occurrence_date`` complete (defaults to this task's own date)."""
        pass

    def is_complete_on(self, occurrence_date: date | None = None) -> bool:
        """Whether the occurrence on ``occurrence_date`` has been completed."""
        pass

    def occurs_on(self, target_date: date) -> bool:
        """Whether this task (recurring or not) has an occurrence touching ``target_date``.

        True if ``target_date`` matches the occurrence's start date or its
        rollover end date (see class docstring), the recurrence pattern
        includes that date, and (for recurring tasks) ``target_date`` is on
        or before ``recurrence_end_date`` when one is set.
        """
        pass

    def reschedule(self, new_scheduled_time: datetime) -> None:
        """Move a missed/overdue one-off task to a new time.

        Intended for the "missed task" recovery flow: an owner sees an
        overdue occurrence (see Scheduler.get_missed_tasks) and reschedules
        it instead of leaving it permanently missed. For a recurring task,
        this shifts the anchor for all future occurrences -- rescheduling a
        single occurrence in a series is not supported by this model.
        """
        pass

    def conflicts_with(self, other: "Task", *, on: date) -> bool:
        """Whether this task's occurrence on ``on`` overlaps ``other``'s occurrence on ``on``.

        Overlap is strict: if one occurrence ends exactly when the other
        begins, that is NOT a conflict (touching, not overlapping).
        """
        pass


@dataclass(frozen=True)
class TaskOccurrence:
    """A single dated instance of a Task, produced by the Scheduler.

    Occurrences are ephemeral (never stored on Pet.tasks) -- they're what
    gets displayed in a daily plan. Completion reads/writes go back through
    to the underlying template so there's one source of truth per date.
    """

    task: Task
    occurrence_date: date
    start_time: datetime
    end_time: datetime

    @property
    def completed(self) -> bool:
        return self.task.is_complete_on(self.occurrence_date)

    def mark_complete(self) -> None:
        self.task.mark_complete(self.occurrence_date)


@dataclass
class Pet:
    name: str
    species: str
    birthdate: date
    preferences: dict = field(default_factory=dict)
    tasks: list[Task] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task_id: str) -> None:
        """Remove a task template by id (e.g. an owner deleting a mis-entered task)."""
        pass

    def get_tasks_for_date(self, target_date: date) -> list[TaskOccurrence]:
        """Templates whose recurrence includes target_date, expanded via Task.occurs_on.

        Returns [] if this pet has no tasks -- an empty result, not an error.
        This only filters/expands -- ordering, conflict-checking, and any
        time-budget constraints are Scheduler's job, not Pet's.
        """
        pass


@dataclass
class Owner:
    name: str
    email: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def get_pet(self, pet_id: str) -> Pet | None:
        """Look up a pet by id -- names aren't unique (e.g. two pets both named "Max")."""
        pass


class Scheduler:
    """Stateless scheduling logic that operates on a Pet's tasks.

    Owns ordering, conflict-checking, and turning templates into dated
    occurrences. Pet.get_tasks_for_date only filters/expands via
    Task.occurs_on -- it does not sort or resolve conflicts.
    """

    def build_daily_plan(
        self,
        pet: Pet,
        target_date: date,
        *,
        time_budget_minutes: int | None = None,
    ) -> list[TaskOccurrence]:
        """Not-yet-completed occurrences for target_date.

        Ordering: by Priority (HIGH first), and alphabetically by title as
        the initial tie-break within a priority tier. Already-completed
        occurrences (``occurrence.completed``) are excluded -- a finished
        walk shouldn't clutter the plan. If ``time_budget_minutes`` is
        given and the sorted occurrences would exceed it, lower-priority
        occurrences are dropped from the end once the running total would
        exceed the budget. Returns [] for a pet with no tasks/occurrences
        that day -- never raises for the empty case.
        """
        pass

    def detect_conflicts(
        self, occurrences: list[TaskOccurrence]
    ) -> list[tuple[TaskOccurrence, TaskOccurrence]]:
        """Pairs of occurrences whose time windows strictly overlap.

        Two occurrences that merely touch (one ends exactly when the other
        starts) are NOT a conflict. Two occurrences generated from the same
        Task (matching task.id) are never compared against each other.
        """
        pass

    def expand_recurring(self, task: Task, target_date: date) -> TaskOccurrence | None:
        """The occurrence of task on target_date, or None if it doesn't occur that day.

        Delegates the occurs-on-this-date decision to Task.occurs_on, which
        accounts for recurrence_end_date and midnight rollover.
        """
        pass

    def get_missed_tasks(self, pet: Pet, as_of: date) -> list[TaskOccurrence]:
        """Past occurrences (strictly before ``as_of``) that were never completed.

        Surfaces "missed/overdue" tasks so the caller (e.g. the UI) can
        offer to reschedule them via Task.reschedule rather than letting
        them silently disappear once their date has passed.
        """
        pass
