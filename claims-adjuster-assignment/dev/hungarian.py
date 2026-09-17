"""From-scratch Hungarian algorithm (Kuhn-Munkres, O(n^3), potentials +
augmenting path form) for the square minimum-cost assignment problem.
Used to compute the exact-optimal reference for the claims-adjuster
task. Cross-validated against scipy.optimize.linear_sum_assignment in
dev/validate_hungarian.py -- this file itself has no scipy dependency,
matching what ships in solution/policy.py."""

INF = float("inf")


def hungarian_min_cost(cost):
    """cost: square list-of-lists, cost[i][j] = cost of assigning row i
    to column j. Returns (row_to_col, total_cost) where row_to_col[i] is
    the column assigned to row i."""
    n = len(cost)
    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)  # p[j] = row matched to column j (1-indexed), 0 = unmatched
    way = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = -1
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    row_to_col = [0] * (n + 1)
    for j in range(1, n + 1):
        if p[j] != 0:
            row_to_col[p[j]] = j
    total = sum(cost[i - 1][row_to_col[i] - 1] for i in range(1, n + 1) if row_to_col[i] != 0)
    return {i - 1: (row_to_col[i] - 1 if row_to_col[i] else None) for i in range(1, n + 1)}, total


def max_weight_bipartite_matching(rows, cols, value_fn):
    """rows, cols: lists of ids. value_fn(row_id, col_id) -> value in
    cents if the pair is eligible, else None. Returns dict row_id ->
    col_id for the assignment maximizing total value (unmatched rows/
    cols contribute 0).

    Padded to an (n_rows+n_cols) x (n_rows+n_cols) square matrix -- NOT
    just max(n_rows, n_cols) -- so that leaving a row or column unmatched
    is always available at zero cost, even when n_rows == n_cols exactly.
    Padding only up to max(n_rows, n_cols) is a bug: when the two sides
    are equal in size, Hungarian is a pure perfect-matching solver and
    would be forced to match every row to a real column even if a
    particular column has zero eligible rows, producing an ineligible
    (and therefore dropped, value-destroying) assignment instead of
    correctly leaving that column unmatched."""
    n_rows, n_cols = len(rows), len(cols)
    if n_rows == 0 or n_cols == 0:
        return {}
    n = n_rows + n_cols

    BIG = 10 ** 15  # far larger than any real value difference, penalizes ineligible pairs
    cost = [[0.0] * n for _ in range(n)]
    for i in range(n_rows):
        for j in range(n_cols):
            val = value_fn(rows[i], cols[j])
            cost[i][j] = -val if val is not None else BIG
    # cost[i][j] for i>=n_rows or j>=n_cols stays 0.0 (dummy skip options)

    row_to_col_idx, _ = hungarian_min_cost(cost)
    result = {}
    for i in range(n_rows):
        j = row_to_col_idx.get(i)
        if j is not None and j < n_cols:
            result[rows[i]] = cols[j]
    return result
