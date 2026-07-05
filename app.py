from datetime import date, datetime, time

import streamlit as st

from pawpal_system import Owner, Pet, Priority, Recurrence, Scheduler, Task, TaskType

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

owner_name = st.text_input("Owner name", value="Jordan")

# Streamlit reruns this whole script on every interaction, so an Owner()
# created here directly would be re-created (and lose all its pets/tasks)
# on every click. Checking session_state first means it's only created once
# per session and persists across reruns.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name, email="")
owner: Owner = st.session_state.owner
owner.name = owner_name

st.subheader("Add a Pet")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])
birthdate = st.date_input("Birthdate", value=date(2022, 1, 1))

if st.button("Add pet"):
    owner.add_pet(Pet(name=pet_name, species=species, birthdate=birthdate))
    st.success(f"Added {pet_name} to {owner.name}'s pets.")

if owner.pets:
    st.write("Current pets:")
    st.table([{"name": pet.name, "species": pet.species} for pet in owner.pets])
else:
    st.info("No pets yet. Add one above.")

st.divider()

st.subheader("Add a Task")

if not owner.pets:
    st.info("Add a pet first -- tasks need to belong to a pet.")
else:
    pet_names = [pet.name for pet in owner.pets]
    selected_pet_name = st.selectbox("Pet", pet_names)
    selected_pet = next(pet for pet in owner.pets if pet.name == selected_pet_name)

    task_title = st.text_input("Task title", value="Morning walk")
    task_type_label = st.selectbox("Task type", [t.name.title() for t in TaskType])
    col1, col2, col3 = st.columns(3)
    with col1:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col2:
        priority_label = st.selectbox("Priority", [p.name.title() for p in Priority], index=2)
    with col3:
        scheduled_time_input = st.time_input("Time", value=time(8, 0))
    recurrence_label = st.selectbox("Recurrence", [r.name.title() for r in Recurrence])

    if st.button("Add task"):
        selected_pet.add_task(
            Task(
                title=task_title,
                task_type=TaskType[task_type_label.upper()],
                duration_minutes=int(duration),
                priority=Priority[priority_label.upper()],
                scheduled_time=datetime.combine(date.today(), scheduled_time_input),
                recurrence=Recurrence[recurrence_label.upper()],
            )
        )
        st.success(f"Added '{task_title}' to {selected_pet.name}.")

    all_tasks = [(pet, task) for pet in owner.pets for task in pet.tasks]
    if all_tasks:
        st.write("Current tasks:")
        st.table(
            [
                {
                    "pet": pet.name,
                    "title": task.title,
                    "type": task.task_type.name,
                    "duration_minutes": task.duration_minutes,
                    "priority": task.priority.name,
                    "recurrence": task.recurrence.name,
                    "time": task.scheduled_time.strftime("%I:%M %p"),
                }
                for pet, task in all_tasks
            ]
        )
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Builds today's plan across all of this owner's pets.")

if st.button("Generate schedule"):
    scheduler = Scheduler()
    plan = scheduler.build_daily_plan_for_owner(owner, date.today())

    if not plan:
        st.info("Nothing scheduled for today.")
    else:
        for occurrence in plan:
            start = occurrence.start_time.strftime("%I:%M %p")
            st.write(
                f"**{start}** — {occurrence.pet.name}: {occurrence.task.title} "
                f"[{occurrence.task.priority.name}]"
            )

        conflicts = scheduler.detect_conflicts(plan)
        if conflicts:
            st.warning("Conflicts detected:")
            for a, b in conflicts:
                st.write(f"- {a.pet.name}'s {a.task.title} overlaps {b.pet.name}'s {b.task.title}")
