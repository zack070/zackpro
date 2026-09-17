"""Generate a scarcity-neutral, high-sustained-load scenario where fatigue
is the intended bottleneck: all technicians share the same skill (so a
scarcity/skill-reservation heuristic has nothing to work with), but total
workload is high enough that greedily keeping whichever technician is
currently free continuously busy triggers repeated fatigue penalties,
while a policy that deliberately rests technicians avoids them."""
import csv
import json
import os
import random


def gen(seed, out_dir, n_techs=4, n_jobs=48, shift_length=480):
    rng = random.Random(seed)
    techs = []
    for i in range(n_techs):
        techs.append({
            "tech_id": f"T{i+1}",
            "skills": ["general"],
            "shift_end": shift_length,
            "max_overtime": rng.choice([30, 60]),
        })

    jobs = []
    rng_jobs = random.Random(seed * 7919 + 13)
    for i in range(n_jobs):
        duration = rng_jobs.choice([40, 50, 60, 70])
        dynamic = rng_jobs.random() < 0.25
        arrival = rng_jobs.randint(30, 300) if dynamic else 0
        urgent = rng_jobs.random() < 0.2
        slack = rng_jobs.randint(60, 150) if urgent else rng_jobs.randint(150, 380)
        deadline = min(shift_length, arrival + duration + slack)
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
    n_techs = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    n_jobs = int(sys.argv[4]) if len(sys.argv) > 4 else 34
    gen(seed, out_dir, n_techs, n_jobs)
    print(f"wrote fatigue scenario seed={seed} to {out_dir}")
