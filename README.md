# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Testing PawPal+

### Run the tests

```bash
python -m pytest
```

### What the tests cover

| Test class | Behaviours verified |
|---|---|
| `TestTask` | `mark_complete()` status change, idempotency, `priority_score()` ordering, `__str__` content |
| `TestTaskRecurrence` | `next_occurrence()` advances `due_date` by 1 day, resets `completed`, preserves all other fields; raises `ValueError` for non-recurring tasks; `get_recurring_next_occurrences()` filters correctly |
| `TestPet` | Add / remove tasks, task count, filter by priority and type, `total_care_minutes()` |
| `TestOwner` | Add / get / remove pets, flatten all tasks across pets |
| `TestScheduler` | Schedule generation, daily time budget enforcement, priority ordering, time-of-day ordering, conflict-free sequential output |
| `TestSortByTime` | Chronological sort by explicit `scheduled_time`, bucket fallback order, mixed input, empty list |
| `TestFilterTasks` | Filter by pet name, completion status, combined criteria, no-match returns `[]` |
| `TestConflictDetection` | Exact-same-time conflict, overlapping windows, adjacent (non-overlapping) tasks, tasks without `scheduled_time` ignored, three-way conflicts, cross-pet conflicts |
| `TestEdgeCases` | Empty pet, empty owner, pet with no tasks, single task at budget limit, 1-minute over budget, remove-only task |

**Total: 59 tests — all passing**

### Confidence level

★★★★☆ (4 / 5)

The scheduler's core behaviours — priority ordering, time-of-day bucketing, time budget enforcement, recurring roll-over, and conflict detection — are all verified with both happy-path and edge-case tests. The main gap is end-to-end UI integration tests (Streamlit interactions are not covered by pytest) and load tests with very large task lists.

## Smarter Scheduling

PawPal+ goes beyond a simple task list with four algorithmic features built into `Scheduler`:

### Priority-first scheduling
Tasks are sorted HIGH → MEDIUM → LOW within each time window. A high-priority medication will always be placed before a low-priority grooming session, even if they share the same time-of-day bucket. Sorting uses a numeric score (HIGH=3, MEDIUM=2, LOW=1) as the key for Python's `sorted()`.

### Chronological sort (`sort_by_time`)
Tasks that carry an explicit `scheduled_time` (e.g. `"08:30"`) can be displayed in wall-clock order using `Scheduler.sort_by_time()`. It uses a lambda key that compares zero-padded `"HH:MM"` strings lexicographically — a clean trick that avoids converting to `datetime` objects for simple ordering.

### Completion-status and pet filtering (`filter_tasks`)
`Scheduler.filter_tasks(pet_name=..., completed=...)` lets you slice the task list by pet and/or status. Useful for building "what's left today?" views or per-pet dashboards without re-running the full scheduler.

### Recurring task roll-over (`next_occurrence`)
Tasks marked `recurring=True` carry a `due_date`. Calling `task.next_occurrence()` returns a fresh copy of the task with `completed=False` and `due_date` advanced by one day using Python's `timedelta`. `Scheduler.get_recurring_next_occurrences()` collects all next-day instances in one call.

### Conflict detection (`detect_time_conflicts`)
When tasks have an explicit `scheduled_time`, `Scheduler.detect_time_conflicts()` scans every pair with an O(n²) overlap check:

```
task_a.start < task_b.end  AND  task_b.start < task_a.end
```

It returns human-readable warning strings instead of raising exceptions, so the app can display warnings without crashing. The tradeoff: it only catches conflicts between tasks with a `scheduled_time` set; tasks using only `time_of_day` buckets are not checked here (the post-scheduling `detect_conflicts()` on `ScheduledTask` objects handles those).
