"""Kitchen-sink greedy: combines every tie-break trick tried this session
(job order = scarcity of required skill, then urgent, then deadline; tech
choice = feasibility filter, then prefer least-fatigued, then prefer
least-scarce-other-skills, then best-fit remaining capacity) in one
fixed-priority pass. Still greedy (one job at a time, no joint
reasoning) -- used as the toughest single adversarial probe against the
batch-matching reference."""

FATIGUE_THRESHOLD_MIN = 180
FATIGUE_MULTIPLIER = 1.25


def _scarcity(skill, techs):
    return sum(1 for t in techs if skill in t.skills)


def decide(state):
    def job_key(j):
        scarcity = _scarcity(j.required_skill, state.free_technicians)
        return (scarcity, 0 if j.priority == "urgent" else 1, j.deadline)

    jobs_sorted = sorted(state.pending_jobs, key=job_key)
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
            if finish <= t.shift_end + t.max_overtime:
                feasible.append(t)
        pool = feasible if feasible else candidates

        rested = [t for t in pool if t.continuous_work < FATIGUE_THRESHOLD_MIN]
        pool2 = rested if rested else pool

        def tech_score(t):
            other_skills = t.skills - {job.required_skill}
            other_scarcity = min((_scarcity(s, state.free_technicians) for s in other_skills), default=99)
            dur = duration_for(t)
            finish = state.current_time + dur
            leftover = (t.shift_end + t.max_overtime) - finish
            return (-other_scarcity, leftover)

        pool2.sort(key=tech_score)
        chosen = pool2[0]
        assignments.append((chosen.tech_id, job.job_id))
        used_techs.add(chosen.tech_id)
        used_jobs.add(job.job_id)

    return assignments
