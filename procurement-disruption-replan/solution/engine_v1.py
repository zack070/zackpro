"""
Canonical authoritative-semantics replay/accounting engine.

This module is the single source of truth for what "correct" means under
the operational contract. It is copied byte-identical into:
  - environment/tools/  (agent-visible check_plan.py / advance_horizon.py)
  - tests/              (hidden verifier's independent feasibility replay)
  - solution/           (oracle's own self-check before finalizing output)

Keep dev/sync_engine.sh in sync after any edit here.

The engine is a pure, deterministic state-machine simulator. It never makes
decisions; it only replays a given set of order decisions against fixed
input data and reports the resulting state, any constraint violations, and
period-by-period ledgers. Cost is *not* computed here on purpose in the
verifier's grading path -- callers that need cost recompute it themselves,
independently, from the ledgers this engine returns (see tests/ grading
script). check_plan.py / advance_horizon.py do call cost() for convenience
since that is not privileged information (the price data is fully
agent-visible).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

NUM_PERIODS = 8
PERIODS = list(range(1, NUM_PERIODS + 1))

# Deterministic disruption applied only from period 5 onward. This constant
# is intentionally NOT surfaced anywhere in agent-visible static data files;
# it is applied only inside this engine's capacity-lookup logic, and the
# only way an agent-visible tool exposes it is by actually calling
# advance_horizon.py, which internally uses this same engine.
DISRUPTED_SUPPLIER = "S2"
DISRUPTED_PERIODS = {5, 6}


@dataclass
class StaticData:
    products: List[str]
    suppliers: List[str]
    holding_cost: Dict[str, float]                       # product -> $/unit/period
    supplier_products: Dict[Tuple[str, str], dict]        # (supplier,product) -> {unit_price, lead_time, moq, payment_term}
    supplier_capacity: Dict[Tuple[str, int], float]       # (supplier,period) -> units, UNDISRUPTED baseline capacity
    demand: Dict[Tuple[str, int], float]                  # (product,period) -> units
    initial_inventory: Dict[str, float]                   # product -> units at start of period 1
    existing_pos: List[dict]                              # list of existing PO dicts
    initial_cash: float
    other_cash_outflows: Dict[int, float]                 # period -> $ (fixed, non-procurement)
    warehouse_capacity: float                             # constant across periods


@dataclass
class NewOrder:
    period: int
    supplier_id: str
    product_id: str
    quantity: float


class Violation(str):
    pass


@dataclass
class ReplayResult:
    ok: bool
    violations: List[str] = field(default_factory=list)
    # per-period, per-product ledgers
    beginning_inventory: Dict[Tuple[str, int], float] = field(default_factory=dict)
    arrivals: Dict[Tuple[str, int], float] = field(default_factory=dict)
    ending_inventory: Dict[Tuple[str, int], float] = field(default_factory=dict)
    demand_served: Dict[Tuple[str, int], float] = field(default_factory=dict)
    # per-period, per-supplier capacity usage
    supplier_capacity_used: Dict[Tuple[str, int], float] = field(default_factory=dict)
    # cash
    cash_begin: Dict[int, float] = field(default_factory=dict)
    cash_end: Dict[int, float] = field(default_factory=dict)
    payments: Dict[int, float] = field(default_factory=dict)
    # end-of-period-4 snapshot convenience (filled by caller if needed)


def is_disrupted(supplier_id: str, period: int, apply_disruption: bool) -> bool:
    """The disruption is a real-world event that only exists in the
    post-period-4 (Stage B / replan) world. The baseline (Stage A) is a plan
    made before the disruption occurred and is graded against the
    disruption-free hypothetical world it was actually planned for -- so
    every call site must pass apply_disruption explicitly rather than
    assuming it is always active."""
    return apply_disruption and supplier_id == DISRUPTED_SUPPLIER and period in DISRUPTED_PERIODS


def _arrival_events(data: StaticData, new_orders: List[NewOrder]) -> Dict[Tuple[str, int], float]:
    """Combine existing-PO arrivals and new-order arrivals into a single
    (product, arrival_period) -> quantity map. Arrivals scheduled beyond the
    horizon are dropped (cannot satisfy horizon demand, per contract)."""
    arrivals: Dict[Tuple[str, int], float] = {}

    for po in data.existing_pos:
        ap = po["arrival_period"]
        if 1 <= ap <= NUM_PERIODS:
            key = (po["product_id"], ap)
            arrivals[key] = arrivals.get(key, 0.0) + po["quantity"]

    for o in new_orders:
        sp = data.supplier_products.get((o.supplier_id, o.product_id))
        if sp is None:
            continue  # ineligible pair; caller already flags this as a violation
        arrival_period = o.period + sp["lead_time"]
        if arrival_period > NUM_PERIODS:
            continue  # outside horizon, dropped per contract
        key = (o.product_id, arrival_period)
        arrivals[key] = arrivals.get(key, 0.0) + o.quantity

    return arrivals


def _payment_events(data: StaticData, new_orders: List[NewOrder]) -> Dict[int, float]:
    """period -> total payment amount due in that period (existing POs + new orders)."""
    payments: Dict[int, float] = {}

    for po in data.existing_pos:
        due = po["payment_due_period"]
        if 1 <= due <= NUM_PERIODS:
            amt = po["quantity"] * po["unit_price"]
            payments[due] = payments.get(due, 0.0) + amt

    for o in new_orders:
        sp = data.supplier_products.get((o.supplier_id, o.product_id))
        if sp is None:
            continue
        due = o.period + sp["payment_term"]
        if due > NUM_PERIODS:
            continue  # outside horizon, does not affect horizon cash balance
        amt = o.quantity * sp["unit_price"]
        payments[due] = payments.get(due, 0.0) + amt

    return payments


def replay(
    data: StaticData,
    new_orders: List[NewOrder],
    period_start: int = 1,
    period_end: int = NUM_PERIODS,
    initial_state: Optional[dict] = None,
    require_full_service: bool = True,
    apply_disruption: bool = False,
) -> ReplayResult:
    """
    Replay new_orders (a full or partial set of NEW purchase decisions)
    against the authoritative semantics, for periods [period_start, period_end].

    If initial_state is None, periods start from data.initial_inventory /
    data.initial_cash (i.e. this is a from-period-1 replay).

    If initial_state is provided (as produced by snapshot_state below), it is
    used as the beginning-of-period_start state instead -- this is how
    Stage B (periods 5-8) replay is anchored to the real end-of-period-4
    state rather than re-deriving it from scratch.

    new_orders should contain ONLY orders whose period lies in
    [period_start, period_end]; orders outside that window are ignored for
    arrivals/payments purposes *within this call*, but a full-horizon caller
    should pass the full order list once. (In practice the verifier calls
    this once per stage with only that stage's orders, and pre-existing POs
    plus the initial_state snapshot carry forward everything relevant from
    prior periods.)
    """
    violations: List[str] = []
    res = ReplayResult(ok=True)

    # --- schema-level validation of new orders -----------------------------
    seen_keys = set()
    for o in new_orders:
        key = (o.supplier_id, o.product_id, o.period)
        if key in seen_keys:
            violations.append(f"duplicate row for {o.supplier_id}/{o.product_id}/p{o.period}: submit at most one row per supplier/product/period")
        seen_keys.add(key)

    valid_orders: List[NewOrder] = []
    for o in new_orders:
        if o.period < period_start or o.period > period_end:
            violations.append(f"order in period {o.period} outside replay window [{period_start},{period_end}]")
            continue
        if o.quantity <= 0:
            violations.append(f"non-positive quantity {o.quantity} for order {o.supplier_id}/{o.product_id}/p{o.period}")
            continue
        if float(o.quantity) != int(o.quantity):
            violations.append(f"non-integer quantity {o.quantity} for order {o.supplier_id}/{o.product_id}/p{o.period}")
            continue
        sp = data.supplier_products.get((o.supplier_id, o.product_id))
        if sp is None:
            violations.append(f"ineligible supplier/product pair {o.supplier_id}/{o.product_id}")
            continue
        if is_disrupted(o.supplier_id, o.period, apply_disruption):
            violations.append(f"new order placed with disrupted supplier {o.supplier_id} in period {o.period}")
            continue
        if o.quantity < sp["moq"]:
            violations.append(f"order below MOQ: {o.supplier_id}/{o.product_id}/p{o.period} qty={o.quantity} < moq={sp['moq']}")
            continue
        valid_orders.append(o)

    # existing POs whose order_period falls in this window also consume
    # capacity in this window (relevant mainly for period_start==1 windows,
    # since existing POs in this dataset are all order_period <= period_start
    # boundary by construction, but we compute generally).
    capacity_used: Dict[Tuple[str, int], float] = {}
    for po in data.existing_pos:
        op = po["order_period"]
        if period_start <= op <= period_end:
            key = (po["supplier_id"], op)
            capacity_used[key] = capacity_used.get(key, 0.0) + po["quantity"]
    for o in valid_orders:
        key = (o.supplier_id, o.period)
        capacity_used[key] = capacity_used.get(key, 0.0) + o.quantity

    for (supplier_id, period), used in capacity_used.items():
        if period < period_start or period > period_end:
            continue
        cap = data.supplier_capacity.get((supplier_id, period), 0.0)
        if is_disrupted(supplier_id, period, apply_disruption):
            cap = 0.0
        if used > cap + 1e-9:
            violations.append(f"supplier capacity exceeded: {supplier_id}/p{period} used={used} cap={cap}")

    res.supplier_capacity_used = capacity_used

    # --- arrivals ------------------------------------------------------------
    all_arrivals = _arrival_events(data, valid_orders)
    if initial_state is not None and "pipeline_arrivals" in initial_state:
        # Orders placed in an earlier stage (already committed, capacity and
        # payment already accounted for at that time) that had not yet
        # physically arrived as of the snapshot. These are a fixed supply
        # source for this replay window, not a new decision.
        for key, qty in initial_state["pipeline_arrivals"].items():
            product_id, arrival_period = key
            if period_start <= arrival_period <= period_end:
                all_arrivals[(product_id, arrival_period)] = all_arrivals.get((product_id, arrival_period), 0.0) + qty

    # --- inventory + service replay -------------------------------------------
    if initial_state is None:
        beg_inv = dict(data.initial_inventory)
        cash_begin_period_start = data.initial_cash
    else:
        beg_inv = dict(initial_state["ending_inventory"])
        cash_begin_period_start = initial_state["cash_end"]

    all_payments = _payment_events(data, valid_orders)
    if initial_state is not None and "carried_payments" in initial_state:
        for p, amt in initial_state["carried_payments"].items():
            p = int(p)
            if period_start <= p <= period_end:
                all_payments[p] = all_payments.get(p, 0.0) + amt

    total_served: Dict[str, float] = {p: 0.0 for p in data.products}
    total_demand: Dict[str, float] = {p: 0.0 for p in data.products}

    cash = cash_begin_period_start
    prev_ending = dict(beg_inv)

    for t in range(period_start, period_end + 1):
        begin = dict(prev_ending)
        for p in data.products:
            res.beginning_inventory[(p, t)] = begin.get(p, 0.0)
            arr = all_arrivals.get((p, t), 0.0)
            res.arrivals[(p, t)] = arr
            avail = begin.get(p, 0.0) + arr
            dem = data.demand.get((p, t), 0.0)
            total_demand[p] += dem
            served = min(avail, dem)
            unmet = dem - served
            if unmet > 1e-6 and require_full_service:
                violations.append(f"unmet demand: {p}/p{t} short by {unmet}")
            ending = avail - served
            if ending < -1e-9:
                violations.append(f"negative inventory: {p}/p{t} = {ending}")
                ending = max(ending, 0.0)
            res.demand_served[(p, t)] = served
            total_served[p] += served
            res.ending_inventory[(p, t)] = ending
            prev_ending[p] = ending

        total_end_inv = sum(prev_ending.values())
        if total_end_inv > data.warehouse_capacity + 1e-9:
            violations.append(f"warehouse capacity exceeded: p{t} total_end_inv={total_end_inv} cap={data.warehouse_capacity}")

        res.cash_begin[t] = cash
        pay = all_payments.get(t, 0.0)
        other = data.other_cash_outflows.get(t, 0.0)
        cash = cash - pay - other
        res.payments[t] = pay
        if cash < -1e-9:
            violations.append(f"negative cash: end of p{t} = {cash}")
        res.cash_end[t] = cash

    for p in data.products:
        if total_demand[p] > 0 and require_full_service:
            frac = total_served[p] / total_demand[p]
            if frac < 1.0 - 1e-9:
                violations.append(f"service requirement not met for {p}: {frac:.6f} < 1.0")

    res.ok = len(violations) == 0
    res.violations = violations
    return res


def snapshot_state(res: ReplayResult, at_period: int, data: StaticData, new_orders: List[NewOrder]) -> dict:
    """Produce the carry-forward state to hand to a later replay() call as
    initial_state, capturing ending inventory, cash, and any payment
    obligations from orders already placed (order_period <= at_period) whose
    payment due date is still in the future."""
    ending_inventory = {p: res.ending_inventory[(p, at_period)] for p in data.products}
    carried_payments: Dict[int, float] = {}
    for po in data.existing_pos:
        if po["order_period"] <= at_period and po["payment_due_period"] > at_period:
            carried_payments[po["payment_due_period"]] = carried_payments.get(po["payment_due_period"], 0.0) + po["quantity"] * po["unit_price"]
    pipeline_arrivals: Dict[Tuple[str, int], float] = {}
    for o in new_orders:
        if o.period > at_period:
            continue
        sp = data.supplier_products.get((o.supplier_id, o.product_id))
        if sp is None:
            continue
        due = o.period + sp["payment_term"]
        if due > at_period:
            carried_payments[due] = carried_payments.get(due, 0.0) + o.quantity * sp["unit_price"]
        arrival_period = o.period + sp["lead_time"]
        if arrival_period > at_period:
            # already committed and paid-for-on-schedule, but not yet
            # physically received as of this snapshot: a real in-transit
            # order, distinct from both "available inventory" and "not yet
            # placed."
            key = (o.product_id, arrival_period)
            pipeline_arrivals[key] = pipeline_arrivals.get(key, 0.0) + o.quantity
    return {
        "ending_inventory": ending_inventory,
        "cash_end": res.cash_end[at_period],
        "carried_payments": carried_payments,
        "pipeline_arrivals": pipeline_arrivals,
    }


def purchase_cost(data: StaticData, new_orders: List[NewOrder]) -> float:
    total = 0.0
    for o in new_orders:
        sp = data.supplier_products.get((o.supplier_id, o.product_id))
        if sp is None:
            continue
        total += o.quantity * sp["unit_price"]
    return total


def holding_cost_total(data: StaticData, res: ReplayResult, period_start: int, period_end: int) -> float:
    total = 0.0
    for p in data.products:
        hc = data.holding_cost[p]
        for t in range(period_start, period_end + 1):
            total += hc * res.ending_inventory[(p, t)]
    return total


def total_cost(data: StaticData, new_orders: List[NewOrder], res: ReplayResult, period_start: int, period_end: int) -> float:
    return purchase_cost(data, new_orders) + holding_cost_total(data, res, period_start, period_end)


def load_static_data(data_dir: str) -> StaticData:
    import csv
    import os

    def read_csv(name):
        with open(os.path.join(data_dir, name), newline="") as f:
            return list(csv.DictReader(f))

    products = [r["product_id"] for r in read_csv("products.csv")]
    holding_cost = {r["product_id"]: float(r["holding_cost_per_unit_per_period"]) for r in read_csv("products.csv")}
    suppliers = [r["supplier_id"] for r in read_csv("suppliers.csv")]

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
            "po_id": r["po_id"],
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
    with open(os.path.join(data_dir, "warehouse_capacity.json")) as f:
        wh_data = json.load(f)

    return StaticData(
        products=products,
        suppliers=suppliers,
        holding_cost=holding_cost,
        supplier_products=supplier_products,
        supplier_capacity=supplier_capacity,
        demand=demand,
        initial_inventory=initial_inventory,
        existing_pos=existing_pos,
        initial_cash=float(cash_data["initial_cash"]),
        other_cash_outflows={int(k): float(v) for k, v in cash_data.get("other_cash_outflows", {}).items()},
        warehouse_capacity=float(wh_data["capacity_units"]),
    )


def load_orders_csv(path: str) -> List[NewOrder]:
    import csv
    orders = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            orders.append(NewOrder(
                period=int(r["period"]),
                supplier_id=r["supplier_id"],
                product_id=r["product_id"],
                quantity=float(r["quantity"]),
            ))
    return orders
