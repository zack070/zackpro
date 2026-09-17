TOLERANCE_CENTS = 50

def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def fifo_order(payments, invoices):
    """Process payments and invoices in their given (id) order, a
    plausible 'just go through the list' approach with no sorting at all."""
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


def match(payments, invoices):
    return fifo_order(payments, invoices)
