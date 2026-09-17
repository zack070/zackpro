"""Raises immediately -- tests that a crashing policy is treated as a
failing submission, not a partial-credit case, and that Stage 2 doesn't
silently pass with no output.json."""


def compute_balances(invoices, payments, jurisdiction_rules, queries):
    raise RuntimeError("boom")
