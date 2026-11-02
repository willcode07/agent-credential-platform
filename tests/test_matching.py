"""Smoke tests for the requirement-driven matcher. No market is assumed."""

import pytest
from pydantic import ValidationError

from acp.matching.matcher import match_candidates
from acp.matching.profiles import Candidate, ClaimRequirement, Opportunity


def _candidate(candidate_id: str, **claims: object) -> Candidate:
    return Candidate(id=candidate_id, display_name=candidate_id, claims=dict(claims))


def _role(*requirements: ClaimRequirement, opportunity_id: str = "role-1") -> Opportunity:
    return Opportunity(id=opportunity_id, name="Role", requirements=list(requirements))


def test_required_claim_must_match_and_weights_sum() -> None:
    opportunity = _role(
        ClaimRequirement(
            claim="skill",
            op="equals",
            value="welding",
            weight=50,
            label="skill matches",
        ),
        ClaimRequirement(
            claim="clearance",
            op="equals",
            value="active",
            weight=20,
            required=False,
            label="clearance disclosed",
        ),
    )
    matches = match_candidates(
        opportunity,
        [
            _candidate("ada", skill="welding", clearance="active"),
            _candidate("ben", skill="welding", clearance="expired"),
            _candidate("cara", skill="painting", clearance="active"),
        ],
    )
    assert [(item.candidate_id, item.score) for item in matches] == [("ada", 70), ("ben", 50)]
    assert matches[0].reasons == ["skill matches", "clearance disclosed"]
    assert matches[0].opportunity_id == "role-1"


def test_missing_required_claim_excludes_the_candidate() -> None:
    opportunity = _role(
        ClaimRequirement(
            claim="skill",
            op="contains",
            value="welding",
            weight=10,
            label="has skill",
        ),
    )
    matches = match_candidates(opportunity, [_candidate("ada", skill=["Welding"])])
    assert len(matches) == 1
    assert match_candidates(opportunity, [_candidate("ben", skill=["painting"])]) == []
    assert match_candidates(opportunity, [_candidate("cara")]) == []


def test_range_and_overlap_are_inclusive() -> None:
    opportunity = _role(
        ClaimRequirement(
            claim="level",
            op="in_range",
            value=[9, 12],
            weight=20,
            label="level in range",
        ),
        ClaimRequirement(
            claim="span",
            op="overlaps",
            value=[9, 12],
            weight=20,
            label="span overlaps",
        ),
    )
    inside = _candidate("ada", level=10, span=[8, 9])
    outside = _candidate("ben", level=4, span=[1, 3])
    matches = match_candidates(opportunity, [inside, outside])
    assert [item.candidate_id for item in matches] == ["ada"]


def test_one_of_and_tie_break_on_id() -> None:
    opportunity = _role(
        ClaimRequirement(claim="site", op="one_of", value=["remote", "anywhere"], weight=10),
    )
    matches = match_candidates(
        opportunity,
        [_candidate("b", site="remote"), _candidate("a", site="anywhere")],
    )
    assert [item.candidate_id for item in matches] == ["a", "b"]


def test_present_and_invalid_requirement_shape() -> None:
    opportunity = _role(
        ClaimRequirement(claim="skill", op="present", weight=1, label="skill present"),
    )
    assert len(match_candidates(opportunity, [_candidate("ada", skill="any")])) == 1
    with pytest.raises(ValidationError):
        ClaimRequirement(claim="level", op="in_range", value=[12, 9])
    with pytest.raises(ValidationError):
        ClaimRequirement(claim="site", op="one_of", value="remote")
