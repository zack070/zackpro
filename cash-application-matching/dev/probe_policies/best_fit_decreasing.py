TOLERANCE_CENTS = 50

def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def best_fit_decreasing(payments, invoices):
    """Classic bin-covering heuristic: process payments largest-first; each
    payment goes to whichever not-yet-cleared invoice it brings closest to
    (without excessively overshooting) full coverage."""
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


def match(payments, invoices):
    return best_fit_decreasing(payments, invoices)
