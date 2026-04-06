"""
PawPal+ CLI Demo
Verifies all backend logic: scheduling, sorting, filtering,
recurring tasks, and conflict detection.
    python main.py
"""

from datetime import date
from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    Priority, TaskType, TimeOfDay,
)


def sep(title: str) -> None:
    print(f"\n{'-' * 54}")
    print(f"  {title}")
    print(f"{'-' * 54}")


# ---------------------------------------------------------------------------
# Build demo data  (tasks added intentionally out of chronological order)
# ---------------------------------------------------------------------------

owner = Owner(name="Jordan", available_minutes_per_day=150)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# Mochi's tasks – added out of time order to prove sort_by_time works
mochi.add_task(Task(
    title="Evening Walk",
    duration_minutes=25,
    priority=Priority.MEDIUM,
    task_type=TaskType.WALK,
    time_of_day=TimeOfDay.EVENING,
    scheduled_time="18:00",
    recurring=True,
    due_date=date.today(),
))
mochi.add_task(Task(
    title="Breakfast",
    duration_minutes=10,
    priority=Priority.HIGH,
    task_type=TaskType.FEEDING,
    time_of_day=TimeOfDay.MORNING,
    scheduled_time="08:00",
    recurring=True,
    due_date=date.today(),
))
mochi.add_task(Task(
    title="Afternoon Play",
    duration_minutes=20,
    priority=Priority.LOW,
    task_type=TaskType.ENRICHMENT,
    time_of_day=TimeOfDay.AFTERNOON,
    scheduled_time="13:00",
))
mochi.add_task(Task(
    title="Heartworm Pill",
    duration_minutes=5,
    priority=Priority.HIGH,
    task_type=TaskType.MEDICATION,
    time_of_day=TimeOfDay.EVENING,
    scheduled_time="18:00",   # <-- same slot as Evening Walk -> CONFLICT
    notes="Give with food",
    recurring=True,
    due_date=date.today(),
))

# Luna's tasks
luna.add_task(Task(
    title="Breakfast",
    duration_minutes=5,
    priority=Priority.HIGH,
    task_type=TaskType.FEEDING,
    time_of_day=TimeOfDay.MORNING,
    scheduled_time="08:15",
    recurring=True,
    due_date=date.today(),
))
luna.add_task(Task(
    title="Vet Appointment",
    duration_minutes=60,
    priority=Priority.HIGH,
    task_type=TaskType.APPOINTMENT,
    time_of_day=TimeOfDay.AFTERNOON,
    scheduled_time="14:00",
))
luna.add_task(Task(
    title="Evening Brushing",
    duration_minutes=10,
    priority=Priority.LOW,
    task_type=TaskType.GROOMING,
    time_of_day=TimeOfDay.EVENING,
    scheduled_time="19:00",
))

owner.add_pet(mochi)
owner.add_pet(luna)

scheduler = Scheduler(owner)

# ---------------------------------------------------------------------------
# 1. Sort by time (chronological order, not insertion order)
# ---------------------------------------------------------------------------

sep("1. SORT BY TIME  (chronological across all pets)")

all_pairs = [(task, pet) for pet in owner.pets for task in pet.tasks]
sorted_pairs = scheduler.sort_by_time(all_pairs)

for task, pet in sorted_pairs:
    time_label = task.scheduled_time or f"[{task.time_of_day.value}]"
    print(f"  {time_label}  [{pet.name}]  {task.title}  ({task.priority.value})")

# ---------------------------------------------------------------------------
# 2. Filter by pet and by completion status
# ---------------------------------------------------------------------------

sep("2. FILTER TASKS")

print("  >> All Mochi tasks:")
for task, pet in scheduler.filter_tasks(pet_name="Mochi"):
    print(f"     {task}")

# Mark one task complete to make the status filter interesting
mochi_breakfast = next(t for t in mochi.tasks if t.title == "Breakfast")
mochi_breakfast.mark_complete()

print("\n  >> Completed tasks (all pets):")
for task, pet in scheduler.filter_tasks(completed=True):
    print(f"     [{pet.name}] {task}")

print("\n  >> Pending tasks (all pets):")
for task, pet in scheduler.filter_tasks(completed=False):
    print(f"     [{pet.name}] {task}")

# ---------------------------------------------------------------------------
# 3. Recurring task – generate next occurrence
# ---------------------------------------------------------------------------

sep("3. RECURRING TASKS  (next-day occurrence after completion)")

# Mark all recurring tasks complete to demo the feature
for pet in owner.pets:
    for task in pet.tasks:
        if task.recurring:
            task.mark_complete()

next_occurrences = scheduler.get_recurring_next_occurrences()
print(f"  Recurring tasks completed today: {len(next_occurrences)}")
for next_task, pet in next_occurrences:
    print(
        f"  [{pet.name}] '{next_task.title}' "
        f"rescheduled for {next_task.due_date}  (completed={next_task.completed})"
    )

# ---------------------------------------------------------------------------
# 4. Conflict detection (Heartworm Pill and Evening Walk share 18:00)
# ---------------------------------------------------------------------------

sep("4. CONFLICT DETECTION  (explicit scheduled_time overlaps)")

conflicts = scheduler.detect_time_conflicts()
if conflicts:
    print(f"  Found {len(conflicts)} conflict(s):")
    for c in conflicts:
        print(f"  {c}")
else:
    print("  No conflicts detected.")

# ---------------------------------------------------------------------------
# 5. Full daily schedule
# ---------------------------------------------------------------------------

sep("5. DAILY SCHEDULE")

# Reset completions so all tasks appear in the schedule
for pet in owner.pets:
    for task in pet.tasks:
        task.completed = False

scheduler.generate_schedule()
print(scheduler.get_daily_plan())
