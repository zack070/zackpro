"""Cross-validate engine_v1 against the structurally independent engine_v2
over many randomized candidate order sets (both baseline and replan
windows), checking that feasibility verdicts and costs agree. Build-time
confidence check only; not shipped."""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import engine_v1 as v1
import engine_v2 as v2


def to_v2_orders(orders_v1):
    return [v2.Order(period=o.period, supplier_id=o.supplier_id, product_id=o.product_id, quantity=o.quantity) for o in orders_v1]


def random_orders(data, start, end, rng, n):
    orders = []
    pairs = list(data.supplier_products.keys())
    for _ in range(n):
        s, p = rng.choice(pairs)
        period = rng.randint(start, end)
        qty_choices = [0, -5, 1, rng.randint(1, 300), data.supplier_products[(s, p)]["moq"], data.supplier_products[(s, p)]["moq"] - 1]
        qty = rng.choice(qty_choices)
        orders.append(v1.NewOrder(period=period, supplier_id=s, product_id=p, quantity=qty))
    # occasionally inject a duplicate or out-of-window order
    if rng.random() < 0.3 and orders:
        orders.append(orders[rng.randrange(len(orders))])
    if rng.random() < 0.2:
        s, p = rng.choice(pairs)
        orders.append(v1.NewOrder(period=rng.choice([start - 1, end + 1, 0, 99]), supplier_id=s, product_id=p, quantity=100))
    return orders


def compare(name, res1, res2, cost1, cost2):
    problems = []
    if res1.ok != res2.ok:
        problems.append(f"{name}: ok mismatch v1={res1.ok} v2={res2.ok} v1_violations={res1.violations} v2_violations={res2.violations}")
    elif res1.ok and abs(cost1 - cost2) > 1e-6:
        problems.append(f"{name}: cost mismatch v1={cost1} v2={cost2}")
    return problems


def main():
    data = v1.load_static_data("environment/data")
    rng = random.Random(12345)
    problems = []

    N = 3000
    for i in range(N):
        orders_v1 = random_orders(data, 1, 8, rng, rng.randint(0, 40))
        orders_v2 = to_v2_orders(orders_v1)

        res1 = v1.replay(data, orders_v1, period_start=1, period_end=8, apply_disruption=False)
        res2 = v2.replay(data, orders_v2, 1, 8, apply_disruption=False)
        cost1 = v1.total_cost(data, orders_v1, res1, 1, 8) if res1.ok else None
        cost2 = v2.total_cost(data, orders_v2, res2, 1, 8) if res2.ok else None
        problems += compare(f"baseline#{i}", res1, res2, cost1, cost2)

    # replan window, anchored to a real (randomized-but-feasible-ish) state after period 4
    for i in range(N):
        base_orders_v1 = random_orders(data, 1, 4, rng, rng.randint(0, 20))
        r1_1_4 = v1.replay(data, base_orders_v1, period_start=1, period_end=4, apply_disruption=False)
        if not r1_1_4.ok:
            continue  # need a feasible period-4 state to anchor the replan comparison
        state = v1.snapshot_state(r1_1_4, 4, data, base_orders_v1)

        replan_orders_v1 = random_orders(data, 5, 8, rng, rng.randint(0, 30))
        replan_orders_v2 = to_v2_orders(replan_orders_v1)

        res1 = v1.replay(data, replan_orders_v1, period_start=5, period_end=8, initial_state=state, apply_disruption=True)
        res2 = v2.replay(data, replan_orders_v2, 5, 8, initial_state=state, apply_disruption=True)
        cost1 = v1.total_cost(data, replan_orders_v1, res1, 5, 8) if res1.ok else None
        cost2 = v2.total_cost(data, replan_orders_v2, res2, 5, 8) if res2.ok else None
        problems += compare(f"replan#{i}", res1, res2, cost1, cost2)

    print(f"Ran {N} baseline trials and {N} replan trials.")
    if problems:
        print(f"{len(problems)} MISMATCHES FOUND:")
        for p in problems[:30]:
            print(" -", p)
        sys.exit(1)
    else:
        print("No mismatches. engine_v1 and engine_v2 agree on every trial.")


if __name__ == "__main__":
    main()
