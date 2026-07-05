# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

Two stretch tasks in one session: (1) close a gap the agent itself had flagged earlier — `build_daily_plan`'s same-priority tie-break was alphabetical by title instead of chronological (Challenge 3: Advanced Priority Scheduling) — and (2) add a third algorithmic scheduling capability beyond what already existed: priority ordering, conflict detection, and recurrence expansion (Challenge 1: Advanced Algorithmic Capability). I asked for #3 to be a "next available slot" finder.

**What did the agent do?**

*Files modified:* `pawpal_system.py`, `tests/test_pawpal.py`, `main.py`, `README.md`, `reflection.md`, `ai_interactions.md` (this file).

- **Challenge 3:** Changed `Scheduler._finalize_plan`'s sort key from `occurrence.task.title` to `occurrence.start_time`, and updated the docstrings on `build_daily_plan`, `build_daily_plan_for_owner`, and `_finalize_plan` that referenced the old "alphabetically by title" behavior. Added `test_build_daily_plan_orders_by_priority_then_start_time`, deliberately naming two same-priority tasks with titles alphabetized *backwards* from their times ("Zebra checkup" at 9 AM, "Ant grooming" at 2 PM) so the test only passes if the tie-break is genuinely time-based rather than title-based. Ran the full suite (11 passed) before moving on. Updated README's Features list, the Smarter Scheduling table, the test-count/coverage description, and added a dedicated "Priority-based scheduling in action" CLI example built from the same intentionally-backwards-alphabetized scenario. Updated `reflection.md`'s design-changes entry and the constraints/tradeoffs section, which had explicitly called the alphabetical tie-break out as an "initial" choice pending a more meaningful (time-based) rule.
- **Challenge 1:** Added `Scheduler.find_next_available_slot(pet, target_date, duration_minutes, *, earliest, latest)`. It sorts the pet's busy windows for that date, walks them tracking the *furthest* end time seen so far (not just each window's own end), and returns the first gap that's large enough — which correctly handles two occurrences that overlap each other rather than reporting a false gap between them. Verified by hand with five scenarios (empty day, gap after one task, exact-fit between back-to-back tasks, overlapping busy windows, fully booked day returning `None`) before writing three permanent tests covering the busy-window-skip, overlap-collapse, and fully-booked-returns-`None` cases. Wired a demo call into `main.py` and verified its printed output (`08:20 AM`) matched the hand-derived expected result. Documented the method in README's Features list, Smarter Scheduling table, and Sample CLI output block.

**What did you have to verify or fix manually?**

Nothing required a fix in this session — the tie-break change and the new method both passed their tests and manual verification on the first attempt. The main verification step was working out the expected slot-finder result by hand (given Mochi's overlapping 8:00 AM tasks in `main.py`, the next free 30-minute slot after 8:00 AM should be 8:20 AM, right after both tasks end) *before* running the code, then confirming the actual output matched — rather than trusting the printed output at face value.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

**Task:** Add `Scheduler.auto_reschedule_missed_weekly(task, pet, missed_date) -> date | None` -- given a missed occurrence of a `WEEKLY` task, decide whether to recover just that occurrence (find it a new slot before the series' next natural date) or, if there's no room, shift the whole series anchor forward. Both models got the identical prompt, with `pawpal_system.py` attached as the only context file.

| | Option A (Claude) | Option B (Gemini) |
|-|----------|----------|
| **Model / tool used** | Claude (this session) | Gemini (external, same prompt + `pawpal_system.py` pasted manually) |
| **Prompt** | Identical prompt for both -- see the prompt text above this table in the session transcript / commit history. | Same. |
| **Response summary** | Two-phase design: Phase 1 scans day-by-day for an isolated makeup slot before the next natural occurrence (biased to the task's usual time-of-day via `earliest=`); Phase 2 falls back to `task.reschedule()` onto `missed_date` itself with **no availability check**. Raises `ValueError` for a non-`WEEKLY` task. | Same two-phase shape. Phase 1 identical in spirit. Phase 2 also falls back to `task.reschedule()`, but *does* call `find_next_available_slot` first and searches forward day-by-day in an unbounded `while True` loop until it finds a slot or hits `recurrence_end_date`. Returns `None` (not a raise) for a non-`WEEKLY` task. |
| **What was useful** | The `earliest=task.scheduled_time.time()` constraint, so a recovered "9 AM walk" doesn't get shoved to 2 AM. The explicit written explanation that `Task` has no single-occurrence-exception concept, so Phase 1's returned date is a proposal, not a persisted change. | The Phase 2 conflict check (calling `find_next_available_slot` before shifting the series) -- catches exactly the bug in Claude's own Phase 2. Starting the search at `missed_date + 1 day` rather than `missed_date` itself -- `missed_date` is by definition already in the past (per `get_missed_tasks`'s contract), so searching on it doesn't make sense. |
| **Problems noticed** | **Real bug:** Phase 2 calls `task.reschedule()` directly onto `missed_date` with zero conflict checking, directly contradicting the prompt's own requirement to avoid creating a new conflict. **Also:** Phase 1's search range started at `missed_date` itself (offset 0), i.e., searching a date that has already passed. | **Real bug:** Phase 2's `while True` loop has no upper bound at all when `recurrence_end_date` is `None` -- a pet with a fully booked calendar and an unbounded series would loop forever. Doesn't bias the recovered slot to the task's usual time-of-day, so a "9 AM walk" could get recovered at 2 AM. Silently returning `None` for a misuse case (wrong recurrence type) hides a caller bug instead of surfacing it, inconsistent with this codebase's existing pattern of raising in `Task.__post_init__`. |
| **Decision** | Neither response was used as-is -- both had a genuine bug serious enough to ship a wrong result (Claude's: blind conflict creation; Gemini's: unbounded loop / no time-of-day bias). | Synthesized the two: adopted Gemini's "search starts at `missed_date + 1`" and "Phase 2 must conflict-check via `find_next_available_slot` before rescheduling," combined with Claude's `earliest=` time-of-day bias and `raise ValueError` on misuse, plus a new `max_days_ahead` cap (neither model added) to bound Phase 2's search and eliminate Gemini's unbounded-loop risk. |

**Which approach did you use in your final implementation and why?**

Neither response verbatim. The two models made the *same* high-level design choice (try an isolated single-occurrence fix first, fall back to shifting the whole series) but diverged on exactly the details that matter for correctness -- and each other's version happened to fix a bug the other one had. Claude's Phase 2 would have silently created a new conflict; Gemini's Phase 2 could spin forever on a fully-booked, open-ended series. Treating this as a two-vs-one problem rather than picking a "winner" produced a version with none of either's known bugs (`pawpal_system.py::Scheduler.auto_reschedule_missed_weekly`), verified against four scenarios (isolated recovery, forced series shift, `recurrence_end_date` exhaustion, misuse) and covered by four new tests in `tests/test_pawpal.py`. The lesson: comparing two models' output surfaces real bugs neither one's own self-review would have caught, precisely because they diverged on the parts that were actually hard (conflict-checking discipline, loop termination, past-date handling) rather than the parts that were obvious (the two-phase shape itself).
