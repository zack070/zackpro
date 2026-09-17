"""Reference heuristic: earliest-deadline-first with urgency weighting,
skill-scarcity-aware technician selection (don't burn a scarce-skill tech
on a job any generalist could do), and a preference for rested technicians
over fatigued ones when a rested alternative can still make the deadline."""

FATIGUE_THRESHOLD_MIN = 180


def _scarcity(job, techs):
    return sum(1 for t in techs if job.required_skill in t.skills)


def decide(state):
    jobs_sorted = sorted(
        state.pending_jobs,
        key=lambda j: (0 if j.priority == "urgent" else 1, j.deadline),
    )
    used_techs = set()
    used_jobs = set()
    assignments = []

    for job in jobs_sorted:
        if job.job_id in used_jobs:
            continue
        candidates = [t for t in state.free_technicians if t.tech_id not in used_techs and job.required_skill in t.skills]
        if not candidates:
            continue

        def tech_score(t):
            scarce_skills = sum(1 for s in t.skills if _scarcity_by_name(s, state.free_technicians) <= 2)
            rested = 0 if t.continuous_work < FATIGUE_THRESHOLD_MIN else 1
            remaining_capacity = (t.shift_end + t.max_overtime) - state.current_time
            return (rested, scarce_skills, -remaining_capacity)

        candidates.sort(key=tech_score)
        chosen = candidates[0]
        assignments.append((chosen.tech_id, job.job_id))
        used_techs.add(chosen.tech_id)
        used_jobs.add(job.job_id)

    return assignments


def _scarcity_by_name(skill, techs):
    return sum(1 for t in techs if skill in t.skills)
