"""Stage 1 (untrusted, unprivileged): imports the candidate's submitted
policy module, calls its compute_balances() function ONCE against the
sealed held-out scenario, and writes the raw returned answers to
/work/output.json. Computes nothing about correctness -- that is Stage
2's job, running as a separate trusted process afterward."""
import importlib.util
import json
import sys

sys.path.insert(0, "/tests")
import engine  # noqa: E402

OUTPUT_PATH = "/work/output.json"
POLICY_PATH = "/app/outputs/policy.py"
HELD_OUT_DIR = "/tests/sealed/inputs/held_out"


def write_output(status, **kwargs):
    with open(OUTPUT_PATH, "w") as f:
        json.dump({"status": status, **kwargs}, f)
    print(f"collected -> {OUTPUT_PATH}: status={status}")


def main():
    try:
        spec = importlib.util.spec_from_file_location("policy", POLICY_PATH)
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)
    except Exception as e:
        write_output("import_error", error=repr(e))
        return

    if not hasattr(policy, "compute_balances"):
        write_output("missing_function")
        return

    invoices, payments, jurisdiction_rules, queries = engine.load_scenario(HELD_OUT_DIR)

    try:
        answers = policy.compute_balances(invoices, payments, jurisdiction_rules, queries)
    except Exception as e:
        write_output("call_error", error=repr(e))
        return

    if not isinstance(answers, dict):
        write_output("bad_return_type", type=str(type(answers)))
        return

    try:
        serializable = {str(k): (int(v) if v is not None else None) for k, v in answers.items()}
    except Exception as e:
        write_output("not_serializable", error=repr(e))
        return

    write_output("ok", answers=serializable)


if __name__ == "__main__":
    main()
