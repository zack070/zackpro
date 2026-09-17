# Procurement Planning and Disruption Replan

You are working in `/app` on a procurement planning problem covering eight periods, numbered 1 through 8. The goal is to produce a complete baseline purchasing plan and, after the horizon is advanced, a separate replan for periods 5 through 8.

The authoritative operating rules are in `README.md`. Treat that file and the supplied data as the contract for the task. The incumbent planner and its reports are useful for investigation, but they are not a correctness oracle.

Your baseline submission belongs at `/app/outputs/baseline_plan.csv`. It must contain the columns `period,supplier_id,product_id,quantity`, with one row for each positive order actually placed. Quantities must be positive integers, and zero-quantity combinations should be omitted. The baseline covers all eight periods and must be prepared without knowing the future disruption. Only periods 1 through 4 of this plan are ultimately treated as executed; its later periods are replaced by the replan.

The second file, `/app/outputs/replan.csv`, uses the same columns but contains only new purchasing decisions for periods 5 through 8. Rows for any other period make the submission invalid. The replan is made only after the actual period-4 state and the disruption have been revealed.

There are six products and eight planning periods. Inventory is tracked separately for every product. At the start of each period, arrivals are received before demand is served. For each product and period:

ending_inventory[t] = beginning_inventory[t] + arrivals[t] - demand_served[t]

Beginning inventory in period 1 comes from initial_inventory.csv; thereafter it is the previous period's ending inventory. Inventory may never become negative. There is no backordering, and every unit of demand in every period must be fulfilled. This is a hard 100% service requirement. Total ending inventory across all products must also remain within the constant warehouse capacity in every period.

A new purchase made in period t uses the lead time for its supplier-product pair and arrives at the start of period t + lead_time. Placing an order does not make its quantity available immediately. An order arriving after period 8 cannot help satisfy demand within this horizon.

Every existing purchase order is binding. Its quantity, arrival period, payment due period, and other supplied details must be respected exactly. These commitments cannot be cancelled, reduced, or moved. In particular, their arrival and payment dates are already specified and must not be recalculated from current supplier terms.

New purchases may only use supplier-product pairs listed in supplier_products.csv, and each such order must meet that pair's MOQ. Supplier capacity is shared across all products supplied by that supplier in a period. Both new orders placed during a period and existing purchase orders whose order_period falls in that same period consume the supplier's capacity.

Cash is another hard constraint. For new purchases, payment becomes due at the order period plus the applicable payment term, unless that due date falls after the eight-period horizon. Existing purchase orders are paid on their stated payment_due_period, regardless of when they arrive. Cash is calculated as:

cash_end[t] = cash_begin[t] - payments_due[t] - other_cash_outflows[t]

Cash must never fall below zero. A purchase whose payment has not yet become due is not a cash outflow in the current period.

The cost being minimized is the total cost of new purchasing plus inventory holding:

sum(new quantity × unit price) + sum(ending inventory × holding cost)

Holding cost applies for every product and period in the planning window. Existing purchase orders are sunk and are excluded from this cost calculation.

At some point during the horizon, one supplier becomes unavailable for new purchases for a contiguous range of periods. During that range, no new order may use that supplier and its available new-order capacity is zero. Existing commitments with that supplier continue normally, including their original arrival and payment dates. The identity and affected periods are intentionally not given in advance. To discover them, first submit a feasible baseline and run:

python3 tools/advance_horizon.py --data /app/data --baseline /app/outputs/baseline_plan.csv --out /app/outputs/period4_state.json

This command produces the actual end-of-period-4 state resulting from your own baseline and reveals the disruption information needed for periods 5 through 8. It will refuse to advance an infeasible baseline.

You can use tools/check_plan.py to independently check feasibility. For the baseline:

python3 tools/check_plan.py --data /app/data --plan <csv> --stage baseline

For a replan, the period-4 state is also required:

python3 tools/check_plan.py --data /app/data --plan <csv> --stage replan --state <period4_state.json>

These checks establish feasibility only. They do not establish that the plan is close enough to the required cost.

The baseline is judged on two things: it must satisfy the full contract, and its cost must be at or extremely close to the true minimum achievable cost for the disruption-free eight-period problem. A merely feasible baseline is not sufficient. Since only its first four periods are executed, the later baseline decisions are ultimately superseded by the replan.

The replan is judged from the exact state produced by replaying your own baseline through period 4. That state is important: different valid baselines can leave different inventory, cash, and commitment positions even when their baseline costs are similar. The replan therefore has its own hidden quality requirement and must be at or extremely close to the true minimum cost achievable from your actual period-4 state, while respecting the discovered disruption and every other rule in the contract.

The supplied reports/current_plan.csv and reports/failed_replay.txt show what the incumbent planning process produced and how an independent replay reacts to it. Use them as investigation material, not as an answer to copy. You are free to inspect or replace the incumbent planning approach, but your submitted CSV files are what matter.

The data files describe products and holding costs, suppliers, supplier-product eligibility and purchasing terms, pooled supplier capacities, demand, initial inventory, binding purchase orders, starting cash and fixed cash outflows, warehouse capacity, and the eight-period configuration. Work from those records rather than assuming values that are not present in the data.

Both output files must be well-formed CSVs. Duplicate (period,supplier_id,product_id) rows, missing files, malformed records, unknown combinations, non-integer quantities, zero or negative quantities, and orders outside the allowed period range are invalid. The baseline must stay within periods 1 through 8, while the replan must contain only periods 5 through 8.

Before finishing, independently replay the baseline and the replan against the supplied rules. In particular, check aggregate supplier capacity, product inventory, warehouse capacity, cash timing, existing purchase-order commitments, lead times, MOQs, full demand coverage, and the disruption restriction. Make sure the replan starts from the state generated by your own baseline rather than from an assumed or fixed period-4 state.

You have 14400 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
