#!/usr/bin/env python3
"""
Validate a candidate plan against the operational contract (see
../README.md). This performs the same feasibility checks the grading
verifier performs -- it does not compute or reveal any cost threshold or
optimum, only whether the plan is feasible and what it would cost.

Usage:
  Baseline (periods 1-8, no disruption -- this plan predates it):
    python3 check_plan.py --data /app/data --plan /app/outputs/baseline_plan.csv --stage baseline

  Replan (periods 5-8, disrupted world, anchored to a real state):
    python3 check_plan.py --data /app/data --plan /app/outputs/replan.csv --stage replan --state /app/outputs/period4_state.json
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import engine_v1 as eng


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--stage", required=True, choices=["baseline", "replan"])
    ap.add_argument("--state", help="period4_state.json produced by advance_horizon.py; required for --stage replan")
    args = ap.parse_args()

    data = eng.load_static_data(args.data)
    orders = eng.load_orders_csv(args.plan)

    if args.stage == "baseline":
        res = eng.replay(data, orders, period_start=1, period_end=8, apply_disruption=False)
        cost = eng.total_cost(data, orders, res, 1, 8) if res.ok else None
    else:
        if not args.state:
            print("ERROR: --state is required for --stage replan (run advance_horizon.py first)", file=sys.stderr)
            sys.exit(2)
        with open(args.state) as f:
            state = json.load(f)
        state["pipeline_arrivals"] = {
            (k.split("|")[0], int(k.split("|")[1])): v
            for k, v in state.get("pipeline_arrivals", {}).items()
        }
        state["carried_payments"] = {int(k): v for k, v in state.get("carried_payments", {}).items()}
        res = eng.replay(data, orders, period_start=5, period_end=8, initial_state=state, apply_disruption=True)
        cost = eng.total_cost(data, orders, res, 5, 8) if res.ok else None

    if res.ok:
        print(f"FEASIBLE. {args.stage} cost = {cost:.2f}")
        sys.exit(0)
    else:
        print(f"INFEASIBLE ({len(res.violations)} violation(s)):")
        for v in res.violations:
            print(f"  - {v}")
        sys.exit(1)


if __name__ == "__main__":
    main()
