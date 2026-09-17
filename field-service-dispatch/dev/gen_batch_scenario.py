"""Batch-arrival scenario: jobs and technician availability cluster so that
several jobs and several free technicians are routinely pending at once,
with heterogeneous skills and per-pairing cost (via fatigue/overtime), so
the per-decision assignment is a genuine weighted bipartite matching
problem -- greedy one-job-at-a-time assignment (in any fixed priority
order, with any fixed tie-break) is not guaranteed to find the min-cost
matching for the batch, only true joint optimization is."""
import csv
import json
import os
import random

SKILLS = ["A", "B", "C", "general"]


def gen(seed, out_dir, n_techs=5, n_batches=6, jobs_per_batch=(4, 6), batch_gap=70, shift_length=420):
    rng = random.Random(seed)
    techs = []
    for i in range(n_techs):
        skills = {"general"}
        specialty_count = rng.choice([1, 1, 2])
        specialties = rng.sample(["A", "B", "C"], k=specialty_count)
        skills.update(specialties)
        techs.append({
            "tech_id": f"T{i+1}", "skills": sorted(skills),
            "shift_end": shift_length, "max_overtime": 90,
        })
    # guarantee each specialty has at least 2 qualified techs (avoid trivial monopoly)
    for sk in ["A", "B", "C"]:
        qualified = [t for t in techs if sk in t["skills"]]
        if len(qualified) < 2:
            for t in techs:
                if sk not in t["skills"]:
                    t["skills"] = sorted(set(t["skills"]) | {sk})
                    break

    rng_jobs = random.Random(seed * 7919 + 13)
    jobs = []
    jid = 1
    for b in range(n_batches):
        batch_time = b * batch_gap
        n_this_batch = rng_jobs.randint(*jobs_per_batch)
        for _ in range(n_this_batch):
            skill = rng_jobs.choices(SKILLS, weights=[3, 3, 3, 2])[0]
            duration = rng_jobs.choice([30, 40, 50, 60])
            urgent = rng_jobs.random() < 0.2
            slack = rng_jobs.randint(40, 100) if urgent else rng_jobs.randint(100, 260)
            deadline = min(shift_length + 60, batch_time + duration + slack)
            jobs.append({
                "job_id": f"J{jid}", "required_skill": skill, "base_duration": duration,
                "priority": "urgent" if urgent else "standard",
                "deadline": deadline, "arrival_time": batch_time,
            })
            jid += 1

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "technicians.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tech_id", "skills", "shift_end", "max_overtime"])
        for t in techs:
            w.writerow([t["tech_id"], ";".join(t["skills"]), t["shift_end"], t["max_overtime"]])
    with open(os.path.join(out_dir, "jobs.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["job_id", "required_skill", "base_duration", "priority", "deadline", "arrival_time"])
        for j in jobs:
            w.writerow([j["job_id"], j["required_skill"], j["base_duration"], j["priority"], j["deadline"], j["arrival_time"]])
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump({"shift_length": shift_length}, f, indent=2)
    return techs, jobs


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1])
    out_dir = sys.argv[2]
    gen(seed, out_dir)
    print(f"wrote batch scenario seed={seed} to {out_dir}")
