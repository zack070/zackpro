"""Genuinely fatigue- and cascade-aware policy: prioritizes urgent jobs,
actively avoids assigning an already-fatigued technician when a rested
eligible alternative exists (even at the cost of deadline-optimality),
and reserves scarce-skill technicians for jobs only they can do."""

FATIGUE_THRESHOLD_MIN = 180


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

        rested = [t for t in candidates if t.continuous_work < FATIGUE_THRESHOLD_MIN]
        pool = rested if rested else candidates

        def tech_score(t):
            scarcity = _scarcity(job.required_skill, state.free_technicians)
            # among rested candidates, prefer the one with the LEAST scarce
            # skill set free for other jobs (i.e. save scarce-skill techs)
            other_skills_scarcity = min((_scarcity(s, state.free_technicians) for s in t.skills), default=99)
            return (-other_skills_scarcity, t.continuous_work)

        pool.sort(key=tech_score)
        chosen = pool[0]
        assignments.append((chosen.tech_id, job.job_id))
        used_techs.add(chosen.tech_id)
        used_jobs.add(job.job_id)

    return assignments
