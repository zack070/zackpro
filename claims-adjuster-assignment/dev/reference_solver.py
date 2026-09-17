"""Reference solution: exact optimal per region via the Hungarian
algorithm. This is not a heuristic -- it computes the provably maximum
total captured value for each region's batch, so no other approach can
score higher; it can only be matched (if it happens to find the same
optimum) or fall short."""
import hungarian


def _by_region(adjusters, claims):
    regions = sorted(set(a.region_id for a in adjusters) | set(c.region_id for c in claims))
    for region in regions:
        yield ([a for a in adjusters if a.region_id == region],
               [c for c in claims if c.region_id == region])


def match(adjusters, claims, proficiency):
    matching = {}
    for region_adjusters, region_claims in _by_region(adjusters, claims):
        if not region_adjusters or not region_claims:
            continue
        adjuster_ids = [a.adjuster_id for a in region_adjusters]
        claim_ids = [c.claim_id for c in region_claims]
        adj_by_id = {a.adjuster_id: a for a in region_adjusters}
        claim_by_id = {c.claim_id: c for c in region_claims}

        def value_fn(adjuster_id, claim_id, adj_by_id=adj_by_id, claim_by_id=claim_by_id):
            a = adj_by_id[adjuster_id]
            c = claim_by_id[claim_id]
            if c.claim_type not in a.certifications:
                return None
            prof = proficiency[adjuster_id][c.claim_type]
            return round(c.claim_value_cents * prof)

        result = hungarian.max_weight_bipartite_matching(adjuster_ids, claim_ids, value_fn)
        for adjuster_id, claim_id in result.items():
            matching[claim_id] = adjuster_id
    return matching
