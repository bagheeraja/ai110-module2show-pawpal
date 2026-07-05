from datetime import date, datetime, time, timedelta

import streamlit as st

from pawpal_system import Owner, Pet, Priority, Recurrence, Scheduler, Task, TaskType

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

SPECIES_ICONS = {"dog": "🐶", "cat": "🐱", "other": "🐾"}

with st.sidebar:
    st.header("🐾 PawPal+")
    st.caption("A pet care planning assistant")

    owner_name = st.text_input("Your name", value="Jordan")

    # Streamlit reruns this whole script on every interaction, so an Owner()
    # created here directly would be re-created (and lose all its pets/tasks)
    # on every click. Checking session_state first means it's only created
    # once per session and persists across reruns.
    if "owner" not in st.session_state:
        st.session_state.owner = Owner(name=owner_name, email="")
    owner: Owner = st.session_state.owner
    owner.name = owner_name

    st.divider()
    st.markdown(
        """
**How to use this app**
1. Add a pet in the **Pets** tab.
2. Add tasks (walks, feeding, meds, appointments) for that pet in the **Tasks** tab — use "Find the next open slot" if you're not sure when they're free.
3. Build today's plan in the **Schedule** tab — it's ordered by priority (or time), flags any scheduling conflicts, and lets you check tasks off as complete.
4. Catch up on anything overdue in the **Missed Tasks** tab, either by picking a new time yourself or letting weekly tasks auto-reschedule.
        """
    )

    if owner.pets:
        st.divider()
        total_tasks = sum(len(pet.tasks) for pet in owner.pets)
        col1, col2 = st.columns(2)
        col1.metric("Pets", len(owner.pets))
        col2.metric("Tasks", total_tasks)

st.title(f"{owner.name}'s pet care planner")

# Scheduler is stateless, so one instance is shared across every tab below.
scheduler = Scheduler()

pets_tab, tasks_tab, schedule_tab, missed_tab = st.tabs(
    ["🐕 Pets", "📝 Tasks", "📅 Schedule", "⏰ Missed Tasks"]
)

with pets_tab:
    st.subheader("Add a pet")
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        birthdate = st.date_input("Birthdate", value=date(2022, 1, 1))

    if st.button("➕ Add pet", type="primary"):
        owner.add_pet(Pet(name=pet_name, species=species, birthdate=birthdate))
        st.success(f"Added {pet_name} to {owner.name}'s pets.")

    st.divider()

    if owner.pets:
        st.write("**Your pets**")
        st.dataframe(
            [
                {
                    "": SPECIES_ICONS.get(pet.species, "🐾"),
                    "Name": pet.name,
                    "Species": pet.species.title(),
                    "Birthdate": pet.birthdate.isoformat(),
                    "Tasks": len(pet.tasks),
                }
                for pet in owner.pets
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No pets yet. Add one above to get started.")

with tasks_tab:
    if not owner.pets:
        st.info("Add a pet first, in the **Pets** tab — tasks need to belong to a pet.")
    else:
        st.subheader("Add a task")

        pet_names = [pet.name for pet in owner.pets]
        selected_pet_name = st.selectbox("Pet", pet_names)
        selected_pet = next(pet for pet in owner.pets if pet.name == selected_pet_name)

        with st.expander(f"🔍 Not sure when {selected_pet.name}'s free? Find the next open slot"):
            col1, col2 = st.columns(2)
            with col1:
                slot_date = st.date_input("Date", value=date.today(), key="slot-date")
            with col2:
                slot_duration = st.number_input(
                    "Duration (minutes)", min_value=1, max_value=240, value=20, key="slot-duration"
                )
            col3, col4 = st.columns(2)
            with col3:
                slot_earliest = st.time_input("Earliest", value=time(7, 0), key="slot-earliest")
            with col4:
                slot_latest = st.time_input("Latest", value=time(21, 0), key="slot-latest")

            if st.button("🔍 Find slot", key="find-slot"):
                slot = scheduler.find_next_available_slot(
                    selected_pet,
                    slot_date,
                    int(slot_duration),
                    earliest=slot_earliest,
                    latest=slot_latest,
                )
                if slot is not None:
                    st.success(
                        f"Next open {int(slot_duration)}-minute slot for {selected_pet.name}: "
                        f"{slot.strftime('%I:%M %p')} on {slot.strftime('%A, %B %d')}"
                    )
                else:
                    st.warning(
                        f"No {int(slot_duration)}-minute slot free for {selected_pet.name} between "
                        f"{slot_earliest.strftime('%I:%M %p')} and {slot_latest.strftime('%I:%M %p')} "
                        f"on {slot_date.isoformat()}."
                    )

        task_title = st.text_input("Task title", value="Morning walk")

        col1, col2, col3 = st.columns(3)
        with col1:
            task_type_label = st.selectbox("Task type", [t.name.title() for t in TaskType])
        with col2:
            priority_label = st.selectbox("Priority", [p.name.title() for p in Priority], index=2)
        with col3:
            recurrence_label = st.selectbox("Recurrence", [r.name.title() for r in Recurrence])

        col4, col5 = st.columns(2)
        with col4:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col5:
            scheduled_time_input = st.time_input("Time", value=time(8, 0))

        if st.button("➕ Add task", type="primary"):
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

        st.divider()

        all_tasks = [(pet, task) for pet in owner.pets for task in pet.tasks]
        if all_tasks:
            st.write("**Current tasks**")

            widths = [2, 3, 2, 2, 2, 2, 2, 1]
            header_cols = st.columns(widths)
            for col, label in zip(
                header_cols, ["Pet", "Task", "Type", "Duration", "Priority", "Recurrence", "Time", ""]
            ):
                col.markdown(f"**{label}**")

            for pet, task in all_tasks:
                row = st.columns(widths)
                row[0].write(pet.name)
                row[1].write(task.title)
                row[2].write(task.task_type.name.title())
                row[3].write(f"{task.duration_minutes} min")
                row[4].write(task.priority.name.title())
                row[5].write(task.recurrence.name.title())
                row[6].write(task.scheduled_time.strftime("%I:%M %p"))
                if row[7].button("🗑️", key=f"delete-{task.id}", help=f"Delete '{task.title}'"):
                    pet.remove_task(task.id)
                    st.rerun()
        else:
            st.info("No tasks yet. Add one above.")

with schedule_tab:
    st.subheader("Today's plan")

    if not owner.pets:
        st.info("Add a pet and some tasks first.")
    else:
        st.caption(f"Builds {date.today().strftime('%A, %B %d')}'s plan across all of {owner.name}'s pets.")

        sort_mode = st.radio(
            "Sort by",
            ["Priority (default plan order)", "Time of day"],
            horizontal=True,
        )

        if st.button("📅 Generate schedule", type="primary"):
            st.session_state.schedule_shown = True

        # Marking a task complete below is itself a button click, which would
        # otherwise reset the "Generate schedule" button's own if-block back to
        # False on the next rerun and make the whole plan vanish. Tracking
        # "should the plan be shown" in session_state instead means the plan
        # (recomputed fresh each time, so it reflects the latest completions)
        # stays visible across those inner button clicks.
        if st.session_state.get("schedule_shown"):
            plan = scheduler.build_daily_plan_for_owner(owner, date.today())

            if not plan:
                st.info("Nothing scheduled for today.")
            else:
                # Surface conflicts first, above the schedule -- an owner should see
                # "these two things clash" before they see the full list of tasks,
                # so it doesn't get missed by scrolling past it.
                conflicts = scheduler.detect_conflicts(plan)
                conflicting_ids = {occurrence.task.id for pair in conflicts for occurrence in pair}

                warnings = scheduler.get_conflict_warnings(plan)
                if warnings:
                    st.error(f"⚠️ {len(warnings)} scheduling conflict(s) found today:")
                    for warning in warnings:
                        st.warning(warning)
                else:
                    st.success("✅ No conflicts — today's plan is clash-free.")

                ordered = plan if sort_mode.startswith("Priority") else scheduler.sort_by_time(plan)

                widths = [2, 2, 3, 2, 1, 2]
                header_cols = st.columns(widths)
                for col, label in zip(header_cols, ["Time", "Pet", "Task", "Priority", "Conflict", ""]):
                    col.markdown(f"**{label}**")

                for occurrence in ordered:
                    row = st.columns(widths)
                    row[0].write(occurrence.start_time.strftime("%I:%M %p"))
                    row[1].write(occurrence.pet.name)
                    row[2].write(occurrence.task.title)
                    row[3].write(occurrence.task.priority.name.title())
                    row[4].write("⚠️" if occurrence.task.id in conflicting_ids else "")
                    if row[5].button("✅ Complete", key=f"complete-{occurrence.task.id}"):
                        occurrence.mark_complete()
                        st.rerun()

with missed_tab:
    st.subheader("Missed tasks")

    if not owner.pets:
        st.info("Add a pet and some tasks first.")
    else:
        missed = [
            (pet, occurrence)
            for pet in owner.pets
            for occurrence in scheduler.get_missed_tasks(pet, date.today())
        ]

        if not missed:
            st.success("✅ No missed tasks — everyone's caught up.")
        else:
            st.warning(f"{len(missed)} missed task(s) found:")

            for pet, occurrence in missed:
                task = occurrence.task
                missed_when = (
                    f"{occurrence.occurrence_date.isoformat()} at "
                    f"{occurrence.start_time.strftime('%I:%M %p')}"
                )
                with st.expander(f"{pet.name}: {task.title} — missed {missed_when}"):
                    if task.recurrence == Recurrence.WEEKLY:
                        st.caption(
                            "This is a weekly task -- auto-reschedule will try to patch just "
                            "this occurrence first, and only shift future weeks if there's no "
                            "room before the next one is due."
                        )
                        if st.button(
                            "🔁 Auto-reschedule", key=f"auto-{task.id}-{occurrence.occurrence_date}"
                        ):
                            recovered = scheduler.auto_reschedule_missed_weekly(
                                task, pet, occurrence.occurrence_date
                            )
                            if recovered is not None:
                                st.success(f"Recovered to {recovered.isoformat()}.")
                                st.rerun()
                            else:
                                st.error("No available slot found to recover this task.")
                        st.divider()

                    st.caption("Or pick a new time yourself:")
                    col1, col2 = st.columns(2)
                    with col1:
                        new_date = st.date_input(
                            "New date",
                            value=date.today() + timedelta(days=1),
                            key=f"reschedule-date-{task.id}-{occurrence.occurrence_date}",
                        )
                    with col2:
                        new_time = st.time_input(
                            "New time",
                            value=task.scheduled_time.time(),
                            key=f"reschedule-time-{task.id}-{occurrence.occurrence_date}",
                        )
                    if st.button(
                        "📌 Reschedule", key=f"manual-{task.id}-{occurrence.occurrence_date}"
                    ):
                        task.reschedule(datetime.combine(new_date, new_time))
                        st.success(
                            f"Rescheduled '{task.title}' to {new_date.isoformat()} "
                            f"at {new_time.strftime('%I:%M %p')}."
                        )
                        st.rerun()
