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
    """Represents a single pet care task."""

    title: str
    duration_minutes: int
    priority: Priority
    task_type: TaskType = TaskType.OTHER
    time_of_day: TimeOfDay = TimeOfDay.ANY
    recurring: bool = False
    notes: str = ""

    def is_high_priority(self) -> bool:
        """Return True if this task has high priority."""
        pass

    def priority_score(self) -> int:
        """Return a numeric score for sorting (higher = more urgent)."""
        pass

    def __str__(self) -> str:
        pass


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Represents a pet with its care task list."""

    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet's task list."""
        pass

    def remove_task(self, task_title: str) -> bool:
        """Remove a task by title. Return True if found and removed."""
        pass

    def get_tasks_by_priority(self, priority: Priority) -> list[Task]:
        """Return all tasks matching the given priority level."""
        pass

    def get_tasks_by_type(self, task_type: TaskType) -> list[Task]:
        """Return all tasks matching the given task type."""
        pass

    def total_care_minutes(self) -> int:
        """Return the total minutes required for all tasks."""
        pass

    def __str__(self) -> str:
        pass


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """Represents a pet owner with their preferences and pets."""

    name: str
    available_minutes_per_day: int
    preferred_morning_tasks: list[TaskType] = field(default_factory=list)
    preferred_evening_tasks: list[TaskType] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's profile."""
        pass

    def remove_pet(self, pet_name: str) -> bool:
        """Remove a pet by name. Return True if found and removed."""
        pass

    def get_pet(self, pet_name: str) -> Optional[Pet]:
        """Return a pet by name, or None if not found."""
        pass

    def total_tasks_across_pets(self) -> list[Task]:
        """Return a flat list of all tasks across all pets."""
        pass

    def __str__(self) -> str:
        pass


# ---------------------------------------------------------------------------
# ScheduledTask  (output of the Scheduler)
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A Task placed at a specific time slot in the daily plan."""

    task: Task
    pet: Pet
    start_minute: int
    end_minute: int
    reason: str = ""

    def time_label(self) -> str:
        """Return a human-readable time range string, e.g. '08:00 - 08:20'."""
        pass


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a daily care schedule for an owner's pets.

    Scheduling rules:
    - Tasks are sorted by priority (HIGH first).
    - Tasks are fit within the owner's available_minutes_per_day.
    - Time-of-day preferences are respected where possible.
    - Conflicts (overlapping time slots) are detected and reported.
    """

    PRIORITY_ORDER = {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}

    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self._schedule: list[ScheduledTask] = []
        self._conflicts: list[str] = []

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted from highest to lowest priority."""
        pass

    def detect_conflicts(self, scheduled: list[ScheduledTask]) -> list[str]:
        """
        Check for time-slot overlaps in a list of ScheduledTasks.
        Return a list of human-readable conflict descriptions.
        """
        pass

    def _fits_in_slot(self, task: Task, current_minute: int, limit: int) -> bool:
        """Return True if the task fits within the remaining available time."""
        pass

    def generate_schedule(self) -> list[ScheduledTask]:
        """
        Build and return a full daily schedule for all pets.

        Algorithm:
        1. Collect all tasks from all pets.
        2. Sort by priority.
        3. Assign start/end times sequentially within available_minutes_per_day.
        4. Skip tasks that would exceed the daily time limit.
        5. Detect and store any conflicts.
        """
        pass

    def get_daily_plan(self) -> str:
        """
        Return a formatted string summarising the day's schedule,
        including skipped tasks and any conflict warnings.
        """
        pass

    def get_conflicts(self) -> list[str]:
        """Return the list of conflict messages from the last generate_schedule() call."""
        return self._conflicts
