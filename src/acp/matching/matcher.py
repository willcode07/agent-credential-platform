"""Match candidates to an opportunity using the opportunity's own requirements.

A required check that fails drops the candidate. The score is the sum of the
weights of checks that passed. There is no learning and no fuzzy comparison.

# OPEN QUESTION: equals, one_of, contains, in_range, overlaps, and present
# are a stand-in for a policy language. A market may instead need a predicate
# that is proved without revealing the value.
# OPEN QUESTION: which claims a counterparty may require is a per-market
# policy. This matcher does not know the market.
"""

from typing import Any

from acp.matching.profiles import Candidate, ClaimRequirement, Match, Opportunity


def match_candidates(opportunity: Opportunity, candidates: list[Candidate]) -> list[Match]:
    """Rank candidates who satisfy ``opportunity``. Highest score first, then id."""
    matches: list[Match] = []
    for candidate in candidates:
        reasons: list[str] = []
        score = 0
        eligible = True
        for requirement in opportunity.requirements:
            passed = _passes(candidate.claims, requirement)
            if passed:
                reasons.append(requirement.label or f"{requirement.claim} {requirement.op}")
                score += requirement.weight
            elif requirement.required:
                eligible = False
                break
        if not eligible:
            continue
        matches.append(
            Match(
                candidate_id=candidate.id,
                opportunity_id=opportunity.id,
                score=score,
                reasons=reasons,
            )
        )
    return sorted(matches, key=lambda item: (-item.score, item.candidate_id))


def _passes(claims: dict[str, Any], requirement: ClaimRequirement) -> bool:
    if requirement.op == "present":
        return requirement.claim in claims
    if requirement.claim not in claims:
        return False
    actual = claims[requirement.claim]
    if requirement.op == "equals":
        return _eq(actual, requirement.value)
    if requirement.op == "one_of":
        return any(_eq(actual, item) for item in requirement.value)
    if requirement.op == "contains":
        return _contains(actual, requirement.value)
    if requirement.op == "in_range":
        return _in_range(actual, requirement.value)
    if requirement.op == "overlaps":
        return _overlaps(actual, requirement.value)
    return False


def _eq(left: Any, right: Any) -> bool:
    if isinstance(left, str) and isinstance(right, str):
        return left.casefold() == right.casefold()
    return left == right


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(actual, list):
        if isinstance(expected, list):
            return any(_contains(actual, item) for item in expected)
        return any(_eq(item, expected) for item in actual)
    if isinstance(actual, str) and isinstance(expected, str):
        return expected.casefold() in actual.casefold()
    return False


def _in_range(actual: Any, bounds: Any) -> bool:
    window = _pair(bounds)
    if window is None:
        return False
    try:
        number = float(actual)
    except (TypeError, ValueError):
        return False
    low, high = window
    return low <= number <= high


def _overlaps(actual: Any, bounds: Any) -> bool:
    left = _pair(actual)
    right = _pair(bounds)
    if left is None or right is None:
        return False
    return left[0] <= right[1] and right[0] <= left[1]


def _pair(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    try:
        low = float(value[0])
        high = float(value[1])
    except (TypeError, ValueError):
        return None
    if low > high:
        return None
    return low, high
