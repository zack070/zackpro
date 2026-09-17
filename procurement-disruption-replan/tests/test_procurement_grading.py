"""
Stage 2 (TRUSTED). Runs as root. Never imports or trusts anything the
candidate computed; recomputes feasibility and cost from scratch against
the sealed data and, for the replan, a freshly re-solved optimum
conditioned on the candidate's own actual end-of-period-4 state (Stage A's
optimum is state-independent and can be precomputed once; Stage B's is not,
since it depends on which of possibly several equally cost-optimal
baselines the candidate reached -- see reference_solver.build_stage_b).
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import engine_v1 as eng
import reference_solver as ref

SEALED_DATA_DIR = "/tests/sealed/inputs"
SEALED_REFERENCE = "/tests/sealed/reference/optimum.json"
COLLECTED_PATH = "/work/collected.json"
TOLERANCE = 0.01


@pytest.fixture(scope="session")
def data():
    return eng.load_static_data(SEALED_DATA_DIR)


@pytest.fixture(scope="session")
def reference():
    with open(SEALED_REFERENCE) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def collected():
    with open(COLLECTED_PATH) as f:
        return json.load(f)


def _rows_to_orders(rows):
    return [
        eng.NewOrder(period=r["period"], supplier_id=r["supplier_id"], product_id=r["product_id"], quantity=r["quantity"])
        for r in rows
    ]


@pytest.fixture(scope="session")
def baseline_orders(collected):
    if collected["baseline"]["status"] != "ok":
        pytest.fail(f"baseline_plan.csv could not be parsed: {collected['baseline']}")
    return _rows_to_orders(collected["baseline"]["rows"])


@pytest.fixture(scope="session")
def replan_orders(collected):
    if collected["replan"]["status"] != "ok":
        pytest.fail(f"replan.csv could not be parsed: {collected['replan']}")
    return _rows_to_orders(collected["replan"]["rows"])


@pytest.fixture(scope="session")
def baseline_replay(data, baseline_orders):
    return eng.replay(data, baseline_orders, period_start=1, period_end=8, apply_disruption=False)


@pytest.fixture(scope="session")
def state_after_4(data, baseline_orders):
    orders_1_4 = [o for o in baseline_orders if o.period <= 4]
    res = eng.replay(data, orders_1_4, period_start=1, period_end=4, apply_disruption=False)
    if not res.ok:
        pytest.fail("baseline periods 1-4 are not independently feasible on their own: " + "; ".join(res.violations))
    return eng.snapshot_state(res, 4, data, orders_1_4)


@pytest.fixture(scope="session")
def replan_replay(data, replan_orders, state_after_4):
    return eng.replay(data, replan_orders, period_start=5, period_end=8, initial_state=state_after_4, apply_disruption=True)


@pytest.fixture(scope="session")
def live_stage_b_optimum(data, state_after_4):
    _, obj = ref.build_stage_b(data, state_after_4)
    return obj


def test_baseline_parseable(collected):
    assert collected["baseline"]["status"] == "ok", collected["baseline"]


def test_replan_parseable(collected):
    assert collected["replan"]["status"] == "ok", collected["replan"]


def test_baseline_feasible(baseline_replay):
    assert baseline_replay.ok, "baseline infeasible:\n" + "\n".join(baseline_replay.violations)


def test_baseline_cost_at_optimum(data, baseline_orders, baseline_replay, reference):
    assert baseline_replay.ok
    cost = eng.total_cost(data, baseline_orders, baseline_replay, 1, 8)
    assert cost <= reference["stage_a_cost"] + TOLERANCE, (
        f"baseline cost {cost:.2f} exceeds the minimum feasible cost {reference['stage_a_cost']:.2f}"
    )


def test_replan_feasible(replan_replay):
    assert replan_replay.ok, "replan infeasible:\n" + "\n".join(replan_replay.violations)


def test_replan_cost_at_optimum(data, replan_orders, replan_replay, live_stage_b_optimum):
    assert replan_replay.ok
    cost = eng.total_cost(data, replan_orders, replan_replay, 5, 8)
    assert cost <= live_stage_b_optimum + TOLERANCE, (
        f"replan cost {cost:.2f} exceeds the minimum feasible cost {live_stage_b_optimum:.2f} "
        f"achievable from your own actual end-of-period-4 state"
    )
