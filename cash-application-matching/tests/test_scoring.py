"""
Stage 2 (TRUSTED). Runs as root. Never imports or executes anything from
the candidate; takes the raw matching dict Stage 1 recorded, and
independently recomputes the score from scratch via engine.score_matching
-- the same function that validates legality (skill/customer match,
existence of ids) and computes cost. A fabricated or nonsensical mapping
can only score as badly as the legality rules allow; there is nothing in
this stage that trusts anything Stage 1 computed.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import engine as eng

SEALED_SCENARIO_DIR = "/tests/sealed/inputs/held_out"
SEALED_BAR_PATH = "/tests/sealed/reference/pass_bar.json"
COLLECTED_PATH = "/work/output.json"


@pytest.fixture(scope="session")
def scenario():
    return eng.load_scenario(SEALED_SCENARIO_DIR)


@pytest.fixture(scope="session")
def pass_bar():
    with open(SEALED_BAR_PATH) as f:
        return json.load(f)["pass_bar_cost_cents"]


@pytest.fixture(scope="session")
def collected():
    with open(COLLECTED_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def result(collected, scenario):
    if collected["status"] != "ok" or collected["matching"] is None:
        pytest.fail(f"policy.py could not be run: status={collected['status']} error={collected.get('error')}")
    payments, invoices = scenario
    return eng.score_matching(payments, invoices, collected["matching"])


def test_policy_present_and_loadable(collected):
    assert collected["status"] == "ok", collected


def test_cost_within_pass_bar(result, pass_bar):
    assert result.total_cost_cents <= pass_bar, (
        f"cost {result.total_cost_cents} exceeds pass bar {pass_bar} "
        f"(uncleared={result.uncleared_invoice_cents}, unapplied={result.unapplied_payment_cents}, "
        f"cleared={result.invoices_fully_cleared}/{result.total_invoices})"
    )
