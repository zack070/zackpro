"""Generate a deterministic claims-adjuster batch assignment scenario:
several regions, each with a batch of available adjusters and open claims.
Eligibility (adjuster must hold the claim's required certification) is a
hard binary constraint -- overlapping, not one-to-one. Among eligible
pairs, captured value varies by claim value and adjuster proficiency in
that claim type, so the best adjuster for one claim is often also the
best (or only good) adjuster for other claims -- a genuine joint
assignment conflict, not just a sortable size-matching problem."""
import csv
import os
import random

CLAIM_TYPES = ["auto", "property", "liability", "workers_comp", "marine", "fire"]


def gen_region(rng, region_id, n_adjusters, n_claims):
    adjusters = []
    for a in range(n_adjusters):
        n_certs = rng.randint(2, 3)
        certs = rng.sample(CLAIM_TYPES, n_certs)
        proficiency = {t: round(rng.uniform(0.55, 1.0), 3) for t in certs}
        adjusters.append({
            "adjuster_id": f"{region_id}-ADJ{a+1}",
            "region_id": region_id,
            "certifications": ",".join(certs),
            "proficiency": proficiency,
        })

    claims = []
    for c in range(n_claims):
        ctype = rng.choice(CLAIM_TYPES)
        value_cents = rng.randint(200000, 5000000)  # $2,000 - $50,000
        claims.append({
            "claim_id": f"{region_id}-CLM{c+1}",
            "region_id": region_id,
            "claim_type": ctype,
            "claim_value_cents": value_cents,
        })

    return adjusters, claims


def value_if_eligible(adjuster, claim):
    """Value captured (cents) if this claim is assigned to this adjuster,
    or None if the adjuster lacks the required certification (ineligible
    -- a hard constraint, not a penalty)."""
    prof = adjuster["proficiency"].get(claim["claim_type"])
    if prof is None:
        return None
    return round(claim["claim_value_cents"] * prof)


def gen(seed, out_dir, n_regions=8, adjusters_range=(18, 28), claims_range=(18, 28)):
    rng = random.Random(seed)
    all_adjusters = []
    all_claims = []
    for r in range(n_regions):
        region_id = f"R{r+1}"
        n_a = rng.randint(*adjusters_range)
        n_c = rng.randint(*claims_range)
        adjusters, claims = gen_region(rng, region_id, n_a, n_c)
        all_adjusters.extend(adjusters)
        all_claims.extend(claims)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "adjusters.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["adjuster_id", "region_id", "certifications"])
        for a in all_adjusters:
            w.writerow([a["adjuster_id"], a["region_id"], a["certifications"]])
    with open(os.path.join(out_dir, "claims.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["claim_id", "region_id", "claim_type", "claim_value_cents"])
        for c in all_claims:
            w.writerow([c["claim_id"], c["region_id"], c["claim_type"], c["claim_value_cents"]])

    # Fully disclosed -- the agent needs this to compute value itself,
    # same as payment/invoice amounts were fully disclosed in the prior
    # cash-application-matching task. Nothing is hidden-and-discovered.
    with open(os.path.join(out_dir, "adjuster_proficiency.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["adjuster_id", "claim_type", "proficiency"])
        for a in all_adjusters:
            for t, p in a["proficiency"].items():
                w.writerow([a["adjuster_id"], t, p])

    return all_adjusters, all_claims


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1])
    out_dir = sys.argv[2]
    gen(seed, out_dir)
    print(f"wrote scenario seed={seed} to {out_dir}")
