"""Raises during the normal call, betting on a partial-credit or crashed
verifier defaulting to pass."""


def match(payments, invoices):
    raise RuntimeError("simulated crash")
