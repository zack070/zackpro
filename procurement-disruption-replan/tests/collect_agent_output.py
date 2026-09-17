#!/usr/bin/env python3
"""
Stage 1 (UNTRUSTED). Runs as the unprivileged `runner` user.

Reads the agent's submitted artifact files and does purely mechanical
parsing into a normalized JSON representation -- schema-level only (are the
columns present, are the fields the right type). It makes NO feasibility,
cost, or pass/fail judgment; that is entirely Stage 2's job, run separately
as root against the sealed reference data. This script never imports or
executes anything from the agent's own code, and never judges reward.
"""
import csv
import json
import os

ARTIFACT_DIR = "/app/outputs"
OUT_PATH = "/work/collected.json"

REQUIRED_COLUMNS = {"period", "supplier_id", "product_id", "quantity"}
MAX_ROWS = 10_000  # generous multiple of any legitimate plan (dozens of rows)
MAX_FILE_BYTES = 5_000_000


def parse_orders_file(path):
    result = {"status": "ok", "rows": [], "error": None}
    if not os.path.exists(path):
        result["status"] = "missing"
        return result
    if os.path.getsize(path) > MAX_FILE_BYTES:
        result["status"] = "malformed"
        result["error"] = f"file exceeds {MAX_FILE_BYTES} bytes"
        return result
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
                result["status"] = "malformed"
                result["error"] = f"missing required columns; found {reader.fieldnames}"
                return result
            for raw in reader:
                if len(result["rows"]) >= MAX_ROWS:
                    result["status"] = "malformed"
                    result["error"] = f"more than {MAX_ROWS} rows"
                    return result
                row = {}
                try:
                    row["period"] = int(raw["period"])
                    row["supplier_id"] = str(raw["supplier_id"]).strip()
                    row["product_id"] = str(raw["product_id"]).strip()
                    # keep quantity as the raw string too so stage 2 can
                    # independently re-validate integrality/sign without
                    # trusting this stage's coercion
                    row["quantity_raw"] = raw["quantity"]
                    row["quantity"] = float(raw["quantity"])
                except (ValueError, KeyError, TypeError) as e:
                    result["status"] = "malformed"
                    result["error"] = f"unparseable row {raw!r}: {e}"
                    return result
                result["rows"].append(row)
    except Exception as e:  # noqa: BLE001 - untrusted stage must never crash uncaught
        result["status"] = "malformed"
        result["error"] = str(e)
    return result


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    collected = {
        "baseline": parse_orders_file(os.path.join(ARTIFACT_DIR, "baseline_plan.csv")),
        "replan": parse_orders_file(os.path.join(ARTIFACT_DIR, "replan.csv")),
    }
    with open(OUT_PATH, "w") as f:
        json.dump(collected, f)
    print(f"collected -> {OUT_PATH}: baseline={collected['baseline']['status']} "
          f"({len(collected['baseline']['rows'])} rows), "
          f"replan={collected['replan']['status']} ({len(collected['replan']['rows'])} rows)")


if __name__ == "__main__":
    main()
