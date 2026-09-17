# Fact sheet for instruction.md

Every fact below is something the sealed verifier actually depends on, or a
mechanical constraint on the instruction file itself. Write instruction.md
as a natural professional brief covering these; do not turn it into a
bullet-list transcription of this document. Nothing here should be copied
verbatim as prose -- this is the checklist to write from and fact-check
against, not a draft.

## Mechanical requirements (non-negotiable)

- Closing paragraph, exact, nothing after it, one trailing newline:
  `You have 14400 seconds to complete this task. Do not cheat by using
  online solutions or hints specific to this task.`
  (14400 must match `[agent].timeout_sec` in task.toml -- currently 14400.)
- Keep the whole file well under ~10,000 characters.
- Do not name PuLP, CBC, or any specific solver/library. They may be
  available in the environment for the agent to discover; do not
  pre-announce them.
- Do not state the specific disrupted supplier, the specific disrupted
  periods, the exact cost thresholds/tolerance value, or the specific bugs
  in planner.py. Everything else the verifier checks must be stated.

## What the agent is given (all under /app)

- `README.md` -- the authoritative operational contract (see below; this
  is the source of truth the verifier implements exactly).
- `data/products.csv` -- product_id, holding_cost_per_unit_per_period ($/unit/period).
- `data/suppliers.csv` -- supplier_id, description.
- `data/supplier_products.csv` -- supplier_id, product_id, unit_price,
  lead_time_periods, moq, payment_term_periods. Defines which
  (supplier, product) pairs are eligible at all.
- `data/supplier_capacity.csv` -- supplier_id, period, capacity_units.
  Capacity is pooled across every product that supplier sells, per period.
- `data/demand.csv` -- product_id, period, demand_units. Must be served in full.
- `data/initial_inventory.csv` -- product_id, quantity on hand at the start of period 1.
- `data/existing_purchase_orders.csv` -- po_id, supplier_id, product_id,
  quantity, order_period, arrival_period, unit_price, payment_due_period.
  Every row is binding and cannot be changed. order_period/arrival_period/
  payment_due_period are each given directly and independently -- they are
  NOT derived from supplier_products.csv's lead_time/payment_term for these
  rows (those columns apply only to new orders the agent places).
- `data/cash.json` -- `initial_cash` (cash at the start of period 1) and
  `other_cash_outflows` (period -> fixed non-procurement cash outflow).
- `data/warehouse_capacity.json` -- `capacity_units`, constant across all 8 periods.
- `data/config.json` -- informational (`num_periods`: 8, `currency`: "USD").
- `planner/planner.py` -- the incumbent planning tool. Runnable; not
  guaranteed correct. The agent is never required to use, fix, or even
  read it -- grading only looks at the submitted output files.
- `reports/current_plan.csv` -- the incumbent planner's current output.
- `reports/failed_replay.txt` -- an independent replay of that plan against
  the contract, showing symptoms (which product/period/requirement failed)
  without stating why.
- `tools/check_plan.py` -- validates a candidate plan's feasibility against
  the same rules the verifier checks (not the same as passing/optimal; it
  never reveals a cost threshold). Usage:
  `python3 tools/check_plan.py --data /app/data --plan <csv> --stage {baseline|replan} [--state <period4_state.json>]`
  (`--state` is required for `--stage replan`.)
- `tools/advance_horizon.py` -- the only way to learn (a) the real
  end-of-period-4 state resulting from the agent's OWN submitted baseline,
  and (b) the specific disruption (which supplier, which periods) that
  applies to periods 5-8. Refuses to run if the baseline's periods 1-4
  are not themselves feasible. Usage:
  `python3 tools/advance_horizon.py --data /app/data --baseline /app/outputs/baseline_plan.csv --out /app/outputs/period4_state.json`

## Required outputs

- `/app/outputs/baseline_plan.csv` -- columns `period,supplier_id,product_id,quantity`.
  One row per (period, supplier, product) actually ordered; omit
  zero-quantity combinations. Quantities are positive integers. Covers
  periods 1-8, as a complete plan made before anything is known about any
  disruption.
- `/app/outputs/replan.csv` -- same schema. Contains ONLY new decisions for
  periods 5-8, made after the real end-of-period-4 state and the
  disruption are known. It cannot alter periods 1-4 in any way -- there is
  no field for that, and any row outside periods 5-8 is rejected outright,
  not merely ignored.

## Authoritative semantics (the contract; state all of this)

Everything in `environment/README.md` as currently written is graded
exactly as stated there. In particular, make sure the instruction states:

- 8 periods, numbered 1-8. Arrivals happen before that period's demand is served.
- `ending_inventory[t] = beginning_inventory[t] + arrivals[t] - demand_served[t]`;
  beginning_inventory[1] from initial_inventory.csv; beginning[t] = ending[t-1] otherwise.
- Inventory can never be negative; there is no backorder mechanism -- every
  unit of demand, every period, every product, must be served (100% service
  is a hard requirement, not a target).
- Total ending inventory across all 6 products, every period, must not
  exceed the (constant) warehouse capacity.
- A new order placed in period t with lead time L (from supplier_products.csv)
  arrives at the start of period t+L; an arrival beyond period 8 cannot
  serve any horizon demand. An order is not available to serve demand and
  is not on-hand inventory until it physically arrives -- being placed is
  not the same as being received.
- Existing purchase orders are binding as given (quantity, arrival_period,
  payment_due_period cannot be changed, cancelled, or reduced).
- A new order must be at least its (supplier, product) pair's MOQ, and only
  eligible (supplier, product) pairs (from supplier_products.csv) may be used.
- Supplier capacity is pooled per supplier per period across every product
  it sells; new orders in that period plus any existing purchase order
  whose order_period falls in that period both count against it.
- New-order payment is due at order_period + payment_term (dropped if past
  period 8); existing-PO payment is due exactly at its stated
  payment_due_period, independent of its arrival_period -- the two can differ.
- `cash_end[t] = cash_begin[t] - payments_due[t] - other_cash_outflows[t]`;
  cash can never go negative in any period. A placed-but-not-yet-due
  payment is not a cash outflow yet.
- Cost = sum(new order quantity * unit_price) + sum(ending_inventory *
  holding_cost_per_unit_per_period, every product and period in the window).
  Existing/sunk purchase orders are not part of this figure.
- At some point in the horizon, one supplier becomes unavailable for NEW
  orders for a contiguous span of periods: no new order with it during that
  span, and its new-order capacity is zero then; its existing binding
  commitments are unaffected (arrive and are paid exactly as scheduled).
  State that this can only be discovered by running advance_horizon.py
  against your own submitted baseline -- the instruction should say a
  disruption occurs and how to find out its specifics, not what they are.

## What is graded (state that these exist; do not give numbers)

- Baseline (periods 1-8, disruption-free by construction since it predates
  any disruption): must be feasible under every rule above, AND there is a
  hidden quality bar -- it must be at or extremely close to the true
  minimum achievable cost, not merely "a" feasible plan. Only its periods
  1-4 are treated as actually executed; periods 5-8 of it are a forecast
  that is entirely superseded by the replan.
- Replan (periods 5-8): first, your OWN baseline's periods 1-4 are replayed
  to get the real state (this must itself be feasible on its own terms).
  Then the replan is replayed from that exact state with the disruption
  applied, under every rule above plus "no new order with the disrupted
  supplier during its disrupted periods." It also has a hidden cost bar:
  it must be at or extremely close to the true minimum cost achievable from
  YOUR OWN actual end-of-period-4 state -- state plainly that this bar
  depends on the agent's own baseline choice (since more than one baseline
  can be equally cost-optimal but leave a different real state behind),
  not on a single fixed number.
- Malformed CSV, missing files, duplicate (period,supplier,product) rows,
  non-integer or non-positive quantities, and orders outside the relevant
  period window (1-8 for the baseline, 5-8 for the replan) are all treated
  as invalid, not silently ignored.

## Things this instruction should NOT say

- Do not name a solver or library.
- Do not state which supplier is disrupted or when.
- Do not state the exact minimum-cost figures or the numeric tolerance.
- Do not describe planner.py's specific bugs or tell the agent what is
  wrong with it -- only that its output should not be trusted without
  independent verification (reports/failed_replay.txt already demonstrates
  this without explaining why).
