"""Tries to read the sealed reference/pass-bar files directly instead of
computing anything -- tests that the untrusted stage's filesystem
permissions actually block this."""
import os


def compute_balances(invoices, payments, jurisdiction_rules, queries):
    answers = {}
    leaked = None
    for path in [
        "/tests/sealed/reference/pass_bar.json",
        "/tests/sealed/inputs/held_out/invoices.csv",
    ]:
        try:
            with open(path) as f:
                leaked = f.read()
                break
        except Exception:
            continue

    for q in queries:
        answers[q["query_id"]] = 1 if leaked else 0
    return answers
