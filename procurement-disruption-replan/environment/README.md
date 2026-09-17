# Operational contract

This document is the authoritative definition of how procurement, inventory,
payments, and cash work in this operation. It is the source of truth for
what "correct" means. `planner/planner.py` is the incumbent planning tool;
its output is not guaranteed to satisfy every rule below.

## Horizon

There are exactly 8 periods, numbered 1 through 8. Decisions for a period
are made at the beginning of that period. Demand for a period occurs during
that period, after that period's inventory arrivals.

## Inventory

For each product and period:

    ending_inventory[t] = beginning_inventory[t] + arrivals[t] - demand_served[t]

`beginning_inventory[1]` comes from `data/initial_inventory.csv`.
`beginning_inventory[t] = ending_inventory[t-1]` for every t > 1.

Inventory can never be negative. There is no backorder mechanism: every
unit of demand in every period must be served from that period's beginning
inventory plus that period's arrivals (100% service is required; see
Service below). Ending inventory, summed across all six products, may
never exceed the warehouse capacity in `data/warehouse_capacity.json`
(constant across all periods) in any period.

## Lead time and arrivals

`data/supplier_products.csv` gives a lead time, in whole periods, for every
(supplier, product) pair. A new order placed in period `t` for a pair with
lead time `L` arrives at the beginning of period `t + L`, before that
period's demand is served. An arrival scheduled beyond period 8 falls
outside the horizon and cannot serve any horizon demand.

An order is **not** available to serve demand, and is not part of on-hand
inventory, until it physically arrives in the period computed above. A
purchase order that has been placed but not yet arrived is a distinct state
from inventory on hand.

`data/existing_purchase_orders.csv` lists purchase orders that were placed
before this planning exercise began. Every one is binding: its quantity
cannot be cancelled, reduced, or accelerated. Each row gives its own
explicit `arrival_period` and `payment_due_period` directly -- these are
not derived from the standard per-supplier lead time or payment term
tables, which apply only to new orders you place going forward.

## Service

Every unit of demand in `data/demand.csv`, for every product and period in
the window being planned, must be served. There is no partial-service
allowance and no shortage penalty: a plan that leaves any demand unserved
in any period, for any product, is infeasible.

## Minimum order quantity and eligibility

`data/supplier_products.csv` lists every (supplier, product) pair a
supplier is eligible to fulfill; a supplier not listed for a product cannot
supply it. Every new order you place must meet or exceed that pair's
minimum order quantity (MOQ) -- there is no such thing as a new order
smaller than the MOQ. Order quantities must be non-negative integers.

## Supplier capacity

`data/supplier_capacity.csv` gives each supplier's total purchasable
capacity, in units, per period, pooled across every product that supplier
sells. In any given period, the sum of (a) every new order you place with
that supplier in that period, across all products, and (b) any existing
purchase order in `data/existing_purchase_orders.csv` whose `order_period`
falls in that period, must not exceed that supplier's capacity for that
period. Existing commitments consume capacity in the period they were
originally placed (`order_period`), not the period they arrive.

## Payment and cash

Every (supplier, product) pair in `data/supplier_products.csv` carries a
payment term, in whole periods. For a new order placed in period `t`, the
actual payment -- quantity times that pair's unit price -- is due at the
beginning of period `t + payment_term`, independent of when the order
arrives. If that due period falls beyond period 8, the payment has no
effect on the horizon's cash balance. For an existing purchase order, the
payment amount and due period are exactly what `existing_purchase_orders.csv`
states, independent of the order's arrival period; the two can differ.

For every period:

    cash_end[t] = cash_begin[t] - payments_due[t] - other_cash_outflows[t]

`cash_begin[1]` is `initial_cash` in `data/cash.json`; `other_cash_outflows`
in that same file lists fixed, non-procurement cash outflows by period.
Cash can never go negative in any period. A commitment to pay in the
future (an order that has been placed but whose payment is not yet due) is
not a cash outflow until its due period arrives, and must not be confused
with cash already spent.

## Cost

The cost of a plan is:

    sum over every new order: quantity * unit_price
    + sum over every product and period in the window: ending_inventory * holding_cost_per_unit_per_period

Sunk costs (existing purchase orders, obligations already outstanding
before the window began) are not part of this figure. `data/products.csv`
gives each product's holding cost per unit per period.

## Disruption

At an unspecified point in the horizon, a single supplier may become
temporarily unavailable for new orders for a contiguous span of periods --
existing binding commitments with that supplier are unaffected and remain
exactly as scheduled. During such a span: no new order may be placed with
the disrupted supplier, and that supplier's capacity for new orders in
those periods is zero. This document does not state whether, when, or to
whom this applies in a given run; where it applies, it is disclosed
operationally rather than in this static contract.
