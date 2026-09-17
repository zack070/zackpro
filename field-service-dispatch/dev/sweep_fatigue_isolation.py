"""Isolate fatigue-awareness's marginal contribution, net of urgency-ordering,
on the fatigue-dominant (skill-homogeneous) scenario. Compares:
  urgent_edf_policy         (urgent-first, EDF, first eligible free tech)
  urgent_edf_rested_policy  (urgent-first, EDF, prefer least-fatigued eligible tech)
Both ignore scarcity (moot here, single shared skill). Any gap between them
is fatigue-awareness's isolated effect."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import simulator as sim
from gen_scenario import load_scenario
from gen_fatigue_scenario import gen as gen_fatigue
from run_policy import load_policy

N_TECHS = 4
N_JOBS = 48

edf = load_policy(os.path.join(os.path.dirname(__file__), "urgent_edf_policy.py"))
rested = load_policy(os.path.join(os.path.dirname(__file__), "urgent_edf_rested_policy.py"))
smart = load_policy(os.path.join(os.path.dirname(__file__), "smart_policy.py"))


def run(seed):
    with tempfile.TemporaryDirectory() as d:
        gen_fatigue(seed, d, n_techs=N_TECHS, n_jobs=N_JOBS)
        techs, jobs, shift_length = load_scenario(d)
        r_edf = sim.run_simulation(techs, jobs, shift_length, edf)
        r_rested = sim.run_simulation(techs, jobs, shift_length, rested)
        r_smart = sim.run_simulation(techs, jobs, shift_length, smart)
        return r_edf.total_cost, r_rested.total_cost, r_smart.total_cost


if __name__ == "__main__":
    seeds = range(1, 61)
    print(f"{'seed':>5} {'edf':>10} {'rested':>10} {'smart':>10} {'gap(edf-rested)':>16}")
    gaps = []
    for s in seeds:
        c_edf, c_rested, c_smart = run(s)
        gap = c_edf - c_rested
        gaps.append(gap)
        print(f"{s:>5} {c_edf:>10.1f} {c_rested:>10.1f} {c_smart:>10.1f} {gap:>16.1f}")
    print()
    print(f"mean gap={sum(gaps)/len(gaps):.1f}  max gap={max(gaps):.1f}  min gap={min(gaps):.1f}")
    print(f"seeds with rested strictly better: {sum(1 for g in gaps if g > 0)}/{len(gaps)}")
