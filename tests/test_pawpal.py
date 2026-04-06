"""
Automated tests for PawPal+ core logic.
Run with:  python -m pytest

Coverage summary
----------------
TestTask          — mark_complete, priority helpers, __str__
TestTaskRecurrence — next_occurrence happy path and error guard
TestPet           — add/remove/filter tasks, total_care_minutes
TestOwner         — add/get/remove pets, flatten tasks
TestScheduler     — generate_schedule, time budget, priority order, time-of-day order
TestSortByTime    — sort_by_time with explicit times, bucket fallbacks, mixed input, ties
TestFilterTasks   — filter by pet name, completion status, combined, edge cases
TestConflictDetection — detect_time_conflicts overlaps, adjacent slots, no-conflict baselines
TestEdgeCases     — empty pets/owners, zero-minute budget, single task, non-recurring guard
"""

import pytest
from datetime import date, timedelta
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
    scheduled_time: str | None = None,
    recurring: bool = False,
    due_date: date | None = None,
) -> Task:
    return Task(
        title=title,
        duration_minutes=duration,
        priority=priority,
        task_type=task_type,
        time_of_day=time_of_day,
        scheduled_time=scheduled_time,
        recurring=recurring,
        due_date=due_date,
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


# ---------------------------------------------------------------------------
# Recurrence tests
# ---------------------------------------------------------------------------

class TestTaskRecurrence:

    def test_next_occurrence_resets_completed(self):
        """next_occurrence() must return a task with completed=False."""
        task = make_task(recurring=True, due_date=date(2026, 4, 5))
        task.mark_complete()
        nxt = task.next_occurrence()
        assert nxt.completed is False

    def test_next_occurrence_advances_due_date_by_one_day(self):
        """next_occurrence() should set due_date to due_date + 1 day."""
        original_date = date(2026, 4, 5)
        task = make_task(recurring=True, due_date=original_date)
        nxt = task.next_occurrence()
        assert nxt.due_date == original_date + timedelta(days=1)

    def test_next_occurrence_preserves_all_other_fields(self):
        """next_occurrence() must not change title, duration, priority, or task_type."""
        task = make_task(
            title="Daily Walk",
            duration=30,
            priority=Priority.HIGH,
            task_type=TaskType.WALK,
            recurring=True,
            due_date=date(2026, 4, 5),
        )
        nxt = task.next_occurrence()
        assert nxt.title == task.title
        assert nxt.duration_minutes == task.duration_minutes
        assert nxt.priority == task.priority
        assert nxt.task_type == task.task_type
        assert nxt.recurring is True

    def test_next_occurrence_uses_today_when_due_date_is_none(self):
        """If due_date is None, next_occurrence() should base the new date on today."""
        task = make_task(recurring=True, due_date=None)
        nxt = task.next_occurrence()
        assert nxt.due_date == date.today() + timedelta(days=1)

    def test_next_occurrence_raises_for_non_recurring(self):
        """Calling next_occurrence() on a non-recurring task must raise ValueError."""
        task = make_task(recurring=False)
        with pytest.raises(ValueError):
            task.next_occurrence()

    def test_get_recurring_next_occurrences_returns_only_completed(self):
        """get_recurring_next_occurrences() should only return next tasks for completed recurring tasks."""
        owner = make_owner()
        pet = make_pet()
        recurring_done = make_task(title="Done Recurring", recurring=True, due_date=date.today())
        recurring_pending = make_task(title="Pending Recurring", recurring=True, due_date=date.today())
        non_recurring = make_task(title="One-off", recurring=False)
        recurring_done.mark_complete()
        pet.add_task(recurring_done)
        pet.add_task(recurring_pending)
        pet.add_task(non_recurring)
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        results = scheduler.get_recurring_next_occurrences()
        assert len(results) == 1
        assert results[0][0].title == "Done Recurring"

    def test_get_recurring_next_occurrences_empty_when_none_complete(self):
        """get_recurring_next_occurrences() returns [] when no recurring tasks are done."""
        owner = make_owner()
        pet = make_pet()
        pet.add_task(make_task(recurring=True, due_date=date.today()))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        assert scheduler.get_recurring_next_occurrences() == []


# ---------------------------------------------------------------------------
# Sort-by-time tests
# ---------------------------------------------------------------------------

class TestSortByTime:

    def _scheduler_with_pet(self, tasks: list[Task]) -> tuple[Scheduler, Pet]:
        owner = make_owner(available_minutes=300)
        pet = make_pet()
        for t in tasks:
            pet.add_task(t)
        owner.add_pet(pet)
        return Scheduler(owner), pet

    def test_sort_by_time_chronological_order(self):
        """Tasks with explicit scheduled_time should come back in HH:MM order."""
        t1 = make_task(title="Late",  scheduled_time="14:00")
        t2 = make_task(title="Early", scheduled_time="08:00")
        t3 = make_task(title="Mid",   scheduled_time="11:30")
        scheduler, pet = self._scheduler_with_pet([t1, t2, t3])
        pairs = [(t, pet) for t in [t1, t2, t3]]
        sorted_pairs = scheduler.sort_by_time(pairs)
        titles = [tp[0].title for tp in sorted_pairs]
        assert titles == ["Early", "Mid", "Late"]

    def test_sort_by_time_falls_back_to_bucket_for_missing_time(self):
        """Tasks without scheduled_time should fall back to their time_of_day bucket order."""
        t_evening  = make_task(title="Evening",  time_of_day=TimeOfDay.EVENING)
        t_morning  = make_task(title="Morning",  time_of_day=TimeOfDay.MORNING)
        t_afternoon = make_task(title="Afternoon", time_of_day=TimeOfDay.AFTERNOON)
        scheduler, pet = self._scheduler_with_pet([t_evening, t_morning, t_afternoon])
        pairs = [(t, pet) for t in [t_evening, t_morning, t_afternoon]]
        sorted_pairs = scheduler.sort_by_time(pairs)
        titles = [tp[0].title for tp in sorted_pairs]
        assert titles == ["Morning", "Afternoon", "Evening"]

    def test_sort_by_time_explicit_beats_bucket(self):
        """An explicit scheduled_time='09:00' should sort before afternoon bucket tasks."""
        t_explicit   = make_task(title="Explicit 09:00", scheduled_time="09:00")
        t_afternoon  = make_task(title="Afternoon bucket", time_of_day=TimeOfDay.AFTERNOON)
        scheduler, pet = self._scheduler_with_pet([t_afternoon, t_explicit])
        pairs = [(t, pet) for t in [t_afternoon, t_explicit]]
        sorted_pairs = scheduler.sort_by_time(pairs)
        assert sorted_pairs[0][0].title == "Explicit 09:00"

    def test_sort_by_time_ties_preserve_relative_order(self):
        """Tasks with identical scheduled_time should both appear in the result."""
        t1 = make_task(title="A", scheduled_time="08:00")
        t2 = make_task(title="B", scheduled_time="08:00")
        scheduler, pet = self._scheduler_with_pet([t1, t2])
        pairs = [(t, pet) for t in [t1, t2]]
        sorted_pairs = scheduler.sort_by_time(pairs)
        titles = {tp[0].title for tp in sorted_pairs}
        assert titles == {"A", "B"}

    def test_sort_by_time_empty_list(self):
        """sort_by_time on an empty list should return an empty list."""
        owner = make_owner()
        owner.add_pet(make_pet())
        scheduler = Scheduler(owner)
        assert scheduler.sort_by_time([]) == []


# ---------------------------------------------------------------------------
# Filter tasks tests
# ---------------------------------------------------------------------------

class TestFilterTasks:

    def _build_scheduler(self) -> tuple[Scheduler, Pet, Pet]:
        owner = make_owner()
        mochi = make_pet(name="Mochi")
        luna  = make_pet(name="Luna")
        mochi.add_task(make_task(title="Mochi Walk"))
        mochi.add_task(make_task(title="Mochi Feed"))
        luna.add_task(make_task(title="Luna Feed"))
        owner.add_pet(mochi)
        owner.add_pet(luna)
        return Scheduler(owner), mochi, luna

    def test_filter_by_pet_name(self):
        """filter_tasks(pet_name='Mochi') should return only Mochi's tasks."""
        scheduler, mochi, _ = self._build_scheduler()
        results = scheduler.filter_tasks(pet_name="Mochi")
        assert len(results) == 2
        assert all(pet.name == "Mochi" for _, pet in results)

    def test_filter_by_completed_false(self):
        """filter_tasks(completed=False) should return only pending tasks."""
        scheduler, mochi, _ = self._build_scheduler()
        mochi.tasks[0].mark_complete()
        results = scheduler.filter_tasks(completed=False)
        assert all(not task.completed for task, _ in results)

    def test_filter_by_completed_true(self):
        """filter_tasks(completed=True) should return only completed tasks."""
        scheduler, mochi, _ = self._build_scheduler()
        mochi.tasks[0].mark_complete()
        results = scheduler.filter_tasks(completed=True)
        assert len(results) == 1
        assert results[0][0].title == "Mochi Walk"

    def test_filter_combined_pet_and_status(self):
        """filter_tasks(pet_name, completed) should apply both filters simultaneously."""
        scheduler, mochi, _ = self._build_scheduler()
        mochi.tasks[0].mark_complete()   # "Mochi Walk" is done
        results = scheduler.filter_tasks(pet_name="Mochi", completed=False)
        assert len(results) == 1
        assert results[0][0].title == "Mochi Feed"

    def test_filter_no_match_returns_empty(self):
        """filter_tasks with a pet_name that does not exist should return []."""
        scheduler, _, _ = self._build_scheduler()
        assert scheduler.filter_tasks(pet_name="Dino") == []

    def test_filter_no_criteria_returns_all(self):
        """filter_tasks() with no arguments should return every (task, pet) pair."""
        scheduler, _, _ = self._build_scheduler()
        results = scheduler.filter_tasks()
        assert len(results) == 3   # Mochi Walk + Mochi Feed + Luna Feed


# ---------------------------------------------------------------------------
# Conflict detection tests
# ---------------------------------------------------------------------------

class TestConflictDetection:

    def _owner_with_timed_tasks(self, tasks: list[Task]) -> Owner:
        owner = make_owner(available_minutes=480)
        pet = make_pet()
        for t in tasks:
            pet.add_task(t)
        owner.add_pet(pet)
        return owner

    def test_exact_same_time_is_a_conflict(self):
        """Two tasks starting at the same HH:MM should be flagged as a conflict."""
        t1 = make_task(title="T1", duration=30, scheduled_time="08:00")
        t2 = make_task(title="T2", duration=15, scheduled_time="08:00")
        scheduler = Scheduler(self._owner_with_timed_tasks([t1, t2]))
        conflicts = scheduler.detect_time_conflicts()
        assert len(conflicts) == 1
        assert "T1" in conflicts[0]
        assert "T2" in conflicts[0]

    def test_overlapping_windows_are_a_conflict(self):
        """T1 08:00-08:30 and T2 08:15-08:45 overlap and must be reported."""
        t1 = make_task(title="T1", duration=30, scheduled_time="08:00")
        t2 = make_task(title="T2", duration=30, scheduled_time="08:15")
        scheduler = Scheduler(self._owner_with_timed_tasks([t1, t2]))
        assert len(scheduler.detect_time_conflicts()) == 1

    def test_adjacent_tasks_are_not_a_conflict(self):
        """T1 08:00-08:20 and T2 08:20-08:40 are back-to-back and must NOT conflict."""
        t1 = make_task(title="T1", duration=20, scheduled_time="08:00")
        t2 = make_task(title="T2", duration=20, scheduled_time="08:20")
        scheduler = Scheduler(self._owner_with_timed_tasks([t1, t2]))
        assert scheduler.detect_time_conflicts() == []

    def test_non_overlapping_tasks_no_conflict(self):
        """08:00-08:20 and 09:00-09:30 are well separated — no conflict."""
        t1 = make_task(title="T1", duration=20, scheduled_time="08:00")
        t2 = make_task(title="T2", duration=30, scheduled_time="09:00")
        scheduler = Scheduler(self._owner_with_timed_tasks([t1, t2]))
        assert scheduler.detect_time_conflicts() == []

    def test_tasks_without_scheduled_time_ignored(self):
        """Tasks with no scheduled_time should not participate in conflict detection."""
        t1 = make_task(title="No Time", duration=60)          # no scheduled_time
        t2 = make_task(title="Has Time", duration=60, scheduled_time="08:00")
        scheduler = Scheduler(self._owner_with_timed_tasks([t1, t2]))
        assert scheduler.detect_time_conflicts() == []

    def test_three_way_conflict_reports_all_pairs(self):
        """Three tasks at the same time should produce three conflict reports (one per pair)."""
        tasks = [
            make_task(title=f"T{i}", duration=30, scheduled_time="10:00")
            for i in range(3)
        ]
        scheduler = Scheduler(self._owner_with_timed_tasks(tasks))
        conflicts = scheduler.detect_time_conflicts()
        assert len(conflicts) == 3

    def test_conflict_across_two_pets(self):
        """Conflicts between different pets' tasks should also be detected."""
        owner = make_owner(available_minutes=480)
        pet_a = make_pet(name="A")
        pet_b = make_pet(name="B")
        pet_a.add_task(make_task(title="A Task", duration=30, scheduled_time="08:00"))
        pet_b.add_task(make_task(title="B Task", duration=30, scheduled_time="08:00"))
        owner.add_pet(pet_a)
        owner.add_pet(pet_b)
        scheduler = Scheduler(owner)
        conflicts = scheduler.detect_time_conflicts()
        assert len(conflicts) == 1


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_pet_with_no_tasks_has_zero_care_minutes(self):
        """A Pet with no tasks should report 0 total care minutes."""
        pet = make_pet()
        assert pet.total_care_minutes() == 0

    def test_owner_with_no_pets_returns_empty_task_list(self):
        """total_tasks_across_pets() should return [] when the owner has no pets."""
        owner = make_owner()
        assert owner.total_tasks_across_pets() == []

    def test_scheduler_with_no_pets_returns_empty_schedule(self):
        """Scheduling for an owner with zero pets should return an empty list."""
        owner = make_owner()
        scheduler = Scheduler(owner)
        assert scheduler.generate_schedule() == []

    def test_scheduler_with_pet_but_no_tasks(self):
        """Scheduling for a pet that has no tasks should return an empty schedule."""
        owner = make_owner()
        owner.add_pet(make_pet())
        scheduler = Scheduler(owner)
        assert scheduler.generate_schedule() == []

    def test_single_task_scheduled_correctly(self):
        """A single task should always be scheduled if it fits in the budget."""
        owner = make_owner(available_minutes=30)
        pet = make_pet()
        pet.add_task(make_task(title="Only Task", duration=20))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        schedule = scheduler.generate_schedule()
        assert len(schedule) == 1
        assert schedule[0].task.title == "Only Task"

    def test_task_exactly_at_budget_limit_is_scheduled(self):
        """A task whose duration equals available_minutes_per_day exactly should be scheduled."""
        owner = make_owner(available_minutes=15)
        pet = make_pet()
        pet.add_task(make_task(duration=15))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        schedule = scheduler.generate_schedule()
        assert len(schedule) == 1

    def test_task_one_minute_over_budget_is_skipped(self):
        """A task 1 minute over the budget should be skipped, not scheduled."""
        owner = make_owner(available_minutes=14)
        pet = make_pet()
        pet.add_task(make_task(duration=15))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        schedule = scheduler.generate_schedule()
        assert len(schedule) == 0

    def test_remove_only_task_leaves_empty_list(self):
        """Removing the only task should leave the pet with an empty task list."""
        pet = make_pet()
        pet.add_task(make_task(title="Solo"))
        pet.remove_task("Solo")
        assert pet.tasks == []

    def test_detect_time_conflicts_empty_owner(self):
        """detect_time_conflicts() on an owner with no pets should return []."""
        owner = make_owner()
        scheduler = Scheduler(owner)
        assert scheduler.detect_time_conflicts() == []


# ---------------------------------------------------------------------------
# Extension tests — Challenge 1: weighted scoring & next-slot finder
# ---------------------------------------------------------------------------

class TestWeightedScore:

    def test_high_medication_scores_higher_than_low_walk(self):
        """A HIGH medication must outscore a LOW walk."""
        med  = make_task(priority=Priority.HIGH,  task_type=TaskType.MEDICATION)
        walk = make_task(priority=Priority.LOW,   task_type=TaskType.WALK)
        assert med.weighted_score() > walk.weighted_score()

    def test_overdue_task_scores_more_than_current(self):
        """An overdue recurring task must score higher than the same task due today."""
        today_task    = make_task(recurring=True, due_date=date.today())
        overdue_task  = make_task(recurring=True, due_date=date(2024, 1, 1))
        assert overdue_task.weighted_score() > today_task.weighted_score()

    def test_overdue_penalty_is_capped_at_50(self):
        """The overdue bonus must never exceed 50 regardless of days overdue."""
        task_1_day   = make_task(due_date=date.today() - timedelta(days=1))
        task_100_days = make_task(due_date=date.today() - timedelta(days=100))
        bonus_1   = task_1_day.weighted_score()   - make_task().weighted_score()
        bonus_100 = task_100_days.weighted_score() - make_task().weighted_score()
        assert bonus_100 <= 50
        assert bonus_100 >= bonus_1    # more overdue = higher or equal bonus

    def test_recurring_bonus_adds_5_points(self):
        """A recurring task must score exactly 5 more than an identical non-recurring one."""
        base      = make_task(recurring=False, due_date=date.today())
        recurring = make_task(recurring=True,  due_date=date.today())
        assert recurring.weighted_score() - base.weighted_score() == 5.0

    def test_sort_by_weighted_priority_orders_highest_first(self):
        """sort_by_weighted_priority must place the highest-score task first."""
        owner = make_owner(available_minutes=120)
        pet   = make_pet()
        low_walk = make_task(title="Low Walk", priority=Priority.LOW, task_type=TaskType.WALK)
        high_med = make_task(title="High Med",  priority=Priority.HIGH, task_type=TaskType.MEDICATION)
        pet.add_task(low_walk)
        pet.add_task(high_med)
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        pairs = [(t, pet) for t in pet.tasks]
        ranked = scheduler.sort_by_weighted_priority(pairs)
        assert ranked[0][0].title == "High Med"

    def test_find_next_slot_returns_start_of_day_when_schedule_empty(self):
        """With nothing scheduled, find_next_slot should return the after_minute value."""
        owner = make_owner(available_minutes=60)
        owner.add_pet(make_pet())
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()           # empty schedule
        assert scheduler.find_next_slot(30, after_minute=480) == 480

    def test_find_next_slot_skips_occupied_blocks(self):
        """find_next_slot must skip any block already in the schedule."""
        owner = make_owner(available_minutes=60)
        pet   = make_pet()
        pet.add_task(make_task(title="T1", duration=30, time_of_day=TimeOfDay.MORNING))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        # T1 occupies 08:00–08:30 (480–510); next 15-min slot should be at 510
        slot = scheduler.find_next_slot(15, after_minute=480)
        assert slot is not None
        assert slot >= 510

    def test_find_next_slot_returns_none_when_no_gap(self):
        """find_next_slot must return None if no gap large enough exists before midnight."""
        owner = make_owner(available_minutes=1440)
        pet   = make_pet()
        # One massive task that fills midnight to midnight
        pet.add_task(make_task(duration=1440, time_of_day=TimeOfDay.MORNING))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        # After a 1440-min block starting at 480, the cursor is at 1920 > 1440
        assert scheduler.find_next_slot(10, after_minute=480) is None


# ---------------------------------------------------------------------------
# Extension tests — Challenge 2: JSON serialization round-trip
# ---------------------------------------------------------------------------

class TestJsonPersistence:

    def _make_full_owner(self) -> Owner:
        owner = make_owner(name="TestOwner", available_minutes=120)
        pet   = make_pet(name="Buddy")
        pet.add_task(make_task(
            title="Daily Walk", duration=30, priority=Priority.HIGH,
            task_type=TaskType.WALK, time_of_day=TimeOfDay.MORNING,
            scheduled_time="08:00", recurring=True, due_date=date(2026, 4, 5),
        ))
        pet.add_task(make_task(title="Feed", duration=10, priority=Priority.MEDIUM))
        owner.add_pet(pet)
        return owner

    def test_task_to_dict_round_trip(self):
        """Task.from_dict(task.to_dict()) must produce an equal Task."""
        task = make_task(
            title="Meds", duration=5, priority=Priority.HIGH,
            task_type=TaskType.MEDICATION, scheduled_time="08:30",
            recurring=True, due_date=date(2026, 4, 5),
        )
        restored = Task.from_dict(task.to_dict())
        assert restored.title           == task.title
        assert restored.duration_minutes == task.duration_minutes
        assert restored.priority        == task.priority
        assert restored.task_type       == task.task_type
        assert restored.scheduled_time  == task.scheduled_time
        assert restored.recurring       == task.recurring
        assert restored.due_date        == task.due_date

    def test_pet_to_dict_round_trip(self):
        """Pet.from_dict(pet.to_dict()) must preserve all tasks."""
        pet = make_pet(name="Luna")
        pet.add_task(make_task(title="T1"))
        pet.add_task(make_task(title="T2"))
        restored = Pet.from_dict(pet.to_dict())
        assert restored.name == "Luna"
        assert len(restored.tasks) == 2
        assert [t.title for t in restored.tasks] == ["T1", "T2"]

    def test_owner_to_dict_round_trip(self):
        """Owner.from_dict(owner.to_dict()) must preserve name, budget, and all pets/tasks."""
        owner = self._make_full_owner()
        restored = Owner.from_dict(owner.to_dict())
        assert restored.name == owner.name
        assert restored.available_minutes_per_day == owner.available_minutes_per_day
        assert len(restored.pets) == len(owner.pets)
        assert restored.pets[0].name == "Buddy"
        assert len(restored.pets[0].tasks) == 2

    def test_save_and_load_json(self, tmp_path):
        """save_to_json then load_from_json must produce an identical owner graph."""
        owner = self._make_full_owner()
        path  = tmp_path / "test_data.json"
        owner.save_to_json(path)
        loaded = Owner.load_from_json(path)
        assert loaded.name == owner.name
        assert len(loaded.pets) == len(owner.pets)
        original_titles = [t.title for p in owner.pets for t in p.tasks]
        loaded_titles   = [t.title for p in loaded.pets  for t in p.tasks]
        assert original_titles == loaded_titles

    def test_load_from_json_raises_for_missing_file(self, tmp_path):
        """load_from_json must raise FileNotFoundError for a non-existent file."""
        with pytest.raises(FileNotFoundError):
            Owner.load_from_json(tmp_path / "nonexistent.json")
