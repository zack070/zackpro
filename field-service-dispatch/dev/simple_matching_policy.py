"""A plainer exact-matching policy: recognizes this is an assignment
problem and solves it exactly (brute force over small batches), but
without the fine-tuned scarcity/breach-credit shaping in the shipped
reference -- just urgency-first job selection and minimum feasible
overtime cost for the tech assignment. Used to check that a good-faith
'this is a matching problem' submission clears the bar even without
matching every nuance of the shipped reference's cost function."""
import itertools

FATIGUE_THRESHOLD_MIN = 180
FATIGUE_MULTIPLIER = 1.25
MAX_JOINT = 8


def _duration_for(job, tech):
    if tech.continuous_work >= FATIGUE_THRESHOLD_MIN:
        return int(round(job.duration * FATIGUE_MULTIPLIER))
    return job.duration


def _cost(job, tech, now):
    if job.required_skill not in tech.skills:
        return None
    dur = _duration_for(job, tech)
    finish = now + dur
    if finish > tech.shift_end + tech.max_overtime:
        return None
    overtime = max(0, finish - max(now, tech.shift_end))
    miss_penalty = 100.0 if finish > job.deadline else 0.0
    return overtime + miss_penalty


def decide(state):
    all_jobs = list(state.pending_jobs)
    all_techs = list(state.free_technicians)
    if not all_jobs or not all_techs:
        return []

    jobs_sorted = sorted(all_jobs, key=lambda j: (0 if j.priority == "urgent" else 1, j.deadline))[:MAX_JOINT]
    m = min(len(jobs_sorted), len(all_techs))
    if m == 0:
        return []

    best = []
    best_key = (0, 0.0)
    for job_subset in itertools.combinations(jobs_sorted, m):
        for tech_perm in itertools.permutations(all_techs, m):
            assignment = []
            total = 0.0
            count = 0
            for j, t in zip(job_subset, tech_perm):
                c = _cost(j, t, state.current_time)
                if c is not None:
                    assignment.append((j, t))
                    count += 1
                    total += c
            key = (count, -total)
            if key > best_key:
                best_key = key
                best = assignment

    return [(t.tech_id, j.job_id) for j, t in best]
