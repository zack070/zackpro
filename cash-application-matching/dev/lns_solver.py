"""Second, structurally independent approach: GRASP-style randomized
construction (best-fit-decreasing with randomized tie-breaking among
near-equally-good choices) followed by large-neighborhood-search repair
(destroy a random fraction of assignments, greedily reinsert), repeated
across many restarts. Deliberately a different algorithmic family from
local_search_solver.py's simulated annealing over single reassignments,
used only to confirm the floor is a real property of the problem."""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from engine import TOLERANCE_CENTS
from greedy_probes import _by_customer


def _cost_for_customer(cust_payments, cust_invoices, assignment):
    covered = {i.invoice_id: 0 for i in cust_invoices}
    inv_by_id = {i.invoice_id: i for i in cust_invoices}
    unapplied = 0
    for p in cust_payments:
        inv_id = assignment.get(p.payment_id)
        if inv_id is None:
            unapplied += p.amount_cents
        else:
            covered[inv_id] += p.amount_cents
    uncleared = sum(max(0, inv.amount_due_cents - covered[inv.invoice_id] - TOLERANCE_CENTS) for inv in cust_invoices)
    return uncleared + unapplied


def _randomized_construct(cust_payments, cust_invoices, rng, alpha=0.3):
    covered = {i.invoice_id: 0 for i in cust_invoices}
    inv_by_id = {i.invoice_id: i for i in cust_invoices}
    assignment = {}
    order = list(cust_payments)
    rng.shuffle(order)
    order.sort(key=lambda p: -p.amount_cents)
    for p in order:
        open_invs = [iid for iid, c in covered.items() if c + TOLERANCE_CENTS < inv_by_id[iid].amount_due_cents]
        if not open_invs:
            assignment[p.payment_id] = None
            continue

        def gap_after(iid):
            return abs(inv_by_id[iid].amount_due_cents - (covered[iid] + p.amount_cents))

        scored = sorted(open_invs, key=gap_after)
        cutoff = max(1, int(len(scored) * alpha))
        candidates = scored[:cutoff]
        chosen = rng.choice(candidates)
        assignment[p.payment_id] = chosen
        covered[chosen] += p.amount_cents
    return assignment


def _destroy_and_repair(cust_payments, cust_invoices, assignment, rng, destroy_frac=0.25):
    inv_by_id = {i.invoice_id: i for i in cust_invoices}
    pay_ids = [p.payment_id for p in cust_payments]
    n_destroy = max(1, int(len(pay_ids) * destroy_frac))
    to_destroy = set(rng.sample(pay_ids, min(n_destroy, len(pay_ids))))

    new_assignment = {pid: iid for pid, iid in assignment.items() if pid not in to_destroy}
    covered = {i.invoice_id: 0 for i in cust_invoices}
    pay_by_id = {p.payment_id: p for p in cust_payments}
    for pid, iid in new_assignment.items():
        if iid is not None:
            covered[iid] += pay_by_id[pid].amount_cents

    destroyed_payments = sorted((pay_by_id[pid] for pid in to_destroy), key=lambda p: -p.amount_cents)
    for p in destroyed_payments:
        open_invs = [iid for iid, c in covered.items() if c + TOLERANCE_CENTS < inv_by_id[iid].amount_due_cents]
        if not open_invs:
            new_assignment[p.payment_id] = None
            continue

        def gap_after(iid):
            return abs(inv_by_id[iid].amount_due_cents - (covered[iid] + p.amount_cents))

        chosen = min(open_invs, key=gap_after)
        new_assignment[p.payment_id] = chosen
        covered[chosen] += p.amount_cents
    return new_assignment


def _optimize_customer(cust_payments, cust_invoices, rng, restarts=6, repair_rounds=40):
    if not cust_payments:
        return {}
    best_assignment = None
    best_cost = None
    for _ in range(restarts):
        assignment = _randomized_construct(cust_payments, cust_invoices, rng)
        cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
        for _ in range(repair_rounds):
            candidate = _destroy_and_repair(cust_payments, cust_invoices, assignment, rng)
            cand_cost = _cost_for_customer(cust_payments, cust_invoices, candidate)
            if cand_cost <= cost:
                assignment, cost = candidate, cand_cost
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_assignment = assignment
    return best_assignment


def solve_lns(payments, invoices, seed=0, restarts=6, repair_rounds=40):
    rng = random.Random(seed)
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        result = _optimize_customer(cust_payments, cust_invoices, rng, restarts, repair_rounds)
        matching.update(result)
    return matching
