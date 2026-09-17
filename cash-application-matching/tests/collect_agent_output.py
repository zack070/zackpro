"""
Stage 1 (UNTRUSTED). Runs as an unprivileged user. Imports and executes the
candidate's submitted policy module, calling its match() function exactly
once against the sealed held-out scenario. The only thing written out is
the raw returned mapping -- no score is computed here, and none of this
stage's own arithmetic is ever trusted by Stage 2.
"""
import importlib.util
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import engine as eng

CANDIDATE_PATH = "/app/outputs/policy.py"
SEALED_SCENARIO_DIR = "/tests/sealed/inputs/held_out"
OUTPUT_PATH = "/work/output.json"


def main():
    result = {"status": None, "matching": None, "error": None}

    payments, invoices = eng.load_scenario(SEALED_SCENARIO_DIR)

    try:
        spec = importlib.util.spec_from_file_location("candidate_policy", CANDIDATE_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        result["status"] = "malformed"
        result["error"] = f"import failed: {e!r}"
        _write(result)
        return

    match_fn = getattr(mod, "match", None)
    if not callable(match_fn):
        result["status"] = "malformed"
        result["error"] = "policy.py does not define a callable match(payments, invoices)"
        _write(result)
        return

    try:
        matching = match_fn(payments, invoices)
    except Exception as e:
        result["status"] = "crashed"
        result["error"] = f"match() raised: {e!r}"
        _write(result)
        return

    if not isinstance(matching, dict):
        result["status"] = "malformed"
        result["error"] = f"match() must return a dict, got {type(matching)!r}"
        _write(result)
        return

    # normalize to plain str->str-or-None so it survives JSON round-trip cleanly
    try:
        normalized = {str(k): (None if v is None else str(v)) for k, v in matching.items()}
    except Exception as e:
        result["status"] = "malformed"
        result["error"] = f"returned mapping was not serializable: {e!r}"
        _write(result)
        return

    result["status"] = "ok"
    result["matching"] = normalized
    _write(result)


def _write(result):
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f)
    print(f"collected -> {OUTPUT_PATH}: status={result['status']}")


if __name__ == "__main__":
    main()
