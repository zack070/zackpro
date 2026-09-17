"""Adversarial probe battery: every plausible one-at-a-time greedy
policy for this batch assignment problem, crossed over ordering and
tie-break dimensions."""


def _by_region(adjusters, claims):
    regions = sorted(set(a.region_id for a in adjusters) | set(c.region_id for c in claims))
    for region in regions:
        yield ([a for a in adjusters if a.region_id == region],
               [c for c in claims if c.region_id == region])


def _value(a, c, proficiency):
    if c.claim_type not in a.certifications:
        return None
    return round(c.claim_value_cents * proficiency[a.adjuster_id][c.claim_type])


def greedy_by_claim_value_desc_best_adjuster(adjusters, claims, proficiency):
    """Process claims highest-value-first; assign each to whichever
    eligible, still-available adjuster gives the highest captured value."""
    matching = {}
    for region_a, region_c in _by_region(adjusters, claims):
        available = set(a.adjuster_id for a in region_a)
        adj_by_id = {a.adjuster_id: a for a in region_a}
        for c in sorted(region_c, key=lambda c: -c.claim_value_cents):
            best_aid, best_val = None, None
            for aid in available:
                v = _value(adj_by_id[aid], c, proficiency)
                if v is not None and (best_val is None or v > best_val):
                    best_aid, best_val = aid, v
            if best_aid is not None:
                matching[c.claim_id] = best_aid
                available.discard(best_aid)
    return matching


def greedy_by_claim_value_asc_best_adjuster(adjusters, claims, proficiency):
    matching = {}
    for region_a, region_c in _by_region(adjusters, claims):
        available = set(a.adjuster_id for a in region_a)
        adj_by_id = {a.adjuster_id: a for a in region_a}
        for c in sorted(region_c, key=lambda c: c.claim_value_cents):
            best_aid, best_val = None, None
            for aid in available:
                v = _value(adj_by_id[aid], c, proficiency)
                if v is not None and (best_val is None or v > best_val):
                    best_aid, best_val = aid, v
            if best_aid is not None:
                matching[c.claim_id] = best_aid
                available.discard(best_aid)
    return matching


def greedy_most_constrained_claim_first(adjusters, claims, proficiency):
    """Process claims that have the FEWEST eligible remaining adjusters
    first (a classic 'most-constrained-variable' heuristic), assigning
    each to its best available eligible adjuster."""
    matching = {}
    for region_a, region_c in _by_region(adjusters, claims):
        available = set(a.adjuster_id for a in region_a)
        adj_by_id = {a.adjuster_id: a for a in region_a}
        remaining = list(region_c)
        while remaining:
            def n_eligible(c):
                return sum(1 for aid in available if _value(adj_by_id[aid], c, proficiency) is not None)
            remaining.sort(key=n_eligible)
            c = remaining.pop(0)
            best_aid, best_val = None, None
            for aid in available:
                v = _value(adj_by_id[aid], c, proficiency)
                if v is not None and (best_val is None or v > best_val):
                    best_aid, best_val = aid, v
            if best_aid is not None:
                matching[c.claim_id] = best_aid
                available.discard(best_aid)
    return matching


def greedy_global_best_pair_first(adjusters, claims, proficiency):
    """Repeatedly pick the single highest-value ELIGIBLE (adjuster,
    claim) pair remaining anywhere, assign it, remove both, repeat --
    a natural-seeming 'take the best deal available' greedy."""
    matching = {}
    for region_a, region_c in _by_region(adjusters, claims):
        pairs = []
        for a in region_a:
            for c in region_c:
                v = _value(a, c, proficiency)
                if v is not None:
                    pairs.append((v, a.adjuster_id, c.claim_id))
        pairs.sort(key=lambda t: -t[0])
        used_a, used_c = set(), set()
        for v, aid, cid in pairs:
            if aid in used_a or cid in used_c:
                continue
            matching[cid] = aid
            used_a.add(aid)
            used_c.add(cid)
    return matching


def greedy_by_adjuster_first_best_claim(adjusters, claims, proficiency):
    """Process ADJUSTERS in arbitrary (id) order; each picks its best
    remaining eligible claim."""
    matching = {}
    for region_a, region_c in _by_region(adjusters, claims):
        available_claims = {c.claim_id: c for c in region_c}
        for a in sorted(region_a, key=lambda a: a.adjuster_id):
            best_cid, best_val = None, None
            for cid, c in available_claims.items():
                v = _value(a, c, proficiency)
                if v is not None and (best_val is None or v > best_val):
                    best_cid, best_val = cid, v
            if best_cid is not None:
                matching[best_cid] = a.adjuster_id
                del available_claims[best_cid]
    return matching


def greedy_random_order_first_fit(adjusters, claims, proficiency, seed=1):
    import random
    rng = random.Random(seed)
    matching = {}
    for region_a, region_c in _by_region(adjusters, claims):
        available = set(a.adjuster_id for a in region_a)
        adj_by_id = {a.adjuster_id: a for a in region_a}
        order = list(region_c)
        rng.shuffle(order)
        for c in order:
            best_aid, best_val = None, None
            for aid in available:
                v = _value(adj_by_id[aid], c, proficiency)
                if v is not None and (best_val is None or v > best_val):
                    best_aid, best_val = aid, v
            if best_aid is not None:
                matching[c.claim_id] = best_aid
                available.discard(best_aid)
    return matching


ALL_PROBES = {
    "claim_value_desc_best_adjuster": greedy_by_claim_value_desc_best_adjuster,
    "claim_value_asc_best_adjuster": greedy_by_claim_value_asc_best_adjuster,
    "most_constrained_claim_first": greedy_most_constrained_claim_first,
    "global_best_pair_first": greedy_global_best_pair_first,
    "adjuster_first_best_claim": greedy_by_adjuster_first_best_claim,
    "random_order_first_fit": greedy_random_order_first_fit,
}


def kitchen_sink(adjusters, claims, proficiency):
    """Run every probe, keep the best PER REGION (mixing winners across
    regions is legal -- claim/adjuster ids are region-scoped)."""
    from collections import defaultdict
    import engine as engine_mod

    all_results = {name: fn(adjusters, claims, proficiency) for name, fn in ALL_PROBES.items()}
    by_region_claims = defaultdict(list)
    for c in claims:
        by_region_claims[c.region_id].append(c.claim_id)

    best_matching = {}
    for region, claim_ids in by_region_claims.items():
        best_val, best_sub = -1, {}
        for name, m in all_results.items():
            sub = {cid: m[cid] for cid in claim_ids if cid in m}
            r = engine_mod.score_matching(adjusters, claims, proficiency, sub)
            if r.total_value_cents > best_val:
                best_val, best_sub = r.total_value_cents, sub
        best_matching.update(best_sub)
    return best_matching
