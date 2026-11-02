"""Domain-generic profiles for credential matching.

A market (education, hiring, anything else) maps its revealed claims onto
these types. The matcher does not know what a claim means.

Roles elsewhere in the platform:

* **Issuer** — the DID in ``VerifiableCredential.issuer``.
* **Holder** — the credential subject (``holder_did``). Chooses what to reveal.
* **Verifier** — ``SelectiveDisclosureVerifier``, which checks a disclosure
  before a ``Candidate`` is built.
* **Candidate** — a holder reduced to revealed claims.
* **Opportunity** — a counterparty's configurable claim requirements.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

RequirementOp = Literal["equals", "one_of", "contains", "in_range", "overlaps", "present"]


class ClaimRequirement(BaseModel):
    """One check against a revealed claim.

    ``required`` drops the candidate when the check fails. ``weight`` is added
    to the score when the check passes. ``label`` is the reason text.
    """

    claim: str
    op: RequirementOp
    value: Any = None
    required: bool = True
    weight: int = Field(default=10, ge=0)
    label: str | None = None

    @model_validator(mode="after")
    def value_matches_op(self) -> "ClaimRequirement":
        if self.op == "present":
            return self
        if self.value is None:
            raise ValueError(f"{self.op} requires a value")
        if self.op == "one_of" and not isinstance(self.value, list):
            raise ValueError("one_of requires a list value")
        if self.op in {"in_range", "overlaps"} and _bounds(self.value) is None:
            raise ValueError(f"{self.op} requires a [min, max] value")
        return self


class Candidate(BaseModel):
    """A holder as presented to the matcher. ``claims`` are revealed claims only."""

    id: str
    display_name: str
    claims: dict[str, Any] = Field(default_factory=dict)


class Opportunity(BaseModel):
    """Something a counterparty wants filled, described as claim requirements."""

    id: str
    name: str
    requirements: list[ClaimRequirement] = Field(default_factory=list)


class Match(BaseModel):
    """One scored pairing. ``score`` is the sum of passed weights, not a probability."""

    candidate_id: str
    opportunity_id: str
    score: int
    reasons: list[str]


def _bounds(value: Any) -> tuple[float, float] | None:
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
