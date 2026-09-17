TOLERANCE_CENTS = 50

def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def one_to_one_nearest(payments, invoices):
    """For each invoice (largest first), find the single unused payment
    whose amount is closest to it, with no combining -- a very natural
    'match the check to the invoice it most looks like' approach."""
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


def match(payments, invoices):
    return one_to_one_nearest(payments, invoices)
