"""Returns a malformed / wrong-shaped result (not a dict, or a dict with
non-numeric values) -- tests that Stage 1 catches this cleanly and
Stage 2 doesn't crash trying to score it."""


def compute_balances(invoices, payments, jurisdiction_rules, queries):
    return "not a dict"
