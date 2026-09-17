"""The reviewer's exact probe: earliest-deadline-first, but among eligible
free technicians prefer whichever has the fewest total skills (the
least-flexible-resource heuristic), with no fatigue awareness at all."""


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
        candidates.sort(key=lambda t: len(t.skills))
        chosen = candidates[0]
        assignments.append((chosen.tech_id, job.job_id))
        used_techs.add(chosen.tech_id)
        used_jobs.add(job.job_id)
    return assignments
