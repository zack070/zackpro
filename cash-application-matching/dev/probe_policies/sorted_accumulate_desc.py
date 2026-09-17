TOLERANCE_CENTS = 50

def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def sorted_accumulate_desc(payments, invoices):
    """Sort invoices descending by amount, sort payments descending by
    amount; for each invoice in turn, greedily accumulate the largest
    remaining payments until the invoice is covered (or payments run out),
    then move to the next invoice."""
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


def match(payments, invoices):
    return sorted_accumulate_desc(payments, invoices)
