"""
Reference MILP oracle. Solves Stage A (periods 1-8, disruption-blind,
minimum cost, 100% service) and, from the REAL replayed end-of-period-4
state, Stage B (periods 5-8, S2 disrupted in periods 5-6, minimum cost,
100% service, all pre-period-5 commitments binding).

This is deliberately independent of engine_v1's internal machinery for the
optimization itself (it builds its own constraint matrix from StaticData),
but uses engine_v1.replay() to confirm its own output is feasible before
declaring victory -- a legitimate reference-solution self-check, not
"trusting the agent."
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import pulp
import engine_v1 as eng


def eligible_pairs(data: eng.StaticData):
    return list(data.supplier_products.keys())


def existing_capacity_used(data: eng.StaticData):
    used = {}
    for po in data.existing_pos:
        key = (po["supplier_id"], po["order_period"])
        used[key] = used.get(key, 0.0) + po["quantity"]
    return used


def existing_arrivals(data: eng.StaticData):
    arr = {}
    for po in data.existing_pos:
        if 1 <= po["arrival_period"] <= eng.NUM_PERIODS:
            key = (po["product_id"], po["arrival_period"])
            arr[key] = arr.get(key, 0.0) + po["quantity"]
    return arr


def existing_payments(data: eng.StaticData):
    pay = {}
    for po in data.existing_pos:
        if 1 <= po["payment_due_period"] <= eng.NUM_PERIODS:
            pay[po["payment_due_period"]] = pay.get(po["payment_due_period"], 0.0) + po["quantity"] * po["unit_price"]
    return pay


def solve_stage(
    data: eng.StaticData,
    periods,
    beginning_inventory,
    cash_begin,
    carried_payments,
    disrupted,
    name,
    pipeline_arrivals=None,
):
    pipeline_arrivals = pipeline_arrivals or {}
    prob = pulp.LpProblem(name, pulp.LpMinimize)
    pairs = eligible_pairs(data)

    x = {}
    y = {}
    for (s, p) in pairs:
        for t in periods:
            if eng.is_disrupted(s, t, disrupted):
                continue
            x[(s, p, t)] = pulp.LpVariable(f"x_{s}_{p}_{t}", lowBound=0, cat="Integer")
            y[(s, p, t)] = pulp.LpVariable(f"y_{s}_{p}_{t}", cat="Binary")

    exist_cap = existing_capacity_used(data)
    exist_arr = existing_arrivals(data)
    exist_pay = existing_payments(data)

    # MOQ / big-M linkage
    for (s, p, t), var in x.items():
        sp = data.supplier_products[(s, p)]
        cap_t = data.supplier_capacity.get((s, t), 0.0) - exist_cap.get((s, t), 0.0)
        big_m = max(0.0, cap_t)
        prob += var <= big_m * y[(s, p, t)]
        prob += var >= sp["moq"] * y[(s, p, t)]

    # capacity per supplier per period
    suppliers_in_play = sorted({s for (s, p) in pairs})
    for s in suppliers_in_play:
        for t in periods:
            terms = [x[(s, p, t)] for p in data.products if (s, p, t) in x]
            if not terms:
                continue
            cap_t = data.supplier_capacity.get((s, t), 0.0) - exist_cap.get((s, t), 0.0)
            prob += pulp.lpSum(terms) <= cap_t

    # inventory balance
    ending = {}
    prev = dict(beginning_inventory)
    for t in periods:
        for p in data.products:
            arrivals_terms = [exist_arr.get((p, t), 0.0), pipeline_arrivals.get((p, t), 0.0)]
            for (s, pp) in pairs:
                if pp != p:
                    continue
                lt = data.supplier_products[(s, pp)]["lead_time"]
                src_t = t - lt
                if src_t in periods and (s, pp, src_t) in x:
                    arrivals_terms.append(x[(s, pp, src_t)])
            dem = data.demand.get((p, t), 0.0)
            end_var = pulp.LpVariable(f"end_{p}_{t}", lowBound=0)
            prob += end_var == prev[p] + pulp.lpSum(arrivals_terms) - dem
            ending[(p, t)] = end_var
            prev[p] = end_var

    # warehouse capacity
    for t in periods:
        prob += pulp.lpSum(ending[(p, t)] for p in data.products) <= data.warehouse_capacity

    # cash
    cash = {}
    prev_cash = cash_begin
    for t in periods:
        pay_terms = [exist_pay.get(t, 0.0), carried_payments.get(t, 0.0)]
        for (s, p) in pairs:
            pt = data.supplier_products[(s, p)]["payment_term"]
            src_t = t - pt
            if src_t in periods and (s, p, src_t) in x:
                pay_terms.append(x[(s, p, src_t)] * data.supplier_products[(s, p)]["unit_price"])
        cash_var = pulp.LpVariable(f"cash_{t}", lowBound=0)
        other = data.other_cash_outflows.get(t, 0.0)
        prob += cash_var == prev_cash - pulp.lpSum(pay_terms) - other
        cash[t] = cash_var
        prev_cash = cash_var

    # objective
    purchase = pulp.lpSum(var * data.supplier_products[(s, p)]["unit_price"] for (s, p, t), var in x.items())
    holding = pulp.lpSum(ending[(p, t)] * data.holding_cost[p] for p in data.products for t in periods)
    prob += purchase + holding

    solver = pulp.PULP_CBC_CMD(msg=0)
    status = prob.solve(solver)
    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"{name}: solver status {pulp.LpStatus[status]}")

    orders = []
    for (s, p, t), var in x.items():
        q = var.value()
        if q is not None and q > 0.5:
            orders.append(eng.NewOrder(period=t, supplier_id=s, product_id=p, quantity=round(q)))

    return orders, pulp.value(prob.objective)


def build_stage_a(data: eng.StaticData):
    periods = list(range(1, 9))
    return solve_stage(
        data, periods,
        beginning_inventory=dict(data.initial_inventory),
        cash_begin=data.initial_cash,
        carried_payments={},
        disrupted=False,
        name="StageA",
    )


def build_stage_b(data: eng.StaticData, state_after_4: dict):
    periods = list(range(5, 9))
    return solve_stage(
        data, periods,
        beginning_inventory=state_after_4["ending_inventory"],
        cash_begin=state_after_4["cash_end"],
        carried_payments=state_after_4["carried_payments"],
        disrupted=True,
        name="StageB",
        pipeline_arrivals=state_after_4["pipeline_arrivals"],
    )


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "environment/data"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "dev/out"
    os.makedirs(out_dir, exist_ok=True)
    data = eng.load_static_data(data_dir)

    stage_a_orders, stage_a_obj = build_stage_a(data)
    baseline_orders_1_4 = [o for o in stage_a_orders if o.period <= 4]
    res_1_4 = eng.replay(data, baseline_orders_1_4, period_start=1, period_end=4, apply_disruption=False)
    if not res_1_4.ok:
        print("STAGE A (periods 1-4) REPLAY FAILED:")
        for v in res_1_4.violations:
            print(" -", v)
        sys.exit(1)
    state_after_4 = eng.snapshot_state(res_1_4, 4, data, baseline_orders_1_4)

    full_res_a = eng.replay(data, stage_a_orders, period_start=1, period_end=8, apply_disruption=False)
    if not full_res_a.ok:
        print("STAGE A (full 1-8, as a hypothetical no-disruption world) REPLAY FAILED:")
        for v in full_res_a.violations:
            print(" -", v)
        sys.exit(1)
    stage_a_cost = eng.total_cost(data, stage_a_orders, full_res_a, 1, 8)

    stage_b_orders, stage_b_obj = build_stage_b(data, state_after_4)
    res_b = eng.replay(data, stage_b_orders, period_start=5, period_end=8, initial_state=state_after_4, apply_disruption=True)
    if not res_b.ok:
        print("STAGE B REPLAY FAILED:")
        for v in res_b.violations:
            print(" -", v)
        sys.exit(1)
    stage_b_cost = eng.total_cost(data, stage_b_orders, res_b, 5, 8)

    print(f"Stage A: {len(stage_a_orders)} orders, LP obj={stage_a_obj:.2f}, replay cost={stage_a_cost:.2f}")
    print(f"  end-of-period-4 cash={state_after_4['cash_end']:.2f}")
    print(f"  end-of-period-4 inventory={state_after_4['ending_inventory']}")
    print(f"Stage B: {len(stage_b_orders)} orders, LP obj={stage_b_obj:.2f}, replay cost={stage_b_cost:.2f}")

    def write_orders(path, orders):
        import csv
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["period", "supplier_id", "product_id", "quantity"])
            for o in sorted(orders, key=lambda o: (o.period, o.supplier_id, o.product_id)):
                w.writerow([o.period, o.supplier_id, o.product_id, int(o.quantity)])

    write_orders(os.path.join(out_dir, "baseline_plan.csv"), stage_a_orders)
    write_orders(os.path.join(out_dir, "replan.csv"), stage_b_orders)

    debug_path = sys.argv[3] if len(sys.argv) > 3 else None
    if debug_path:
        import json
        with open(debug_path, "w") as f:
            json.dump({
                "stage_a_cost": stage_a_cost,
                "stage_b_cost": stage_b_cost,
                "state_after_4": {
                    "ending_inventory": state_after_4["ending_inventory"],
                    "cash_end": state_after_4["cash_end"],
                    "carried_payments": state_after_4["carried_payments"],
                },
            }, f, indent=2)


if __name__ == "__main__":
    main()
