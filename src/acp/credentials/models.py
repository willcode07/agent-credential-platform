"""Pydantic models for a narrow slice of the W3C VC Data Model 2.0.

The field names follow the data model (``@context``, ``credentialSubject``,
``validFrom``). This is not a full VC implementation: there is no proof
block, no status list, and no JSON-LD processing.

# OPEN QUESTION: adopt VC Data Model 2.0 only, or also accept JWT/SD-JWT
# credentials that do not carry an ``@context``?
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VerifiableCredential(BaseModel):
    """A credential as stored by the holder. Claims live in ``credential_subject``."""

    model_config = ConfigDict(populate_by_name=True)

    context: list[str] = Field(
        default_factory=lambda: ["https://www.w3.org/ns/credentials/v2"],
        alias="@context",
    )
    id: str
    type: list[str] = Field(default_factory=lambda: ["VerifiableCredential"])
    issuer: str
    valid_from: str | None = Field(default=None, alias="validFrom")
    credential_subject: dict[str, Any] = Field(alias="credentialSubject")

    def holder_did(self) -> str | None:
        subject_id = self.credential_subject.get("id")
        if isinstance(subject_id, str) and subject_id:
            return subject_id
        return None

    def summary(self) -> dict[str, str]:
        """Identifiers only. Claim values stay out of list responses."""
        return {
            "id": self.id,
            "issuer": self.issuer,
            "holder": self.holder_did() or "",
            "types": ",".join(self.type),
        }
