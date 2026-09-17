"""
Independent, structurally distinct reimplementation of engine_v1's replay
semantics, used ONLY to cross-validate engine_v1 at build time (see
dev/cross_validate_engines.py). Not shipped in the bundle.

Where engine_v1 uses flat dicts keyed by (product, period) and a single
combined loop, this uses fixed-size per-period arrays built by a full
upfront schedule pass, plus a small class per product, deliberately
different control flow and data structures so the two are unlikely to
share the same bug.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

NUM_PERIODS = 8
DISRUPTED_SUPPLIER = "S2"
DISRUPTED_PERIODS = {5, 6}


@dataclass
class Order:
    period: int
    supplier_id: str
    product_id: str
    quantity: float


def is_disrupted(supplier_id, period, apply_disruption):
    return apply_disruption and supplier_id == DISRUPTED_SUPPLIER and period in DISRUPTED_PERIODS


class ProductLedger:
    def __init__(self, product_id, horizon_len):
        self.product_id = product_id
        self.arrival = [0.0] * (horizon_len + 1)  # index by absolute period
        self.beginning = {}
        self.ending = {}
        self.served = {}

    def add_arrival(self, period, qty, horizon_end):
        if 1 <= period <= horizon_end:
            self.arrival[period] += qty

    def run(self, start, end, opening_stock, demand_by_period, violations):
        stock = opening_stock
        for t in range(start, end + 1):
            self.beginning[t] = stock
            avail = stock + self.arrival[t]
            dem = demand_by_period.get(t, 0.0)
            served = dem if avail >= dem - 1e-9 else avail
            if avail < dem - 1e-9:
                violations.append(f"unmet demand: {self.product_id}/p{t} short by {dem - avail}")
            end_stock = avail - served
            if end_stock < -1e-9:
                violations.append(f"negative inventory: {self.product_id}/p{t} = {end_stock}")
                end_stock = max(end_stock, 0.0)
            self.served[t] = served
            self.ending[t] = end_stock
            stock = end_stock


class Result:
    def __init__(self):
        self.violations: List[str] = []
        self.ending_inventory: Dict = {}  # (product, period) -> qty, all periods in window
        self.cash_end: Dict[int, float] = {}
        self.ok = True


def replay(static, orders: List[Order], start: int, end: int, initial_state: Optional[dict] = None,
           require_full_service: bool = True, apply_disruption: bool = False) -> Result:
    res = Result()
    violations = res.violations

    key_counts = {}
    for o in orders:
        k = (o.supplier_id, o.product_id, o.period)
        key_counts[k] = key_counts.get(k, 0) + 1
    for k, c in key_counts.items():
        if c > 1:
            violations.append(f"duplicate row for {k[0]}/{k[1]}/p{k[2]}: submit at most one row per supplier/product/period")

    good_orders = []
    for o in orders:
        if not (start <= o.period <= end):
            violations.append(f"order in period {o.period} outside replay window [{start},{end}]")
            continue
        if o.quantity <= 0:
            violations.append(f"non-positive quantity {o.quantity} for order {o.supplier_id}/{o.product_id}/p{o.period}")
            continue
        if int(o.quantity) != o.quantity:
            violations.append(f"non-integer quantity {o.quantity} for order {o.supplier_id}/{o.product_id}/p{o.period}")
            continue
        pair = static.supplier_products.get((o.supplier_id, o.product_id))
        if pair is None:
            violations.append(f"ineligible supplier/product pair {o.supplier_id}/{o.product_id}")
            continue
        if is_disrupted(o.supplier_id, o.period, apply_disruption):
            violations.append(f"new order placed with disrupted supplier {o.supplier_id} in period {o.period}")
            continue
        if o.quantity < pair["moq"]:
            violations.append(f"order below MOQ: {o.supplier_id}/{o.product_id}/p{o.period} qty={o.quantity} < moq={pair['moq']}")
            continue
        good_orders.append(o)

    # capacity matrix: supplier -> period -> used
    cap_used: Dict[str, Dict[int, float]] = {}

    def bump(supplier, period, qty):
        cap_used.setdefault(supplier, {})
        cap_used[supplier][period] = cap_used[supplier].get(period, 0.0) + qty

    for po in static.existing_pos:
        if start <= po["order_period"] <= end:
            bump(po["supplier_id"], po["order_period"], po["quantity"])
    for o in good_orders:
        bump(o.supplier_id, o.period, o.quantity)

    for supplier, per_period in cap_used.items():
        for period, used in per_period.items():
            cap = 0.0 if is_disrupted(supplier, period, apply_disruption) else static.supplier_capacity.get((supplier, period), 0.0)
            if used > cap + 1e-9:
                violations.append(f"supplier capacity exceeded: {supplier}/p{period} used={used} cap={cap}")

    ledgers = {p: ProductLedger(p, NUM_PERIODS) for p in static.products}

    for po in static.existing_pos:
        ledgers[po["product_id"]].add_arrival(po["arrival_period"], po["quantity"], NUM_PERIODS)
    if initial_state and "pipeline_arrivals" in initial_state:
        for (p, t), q in initial_state["pipeline_arrivals"].items():
            ledgers[p].add_arrival(t, q, NUM_PERIODS)
    for o in good_orders:
        pair = static.supplier_products[(o.supplier_id, o.product_id)]
        arrival_t = o.period + pair["lead_time"]
        ledgers[o.product_id].add_arrival(arrival_t, o.quantity, NUM_PERIODS)

    opening = dict(static.initial_inventory) if initial_state is None else dict(initial_state["ending_inventory"])

    demand_by_product_period: Dict[str, Dict[int, float]] = {p: {} for p in static.products}
    for (p, t), d in static.demand.items():
        demand_by_product_period[p][t] = d

    for p in static.products:
        ledgers[p].run(start, end, opening.get(p, 0.0), demand_by_product_period[p], violations)

    for t in range(start, end + 1):
        total_end = sum(ledgers[p].ending[t] for p in static.products)
        if total_end > static.warehouse_capacity + 1e-9:
            violations.append(f"warehouse capacity exceeded: p{t} total_end_inv={total_end} cap={static.warehouse_capacity}")

    # cash
    pay_schedule: Dict[int, float] = {}
    for po in static.existing_pos:
        if 1 <= po["payment_due_period"] <= NUM_PERIODS:
            pay_schedule[po["payment_due_period"]] = pay_schedule.get(po["payment_due_period"], 0.0) + po["quantity"] * po["unit_price"]
    if initial_state and "carried_payments" in initial_state:
        for t, amt in initial_state["carried_payments"].items():
            t = int(t)
            pay_schedule[t] = pay_schedule.get(t, 0.0) + amt
    for o in good_orders:
        pair = static.supplier_products[(o.supplier_id, o.product_id)]
        due = o.period + pair["payment_term"]
        if due <= NUM_PERIODS:
            pay_schedule[due] = pay_schedule.get(due, 0.0) + o.quantity * pair["unit_price"]

    cash = static.initial_cash if initial_state is None else initial_state["cash_end"]
    for t in range(start, end + 1):
        cash = cash - pay_schedule.get(t, 0.0) - static.other_cash_outflows.get(t, 0.0)
        res.cash_end[t] = cash
        if cash < -1e-9:
            violations.append(f"negative cash: end of p{t} = {cash}")

    if require_full_service:
        for p in static.products:
            total_dem = sum(demand_by_product_period[p].get(t, 0.0) for t in range(start, end + 1))
            total_srv = sum(ledgers[p].served.get(t, 0.0) for t in range(start, end + 1))
            if total_dem > 0:
                frac = total_srv / total_dem
                if frac < 1.0 - 1e-9:
                    violations.append(f"service requirement not met for {p}: {frac:.6f} < 1.0")

    for p in static.products:
        for t in range(start, end + 1):
            res.ending_inventory[(p, t)] = ledgers[p].ending[t]

    res.ok = len(violations) == 0
    return res


def total_cost(static, orders: List[Order], res: Result, start: int, end: int) -> float:
    purchase = sum(o.quantity * static.supplier_products[(o.supplier_id, o.product_id)]["unit_price"]
                   for o in orders if (o.supplier_id, o.product_id) in static.supplier_products)
    holding = sum(static.holding_cost[p] * res.ending_inventory[(p, t)]
                  for p in static.products for t in range(start, end + 1))
    return purchase + holding
