import streamlit as st

from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    Priority, TaskType, TimeOfDay,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session-state initialisation
# Streamlit reruns the entire script on every interaction.
# Storing the Owner in st.session_state keeps the object alive across reruns.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner: Owner | None = None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("PawPal+")
st.caption("A smart pet care scheduling assistant")
st.divider()

# ---------------------------------------------------------------------------
# Section 1: Owner Setup
# ---------------------------------------------------------------------------

st.subheader("1. Owner Profile")

with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col2:
        available_mins = st.number_input(
            "Available minutes per day",
            min_value=10, max_value=480, value=120, step=10,
        )
    submitted_owner = st.form_submit_button("Save Owner")

if submitted_owner:
    st.session_state.owner = Owner(
        name=owner_name,
        available_minutes_per_day=int(available_mins),
    )
    st.success(f"Owner '{owner_name}' saved with {available_mins} min/day.")

if st.session_state.owner:
    st.info(str(st.session_state.owner))

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Add a Pet
# ---------------------------------------------------------------------------

st.subheader("2. Add a Pet")

if st.session_state.owner is None:
    st.warning("Save an Owner profile first (Section 1).")
else:
    with st.form("pet_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            pet_name = st.text_input("Pet name", value="Mochi")
        with col2:
            species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        with col3:
            age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
        submitted_pet = st.form_submit_button("Add Pet")

    if submitted_pet:
        owner: Owner = st.session_state.owner
        if owner.get_pet(pet_name):
            st.warning(f"A pet named '{pet_name}' already exists.")
        else:
            owner.add_pet(Pet(name=pet_name, species=species, age=int(age)))
            st.success(f"Added {pet_name} ({species}, {age} yr).")

    # Show current pets
    owner: Owner = st.session_state.owner
    if owner.pets:
        st.markdown("**Registered pets:**")
        for pet in owner.pets:
            st.markdown(f"- {pet}")

st.divider()

# ---------------------------------------------------------------------------
# Section 3: Add a Task to a Pet
# ---------------------------------------------------------------------------

st.subheader("3. Add a Care Task")

if st.session_state.owner is None or not st.session_state.owner.pets:
    st.warning("Add at least one pet before creating tasks.")
else:
    owner: Owner = st.session_state.owner
    pet_names = [p.name for p in owner.pets]

    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            target_pet = st.selectbox("Assign to pet", pet_names)
            task_title = st.text_input("Task title", value="Morning Walk")
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20
            )
        with col2:
            priority = st.selectbox(
                "Priority",
                [p.value for p in Priority],
                index=2,          # HIGH default
            )
            task_type = st.selectbox(
                "Task type",
                [t.value for t in TaskType],
            )
            time_of_day = st.selectbox(
                "Preferred time of day",
                [t.value for t in TimeOfDay],
            )
        notes = st.text_area("Notes (optional)", value="")
        recurring = st.checkbox("Recurring daily task")
        submitted_task = st.form_submit_button("Add Task")

    if submitted_task:
        pet = owner.get_pet(target_pet)
        pet.add_task(Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=Priority(priority),
            task_type=TaskType(task_type),
            time_of_day=TimeOfDay(time_of_day),
            recurring=recurring,
            notes=notes,
        ))
        st.success(f"Added '{task_title}' to {target_pet}.")

    # Show tasks per pet
    has_tasks = any(pet.tasks for pet in owner.pets)
    if has_tasks:
        st.markdown("**Current tasks by pet:**")
        for pet in owner.pets:
            if pet.tasks:
                st.markdown(f"**{pet.name}** ({pet.total_care_minutes()} min total)")
                for task in pet.tasks:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(
                            f"- `{task.priority.value.upper()}` &nbsp; "
                            f"**{task.title}** &nbsp; "
                            f"({task.duration_minutes} min | {task.task_type.value} | {task.time_of_day.value})"
                        )

st.divider()

# ---------------------------------------------------------------------------
# Section 4: Generate Schedule
# ---------------------------------------------------------------------------

st.subheader("4. Generate Daily Schedule")

if st.session_state.owner is None:
    st.warning("Complete the Owner Profile (Section 1) first.")
elif not st.session_state.owner.total_tasks_across_pets():
    st.warning("Add at least one task (Section 3) before generating a schedule.")
else:
    owner: Owner = st.session_state.owner

    if st.button("Generate Schedule", type="primary"):
        scheduler = Scheduler(owner)
        schedule = scheduler.generate_schedule()

        st.markdown(f"### Daily Plan for {owner.name}")
        st.caption(f"Available time: {owner.available_minutes_per_day} min")

        if schedule:
            for st_item in sorted(schedule, key=lambda x: x.start_minute):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 3, 2])
                    with col1:
                        st.markdown(f"**{st_item.time_label()}**")
                    with col2:
                        st.markdown(
                            f"**{st_item.task.title}** — {st_item.pet.name}"
                        )
                        st.caption(st_item.reason)
                    with col3:
                        priority_color = {
                            "high": ":red[HIGH]",
                            "medium": ":orange[MEDIUM]",
                            "low": ":green[LOW]",
                        }
                        st.markdown(priority_color.get(st_item.task.priority.value, ""))
                        st.caption(f"{st_item.task.duration_minutes} min")
        else:
            st.error("No tasks could be scheduled within the daily time limit.")

        skipped = scheduler._skipped
        if skipped:
            with st.expander(f"Skipped tasks ({len(skipped)}) — exceeded daily limit"):
                for task, pet in skipped:
                    st.markdown(
                        f"- [{pet.name}] **{task.title}** "
                        f"({task.duration_minutes} min | {task.priority.value})"
                    )

        conflicts = scheduler.get_conflicts()
        if conflicts:
            st.warning("**Schedule conflicts detected:**")
            for c in conflicts:
                st.markdown(f"- {c}")
