"""Reference solution: for each customer, run two structurally different
search algorithms -- simulated annealing over single reassignments (seeded
by a best-fit-decreasing greedy construction), and a GRASP-style
randomized-construction + large-neighborhood-search repair loop -- and
keep whichever result scores better for that customer. Per-customer
instance sizes here (20-30 payments/invoices) put exact solving (bitmask
subset-sum DP) well past practical reach, so both algorithms are genuine
approximate search, not disguised exact enumeration."""
import math
import random

TOLERANCE_CENTS = 50


def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def _best_fit_decreasing(cust_payments, cust_invoices):
    covered = {i.invoice_id: 0 for i in cust_invoices}
    inv_by_id = {i.invoice_id: i for i in cust_invoices}
    assignment = {}
    for p in sorted(cust_payments, key=lambda p: -p.amount_cents):
        open_invs = [iid for iid, c in covered.items() if c + TOLERANCE_CENTS < inv_by_id[iid].amount_due_cents]
        if not open_invs:
            assignment[p.payment_id] = None
            continue

        def gap_after(iid):
            return abs(inv_by_id[iid].amount_due_cents - (covered[iid] + p.amount_cents))

        chosen = min(open_invs, key=gap_after)
        assignment[p.payment_id] = chosen
        covered[chosen] += p.amount_cents
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


def _anneal_customer(cust_payments, cust_invoices, seed_assignment, rng, iterations):
    if not cust_payments:
        return {}
    assignment = dict(seed_assignment)
    current_cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
    best_assignment = dict(assignment)
    best_cost = current_cost

    inv_ids = [i.invoice_id for i in cust_invoices] + [None]
    temperature = max(1.0, current_cost / 10.0)
    cooling = 0.999

    for _ in range(iterations):
        p = rng.choice(cust_payments)
        new_target = rng.choice(inv_ids)
        old_target = assignment.get(p.payment_id)
        if new_target == old_target:
            continue

        assignment[p.payment_id] = new_target
        new_cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
        delta = new_cost - current_cost

        if delta <= 0 or rng.random() < math.exp(-delta / max(temperature, 1e-6)):
            current_cost = new_cost
            if current_cost < best_cost:
                best_cost = current_cost
                best_assignment = dict(assignment)
        else:
            assignment[p.payment_id] = old_target

        temperature *= cooling

    return best_assignment


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
        chosen = rng.choice(scored[:cutoff])
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

    for p in sorted((pay_by_id[pid] for pid in to_destroy), key=lambda p: -p.amount_cents):
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


def _lns_customer(cust_payments, cust_invoices, rng, restarts=30, repair_rounds=100):
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


def match(payments, invoices):
    rng = random.Random(12345)
    result = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        if not cust_payments:
            continue
        seed_assignment = _best_fit_decreasing(cust_payments, cust_invoices)
        anneal_result = _anneal_customer(cust_payments, cust_invoices, seed_assignment, rng, iterations=12000)
        lns_result = _lns_customer(cust_payments, cust_invoices, rng, restarts=30, repair_rounds=100)
        c1 = _cost_for_customer(cust_payments, cust_invoices, anneal_result)
        c2 = _cost_for_customer(cust_payments, cust_invoices, lns_result)
        result.update(anneal_result if c1 <= c2 else lns_result)
    return result
