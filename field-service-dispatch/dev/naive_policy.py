"""Naive baseline: assign the first eligible pending job (in the order the
simulator hands them to us) to the first eligible free technician, no
regard for priority, deadline, or fatigue."""


def decide(state):
    assignments = []
    used_techs = set()
    used_jobs = set()
    for job in state.pending_jobs:
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
