"""Generate a deterministic field-service dispatch scenario (technicians +
jobs) from a random seed. Used to produce agent-visible sample scenarios
and the sealed held-out grading scenario -- same generator, different
seeds, so scenarios are comparable in character but not identical."""
import csv
import json
import os
import random

SKILLS = ["hvac", "electrical", "plumbing", "general"]
SHIFT_LENGTH = 480


def gen_technicians(rng, n=6):
    techs = []
    # deliberate scarcity: electrical only ever has 1-2 qualified techs
    skill_pool = []
    skill_pool += ["general"] * n  # everyone can do general work
    skill_pool += rng.sample(["hvac", "hvac", "plumbing", "plumbing", "electrical"], k=min(5, n))
    for i in range(n):
        tid = f"T{i+1}"
        skills = {"general"}
        # assign 0-2 additional specialty skills per tech, electrical rare
        if rng.random() < 0.35:
            skills.add(rng.choice(["hvac", "plumbing"]))
        if i < 2 and rng.random() < 0.5:
            skills.add("electrical")
        shift_end = SHIFT_LENGTH if rng.random() < 0.8 else rng.choice([360, 420])
        max_overtime = rng.choice([30, 60, 60, 90])
        techs.append({"tech_id": tid, "skills": sorted(skills), "shift_end": shift_end, "max_overtime": max_overtime})
    # guarantee at least one electrical-capable tech
    if not any("electrical" in t["skills"] for t in techs):
        techs[0]["skills"] = sorted(set(techs[0]["skills"]) | {"electrical"})
    return techs


def gen_jobs(rng, n=22):
    jobs = []
    for i in range(n):
        jid = f"J{i+1}"
        skill = rng.choices(SKILLS, weights=[3, 1, 2, 4])[0]
        duration = rng.choice([30, 45, 60, 75, 90])
        dynamic = rng.random() < 0.3
        arrival = rng.randint(60, 360) if dynamic else 0
        urgent = rng.random() < 0.18
        if urgent:
            slack = rng.randint(60, 180)
        else:
            slack = rng.randint(180, 420)
        deadline = min(SHIFT_LENGTH, arrival + duration + slack)
        jobs.append({
            "job_id": jid, "required_skill": skill, "base_duration": duration,
            "priority": "urgent" if urgent else "standard",
            "deadline": deadline, "arrival_time": arrival,
        })
    return jobs


def write_scenario(out_dir, techs, jobs, shift_length=SHIFT_LENGTH):
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


def load_scenario(data_dir):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    import simulator as sim

    def read_csv(name):
        with open(os.path.join(data_dir, name), newline="") as f:
            return list(csv.DictReader(f))

    techs = [
        sim.TechnicianSpec(
            tech_id=r["tech_id"], skills=frozenset(r["skills"].split(";")),
            shift_end=int(r["shift_end"]), max_overtime=int(r["max_overtime"]),
        )
        for r in read_csv("technicians.csv")
    ]
    jobs = [
        sim.JobSpec(
            job_id=r["job_id"], required_skill=r["required_skill"], base_duration=int(r["base_duration"]),
            priority=r["priority"], deadline=int(r["deadline"]), arrival_time=int(r["arrival_time"]),
        )
        for r in read_csv("jobs.csv")
    ]
    with open(os.path.join(data_dir, "config.json")) as f:
        cfg = json.load(f)
    return techs, jobs, cfg["shift_length"]


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1])
    out_dir = sys.argv[2]
    n_techs = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    n_jobs = int(sys.argv[4]) if len(sys.argv) > 4 else 22
    rng = random.Random(seed)
    techs = gen_technicians(rng, n_techs)
    rng_jobs = random.Random(seed * 7919 + 13)
    jobs = gen_jobs(rng_jobs, n_jobs)
    write_scenario(out_dir, techs, jobs)
    print(f"wrote scenario seed={seed} to {out_dir}: {len(techs)} techs, {len(jobs)} jobs")
