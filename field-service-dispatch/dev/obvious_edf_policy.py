"""The exact adversarial probe the reviewer used: earliest-deadline-first,
first eligible free technician, zero fatigue/scarcity/cascade awareness.
This is now a permanent calibration gate -- any scenario set we ship must
make this policy fail the pass bar."""


def decide(state):
    jobs_sorted = sorted(state.pending_jobs, key=lambda j: j.deadline)
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
