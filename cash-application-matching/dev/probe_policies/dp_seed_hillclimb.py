"""Adversarial probe: the exact algorithm a real reviewer used to catch the
previous bar as too loose -- a bitset subset-sum DP assigns invoices
smallest-first (a much better construction than best-fit-decreasing), then
a plain first-improvement hill climb (20k iterations, never accepts a
worse move, no annealing, no restarts) refines it. Deterministic by
construction (fixed iteration count, fixed seed) and fast (~1s)."""
import random

TOLERANCE_CENTS = 50


def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def _dp_seed(cust_payments, cust_invoices):
    amounts = [p.amount_cents for p in cust_payments]
    n = len(amounts)
    assignment = {}
    used = [False] * n
    for inv in sorted(cust_invoices, key=lambda i: i.amount_due_cents):
        avail_idx = [i for i in range(n) if not used[i]]
        if not avail_idx:
            continue
        layers = [1]
        reach = 1
        for idx in avail_idx:
            reach = reach | (reach << amounts[idx])
            layers.append(reach)
        final = layers[-1]
        target = inv.amount_due_cents
        max_sum = final.bit_length() - 1
        best_below = None
        below_mask = final & ((1 << (target + 1)) - 1)
        if below_mask != 0:
            best_below = below_mask.bit_length() - 1
        best_above = None
        if target + 1 <= max_sum:
            above_shifted = final >> (target + 1)
            if above_shifted != 0:
                low = above_shifted & (-above_shifted)
                best_above = (target + 1) + (low.bit_length() - 1)
        if best_below is not None and target - best_below <= TOLERANCE_CENTS:
            best_sum = best_below
        elif best_below is None:
            best_sum = best_above if best_above is not None else 0
        elif best_above is None:
            best_sum = best_below
        else:
            best_sum = best_below if (target - best_below) <= (best_above - target) else best_above
        remaining = best_sum
        for k in range(len(avail_idx), 0, -1):
            idx = avail_idx[k - 1]
            if (layers[k - 1] >> remaining) & 1:
                continue
            else:
                assignment[cust_payments[idx].payment_id] = inv.invoice_id
                used[idx] = True
                remaining -= amounts[idx]
    return assignment


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


def match(payments, invoices):
    rng = random.Random(1)
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        if not cust_payments:
            continue
        assignment = _dp_seed(cust_payments, cust_invoices)
        cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
        inv_ids = [i.invoice_id for i in cust_invoices] + [None]
        for _ in range(20000):
            p = rng.choice(cust_payments)
            new_target = rng.choice(inv_ids)
            old_target = assignment.get(p.payment_id)
            if new_target == old_target:
                continue
            assignment[p.payment_id] = new_target
            new_cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
            if new_cost <= cost:
                cost = new_cost
            else:
                assignment[p.payment_id] = old_target
        matching.update(assignment)
    return matching
