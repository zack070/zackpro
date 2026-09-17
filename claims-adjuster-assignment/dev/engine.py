"""
Authoritative scoring engine for the claims-adjuster batch assignment task.

Rules (all disclosed to the agent -- see environment/engine/README.md):
  - Each claim may be assigned to AT MOST ONE adjuster.
  - Each adjuster may be assigned AT MOST ONE claim in this batch.
  - An adjuster may only be assigned a claim whose claim_type is among
    that adjuster's certifications. An attempt to assign an ineligible
    pair is dropped (treated as unassigned), not an error.
  - An adjuster may only be assigned a claim in their OWN region_id. A
    cross-region assignment is dropped, not an error.
  - Captured value for an assigned (adjuster, claim) pair is
    claim_value_cents * that adjuster's proficiency in the claim's type,
    rounded to the nearest cent. Proficiency is fully disclosed data
    (adjuster_proficiency.csv), same as every other input field -- there
    is nothing hidden that must be discovered by trial.
  - Score (higher is better): total captured value across all assigned
    pairs. An unassigned claim contributes 0 (not a penalty) -- leaving
    a claim unassigned is always legal, just captures no value for it.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Adjuster:
    adjuster_id: str
    region_id: str
    certifications: frozenset


@dataclass(frozen=True)
class Claim:
    claim_id: str
    region_id: str
    claim_type: str
    claim_value_cents: int


@dataclass
class ScoreResult:
    total_value_cents: int
    claims_assigned: int
    total_claims: int
    dropped_assignments: List[str]


def load_scenario(data_dir: str):
    def read_csv(name):
        with open(os.path.join(data_dir, name), newline="") as f:
            return list(csv.DictReader(f))

    adjusters = [
        Adjuster(
            adjuster_id=r["adjuster_id"],
            region_id=r["region_id"],
            certifications=frozenset(r["certifications"].split(",")),
        )
        for r in read_csv("adjusters.csv")
    ]
    claims = [
        Claim(
            claim_id=r["claim_id"],
            region_id=r["region_id"],
            claim_type=r["claim_type"],
            claim_value_cents=int(r["claim_value_cents"]),
        )
        for r in read_csv("claims.csv")
    ]
    return adjusters, claims


def load_proficiency(data_dir: str) -> Dict[str, Dict[str, float]]:
    """adjuster_id -> {claim_type: proficiency}. Fully disclosed data,
    loaded from adjuster_proficiency.csv (same file the agent has)."""
    prof: Dict[str, Dict[str, float]] = {}
    with open(os.path.join(data_dir, "adjuster_proficiency.csv"), newline="") as f:
        for r in csv.DictReader(f):
            prof.setdefault(r["adjuster_id"], {})[r["claim_type"]] = float(r["proficiency"])
    return prof


def score_matching(
    adjusters: List[Adjuster],
    claims: List[Claim],
    proficiency: Dict[str, Dict[str, float]],
    matching: Dict[str, Optional[str]],
) -> ScoreResult:
    """matching: dict mapping claim_id -> adjuster_id (or None / absent
    means unassigned). Any claim_id not real, any adjuster_id not real,
    a cross-region assignment, an ineligible (uncertified) assignment, or
    an adjuster used more than once is dropped silently (treated as
    unassigned) -- it does not raise and does not affect other
    assignments."""
    adjusters_by_id = {a.adjuster_id: a for a in adjusters}
    claims_by_id = {c.claim_id: c for c in claims}

    used_adjusters = set()
    dropped: List[str] = []
    total_value = 0
    claims_assigned = 0

    seen_claims = set()
    for claim_id, adjuster_id in matching.items():
        if claim_id in seen_claims:
            continue
        seen_claims.add(claim_id)

        c = claims_by_id.get(claim_id)
        if c is None:
            dropped.append(f"{claim_id}: not a real claim_id")
            continue
        if adjuster_id is None:
            continue  # explicitly left unassigned, not a drop

        a = adjusters_by_id.get(adjuster_id)
        if a is None:
            dropped.append(f"{claim_id}->{adjuster_id}: not a real adjuster_id")
            continue
        if a.region_id != c.region_id:
            dropped.append(f"{claim_id}->{adjuster_id}: cross-region assignment")
            continue
        if c.claim_type not in a.certifications:
            dropped.append(f"{claim_id}->{adjuster_id}: adjuster not certified for {c.claim_type}")
            continue
        if adjuster_id in used_adjusters:
            dropped.append(f"{claim_id}->{adjuster_id}: adjuster already assigned another claim")
            continue

        prof = proficiency[adjuster_id][c.claim_type]
        total_value += round(c.claim_value_cents * prof)
        used_adjusters.add(adjuster_id)
        claims_assigned += 1

    return ScoreResult(
        total_value_cents=total_value,
        claims_assigned=claims_assigned,
        total_claims=len(claims),
        dropped_assignments=dropped,
    )
