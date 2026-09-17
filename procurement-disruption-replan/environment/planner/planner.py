"""
Procurement planner (period-by-period greedy replenishment).

Legacy tool inherited from the previous supply-chain analyst. It has been
used for a few planning cycles. Reads environment data and existing
commitments, walks the horizon period by period, and orders enough from
the cheapest eligible supplier to cover projected shortfalls, respecting
minimum order quantities, available capacity, and cash.

Usage:
    python3 planner.py --data DATA_DIR --out OUT_CSV [--periods START END]
"""
import argparse
import csv
import json
import os


def load_data(data_dir):
    def read_csv(name):
        with open(os.path.join(data_dir, name), newline="") as f:
            return list(csv.DictReader(f))

    products = [r["product_id"] for r in read_csv("products.csv")]
    holding_cost = {r["product_id"]: float(r["holding_cost_per_unit_per_period"]) for r in read_csv("products.csv")}

    supplier_products = {}
    for r in read_csv("supplier_products.csv"):
        supplier_products[(r["supplier_id"], r["product_id"])] = {
            "unit_price": float(r["unit_price"]),
            "lead_time": int(r["lead_time_periods"]),
            "moq": int(r["moq"]),
            "payment_term": int(r["payment_term_periods"]),
        }

    supplier_capacity = {}
    for r in read_csv("supplier_capacity.csv"):
        supplier_capacity[(r["supplier_id"], int(r["period"]))] = float(r["capacity_units"])

    demand = {}
    for r in read_csv("demand.csv"):
        demand[(r["product_id"], int(r["period"]))] = float(r["demand_units"])

    initial_inventory = {r["product_id"]: float(r["quantity"]) for r in read_csv("initial_inventory.csv")}

    existing_pos = []
    for r in read_csv("existing_purchase_orders.csv"):
        existing_pos.append({
            "supplier_id": r["supplier_id"],
            "product_id": r["product_id"],
            "quantity": float(r["quantity"]),
            "order_period": int(r["order_period"]),
            "arrival_period": int(r["arrival_period"]),
            "unit_price": float(r["unit_price"]),
            "payment_due_period": int(r["payment_due_period"]),
        })

    with open(os.path.join(data_dir, "cash.json")) as f:
        cash_data = json.load(f)

    return {
        "products": products,
        "holding_cost": holding_cost,
        "supplier_products": supplier_products,
        "supplier_capacity": supplier_capacity,
        "demand": demand,
        "initial_inventory": initial_inventory,
        "existing_pos": existing_pos,
        "initial_cash": float(cash_data["initial_cash"]),
        "other_cash_outflows": {int(k): float(v) for k, v in cash_data.get("other_cash_outflows", {}).items()},
    }


def plan(data, period_start, period_end):
    """Greedy period-by-period replenishment. Walks periods in order; for
    each product, tops up on-hand stock from the cheapest eligible supplier
    with remaining capacity and cash, respecting each pair's MOQ."""
    orders = []
    on_hand = dict(data["initial_inventory"])
    cash = data["initial_cash"]
    capacity_used = {}  # (supplier, period) -> qty, planner's own orders only

    eligible = {}
    for (s, p), sp in data["supplier_products"].items():
        eligible.setdefault(p, []).append((s, sp["unit_price"], sp))

    for t in range(period_start, period_end + 1):
        # existing commitments arrive and are paid for on their stated periods
        for po in data["existing_pos"]:
            if po["arrival_period"] == t:
                on_hand[po["product_id"]] = on_hand.get(po["product_id"], 0.0) + po["quantity"]
            if po["arrival_period"] == t:
                cash -= po["quantity"] * po["unit_price"]
        cash -= data["other_cash_outflows"].get(t, 0.0)

        for p in data["products"]:
            demand_t = data["demand"].get((p, t), 0.0)
            shortfall = demand_t - on_hand.get(p, 0.0)
            if shortfall <= 0:
                on_hand[p] = max(0.0, on_hand.get(p, 0.0) - demand_t)
                continue

            options = sorted(eligible.get(p, []), key=lambda o: o[1])
            for supplier_id, price, sp in options:
                cap_used = capacity_used.get((supplier_id, t), 0.0)
                cap_avail = data["supplier_capacity"].get((supplier_id, t), 0.0) - cap_used
                if cap_avail <= 0:
                    continue
                qty = max(shortfall, sp["moq"])
                qty = min(qty, cap_avail)
                if qty < sp["moq"]:
                    continue
                cost = qty * price
                if cost > cash:
                    continue

                orders.append({"period": t, "supplier_id": supplier_id, "product_id": p, "quantity": qty})
                capacity_used[(supplier_id, t)] = cap_used + qty
                on_hand[p] = on_hand.get(p, 0.0) + qty
                cash -= cost
                shortfall -= qty
                if shortfall <= 0:
                    break

            on_hand[p] = max(0.0, on_hand.get(p, 0.0) - demand_t)

    return orders


def write_orders(path, orders):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["period", "supplier_id", "product_id", "quantity"])
        for o in orders:
            if o["quantity"] <= 0:
                continue
            w.writerow([o["period"], o["supplier_id"], o["product_id"], int(round(o["quantity"]))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/app/data")
    ap.add_argument("--out", default="/app/reports/current_plan.csv")
    ap.add_argument("--periods", nargs=2, type=int, default=[1, 8])
    args = ap.parse_args()

    data = load_data(args.data)
    orders = plan(data, args.periods[0], args.periods[1])
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    write_orders(args.out, orders)
    print(f"Wrote {len(orders)} orders to {args.out}")


if __name__ == "__main__":
    main()
