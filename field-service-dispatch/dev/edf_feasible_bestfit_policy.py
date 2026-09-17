"""Earliest-deadline-first; among eligible free technicians, filter to those
who can actually finish the job within their shift_end + max_overtime cap
(accounting for the fatigue multiplier if already fatigued), then prefer
the one with the SMALLEST resulting leftover capacity (best-fit), saving
technicians with generous remaining capacity for jobs that may need more
room later."""

FATIGUE_THRESHOLD_MIN = 180
FATIGUE_MULTIPLIER = 1.25


def decide(state):
    jobs_sorted = sorted(state.pending_jobs, key=lambda j: j.deadline)
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
                leftover = shift_limit - finish
                feasible.append((leftover, t))

        if not feasible:
            continue  # no technician can actually complete this job within cap right now

        feasible.sort(key=lambda pair: pair[0])
        chosen = feasible[0][1]
        assignments.append((chosen.tech_id, job.job_id))
        used_techs.add(chosen.tech_id)
        used_jobs.add(job.job_id)
    return assignments
