"""Most-constrained-first: process pending jobs ordered by scarcity of
their required skill (rarest skill first), then urgency, then deadline --
rather than deadline-first with scarcity only as a tech tie-break. Among
eligible technicians for a job, still avoid burning a technician who holds
a scarcer other skill on a job any generalist could do."""


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

        def tech_score(t):
            other_skills_scarcity = min((_scarcity(s, state.free_technicians) for s in t.skills), default=99)
            return (-other_skills_scarcity, t.continuous_work)

        candidates.sort(key=tech_score)
        chosen = candidates[0]
        assignments.append((chosen.tech_id, job.job_id))
        used_techs.add(chosen.tech_id)
        used_jobs.add(job.job_id)

    return assignments
