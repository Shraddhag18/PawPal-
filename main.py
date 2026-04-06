"""
PawPal+ CLI Demo  (Challenge 4: tabulate + emoji formatting)
Verifies all backend logic: scheduling, sorting, filtering,
recurring tasks, conflict detection, weighted priority, next-slot finder,
and JSON persistence.
    python main.py
"""

from datetime import date
from tabulate import tabulate

from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    Priority, TaskType, TimeOfDay,
)

# Challenge 4 — task type labels for CLI (emojis shown in Streamlit UI)
TASK_LABEL = {
    TaskType.WALK:        "[walk]",
    TaskType.FEEDING:     "[feed]",
    TaskType.MEDICATION:  "[med] ",
    TaskType.APPOINTMENT: "[appt]",
    TaskType.GROOMING:    "[groom]",
    TaskType.ENRICHMENT:  "[enrich]",
    TaskType.OTHER:       "[other]",
}

PRIORITY_ICON = {
    Priority.HIGH:   "[HIGH]",
    Priority.MEDIUM: "[MED] ",
    Priority.LOW:    "[LOW] ",
}


def sep(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


# ---------------------------------------------------------------------------
# Build demo data
# ---------------------------------------------------------------------------

owner = Owner(name="Jordan", available_minutes_per_day=150)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

mochi.add_task(Task(
    title="Evening Walk", duration_minutes=25, priority=Priority.MEDIUM,
    task_type=TaskType.WALK, time_of_day=TimeOfDay.EVENING,
    scheduled_time="18:00", recurring=True, due_date=date.today(),
))
mochi.add_task(Task(
    title="Breakfast", duration_minutes=10, priority=Priority.HIGH,
    task_type=TaskType.FEEDING, time_of_day=TimeOfDay.MORNING,
    scheduled_time="08:00", recurring=True, due_date=date.today(),
))
mochi.add_task(Task(
    title="Afternoon Play", duration_minutes=20, priority=Priority.LOW,
    task_type=TaskType.ENRICHMENT, time_of_day=TimeOfDay.AFTERNOON,
    scheduled_time="13:00",
))
mochi.add_task(Task(
    title="Heartworm Pill", duration_minutes=5, priority=Priority.HIGH,
    task_type=TaskType.MEDICATION, time_of_day=TimeOfDay.EVENING,
    scheduled_time="18:00", notes="Give with food",
    recurring=True, due_date=date.today(),
))

luna.add_task(Task(
    title="Breakfast", duration_minutes=5, priority=Priority.HIGH,
    task_type=TaskType.FEEDING, time_of_day=TimeOfDay.MORNING,
    scheduled_time="08:15", recurring=True, due_date=date.today(),
))
luna.add_task(Task(
    title="Vet Appointment", duration_minutes=60, priority=Priority.HIGH,
    task_type=TaskType.APPOINTMENT, time_of_day=TimeOfDay.AFTERNOON,
    scheduled_time="14:00",
))
luna.add_task(Task(
    title="Evening Brushing", duration_minutes=10, priority=Priority.LOW,
    task_type=TaskType.GROOMING, time_of_day=TimeOfDay.EVENING,
    scheduled_time="19:00",
))

owner.add_pet(mochi)
owner.add_pet(luna)
scheduler = Scheduler(owner)

# ---------------------------------------------------------------------------
# 1. Owner & pet summary (tabulate)
# ---------------------------------------------------------------------------

sep("1. OWNER & PET SUMMARY")
pet_rows = [
    [p.name, p.species, p.age, len(p.tasks), f"{p.total_care_minutes()} min"]
    for p in owner.pets
]
print(tabulate(
    pet_rows,
    headers=["Pet", "Species", "Age", "Tasks", "Total care"],
    tablefmt="simple",
))

# ---------------------------------------------------------------------------
# 2. All tasks — sorted by time (tabulate + emoji)
# ---------------------------------------------------------------------------

sep("2. ALL TASKS  sorted chronologically")
all_pairs = [(t, p) for p in owner.pets for t in p.tasks]
sorted_pairs = scheduler.sort_by_time(all_pairs)

task_rows = [
    [
        tp[0].scheduled_time or f"[{tp[0].time_of_day.value}]",
        tp[1].name,
        TASK_LABEL.get(tp[0].task_type, "") + " " + tp[0].title,
        f"{tp[0].duration_minutes} min",
        PRIORITY_ICON[tp[0].priority],
        "Yes" if tp[0].recurring else "No",
    ]
    for tp in sorted_pairs
]
print(tabulate(
    task_rows,
    headers=["Time", "Pet", "Task", "Duration", "Priority", "Recurring"],
    tablefmt="simple",
))

# ---------------------------------------------------------------------------
# 3. Weighted priority ranking (Challenge 1)
# ---------------------------------------------------------------------------

sep("3. WEIGHTED PRIORITY RANKING  (score = priority + type + overdue + recurring)")
weighted = scheduler.sort_by_weighted_priority(all_pairs)
w_rows = [
    [
        i + 1,
        round(tp[0].weighted_score(), 1),
        tp[1].name,
        TASK_LABEL.get(tp[0].task_type, "") + " " + tp[0].title,
        tp[0].priority.value,
        tp[0].task_type.value,
    ]
    for i, tp in enumerate(weighted)
]
print(tabulate(
    w_rows,
    headers=["Rank", "Score", "Pet", "Task", "Priority", "Type"],
    tablefmt="simple",
))

# ---------------------------------------------------------------------------
# 4. Generate schedule + next available slot
# ---------------------------------------------------------------------------

sep("4. DAILY SCHEDULE")
scheduler.generate_schedule()
schedule_rows = [
    [
        st.time_label(),
        st.pet.name,
        TASK_LABEL.get(st.task.task_type, "") + " " + st.task.title,
        f"{st.task.duration_minutes} min",
        st.task.priority.value,
    ]
    for st in sorted(scheduler._schedule, key=lambda x: x.start_minute)
]
print(tabulate(
    schedule_rows,
    headers=["Time", "Pet", "Task", "Duration", "Priority"],
    tablefmt="simple",
))

if scheduler._skipped:
    print(f"\n  Skipped ({len(scheduler._skipped)}):")
    for task, pet in scheduler._skipped:
        print(f"    [skip] [{pet.name}] {task.title} ({task.duration_minutes} min)")

sep("4b. NEXT AVAILABLE SLOT  (Challenge 1)")
slot = scheduler.find_next_slot(30)
if slot is not None:
    h, m = divmod(slot, 60)
    print(f"  Next free 30-min slot starts at {h:02d}:{m:02d}")
else:
    print("  No free 30-min slot found today.")

# ---------------------------------------------------------------------------
# 5. Conflict detection
# ---------------------------------------------------------------------------

sep("5. CONFLICT DETECTION")
conflicts = scheduler.detect_time_conflicts()
if conflicts:
    print(f"  Found {len(conflicts)} conflict(s):")
    for c in conflicts:
        print(f"  {c}")
else:
    print("  No conflicts detected.")

# ---------------------------------------------------------------------------
# 6. JSON persistence (Challenge 2)
# ---------------------------------------------------------------------------

sep("6. JSON PERSISTENCE  (Challenge 2)")
owner.save_to_json("data.json")
print("  Saved to data.json")

reloaded = Owner.load_from_json("data.json")
print(f"  Reloaded: {reloaded}")
print(f"  Pets:     {[p.name for p in reloaded.pets]}")
print(f"  Tasks:    {sum(len(p.tasks) for p in reloaded.pets)} total across all pets")

# Verify round-trip fidelity
original_tasks = [(t.title, p.name) for p in owner.pets for t in p.tasks]
reloaded_tasks = [(t.title, p.name) for p in reloaded.pets for t in p.tasks]
assert original_tasks == reloaded_tasks, "Round-trip fidelity check FAILED"
print("  Round-trip fidelity check: PASSED")
