"""
Automated tests for PawPal+ core logic.
Run with:  python -m pytest
"""

import pytest
from pawpal_system import (
    Owner, Pet, Task, Scheduler, ScheduledTask,
    Priority, TaskType, TimeOfDay,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(
    title: str = "Test Task",
    duration: int = 15,
    priority: Priority = Priority.MEDIUM,
    task_type: TaskType = TaskType.OTHER,
    time_of_day: TimeOfDay = TimeOfDay.ANY,
) -> Task:
    return Task(
        title=title,
        duration_minutes=duration,
        priority=priority,
        task_type=task_type,
        time_of_day=time_of_day,
    )


def make_pet(name: str = "Buddy", species: str = "dog", age: int = 2) -> Pet:
    return Pet(name=name, species=species, age=age)


def make_owner(name: str = "Alex", available_minutes: int = 120) -> Owner:
    return Owner(name=name, available_minutes_per_day=available_minutes)


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

class TestTask:

    def test_mark_complete_changes_status(self):
        """mark_complete() should flip completed from False to True."""
        task = make_task()
        assert task.completed is False
        task.mark_complete()
        assert task.completed is True

    def test_mark_complete_is_idempotent(self):
        """Calling mark_complete() twice should still leave completed as True."""
        task = make_task()
        task.mark_complete()
        task.mark_complete()
        assert task.completed is True

    def test_is_high_priority_true(self):
        """is_high_priority() returns True for HIGH tasks."""
        task = make_task(priority=Priority.HIGH)
        assert task.is_high_priority() is True

    def test_is_high_priority_false_for_medium(self):
        """is_high_priority() returns False for MEDIUM tasks."""
        task = make_task(priority=Priority.MEDIUM)
        assert task.is_high_priority() is False

    def test_priority_score_ordering(self):
        """HIGH score > MEDIUM score > LOW score."""
        high = make_task(priority=Priority.HIGH).priority_score()
        med = make_task(priority=Priority.MEDIUM).priority_score()
        low = make_task(priority=Priority.LOW).priority_score()
        assert high > med > low

    def test_str_includes_title(self):
        """__str__ should include the task title."""
        task = make_task(title="Morning Walk")
        assert "Morning Walk" in str(task)

    def test_str_shows_done_after_complete(self):
        """__str__ should show 'done' after mark_complete() is called."""
        task = make_task(title="Walk")
        task.mark_complete()
        assert "done" in str(task)


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

class TestPet:

    def test_add_task_increases_count(self):
        """Adding a task to a Pet should increase its task list by 1."""
        pet = make_pet()
        initial = len(pet.tasks)
        pet.add_task(make_task())
        assert len(pet.tasks) == initial + 1

    def test_add_multiple_tasks(self):
        """Adding three tasks should result in a task count of 3."""
        pet = make_pet()
        for i in range(3):
            pet.add_task(make_task(title=f"Task {i}"))
        assert len(pet.tasks) == 3

    def test_remove_task_decreases_count(self):
        """Removing a task by title should reduce the list by 1."""
        pet = make_pet()
        pet.add_task(make_task(title="Walk"))
        pet.add_task(make_task(title="Feed"))
        removed = pet.remove_task("Walk")
        assert removed is True
        assert len(pet.tasks) == 1
        assert pet.tasks[0].title == "Feed"

    def test_remove_nonexistent_task_returns_false(self):
        """Removing a task that does not exist should return False."""
        pet = make_pet()
        assert pet.remove_task("Ghost Task") is False

    def test_total_care_minutes(self):
        """total_care_minutes() should sum all task durations."""
        pet = make_pet()
        pet.add_task(make_task(duration=10))
        pet.add_task(make_task(duration=20))
        assert pet.total_care_minutes() == 30

    def test_get_tasks_by_priority(self):
        """get_tasks_by_priority() should return only matching tasks."""
        pet = make_pet()
        pet.add_task(make_task(title="High", priority=Priority.HIGH))
        pet.add_task(make_task(title="Low", priority=Priority.LOW))
        high_tasks = pet.get_tasks_by_priority(Priority.HIGH)
        assert len(high_tasks) == 1
        assert high_tasks[0].title == "High"

    def test_get_tasks_by_type(self):
        """get_tasks_by_type() should return only matching task types."""
        pet = make_pet()
        pet.add_task(make_task(title="Walk", task_type=TaskType.WALK))
        pet.add_task(make_task(title="Feed", task_type=TaskType.FEEDING))
        walks = pet.get_tasks_by_type(TaskType.WALK)
        assert len(walks) == 1
        assert walks[0].title == "Walk"


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

class TestOwner:

    def test_add_pet_increases_count(self):
        """Adding a pet should increase the owner's pet list by 1."""
        owner = make_owner()
        owner.add_pet(make_pet(name="Mochi"))
        assert len(owner.pets) == 1

    def test_get_pet_returns_correct_pet(self):
        """get_pet() should return the pet with the matching name."""
        owner = make_owner()
        owner.add_pet(make_pet(name="Luna"))
        result = owner.get_pet("Luna")
        assert result is not None
        assert result.name == "Luna"

    def test_get_pet_returns_none_for_missing(self):
        """get_pet() should return None for an unknown pet name."""
        owner = make_owner()
        assert owner.get_pet("Dino") is None

    def test_total_tasks_across_pets(self):
        """total_tasks_across_pets() should flatten all tasks from all pets."""
        owner = make_owner()
        pet1 = make_pet(name="A")
        pet2 = make_pet(name="B")
        pet1.add_task(make_task())
        pet1.add_task(make_task())
        pet2.add_task(make_task())
        owner.add_pet(pet1)
        owner.add_pet(pet2)
        assert len(owner.total_tasks_across_pets()) == 3


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

class TestScheduler:

    def _make_owner_with_tasks(self, available: int, tasks: list[Task]) -> Owner:
        owner = make_owner(available_minutes=available)
        pet = make_pet()
        for t in tasks:
            pet.add_task(t)
        owner.add_pet(pet)
        return owner

    def test_generate_schedule_returns_list(self):
        """generate_schedule() should return a list of ScheduledTask objects."""
        owner = self._make_owner_with_tasks(60, [make_task(duration=10)])
        scheduler = Scheduler(owner)
        result = scheduler.generate_schedule()
        assert isinstance(result, list)
        assert all(isinstance(s, ScheduledTask) for s in result)

    def test_scheduler_respects_time_limit(self):
        """Tasks that would exceed available_minutes_per_day should be skipped."""
        owner = self._make_owner_with_tasks(
            30,
            [make_task(title="T1", duration=25), make_task(title="T2", duration=20)],
        )
        scheduler = Scheduler(owner)
        schedule = scheduler.generate_schedule()
        total = sum(s.task.duration_minutes for s in schedule)
        assert total <= 30

    def test_scheduler_sorts_high_priority_first(self):
        """HIGH priority tasks should be scheduled before LOW priority tasks."""
        owner = self._make_owner_with_tasks(
            120,
            [
                make_task(title="Low Task", duration=10, priority=Priority.LOW),
                make_task(title="High Task", duration=10, priority=Priority.HIGH),
            ],
        )
        scheduler = Scheduler(owner)
        schedule = scheduler.generate_schedule()
        titles = [s.task.title for s in schedule]
        assert titles.index("High Task") < titles.index("Low Task")

    def test_scheduled_tasks_have_valid_time_range(self):
        """Each ScheduledTask should have end_minute > start_minute."""
        owner = self._make_owner_with_tasks(60, [make_task(duration=15)])
        scheduler = Scheduler(owner)
        for st in scheduler.generate_schedule():
            assert st.end_minute > st.start_minute

    def test_no_conflicts_in_sequential_schedule(self):
        """A straightforward sequential schedule should produce no conflicts."""
        owner = self._make_owner_with_tasks(
            60,
            [make_task(title="T1", duration=10), make_task(title="T2", duration=10)],
        )
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert scheduler.get_conflicts() == []

    def test_get_daily_plan_contains_owner_name(self):
        """get_daily_plan() output should include the owner's name."""
        owner = make_owner(name="Jordan")
        pet = make_pet()
        pet.add_task(make_task())
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert "Jordan" in scheduler.get_daily_plan()

    def test_morning_tasks_scheduled_before_afternoon(self):
        """MORNING tasks should start before AFTERNOON tasks."""
        owner = make_owner(available_minutes=120)
        pet = make_pet()
        pet.add_task(make_task(title="Afternoon Task", duration=10, time_of_day=TimeOfDay.AFTERNOON))
        pet.add_task(make_task(title="Morning Task", duration=10, time_of_day=TimeOfDay.MORNING))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        schedule = scheduler.generate_schedule()
        by_title = {s.task.title: s for s in schedule}
        assert by_title["Morning Task"].start_minute < by_title["Afternoon Task"].start_minute
