"""Combined-reasoning policy: urgency-first ordering, scarce-skill
reservation (don't burn a technician who can do rare work on a job any
generalist could do), and capacity feasibility -- among remaining
candidates, filter out technicians who cannot actually finish the job
within their shift_end + max_overtime cap (accounting for the fatigue
multiplier), then prefer the technician with the least slack left after
the job (best-fit), to avoid stranding low-capacity technicians on
oversized jobs early in the shift."""

FATIGUE_THRESHOLD_MIN = 180
FATIGUE_MULTIPLIER = 1.25


def _scarcity(skill, techs):
    return sum(1 for t in techs if skill in t.skills)


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

        def duration_for(t):
            if t.continuous_work >= FATIGUE_THRESHOLD_MIN:
                return int(round(job.duration * FATIGUE_MULTIPLIER))
            return job.duration

        feasible = []
        for t in candidates:
            dur = duration_for(t)
            finish = state.current_time + dur
            shift_limit = t.shift_end + t.max_overtime
            if finish <= shift_limit:
                feasible.append(t)
        pool = feasible if feasible else candidates

        def tech_score(t):
            other_skills_scarcity = min((_scarcity(s, state.free_technicians) for s in t.skills), default=99)
            dur = duration_for(t)
            finish = state.current_time + dur
            leftover = (t.shift_end + t.max_overtime) - finish
            return (-other_skills_scarcity, leftover)

        pool.sort(key=tech_score)
        chosen = pool[0]
        assignments.append((chosen.tech_id, job.job_id))
        used_techs.add(chosen.tech_id)
        used_jobs.add(job.job_id)

    return assignments
