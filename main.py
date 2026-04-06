"""
PawPal+ CLI Demo
Run this script to verify the backend logic works before connecting to the UI.
    python main.py
"""

from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    Priority, TaskType, TimeOfDay,
)


def build_demo_data() -> Owner:
    """Create a demo owner with two pets and several tasks."""

    owner = Owner(
        name="Jordan",
        available_minutes_per_day=120,
        preferred_morning_tasks=[TaskType.WALK, TaskType.FEEDING],
        preferred_evening_tasks=[TaskType.MEDICATION],
    )

    # --- Pet 1: Mochi the dog ---
    mochi = Pet(name="Mochi", species="dog", age=3)

    mochi.add_task(Task(
        title="Morning Walk",
        duration_minutes=30,
        priority=Priority.HIGH,
        task_type=TaskType.WALK,
        time_of_day=TimeOfDay.MORNING,
        recurring=True,
    ))
    mochi.add_task(Task(
        title="Breakfast",
        duration_minutes=10,
        priority=Priority.HIGH,
        task_type=TaskType.FEEDING,
        time_of_day=TimeOfDay.MORNING,
        recurring=True,
    ))
    mochi.add_task(Task(
        title="Heartworm Medication",
        duration_minutes=5,
        priority=Priority.HIGH,
        task_type=TaskType.MEDICATION,
        time_of_day=TimeOfDay.EVENING,
        notes="Give with food",
    ))
    mochi.add_task(Task(
        title="Afternoon Play Session",
        duration_minutes=20,
        priority=Priority.MEDIUM,
        task_type=TaskType.ENRICHMENT,
        time_of_day=TimeOfDay.AFTERNOON,
    ))

    # --- Pet 2: Luna the cat ---
    luna = Pet(name="Luna", species="cat", age=5)

    luna.add_task(Task(
        title="Breakfast",
        duration_minutes=5,
        priority=Priority.HIGH,
        task_type=TaskType.FEEDING,
        time_of_day=TimeOfDay.MORNING,
        recurring=True,
    ))
    luna.add_task(Task(
        title="Annual Vet Appointment",
        duration_minutes=60,
        priority=Priority.HIGH,
        task_type=TaskType.APPOINTMENT,
        time_of_day=TimeOfDay.AFTERNOON,
        notes="Annual checkup — bring vaccination records",
    ))
    luna.add_task(Task(
        title="Evening Brushing",
        duration_minutes=10,
        priority=Priority.LOW,
        task_type=TaskType.GROOMING,
        time_of_day=TimeOfDay.EVENING,
    ))

    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner


def print_section(title: str) -> None:
    print(f"\n{'-' * 50}")
    print(f"  {title}")
    print(f"{'-' * 50}")


def main() -> None:
    owner = build_demo_data()

    # --- Owner summary ---
    print_section("Owner Profile")
    print(f"  {owner}")

    # --- Pet summaries ---
    print_section("Registered Pets")
    for pet in owner.pets:
        print(f"  {pet}")
        for task in pet.tasks:
            print(f"    {task}")

    # --- Task totals ---
    print_section("Task Overview")
    total = owner.total_tasks_across_pets()
    print(f"  Total tasks across all pets: {len(total)}")
    high = [t for t in total if t.is_high_priority()]
    print(f"  High-priority tasks: {len(high)}")

    # --- Generate and print the daily schedule ---
    print_section("Generating Daily Schedule...")
    scheduler = Scheduler(owner)
    scheduler.generate_schedule()
    print(scheduler.get_daily_plan())

    # --- Mark a task complete and show it ---
    print_section("Marking 'Morning Walk' as complete")
    mochi = owner.get_pet("Mochi")
    walk = next((t for t in mochi.tasks if t.title == "Morning Walk"), None)
    if walk:
        walk.mark_complete()
        print(f"  {walk}")


if __name__ == "__main__":
    main()
