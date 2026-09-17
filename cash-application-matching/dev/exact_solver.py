"""Exact optimal per-customer solver via bitmask DP over subsets of that
customer's payments. Used as ground truth for calibration (not shipped to
the agent) -- confirms the shipped reference/search-based solution reaches
the true optimum, not just "a good score"."""
import itertools
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from engine import Payment, Invoice, TOLERANCE_CENTS


def solve_customer_exact(payments, invoices, tolerance=TOLERANCE_CENTS):
    """payments, invoices: lists for a SINGLE customer. Returns
    (min_cost_cents, matching: dict[payment_id -> invoice_id])."""
    n = len(payments)
    amounts = [p.amount_cents for p in payments]
    full_mask = (1 << n) - 1

    subset_sum = [0] * (1 << n)
    for mask in range(1, 1 << n):
        low = mask & (-mask)
        idx = low.bit_length() - 1
        subset_sum[mask] = subset_sum[mask ^ low] + amounts[idx]

    # dp[used_mask] = (cost_so_far, list of (invoice_id, submask) choices so far)
    dp = {0: (0, [])}
    for inv in invoices:
        new_dp = {}
        for used_mask, (cost_so_far, choices) in dp.items():
            remaining = full_mask & ~used_mask
            submask = remaining
            while True:
                s = subset_sum[submask]
                contribution = max(0, inv.amount_due_cents - s - tolerance)
                new_mask = used_mask | submask
                new_cost = cost_so_far + contribution
                if new_mask not in new_dp or new_dp[new_mask][0] > new_cost:
                    new_dp[new_mask] = (new_cost, choices + [(inv.invoice_id, submask)])
                if submask == 0:
                    break
                submask = (submask - 1) & remaining
        dp = new_dp

    best_mask, best = min(dp.items(), key=lambda kv: kv[1][0] + subset_sum[full_mask & ~kv[0]])
    best_cost, choices = best
    unapplied_mask = full_mask & ~best_mask
    total_cost = best_cost + subset_sum[unapplied_mask]

    matching = {}
    for inv_id, submask in choices:
        m = submask
        while m:
            low = m & (-m)
            idx = low.bit_length() - 1
            matching[payments[idx].payment_id] = inv_id
            m ^= low
    return total_cost, matching


def solve_exact(payments, invoices, tolerance=TOLERANCE_CENTS):
    """Full scenario: partitions by customer_id and solves each independently
    (legal, since cross-customer assignments are never allowed anyway)."""
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    total_cost = 0
    matching = {}
    for cust in customers:
        cust_payments = [p for p in payments if p.customer_id == cust]
        cust_invoices = [i for i in invoices if i.customer_id == cust]
        if not cust_payments:
            continue
        cost, m = solve_customer_exact(cust_payments, cust_invoices, tolerance)
        total_cost += cost
        matching.update(m)
    return total_cost, matching
