"""Stage 2 (trusted, root): never executes candidate code. Reads the
raw answers Stage 1 recorded and independently recomputes correctness
against the sealed reference calculation."""
import json

import pytest

import engine

OUTPUT_PATH = "/work/output.json"
HELD_OUT_DIR = "/tests/sealed/inputs/held_out"
PASS_BAR_PATH = "/tests/sealed/reference/pass_bar.json"


@pytest.fixture(scope="module")
def collected():
    with open(OUTPUT_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def pass_bar():
    with open(PASS_BAR_PATH) as f:
        return json.load(f)


def test_policy_present_and_loadable(collected):
    assert collected["status"] == "ok", f"policy did not run cleanly: {collected}"


def test_correctness_within_pass_bar(collected, pass_bar):
    assert collected["status"] == "ok", f"policy did not run cleanly: {collected}"
    invoices, payments, jurisdiction_rules, queries = engine.load_scenario(HELD_OUT_DIR)
    answers = collected["answers"]

    result = engine.score_answers(invoices, payments, jurisdiction_rules, queries, answers)

    bar = pass_bar["pass_bar_correct_queries"]
    assert result.correct_within_tolerance >= bar, (
        f"only {result.correct_within_tolerance}/{result.total_queries} queries correct "
        f"within {pass_bar['tolerance_cents']} cents (need >= {bar}); "
        f"worst query {result.worst_query_id} off by {result.max_abs_error_cents} cents; "
        f"missing queries: {result.missing_query_ids[:5]}"
    )
