"""
PawPal+ - Backend Logic Layer
All core classes for managing pet care tasks and scheduling.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, Enum):
    WALK = "walk"
    FEEDING = "feeding"
    MEDICATION = "medication"
    APPOINTMENT = "appointment"
    GROOMING = "grooming"
    ENRICHMENT = "enrichment"
    OTHER = "other"


class TimeOfDay(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    ANY = "any"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """Represents a single pet care activity with priority and scheduling metadata."""

    title: str
    duration_minutes: int
    priority: Priority
    task_type: TaskType = TaskType.OTHER
    time_of_day: TimeOfDay = TimeOfDay.ANY
    recurring: bool = False
    notes: str = ""
    completed: bool = False

    def is_high_priority(self) -> bool:
        """Return True if this task has HIGH priority."""
        return self.priority == Priority.HIGH

    def priority_score(self) -> int:
        """Return a numeric sort key: HIGH=3, MEDIUM=2, LOW=1."""
        return {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}[self.priority]

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def __str__(self) -> str:
        """Return a concise one-line summary of this task."""
        status = "done" if self.completed else "todo"
        return (
            f"[{status}] {self.title} "
            f"({self.duration_minutes} min | {self.priority.value} | {self.task_type.value})"
        )


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Represents a pet and owns its list of care tasks."""

    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a Task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_title: str) -> bool:
        """Remove the first task whose title matches task_title. Returns True if removed."""
        for i, t in enumerate(self.tasks):
            if t.title == task_title:
                self.tasks.pop(i)
                return True
        return False

    def get_tasks_by_priority(self, priority: Priority) -> list[Task]:
        """Return all tasks that match the given priority level."""
        return [t for t in self.tasks if t.priority == priority]

    def get_tasks_by_type(self, task_type: TaskType) -> list[Task]:
        """Return all tasks that match the given task type."""
        return [t for t in self.tasks if t.task_type == task_type]

    def total_care_minutes(self) -> int:
        """Return the total duration in minutes required for all tasks."""
        return sum(t.duration_minutes for t in self.tasks)

    def __str__(self) -> str:
        """Return a one-line summary of this pet."""
        return (
            f"{self.name} ({self.species}, {self.age} yr) - "
            f"{len(self.tasks)} task(s), {self.total_care_minutes()} min total"
        )


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """Represents a pet owner with their time budget and pet roster."""

    name: str
    available_minutes_per_day: int
    preferred_morning_tasks: list[TaskType] = field(default_factory=list)
    preferred_evening_tasks: list[TaskType] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a Pet to this owner's pet list."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> bool:
        """Remove the first pet with the given name. Returns True if removed."""
        for i, p in enumerate(self.pets):
            if p.name == pet_name:
                self.pets.pop(i)
                return True
        return False

    def get_pet(self, pet_name: str) -> Optional[Pet]:
        """Return the Pet with the given name, or None if not found."""
        for p in self.pets:
            if p.name == pet_name:
                return p
        return None

    def total_tasks_across_pets(self) -> list[Task]:
        """Return a flat list of every Task from every pet."""
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    def __str__(self) -> str:
        """Return a one-line summary of this owner."""
        return (
            f"{self.name} | {len(self.pets)} pet(s) | "
            f"{self.available_minutes_per_day} min/day available"
        )


# ---------------------------------------------------------------------------
# ScheduledTask  (output of the Scheduler)
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A Task placed at a concrete time slot in the daily plan."""

    task: Task
    pet: Pet
    start_minute: int   # minutes since midnight (e.g. 480 = 8:00 AM)
    end_minute: int
    reason: str = ""

    def time_label(self) -> str:
        """Return a human-readable time range, e.g. '08:00 – 08:20'."""
        def fmt(m: int) -> str:
            return f"{m // 60:02d}:{m % 60:02d}"
        return f"{fmt(self.start_minute)} - {fmt(self.end_minute)}"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a prioritised daily care schedule for an owner's pets.

    Scheduling rules:
    - Tasks are grouped by time-of-day preference (MORNING → ANY → AFTERNOON → EVENING).
    - Within each group tasks are sorted HIGH priority first.
    - Tasks are placed sequentially; tasks that exceed available_minutes_per_day are skipped.
    - Overlapping time slots are flagged as conflicts.
    """

    _PRIORITY_SCORES = {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}

    # Earliest start minute (from midnight) for each time-of-day bucket
    _BUCKET_START = {
        TimeOfDay.MORNING: 480,    # 08:00
        TimeOfDay.AFTERNOON: 720,  # 12:00
        TimeOfDay.EVENING: 1080,   # 18:00
        TimeOfDay.ANY: 480,        # treated as MORNING
    }

    def __init__(self, owner: Owner) -> None:
        """Initialise the Scheduler with an Owner instance."""
        self.owner = owner
        self._schedule: list[ScheduledTask] = []
        self._conflicts: list[str] = []
        self._skipped: list[tuple[Task, Pet]] = []

    def sort_by_priority(self, pairs: list[tuple[Task, Pet]]) -> list[tuple[Task, Pet]]:
        """Return (Task, Pet) pairs sorted from highest to lowest priority score."""
        return sorted(pairs, key=lambda tp: self._PRIORITY_SCORES[tp[0].priority], reverse=True)

    def detect_conflicts(self, scheduled: list[ScheduledTask]) -> list[str]:
        """Return human-readable messages for every overlapping pair of ScheduledTasks."""
        conflicts: list[str] = []
        for i in range(len(scheduled)):
            for j in range(i + 1, len(scheduled)):
                a, b = scheduled[i], scheduled[j]
                if a.start_minute < b.end_minute and b.start_minute < a.end_minute:
                    conflicts.append(
                        f"CONFLICT: '{a.task.title}' ({a.time_label()}) overlaps "
                        f"'{b.task.title}' ({b.time_label()})"
                    )
        return conflicts

    def _fits_in_budget(self, minutes_used: int, task: Task) -> bool:
        """Return True if adding this task stays within the owner's daily time budget."""
        return minutes_used + task.duration_minutes <= self.owner.available_minutes_per_day

    def generate_schedule(self) -> list[ScheduledTask]:
        """
        Build and return the full daily schedule for all pets.

        Algorithm:
        1. Collect all (Task, Pet) pairs from every pet.
        2. Group pairs by their time_of_day preference.
        3. Process groups in order: MORNING, ANY, AFTERNOON, EVENING.
        4. Within each group sort by priority (HIGH first).
        5. Assign sequential start/end times; advance the cursor to the bucket's
           minimum start time when entering a new time-of-day group.
        6. Skip tasks whose addition would exceed available_minutes_per_day.
        7. Detect and store time-slot conflicts.
        """
        self._schedule = []
        self._conflicts = []
        self._skipped = []

        # Collect all (task, pet) pairs
        all_pairs: list[tuple[Task, Pet]] = [
            (task, pet)
            for pet in self.owner.pets
            for task in pet.tasks
        ]

        # Group by time_of_day
        groups: dict[TimeOfDay, list[tuple[Task, Pet]]] = {
            TimeOfDay.MORNING: [],
            TimeOfDay.AFTERNOON: [],
            TimeOfDay.EVENING: [],
            TimeOfDay.ANY: [],
        }
        for task, pet in all_pairs:
            groups[task.time_of_day].append((task, pet))

        # Process in chronological order; ANY tasks fill the morning window
        process_order = [
            (TimeOfDay.MORNING, self._BUCKET_START[TimeOfDay.MORNING]),
            (TimeOfDay.ANY, self._BUCKET_START[TimeOfDay.ANY]),
            (TimeOfDay.AFTERNOON, self._BUCKET_START[TimeOfDay.AFTERNOON]),
            (TimeOfDay.EVENING, self._BUCKET_START[TimeOfDay.EVENING]),
        ]

        cursor = 480          # current clock position (minutes since midnight)
        minutes_used = 0      # total care-time consumed so far

        for tod, bucket_start in process_order:
            # Advance clock to the bucket's earliest allowed start
            if cursor < bucket_start:
                cursor = bucket_start

            for task, pet in self.sort_by_priority(groups[tod]):
                if not self._fits_in_budget(minutes_used, task):
                    self._skipped.append((task, pet))
                    continue

                start = cursor
                end = start + task.duration_minutes
                reason = (
                    f"Priority: {task.priority.value}. "
                    f"Type: {task.task_type.value}. "
                    f"Placed in {tod.value if tod != TimeOfDay.ANY else 'morning'} slot."
                )
                self._schedule.append(
                    ScheduledTask(task=task, pet=pet, start_minute=start, end_minute=end, reason=reason)
                )
                cursor = end
                minutes_used += task.duration_minutes

        self._conflicts = self.detect_conflicts(self._schedule)
        return self._schedule

    def get_daily_plan(self) -> str:
        """
        Return a formatted string summarising the day's schedule,
        including skipped tasks and any conflict warnings.
        """
        if not self._schedule and not self._skipped:
            return "No schedule generated yet. Call generate_schedule() first."

        lines = [
            f"{'=' * 52}",
            f"  PawPal+ Daily Schedule for {self.owner.name}",
            f"  Available time: {self.owner.available_minutes_per_day} min",
            "=" * 52,
        ]

        if self._schedule:
            lines.append("\nSCHEDULED TASKS:")
            for st in sorted(self._schedule, key=lambda x: x.start_minute):
                lines.append(
                    f"  {st.time_label()}  [{st.pet.name}]  {st.task.title}"
                    f"  ({st.task.duration_minutes} min | {st.task.priority.value})"
                )
                lines.append(f"    > {st.reason}")
        else:
            lines.append("\nNo tasks could be scheduled.")

        if self._skipped:
            lines.append("\nSKIPPED (exceeded daily time limit):")
            for task, pet in self._skipped:
                lines.append(
                    f"  [skip] [{pet.name}] {task.title} "
                    f"({task.duration_minutes} min | {task.priority.value})"
                )

        if self._conflicts:
            lines.append("\nWARNINGS:")
            for c in self._conflicts:
                lines.append(f"  [!] {c}")

        lines.append("\n" + "=" * 52)
        return "\n".join(lines)

    def get_conflicts(self) -> list[str]:
        """Return conflict messages produced by the last generate_schedule() call."""
        return self._conflicts
