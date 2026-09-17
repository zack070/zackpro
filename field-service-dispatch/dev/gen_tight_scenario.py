"""Tight-knapsack fatigue scenario: single shared skill (scarcity-neutral),
total technician capacity (shift + overtime) sized to have only small slack
over total job-minutes, so any capacity wasted by fatigue-multiplier
inflation (or by picking an infeasible technician) has nowhere to hide and
directly produces breaches."""
import csv
import json
import os
import random


def gen(seed, out_dir, n_techs=3, n_jobs=None, shift_length=300, slack_frac=0.12):
    rng = random.Random(seed)
    rng_jobs = random.Random(seed * 7919 + 13)

    durations_pool = [40, 50, 60]
    total_tech_capacity = 0
    techs = []
    for i in range(n_techs):
        max_overtime = rng.choice([20, 30, 40])
        techs.append({"tech_id": f"T{i+1}", "skills": ["general"], "shift_end": shift_length, "max_overtime": max_overtime})
        total_tech_capacity += shift_length + max_overtime

    target_job_minutes = int(total_tech_capacity / (1 + slack_frac))

    jobs = []
    total = 0
    i = 0
    while total < target_job_minutes:
        duration = rng_jobs.choice(durations_pool)
        urgent = rng_jobs.random() < 0.2
        arrival = rng_jobs.randint(0, shift_length // 2) if rng_jobs.random() < 0.3 else 0
        slack = rng_jobs.randint(40, 100) if urgent else rng_jobs.randint(100, 300)
        deadline = min(shift_length + 60, arrival + duration + slack)
        jobs.append({
            "job_id": f"J{i+1}", "required_skill": "general", "base_duration": duration,
            "priority": "urgent" if urgent else "standard",
            "deadline": deadline, "arrival_time": arrival,
        })
        total += duration
        i += 1

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
    print(f"wrote tight scenario seed={seed} to {out_dir}")
