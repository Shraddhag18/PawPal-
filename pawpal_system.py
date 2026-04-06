"""
PawPal+ - Backend Logic Layer
All core classes for managing pet care tasks and scheduling.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from enum import Enum
from pathlib import Path
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
    # Optional explicit start time in "HH:MM" format (e.g. "08:30").
    # Used by sort_by_time() and detect_time_conflicts().
    scheduled_time: Optional[str] = None
    # Tracks which calendar date this task instance is due on.
    # Auto-advances by 1 day when next_occurrence() is called.
    due_date: Optional[date] = None

    def is_high_priority(self) -> bool:
        """Return True if this task has HIGH priority."""
        return self.priority == Priority.HIGH

    def priority_score(self) -> int:
        """Return a numeric sort key: HIGH=3, MEDIUM=2, LOW=1."""
        return {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}[self.priority]

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def next_occurrence(self) -> Task:
        """
        Return a new Task instance for the next day, resetting completion status.
        Raises ValueError if called on a non-recurring task.
        The new due_date is (self.due_date or today) + 1 day.
        """
        if not self.recurring:
            raise ValueError(f"'{self.title}' is not a recurring task.")
        next_date = (self.due_date or date.today()) + timedelta(days=1)
        return replace(self, completed=False, due_date=next_date)

    # ------------------------------------------------------------------
    # Challenge 1 — Weighted priority score
    # ------------------------------------------------------------------

    def weighted_score(self) -> float:
        """
        Compute a multi-factor urgency score for smarter scheduling.

        Formula:
          base_priority  (HIGH=100, MEDIUM=50, LOW=10)
        + task_type_bonus (medication=30, appointment=25, feeding=20,
                           walk=10, grooming=5, enrichment=3, other=0)
        + overdue_bonus  (15 pts per overdue day, capped at 50)
        + recurring_bonus (5 pts if the task recurs daily)

        Higher scores are scheduled first by sort_by_weighted_priority().
        """
        base = {Priority.HIGH: 100, Priority.MEDIUM: 50, Priority.LOW: 10}[self.priority]

        type_bonus = {
            TaskType.MEDICATION:   30,
            TaskType.APPOINTMENT:  25,
            TaskType.FEEDING:      20,
            TaskType.WALK:         10,
            TaskType.GROOMING:      5,
            TaskType.ENRICHMENT:    3,
            TaskType.OTHER:         0,
        }[self.task_type]

        overdue_bonus = 0
        if self.due_date and self.due_date < date.today():
            days_overdue = (date.today() - self.due_date).days
            overdue_bonus = min(days_overdue * 15, 50)

        recurring_bonus = 5 if self.recurring else 0

        return float(base + type_bonus + overdue_bonus + recurring_bonus)

    # ------------------------------------------------------------------
    # Challenge 2 — JSON serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise this Task to a JSON-safe dictionary."""
        return {
            "title":            self.title,
            "duration_minutes": self.duration_minutes,
            "priority":         self.priority.value,
            "task_type":        self.task_type.value,
            "time_of_day":      self.time_of_day.value,
            "recurring":        self.recurring,
            "notes":            self.notes,
            "completed":        self.completed,
            "scheduled_time":   self.scheduled_time,
            "due_date":         self.due_date.isoformat() if self.due_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Reconstruct a Task from a dictionary produced by to_dict()."""
        return cls(
            title=data["title"],
            duration_minutes=data["duration_minutes"],
            priority=Priority(data["priority"]),
            task_type=TaskType(data["task_type"]),
            time_of_day=TimeOfDay(data["time_of_day"]),
            recurring=data.get("recurring", False),
            notes=data.get("notes", ""),
            completed=data.get("completed", False),
            scheduled_time=data.get("scheduled_time"),
            due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
        )

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

    def to_dict(self) -> dict:
        """Serialise this Pet (and all its Tasks) to a JSON-safe dictionary."""
        return {
            "name":    self.name,
            "species": self.species,
            "age":     self.age,
            "tasks":   [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Reconstruct a Pet (and its Tasks) from a dictionary produced by to_dict()."""
        pet = cls(name=data["name"], species=data["species"], age=data["age"])
        pet.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        return pet

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

    def to_dict(self) -> dict:
        """Serialise this Owner (and all pets/tasks) to a JSON-safe dictionary."""
        return {
            "name":                      self.name,
            "available_minutes_per_day": self.available_minutes_per_day,
            "preferred_morning_tasks":   [t.value for t in self.preferred_morning_tasks],
            "preferred_evening_tasks":   [t.value for t in self.preferred_evening_tasks],
            "pets":                      [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Reconstruct an Owner (and all pets/tasks) from a dictionary produced by to_dict()."""
        owner = cls(
            name=data["name"],
            available_minutes_per_day=data["available_minutes_per_day"],
            preferred_morning_tasks=[TaskType(t) for t in data.get("preferred_morning_tasks", [])],
            preferred_evening_tasks=[TaskType(t) for t in data.get("preferred_evening_tasks", [])],
        )
        owner.pets = [Pet.from_dict(p) for p in data.get("pets", [])]
        return owner

    def save_to_json(self, path: str | Path = "data.json") -> None:
        """
        Persist the entire owner graph (pets + tasks) to a JSON file.
        Creates or overwrites the file at the given path.
        """
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load_from_json(cls, path: str | Path = "data.json") -> Owner:
        """
        Load an Owner (and all pets/tasks) from a JSON file written by save_to_json().
        Raises FileNotFoundError if the file does not exist.
        """
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

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

    def sort_by_time(self, pairs: list[tuple[Task, Pet]]) -> list[tuple[Task, Pet]]:
        """
        Sort (Task, Pet) pairs chronologically by explicit scheduled_time ("HH:MM").
        Tasks without a scheduled_time fall back to their time_of_day bucket default
        (morning=08:00, afternoon=12:00, evening=18:00, any=23:59).
        Uses a lambda key so Python's sorted() compares plain strings lexicographically,
        which works correctly for zero-padded "HH:MM" values.
        """
        _bucket_default = {
            TimeOfDay.MORNING: "08:00",
            TimeOfDay.AFTERNOON: "12:00",
            TimeOfDay.EVENING: "18:00",
            TimeOfDay.ANY: "23:59",
        }
        return sorted(
            pairs,
            key=lambda tp: tp[0].scheduled_time or _bucket_default[tp[0].time_of_day],
        )

    def filter_tasks(
        self,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[tuple[Task, Pet]]:
        """
        Return (Task, Pet) pairs filtered by optional criteria.
        - pet_name: if given, only include tasks belonging to that pet.
        - completed: if True return only completed tasks; if False return only pending tasks;
          if None (default) return tasks regardless of completion status.
        """
        results: list[tuple[Task, Pet]] = []
        for pet in self.owner.pets:
            if pet_name is not None and pet.name != pet_name:
                continue
            for task in pet.tasks:
                if completed is not None and task.completed != completed:
                    continue
                results.append((task, pet))
        return results

    def detect_time_conflicts(self) -> list[str]:
        """
        Detect overlaps among tasks that have an explicit scheduled_time set.
        Two tasks conflict when their time windows overlap:
            task_a.start < task_b.end  AND  task_b.start < task_a.end
        Returns a list of warning strings (empty list = no conflicts).
        This is a lightweight O(n^2) check that warns rather than crashes.
        """
        def to_minutes(hhmm: str) -> int:
            """Convert 'HH:MM' string to total minutes since midnight."""
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        timed: list[tuple[Task, Pet]] = [
            (task, pet)
            for pet in self.owner.pets
            for task in pet.tasks
            if task.scheduled_time is not None
        ]

        conflicts: list[str] = []
        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                task_a, pet_a = timed[i]
                task_b, pet_b = timed[j]
                start_a = to_minutes(task_a.scheduled_time)
                end_a = start_a + task_a.duration_minutes
                start_b = to_minutes(task_b.scheduled_time)
                end_b = start_b + task_b.duration_minutes
                if start_a < end_b and start_b < end_a:
                    conflicts.append(
                        f"[!] CONFLICT: [{pet_a.name}] '{task_a.title}' "
                        f"({task_a.scheduled_time}, {task_a.duration_minutes} min) overlaps "
                        f"[{pet_b.name}] '{task_b.title}' "
                        f"({task_b.scheduled_time}, {task_b.duration_minutes} min)"
                    )
        return conflicts

    def get_recurring_next_occurrences(self) -> list[tuple[Task, Pet]]:
        """
        Return (next_Task, Pet) pairs for every recurring task that is already completed.
        Call this after marking recurring tasks complete to get the next-day instances.
        """
        results: list[tuple[Task, Pet]] = []
        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.recurring and task.completed:
                    results.append((task.next_occurrence(), pet))
        return results

    # ------------------------------------------------------------------
    # Challenge 1 — Advanced algorithmic capabilities
    # ------------------------------------------------------------------

    def sort_by_weighted_priority(
        self, pairs: list[tuple[Task, Pet]]
    ) -> list[tuple[Task, Pet]]:
        """
        Sort (Task, Pet) pairs by each task's weighted_score() — highest first.

        weighted_score() combines base priority, task-type urgency, overdue penalty,
        and a recurring-task bonus into a single float, producing a richer ordering
        than a flat HIGH/MEDIUM/LOW sort.  For example, an overdue MEDIUM medication
        outranks a non-overdue HIGH enrichment activity.
        """
        return sorted(pairs, key=lambda tp: tp[0].weighted_score(), reverse=True)

    def find_next_slot(
        self, duration_minutes: int, after_minute: int = 480
    ) -> Optional[int]:
        """
        Find the earliest free start minute for a task of given duration.

        Scans the already-generated schedule for gaps, starting the search at
        after_minute (default 08:00 = minute 480).  Returns the start minute
        of the first gap that fits, or None if no gap exists before midnight.

        Must call generate_schedule() first; returns None if schedule is empty
        and after_minute + duration_minutes > 1440.

        Example:
            slot = scheduler.find_next_slot(30)  # next free 30-min window
            if slot:
                print(f"Next free slot starts at {slot // 60:02d}:{slot % 60:02d}")
        """
        occupied = sorted(
            [(st.start_minute, st.end_minute) for st in self._schedule],
            key=lambda x: x[0],
        )

        cursor = after_minute
        for block_start, block_end in occupied:
            if cursor + duration_minutes <= block_start:
                return cursor          # gap before this block fits
            cursor = max(cursor, block_end)   # jump past this block

        # Check after all blocks
        if cursor + duration_minutes <= 1440:   # 1440 = midnight
            return cursor
        return None

    def get_conflicts(self) -> list[str]:
        """Return conflict messages produced by the last generate_schedule() call."""
        return self._conflicts
