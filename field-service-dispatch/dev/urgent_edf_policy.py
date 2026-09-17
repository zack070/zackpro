"""Urgent-first, then earliest-deadline, first eligible free technician
(no fatigue awareness, no scarcity awareness)."""


def decide(state):
    jobs_sorted = sorted(state.pending_jobs, key=lambda j: (0 if j.priority == "urgent" else 1, j.deadline))
    used_techs = set()
    used_jobs = set()
    assignments = []
    for job in jobs_sorted:
        if job.job_id in used_jobs:
            continue
        for tech in state.free_technicians:
            if tech.tech_id in used_techs:
                continue
            if job.required_skill in tech.skills:
                assignments.append((tech.tech_id, job.job_id))
                used_techs.add(tech.tech_id)
                used_jobs.add(job.job_id)
                break
    return assignments
