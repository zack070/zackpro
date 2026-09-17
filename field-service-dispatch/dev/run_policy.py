import importlib.util
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import simulator as sim
from gen_scenario import load_scenario


def load_policy(path):
    spec = importlib.util.spec_from_file_location("candidate_policy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.decide


def main():
    scenario_dir = sys.argv[1]
    policy_path = sys.argv[2]
    techs, jobs, shift_length = load_scenario(scenario_dir)
    decide = load_policy(policy_path)
    result = sim.run_simulation(techs, jobs, shift_length, decide)
    print(f"scenario={scenario_dir} policy={policy_path}")
    print(f"  total_cost={result.total_cost:.1f}")
    print(f"  num_breaches={result.num_breaches}  followups={result.num_followups_spawned}  overtime_min={result.overtime_minutes_total}")
    print(f"  completed={result.completed_jobs}/{result.total_jobs}")


if __name__ == "__main__":
    main()
