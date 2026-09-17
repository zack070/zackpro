#!/usr/bin/env python3
"""
Advance the horizon past period 4 using your own submitted baseline plan.

This is the only way to learn two things: (1) the actual end-of-period-4
state (inventory, cash, and any commitments still working their way through
the pipeline) that results from YOUR baseline decisions, and (2) whether,
and how, a supply disruption affects periods 5-8 -- neither is
knowable in advance from the static data alone, because the real
end-of-period-4 state depends on which of possibly several feasible
baselines you chose to submit.

Only the periods-1-4 portion of the baseline plan is used: those are the
only orders that have actually been placed as of "now." Anything your
baseline plan proposed for periods 5-8 is a forecast that was never
executed and is superseded entirely by whatever replan you build from the
state this script reports.

If your baseline's periods 1-4 are not feasible on their own, this refuses
to advance -- fix that first (see check_plan.py --stage baseline).

Usage:
    python3 advance_horizon.py --data /app/data --baseline /app/outputs/baseline_plan.csv --out /app/outputs/period4_state.json
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
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = eng.load_static_data(args.data)
    all_orders = eng.load_orders_csv(args.baseline)
    orders_1_4 = [o for o in all_orders if o.period <= 4]
    dropped = [o for o in all_orders if o.period > 4]

    res = eng.replay(data, orders_1_4, period_start=1, period_end=4, apply_disruption=False)
    if not res.ok:
        print("Cannot advance: periods 1-4 of your baseline are not feasible.", file=sys.stderr)
        print("Run check_plan.py --stage baseline first and resolve every violation:", file=sys.stderr)
        for v in res.violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)

    if dropped:
        print(f"Note: {len(dropped)} order(s) in periods 5-8 of your baseline were forecasts only "
              f"and are being discarded now that you are replanning from period 5.", file=sys.stderr)

    state = eng.snapshot_state(res, 4, data, orders_1_4)

    out = {
        "ending_inventory": state["ending_inventory"],
        "cash_end": state["cash_end"],
        "carried_payments": {str(k): v for k, v in state["carried_payments"].items()},
        "pipeline_arrivals": {f"{p}|{t}": q for (p, t), q in state["pipeline_arrivals"].items()},
        "disruption": {
            "supplier_id": eng.DISRUPTED_SUPPLIER,
            "periods": sorted(eng.DISRUPTED_PERIODS),
            "effect": (
                "No new order may be placed with this supplier in these periods; "
                "its capacity for new orders in these periods is zero. Any existing "
                "binding purchase order with this supplier is unaffected and arrives "
                "and is paid for exactly as scheduled."
            ),
        },
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)

    print(f"Wrote real end-of-period-4 state and disruption details to {args.out}")
    print(f"  cash_end (period 4) = {state['cash_end']:.2f}")
    print(f"  ending_inventory (period 4) = {state['ending_inventory']}")
    print(f"  disruption: {out['disruption']['supplier_id']} unavailable for new orders in periods {out['disruption']['periods']}")


if __name__ == "__main__":
    main()
