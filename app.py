import streamlit as st
from datetime import date
from pathlib import Path

from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    Priority, TaskType, TimeOfDay,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_FILE = Path("data.json")

# Challenge 4 — task type emojis for professional UI output
TASK_EMOJI = {
    "walk":        "🦮",
    "feeding":     "🍽️",
    "medication":  "💊",
    "appointment": "🏥",
    "grooming":    "✂️",
    "enrichment":  "🎾",
    "other":       "📝",
}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ---------------------------------------------------------------------------
# Session-state initialisation
# st.session_state acts as a persistent "vault" — the Owner object lives here
# so it survives Streamlit's top-to-bottom reruns on every interaction.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    # Challenge 2 — auto-load from data.json if it exists
    if DATA_FILE.exists():
        try:
            st.session_state.owner = Owner.load_from_json(DATA_FILE)
        except Exception:
            st.session_state.owner = None
    else:
        st.session_state.owner = None

# ---------------------------------------------------------------------------
# Sidebar — Owner setup
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🐾 PawPal+")
    st.caption("Smart pet care scheduling")
    st.divider()

    st.subheader("Owner Profile")
    with st.form("owner_form"):
        owner_name    = st.text_input("Your name", value="Jordan")
        available_mins = st.number_input(
            "Available min / day", min_value=10, max_value=480, value=120, step=10
        )
        if st.form_submit_button("Save Owner", type="primary"):
            st.session_state.owner = Owner(
                name=owner_name,
                available_minutes_per_day=int(available_mins),
            )
            st.session_state.owner.save_to_json(DATA_FILE)   # Challenge 2
            st.success(f"Saved: {owner_name}")

    if st.session_state.owner:
        o = st.session_state.owner
        st.info(
            f"**{o.name}** · {len(o.pets)} pet(s) · {o.available_minutes_per_day} min/day"
        )

# ---------------------------------------------------------------------------
# Guard — nothing works until an owner exists
# ---------------------------------------------------------------------------

if st.session_state.owner is None:
    st.title("Welcome to PawPal+ 🐾")
    st.info("Fill in the **Owner Profile** in the sidebar to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------

tab_pets, tab_tasks, tab_schedule, tab_smart = st.tabs(
    ["🐕 Pets", "📋 Tasks", "📅 Schedule", "🔍 Smart View"]
)

# ===========================================================================
# TAB 1 — Pets
# ===========================================================================

with tab_pets:
    st.subheader("Manage Pets")

    with st.form("pet_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            pet_name = st.text_input("Pet name", value="Mochi")
        with col2:
            species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        with col3:
            age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
        if st.form_submit_button("Add Pet"):
            if owner.get_pet(pet_name):
                st.warning(f"A pet named '{pet_name}' already exists.")
            else:
                owner.add_pet(Pet(name=pet_name, species=species, age=int(age)))
                owner.save_to_json(DATA_FILE)   # Challenge 2
                st.success(f"Added {pet_name} the {species}!")

    if owner.pets:
        st.divider()
        st.markdown("**Registered pets**")
        rows = [
            {
                "Name": p.name,
                "Species": p.species,
                "Age": p.age,
                "Tasks": len(p.tasks),
                "Total care (min)": p.total_care_minutes(),
            }
            for p in owner.pets
        ]
        st.table(rows)
    else:
        st.info("No pets yet — add one above.")

# ===========================================================================
# TAB 2 — Tasks
# ===========================================================================

with tab_tasks:
    st.subheader("Add a Care Task")

    if not owner.pets:
        st.warning("Add at least one pet first (Pets tab).")
    else:
        pet_names = [p.name for p in owner.pets]

        with st.form("task_form"):
            col1, col2 = st.columns(2)
            with col1:
                target_pet     = st.selectbox("Assign to pet", pet_names)
                task_title     = st.text_input("Task title", value="Morning Walk")
                duration       = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
                scheduled_time = st.text_input(
                    "Scheduled time (HH:MM, optional)",
                    value="",
                    help="Set an exact start time to enable conflict detection, e.g. 08:30",
                )
            with col2:
                priority    = st.selectbox("Priority",      [p.value for p in Priority],    index=2)
                task_type   = st.selectbox("Task type",     [t.value for t in TaskType])
                time_of_day = st.selectbox("Time of day",   [t.value for t in TimeOfDay])
                recurring   = st.checkbox("Recurring daily task")
            notes = st.text_area("Notes (optional)", value="")

            if st.form_submit_button("Add Task"):
                pet = owner.get_pet(target_pet)
                pet.add_task(Task(
                    title=task_title,
                    duration_minutes=int(duration),
                    priority=Priority(priority),
                    task_type=TaskType(task_type),
                    time_of_day=TimeOfDay(time_of_day),
                    recurring=recurring,
                    notes=notes,
                    scheduled_time=scheduled_time.strip() or None,
                    due_date=date.today() if recurring else None,
                ))
                owner.save_to_json(DATA_FILE)   # Challenge 2
                st.success(f"Added '{task_title}' to {target_pet}.")

        # Show tasks per pet
        has_tasks = any(p.tasks for p in owner.pets)
        if has_tasks:
            st.divider()
            for pet in owner.pets:
                if not pet.tasks:
                    continue
                st.markdown(f"**{pet.name}** — {pet.total_care_minutes()} min total")
                for task in pet.tasks:
                    priority_badge = {
                        "high":   ":red[HIGH]",
                        "medium": ":orange[MED]",
                        "low":    ":green[LOW]",
                    }.get(task.priority.value, task.priority.value)
                    status_icon  = "✅" if task.completed else "🔲"
                    time_hint    = f" · `{task.scheduled_time}`" if task.scheduled_time else ""
                    recur_hint   = " 🔁" if task.recurring else ""
                    emoji        = TASK_EMOJI.get(task.task_type.value, "📝")  # Challenge 4
                    st.markdown(
                        f"{status_icon} {priority_badge} {emoji} &nbsp; **{task.title}**"
                        f" ({task.duration_minutes} min | {task.task_type.value}"
                        f"{time_hint}){recur_hint}"
                    )
                st.write("")

            # --- Inline conflict warning (live, before scheduling) ----------
            scheduler = Scheduler(owner)
            pre_conflicts = scheduler.detect_time_conflicts()
            if pre_conflicts:
                st.divider()
                st.warning(
                    f"**{len(pre_conflicts)} time conflict(s) detected** — "
                    "two or more tasks overlap at the same scheduled time:"
                )
                for c in pre_conflicts:
                    st.markdown(f"- {c}")
                st.caption(
                    "Tip: adjust the 'Scheduled time' field on one of the conflicting tasks "
                    "or remove its exact time to resolve the conflict."
                )

# ===========================================================================
# TAB 3 — Schedule
# ===========================================================================

with tab_schedule:
    st.subheader("Daily Schedule")

    if not owner.total_tasks_across_pets():
        st.warning("Add at least one task before generating a schedule.")
    else:
        if st.button("Generate Schedule", type="primary"):
            scheduler = Scheduler(owner)
            schedule  = scheduler.generate_schedule()

            total_scheduled = sum(s.task.duration_minutes for s in schedule)
            total_available = owner.available_minutes_per_day

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Tasks scheduled", len(schedule))
            col2.metric("Tasks skipped",   len(scheduler._skipped))
            col3.metric("Minutes used",    total_scheduled)
            col4.metric("Minutes free",    total_available - total_scheduled)

            st.divider()

            if schedule:
                st.markdown("#### Scheduled tasks")
                priority_color = {
                    "high":   ":red[HIGH]",
                    "medium": ":orange[MED]",
                    "low":    ":green[LOW]",
                }
                for item in sorted(schedule, key=lambda x: x.start_minute):
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
                        c1.markdown(f"**{item.time_label()}**")
                        c2.markdown(f"**{item.task.title}** — {item.pet.name}")
                        c2.caption(item.reason)
                        c3.markdown(priority_color.get(item.task.priority.value, ""))
                        emoji = TASK_EMOJI.get(item.task.task_type.value, "")
                        c3.caption(f"{emoji} {item.task.duration_minutes} min · {item.task.task_type.value}")
                        if item.task.recurring:
                            c4.markdown("🔁")
            else:
                st.error("No tasks could be scheduled within the daily time limit.")

            # Skipped tasks
            if scheduler._skipped:
                with st.expander(
                    f"⚠️ {len(scheduler._skipped)} task(s) skipped — exceeded daily time limit"
                ):
                    for task, pet in scheduler._skipped:
                        st.markdown(
                            f"- **[{pet.name}]** {task.title} "
                            f"({task.duration_minutes} min · {task.priority.value})"
                        )

            # Post-schedule conflict report
            conflicts = scheduler.get_conflicts()
            if conflicts:
                st.divider()
                st.warning(
                    f"**{len(conflicts)} scheduling conflict(s) detected.** "
                    "These tasks overlap in the generated plan:"
                )
                for c in conflicts:
                    st.markdown(f"- {c}")
                st.caption(
                    "This can happen when tasks from different time-of-day buckets are "
                    "placed adjacent to each other. Consider reducing task durations or "
                    "increasing your available daily minutes."
                )
            else:
                st.success("No scheduling conflicts — your day looks clean!")

# ===========================================================================
# TAB 4 — Smart View (sort, filter, recurring)
# ===========================================================================

with tab_smart:
    st.subheader("Smart Task Views")

    if not owner.total_tasks_across_pets():
        st.warning("Add tasks first (Tasks tab).")
    else:
        scheduler = Scheduler(owner)

        # --- Sort by time ---------------------------------------------------
        st.markdown("#### Chronological task order")
        st.caption(
            "Tasks sorted by their explicit scheduled time (HH:MM). "
            "Tasks without a fixed time are grouped by time-of-day bucket."
        )
        all_pairs   = [(t, p) for p in owner.pets for t in p.tasks]
        sorted_pairs = scheduler.sort_by_time(all_pairs)

        sort_rows = [
            {
                "Time":     tp[0].scheduled_time or f"[{tp[0].time_of_day.value}]",
                "Pet":      tp[1].name,
                "Task":     tp[0].title,
                "Duration": f"{tp[0].duration_minutes} min",
                "Priority": tp[0].priority.value,
                "Type":     tp[0].task_type.value,
                "Recurring": "Yes" if tp[0].recurring else "No",
            }
            for tp in sorted_pairs
        ]
        st.table(sort_rows)

        st.divider()

        # --- Filter by completion status ------------------------------------
        st.markdown("#### Filter by completion status")
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            pending = scheduler.filter_tasks(completed=False)
            st.markdown(f"**Pending tasks ({len(pending)})**")
            if pending:
                for task, pet in pending:
                    st.markdown(f"- 🔲 [{pet.name}] **{task.title}** ({task.duration_minutes} min)")
            else:
                st.success("All tasks are complete!")

        with filter_col2:
            done = scheduler.filter_tasks(completed=True)
            st.markdown(f"**Completed tasks ({len(done)})**")
            if done:
                for task, pet in done:
                    st.markdown(f"- ✅ [{pet.name}] **{task.title}**")
            else:
                st.info("No completed tasks yet.")

        st.divider()

        # --- Recurring task roll-over ---------------------------------------
        st.markdown("#### Recurring task tracker")
        next_occurrences = scheduler.get_recurring_next_occurrences()

        if next_occurrences:
            st.info(
                f"**{len(next_occurrences)} recurring task(s)** are complete today "
                "and will roll over to tomorrow:"
            )
            for nxt_task, pet in next_occurrences:
                st.markdown(
                    f"- 🔁 [{pet.name}] **{nxt_task.title}** "
                    f"→ next due **{nxt_task.due_date}**"
                )
        else:
            recurring_all = [
                (t, p) for p in owner.pets for t in p.tasks if t.recurring
            ]
            if recurring_all:
                st.success(
                    f"**{len(recurring_all)} recurring task(s)** registered — "
                    "none completed yet today."
                )
            else:
                st.info("No recurring tasks added yet. Check 'Recurring daily task' when adding a task.")

        st.divider()

        # --- Weighted priority ranking (Challenge 1) -----------------------
        st.markdown("#### Weighted priority ranking")
        st.caption(
            "Ranks tasks by a composite score: base priority + task-type urgency "
            "+ overdue penalty + recurring bonus. Gives a smarter ordering than "
            "HIGH/MEDIUM/LOW alone."
        )
        weighted_sorted = scheduler.sort_by_weighted_priority(all_pairs)
        weighted_rows = [
            {
                "Rank":     i + 1,
                "Score":    tp[0].weighted_score(),
                "Pet":      tp[1].name,
                "Task":     tp[0].title,
                "Priority": tp[0].priority.value,
                "Type":     TASK_EMOJI.get(tp[0].task_type.value, "") + " " + tp[0].task_type.value,
                "Overdue":  "Yes" if (tp[0].due_date and tp[0].due_date < date.today()) else "No",
            }
            for i, tp in enumerate(weighted_sorted)
        ]
        st.table(weighted_rows)

        # --- Next available slot (Challenge 1) -----------------------------
        st.markdown("#### Next available scheduling slot")
        slot_duration = st.number_input(
            "Task duration to fit (minutes)", min_value=1, max_value=120, value=15, key="slot_dur"
        )
        if st.button("Find next free slot"):
            temp_scheduler = Scheduler(owner)
            temp_scheduler.generate_schedule()
            slot = temp_scheduler.find_next_slot(int(slot_duration))
            if slot is not None:
                h, m = divmod(slot, 60)
                st.success(f"Next free {slot_duration}-min slot starts at **{h:02d}:{m:02d}**.")
            else:
                st.warning("No free slot found within today's schedule.")

        st.divider()

        # --- Live conflict check -------------------------------------------
        st.markdown("#### Conflict detection")
        conflicts = scheduler.detect_time_conflicts()
        if conflicts:
            st.warning(f"**{len(conflicts)} conflict(s) found:**")
            for c in conflicts:
                st.markdown(f"- {c}")
        else:
            st.success("No time conflicts detected among your scheduled tasks.")
