"""Search for scenario parameters (n_techs, n_jobs, duration mix) that
produce a large, robust, consistently-positive gap between fatigue-blind
and fatigue-aware policies (urgent_edf vs urgent_edf_rested), so fatigue
awareness is a real, dominant bottleneck rather than occasional noise."""
import os
import sys
import tempfile
import random
import csv
import json

sys.path.insert(0, os.path.dirname(__file__))
import simulator as sim
from gen_scenario import load_scenario
from run_policy import load_policy

edf = load_policy(os.path.join(os.path.dirname(__file__), "urgent_edf_policy.py"))
rested = load_policy(os.path.join(os.path.dirname(__file__), "urgent_edf_rested_policy.py"))
smart = load_policy(os.path.join(os.path.dirname(__file__), "smart_policy.py"))


def gen_custom(seed, out_dir, n_techs, n_jobs, shift_length, durations, arrival_max, urgent_frac):
    rng = random.Random(seed)
    techs = []
    for i in range(n_techs):
        techs.append({
            "tech_id": f"T{i+1}", "skills": ["general"],
            "shift_end": shift_length, "max_overtime": rng.choice([30, 60]),
        })
    jobs = []
    rng_jobs = random.Random(seed * 7919 + 13)
    for i in range(n_jobs):
        duration = rng_jobs.choice(durations)
        dynamic = rng_jobs.random() < 0.25
        arrival = rng_jobs.randint(0, arrival_max) if dynamic else 0
        urgent = rng_jobs.random() < urgent_frac
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


def eval_config(n_techs, n_jobs, shift_length, durations, arrival_max, urgent_frac, seeds):
    gaps = []
    for s in seeds:
        with tempfile.TemporaryDirectory() as d:
            gen_custom(s, d, n_techs, n_jobs, shift_length, durations, arrival_max, urgent_frac)
            techs, jobs, sl = load_scenario(d)
            c_edf = sim.run_simulation(techs, jobs, sl, edf).total_cost
            c_rested = sim.run_simulation(techs, jobs, sl, rested).total_cost
            gaps.append(c_edf - c_rested)
    return gaps


if __name__ == "__main__":
    configs = [
        ("baseline(4t,48j,40-70dur,300arr)", 4, 48, 480, [40, 50, 60, 70], 300, 0.2),
        ("3techs,60dur_fixed", 3, 40, 480, [60], 300, 0.2),
        ("3techs,tight90dur", 3, 30, 480, [90], 300, 0.15),
        ("2techs,60dur", 2, 24, 480, [60], 200, 0.15),
        ("3techs,48j,40-70dur,less_dynamic", 3, 48, 480, [40, 50, 60, 70], 150, 0.2),
        ("3techs,60j,60dur,tight_arrival", 3, 60, 480, [60], 100, 0.2),
        ("4techs,60j,60dur", 4, 60, 480, [60], 300, 0.2),
        ("3techs,50j,70dur", 3, 50, 480, [70], 300, 0.2),
    ]
    seeds = range(1, 41)
    for name, nt, nj, sl, durs, am, uf in configs:
        gaps = eval_config(nt, nj, sl, durs, am, uf, seeds)
        mean_g = sum(gaps) / len(gaps)
        pos = sum(1 for g in gaps if g > 0)
        neg = sum(1 for g in gaps if g < 0)
        print(f"{name:45s} mean={mean_g:8.1f} min={min(gaps):8.1f} max={max(gaps):8.1f} pos={pos}/{len(gaps)} neg={neg}")
