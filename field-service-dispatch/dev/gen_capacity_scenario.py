"""Scarcity-neutral scenario (single shared skill) where technicians have
heterogeneous shift_end/max_overtime windows -- some techs have very little
runway past their nominal shift, others have generous overtime capacity.
Tests whether a policy must reserve low-capacity technicians' remaining
window for jobs that need it, rather than spending it on routine work a
high-capacity technician could equally do."""
import csv
import json
import os
import random


def gen(seed, out_dir, n_techs=4, n_jobs=48, shift_length=420):
    rng = random.Random(seed)
    techs = []
    # half the techs have a tight window (short shift + small overtime cap),
    # half have a long window (full shift + generous overtime cap)
    for i in range(n_techs):
        tight = i % 2 == 0
        if tight:
            shift_end = rng.choice([300, 330, 360])
            max_overtime = rng.choice([15, 30])
        else:
            shift_end = shift_length
            max_overtime = rng.choice([90, 120])
        techs.append({
            "tech_id": f"T{i+1}", "skills": ["general"],
            "shift_end": shift_end, "max_overtime": max_overtime,
        })

    jobs = []
    rng_jobs = random.Random(seed * 7919 + 13)
    for i in range(n_jobs):
        duration = rng_jobs.choice([30, 40, 50, 60])
        dynamic = rng_jobs.random() < 0.4
        arrival = rng_jobs.randint(0, shift_length) if dynamic else rng_jobs.randint(0, 100)
        urgent = rng_jobs.random() < 0.2
        slack = rng_jobs.randint(60, 150) if urgent else rng_jobs.randint(150, 380)
        deadline = min(shift_length + 120, arrival + duration + slack)
        jobs.append({
            "job_id": f"J{i+1}", "required_skill": "general", "base_duration": duration,
            "priority": "urgent" if urgent else "standard",
            "deadline": deadline, "arrival_time": arrival,
        })

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
    print(f"wrote capacity scenario seed={seed} to {out_dir}")
