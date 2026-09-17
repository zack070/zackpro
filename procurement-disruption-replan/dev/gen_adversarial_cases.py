"""Generate adversarial candidate submissions from the oracle's valid output,
each with one targeted mutation, for the verifier to reject. Every case's
directory name states what it tests and the expected reward (always 0
here; the "sanity_valid" case is the sole reward=1 control)."""
import csv
import os
import shutil

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "out")
DEST_ROOT = os.path.join(BASE, "adversarial")


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path, rows, fieldnames=("period", "supplier_id", "product_id", "quantity")):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def make_case(name, baseline_rows, replan_rows, baseline_raw=None, replan_raw=None):
    d = os.path.join(DEST_ROOT, name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    if baseline_raw is not None:
        with open(os.path.join(d, "baseline_plan.csv"), "w") as f:
            f.write(baseline_raw)
    else:
        write_rows(os.path.join(d, "baseline_plan.csv"), baseline_rows)
    if replan_raw is not None:
        with open(os.path.join(d, "replan.csv"), "w") as f:
            f.write(replan_raw)
    else:
        write_rows(os.path.join(d, "replan.csv"), replan_rows)


def main():
    baseline = read_rows(os.path.join(OUT_DIR, "baseline_plan.csv"))
    replan = read_rows(os.path.join(OUT_DIR, "replan.csv"))

    # 1. sanity control: byte-identical to the oracle's own valid output -> reward 1
    make_case("sanity_valid_reward1", baseline, replan)

    # 2. duplicate row in baseline
    dup = list(baseline) + [dict(baseline[0])]
    make_case("duplicate_row", dup, replan)

    # 3. negative quantity
    neg = [dict(r) for r in baseline]
    neg[0]["quantity"] = str(-int(neg[0]["quantity"]) or -1)
    make_case("negative_quantity", neg, replan)

    # 4. non-integer quantity
    frac = [dict(r) for r in baseline]
    frac[0]["quantity"] = "12.5"
    make_case("non_integer_quantity", frac, replan)

    # 5. zero quantity row (should just be a violation, not silently accepted)
    zero = [dict(r) for r in baseline]
    zero[0]["quantity"] = "0"
    make_case("zero_quantity", zero, replan)

    # 6. order from disrupted supplier S2 in the replan window (periods 5-6)
    s2_disrupted = list(replan) + [{"period": "5", "supplier_id": "S2", "product_id": "P5", "quantity": "60"}]
    make_case("order_from_disrupted_supplier", baseline, s2_disrupted)

    # 7. replan tries to rewrite history (a period-3 row sneaked into replan.csv)
    rewrite_history = list(replan) + [{"period": "3", "supplier_id": "S1", "product_id": "P1", "quantity": "100"}]
    make_case("replan_rewrites_history", baseline, rewrite_history)

    # 8. ineligible supplier/product pair (S2 does not sell P1)
    ineligible = list(baseline) + [{"period": "2", "supplier_id": "S2", "product_id": "P1", "quantity": "60"}]
    make_case("ineligible_pair", ineligible, replan)

    # 9. below MOQ (S4 MOQ=150 for P6; order 10)
    below_moq = list(baseline) + [{"period": "2", "supplier_id": "S4", "product_id": "P6", "quantity": "10"}]
    make_case("below_moq", below_moq, replan)

    # 10. supplier capacity blown in a single period (S3 capacity 300/period; dump 1000 there)
    cap_blown = list(baseline) + [{"period": "2", "supplier_id": "S3", "product_id": "P3", "quantity": "1000"}]
    make_case("capacity_exceeded", cap_blown, replan)

    # 11. warehouse capacity blown (order a huge amount of everything in period 1)
    wh_blown = list(baseline) + [{"period": "1", "supplier_id": "S3", "product_id": "P6", "quantity": "2000"}]
    make_case("warehouse_capacity_exceeded", wh_blown, replan)

    # 12. malformed CSV (missing required column)
    make_case("malformed_missing_column", None, replan, baseline_raw="period,supplier_id,quantity\n1,S1,100\n")

    # 13. empty baseline (header only)
    make_case("empty_baseline", None, replan, baseline_raw="period,supplier_id,product_id,quantity\n")

    # 14. order after the planning horizon (period 9)
    after_horizon = list(baseline) + [{"period": "9", "supplier_id": "S1", "product_id": "P1", "quantity": "100"}]
    make_case("order_after_horizon", after_horizon, replan)

    # 15. right total quantity, wrong timing (shift all baseline orders 3 periods later)
    shifted = []
    for r in baseline:
        r2 = dict(r)
        p = int(r2["period"]) + 3
        r2["period"] = str(min(p, 8))
        shifted.append(r2)
    make_case("wrong_timing_shifted", shifted, replan)

    # 16. huge garbage file (resource exhaustion attempt)
    garbage_rows = [{"period": "1", "supplier_id": "S1", "product_id": "P1", "quantity": "100"} for _ in range(50_000)]
    make_case("huge_garbage_file", garbage_rows, replan)

    print("Generated adversarial cases in", DEST_ROOT)
    for name in sorted(os.listdir(DEST_ROOT)):
        print(" -", name)


if __name__ == "__main__":
    main()
