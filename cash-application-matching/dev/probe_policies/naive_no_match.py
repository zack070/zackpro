TOLERANCE_CENTS = 50

def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def naive_no_match(payments, invoices):
    """Baseline: apply nothing at all."""
    return {}


def match(payments, invoices):
    return naive_no_match(payments, invoices)
