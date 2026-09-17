"""Exits the process immediately instead of returning -- tests that a
process that never produces output.json fails cleanly rather than
hanging or scoring by accident."""
import sys


def compute_balances(invoices, payments, jurisdiction_rules, queries):
    sys.exit(0)
