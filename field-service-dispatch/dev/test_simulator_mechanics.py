"""Targeted correctness tests for each specific mechanic in simulator.py.
Not part of the shipped bundle -- build-time confidence only."""
import sys
sys.path.insert(0, "dev")
import simulator as sim


def run(techs, jobs, shift_length, decide):
    return sim.run_simulation(techs, jobs, shift_length, decide)


def test_fatigue_triggers_duration_inflation():
    # One tech, one skill. Feed jobs back to back until continuous_work >= 180,
    # then confirm the next job's actual duration is inflated by 1.25x.
    tech = sim.TechnicianSpec(tech_id="T1", skills=frozenset({"x"}), shift_end=1000, max_overtime=200)
    jobs = [
        sim.JobSpec(job_id="J1", required_skill="x", base_duration=100, priority="standard", deadline=900, arrival_time=0),
        sim.JobSpec(job_id="J2", required_skill="x", base_duration=100, priority="standard", deadline=900, arrival_time=0),
        sim.JobSpec(job_id="J3", required_skill="x", base_duration=40, priority="standard", deadline=900, arrival_time=0),
    ]

    def decide(state):
        if state.pending_jobs and state.free_technicians:
            return [(state.free_technicians[0].tech_id, state.pending_jobs[0].job_id)]
        return []

    result = run([tech], jobs, 1000, decide)
    # J1: 0-100 (continuous=100). J2 assigned at t=100, continuous_work=100 < 180 -> not fatigued yet, runs 100-200 (continuous=200).
    # J3 assigned at t=200, continuous_work=200 >= 180 -> fatigued, duration = round(40*1.25) = 50.
    j3_line = [l for l in result.log if "J3" in l and "ASSIGN" in l][0]
    assert "duration=50" in j3_line, f"expected fatigue-inflated duration=50, got: {j3_line}"
    print("PASS: fatigue triggers duration inflation")


def test_break_resets_fatigue():
    tech = sim.TechnicianSpec(tech_id="T1", skills=frozenset({"x"}), shift_end=1000, max_overtime=200)
    jobs = [
        sim.JobSpec(job_id="J1", required_skill="x", base_duration=200, priority="standard", deadline=900, arrival_time=0),
        # arrives well after J1 finishes (t=200) plus a 15+ minute gap -> break resets fatigue
        sim.JobSpec(job_id="J2", required_skill="x", base_duration=40, priority="standard", deadline=900, arrival_time=220),
    ]

    def decide(state):
        if state.pending_jobs and state.free_technicians:
            return [(state.free_technicians[0].tech_id, state.pending_jobs[0].job_id)]
        return []

    result = run([tech], jobs, 1000, decide)
    j2_line = [l for l in result.log if "J2" in l and "ASSIGN" in l][0]
    assert "duration=40" in j2_line, f"expected un-inflated duration=40 after break, got: {j2_line}"
    print("PASS: break resets fatigue")


def test_urgent_breach_spawns_followup_standard_does_not():
    tech = sim.TechnicianSpec(tech_id="T1", skills=frozenset({"x"}), shift_end=1000, max_overtime=200)
    jobs = [
        sim.JobSpec(job_id="URG", required_skill="x", base_duration=50, priority="urgent", deadline=10, arrival_time=0),
        sim.JobSpec(job_id="STD", required_skill="x", base_duration=50, priority="standard", deadline=10, arrival_time=100),
    ]

    def decide(state):
        # deliberately never assign either job so both breach while pending
        return []

    result = run([tech], jobs, 1000, decide)
    assert result.num_followups_spawned == 1, f"expected exactly 1 followup (from URG only), got {result.num_followups_spawned}"
    assert any(j == "URG-followup" for j in [l for l in result.log if "CASCADE" in l]) or \
           any("URG-followup" in l for l in result.log)
    print("PASS: urgent breach cascades, standard breach does not")


def test_overtime_cap_blocks_assignment():
    tech = sim.TechnicianSpec(tech_id="T1", skills=frozenset({"x"}), shift_end=100, max_overtime=10)
    jobs = [
        sim.JobSpec(job_id="J1", required_skill="x", base_duration=50, priority="standard", deadline=900, arrival_time=0),
    ]

    def decide(state):
        if state.pending_jobs and state.free_technicians:
            return [(state.free_technicians[0].tech_id, state.pending_jobs[0].job_id)]
        return []

    result = run([tech], jobs, 1000, decide)
    # finish_time would be 50, well within shift_end=100 -- should be assignable, sanity check
    assert result.completed_jobs == 1

    # Now a job whose duration would exceed shift_end + max_overtime
    jobs2 = [sim.JobSpec(job_id="J2", required_skill="x", base_duration=200, priority="standard", deadline=900, arrival_time=0)]
    result2 = run([tech], jobs2, 1000, decide)
    assert result2.completed_jobs == 0, "job exceeding overtime cap must never be assigned"
    assert result2.num_breaches == 1
    print("PASS: overtime cap blocks assignment of an over-long job")


def test_never_assignable_job_still_detected_as_breach():
    # A job requiring a skill nobody has -- must still be flagged breached, not silently dropped.
    tech = sim.TechnicianSpec(tech_id="T1", skills=frozenset({"x"}), shift_end=1000, max_overtime=0)
    jobs = [
        sim.JobSpec(job_id="J1", required_skill="y", base_duration=10, priority="standard", deadline=50, arrival_time=0),
    ]

    def decide(state):
        return []

    result = run([tech], jobs, 480, decide)
    assert result.num_breaches == 1, f"unassignable job must be detected as a breach, got num_breaches={result.num_breaches}"
    print("PASS: unassignable job still detected as breach via horizon event")


def test_trace_replay_matches_live_run():
    tech = sim.TechnicianSpec(tech_id="T1", skills=frozenset({"x"}), shift_end=480, max_overtime=60)
    jobs = [
        sim.JobSpec(job_id=f"J{i}", required_skill="x", base_duration=30, priority="standard", deadline=400, arrival_time=i * 10)
        for i in range(10)
    ]

    def decide(state):
        if state.pending_jobs and state.free_technicians:
            return [(state.free_technicians[0].tech_id, state.pending_jobs[0].job_id)]
        return []

    live = run([tech], jobs, 480, decide)
    replay_fn = sim.make_replay_policy(live.decision_trace)
    replayed = run([tech], jobs, 480, replay_fn)
    assert live.total_cost == replayed.total_cost
    assert live.num_breaches == replayed.num_breaches
    assert live.completed_jobs == replayed.completed_jobs
    print("PASS: trace replay matches live run")


def test_tampered_trace_cannot_score_better():
    # A trace claiming an assignment to an already-busy technician (invalid at
    # replay time) must be silently dropped, never honored.
    tech = sim.TechnicianSpec(tech_id="T1", skills=frozenset({"x"}), shift_end=480, max_overtime=60)
    jobs = [
        sim.JobSpec(job_id="J1", required_skill="x", base_duration=100, priority="standard", deadline=400, arrival_time=0),
        sim.JobSpec(job_id="J2", required_skill="x", base_duration=100, priority="standard", deadline=400, arrival_time=0),
    ]
    # Fabricated trace: at the very first decision point, claim BOTH J1 and J2
    # go to T1 simultaneously (impossible -- only one tech).
    fake_trace = [[("T1", "J1"), ("T1", "J2")]]
    replay_fn = sim.make_replay_policy(fake_trace)
    result = run([tech], jobs, 480, replay_fn)
    # only the first (T1, J1) can be honored; J2 remains pending and eventually breaches
    assert result.completed_jobs == 1
    assert result.num_breaches == 1
    print("PASS: tampered/impossible trace entries are dropped, not double-honored")


if __name__ == "__main__":
    test_fatigue_triggers_duration_inflation()
    test_break_resets_fatigue()
    test_urgent_breach_spawns_followup_standard_does_not()
    test_overtime_cap_blocks_assignment()
    test_never_assignable_job_still_detected_as_breach()
    test_trace_replay_matches_live_run()
    test_tampered_trace_cannot_score_better()
    print("\nALL MECHANIC TESTS PASSED")
