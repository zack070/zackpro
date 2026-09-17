"""Kitchen-sink probe: tries every adversarial heuristic tried this build
and picks whichever scores best for this specific batch -- simulates an
agent who tries several plausible approaches and submits the winner."""
TOLERANCE_CENTS = 50


def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def one_to_one_nearest(payments, invoices):
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        used = set()
        for inv in sorted(cust_invoices, key=lambda i: -i.amount_due_cents):
            candidates = [p for p in cust_payments if p.payment_id not in used]
            if not candidates:
                continue
            best = min(candidates, key=lambda p: abs(p.amount_cents - inv.amount_due_cents))
            matching[best.payment_id] = inv.invoice_id
            used.add(best.payment_id)
    return matching


def sorted_accumulate_desc(payments, invoices):
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        remaining = sorted(cust_payments, key=lambda p: -p.amount_cents)
        for inv in sorted(cust_invoices, key=lambda i: -i.amount_due_cents):
            total = 0
            still = []
            for p in remaining:
                if total >= inv.amount_due_cents:
                    still.append(p)
                    continue
                matching[p.payment_id] = inv.invoice_id
                total += p.amount_cents
            remaining = [p for p in remaining if matching.get(p.payment_id) != inv.invoice_id]
    return matching


def sorted_accumulate_asc(payments, invoices):
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        remaining = sorted(cust_payments, key=lambda p: p.amount_cents)
        for inv in sorted(cust_invoices, key=lambda i: i.amount_due_cents):
            total = 0
            for p in list(remaining):
                if total >= inv.amount_due_cents:
                    break
                matching[p.payment_id] = inv.invoice_id
                total += p.amount_cents
                remaining.remove(p)
    return matching


def best_fit_decreasing(payments, invoices):
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        covered = {i.invoice_id: 0 for i in cust_invoices}
        inv_by_id = {i.invoice_id: i for i in cust_invoices}
        for p in sorted(cust_payments, key=lambda p: -p.amount_cents):
            open_invs = [iid for iid, c in covered.items() if c + TOLERANCE_CENTS < inv_by_id[iid].amount_due_cents]
            if not open_invs:
                continue

            def gap_after(iid):
                new_total = covered[iid] + p.amount_cents
                due = inv_by_id[iid].amount_due_cents
                return abs(due - new_total)

            chosen = min(open_invs, key=gap_after)
            matching[p.payment_id] = chosen
            covered[chosen] += p.amount_cents
    return matching


def fifo_order(payments, invoices):
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        covered = {i.invoice_id: 0 for i in cust_invoices}
        inv_by_id = {i.invoice_id: i for i in cust_invoices}
        inv_order = [i.invoice_id for i in cust_invoices]
        ptr = 0
        for p in cust_payments:
            while ptr < len(inv_order) and covered[inv_order[ptr]] + TOLERANCE_CENTS >= inv_by_id[inv_order[ptr]].amount_due_cents:
                ptr += 1
            if ptr >= len(inv_order):
                break
            matching[p.payment_id] = inv_order[ptr]
            covered[inv_order[ptr]] += p.amount_cents
    return matching


def _cost(payments, invoices, matching):
    inv_by_id = {i.invoice_id: i for i in invoices}
    pay_by_id = {p.payment_id: p for p in payments}
    covered = {i.invoice_id: 0 for i in invoices}
    unapplied = 0
    applied_ids = set()
    for pid, iid in matching.items():
        p = pay_by_id.get(pid)
        if p is None or iid is None:
            continue
        inv = inv_by_id.get(iid)
        if inv is None or inv.customer_id != p.customer_id:
            continue
        covered[iid] += p.amount_cents
        applied_ids.add(pid)
    for p in payments:
        if p.payment_id not in applied_ids:
            unapplied += p.amount_cents
    uncleared = sum(max(0, inv.amount_due_cents - covered[inv.invoice_id] - TOLERANCE_CENTS) for inv in invoices)
    return uncleared + unapplied


def match(payments, invoices):
    candidates = [
        one_to_one_nearest(payments, invoices),
        sorted_accumulate_desc(payments, invoices),
        sorted_accumulate_asc(payments, invoices),
        best_fit_decreasing(payments, invoices),
        fifo_order(payments, invoices),
    ]
    best = min(candidates, key=lambda m: _cost(payments, invoices, m))
    return best
