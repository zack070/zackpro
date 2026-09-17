"""Earliest-deadline-first; among eligible free technicians, filter to those
who can actually finish the job within their shift_end + max_overtime cap,
then take the first one in list order (no best/worst-fit preference) --
isolates the value of feasibility-checking itself, apart from any tie-break
sophistication."""

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
        chosen = None
        for t in candidates:
            dur = job.duration
            if t.continuous_work >= FATIGUE_THRESHOLD_MIN:
                dur = int(round(job.duration * FATIGUE_MULTIPLIER))
            if state.current_time + dur <= t.shift_end + t.max_overtime:
                chosen = t
                break
        if chosen is None:
            continue
        assignments.append((chosen.tech_id, job.job_id))
        used_techs.add(chosen.tech_id)
        used_jobs.add(job.job_id)
    return assignments
