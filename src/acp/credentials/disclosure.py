"""Pluggable selective disclosure.

SD-JWT is the default. BBS+ and zk-SNARK predicate proofs are named so a
later scheme can be dropped in, and they refuse to run.

Decided 2026-11-02: SD-JWT is the disclosure scheme this platform issues.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from acp.credentials.models import VerifiableCredential
from acp.credentials.sdjwt import SdJwtError, issue_presentation, read_presentation

DEFAULT_SCHEME = "sd-jwt"


class DisclosureProof(BaseModel):
    """A selective-disclosure presentation and the claims it opens."""

    scheme: str
    credential_id: str
    issuer: str
    holder: str | None = None
    revealed: dict[str, Any]
    presentation: str
    note: str = ""


class VerificationResult(BaseModel):
    """Outcome of checking a presentation against a trusted-issuer set."""

    ok: bool
    reason: str


class DisclosureScheme(ABC):
    """One way to present and check a subset of credential claims."""

    name: str

    @abstractmethod
    def present(self, credential: VerifiableCredential, reveal: list[str]) -> DisclosureProof:
        """Build a presentation that opens only ``reveal``."""

    @abstractmethod
    def verify(
        self,
        proof: DisclosureProof,
        *,
        trusted_issuers: set[str],
    ) -> VerificationResult:
        """Check the presentation. ``trusted_issuers`` comes from a rule pack."""


class SdJwtScheme(DisclosureScheme):
    """IETF SD-JWT. Hidden claims are hashes inside the signed JWT, not the presentation."""

    name = DEFAULT_SCHEME

    def present(self, credential: VerifiableCredential, reveal: list[str]) -> DisclosureProof:
        if not reveal:
            raise ValueError("at least one claim must be revealed")
        try:
            presentation, revealed = issue_presentation(
                issuer=credential.issuer,
                holder=credential.holder_did(),
                credential_id=credential.id,
                subject=credential.credential_subject,
                reveal=reveal,
            )
        except SdJwtError as exc:
            raise ValueError(str(exc)) from exc
        return DisclosureProof(
            scheme=self.name,
            credential_id=credential.id,
            issuer=credential.issuer,
            holder=credential.holder_did(),
            revealed=revealed,
            presentation=presentation,
            note="SD-JWT. HS256 under the platform dev issuer key, not a DID key.",
        )

    def verify(
        self,
        proof: DisclosureProof,
        *,
        trusted_issuers: set[str],
    ) -> VerificationResult:
        if proof.issuer not in trusted_issuers:
            return VerificationResult(ok=False, reason="issuer is not trusted")
        if proof.scheme != self.name:
            return VerificationResult(ok=False, reason="unsupported disclosure scheme")
        try:
            opened = read_presentation(proof.presentation)
        except SdJwtError as exc:
            return VerificationResult(ok=False, reason=str(exc))
        if opened["issuer"] != proof.issuer:
            return VerificationResult(ok=False, reason="presentation issuer does not match")
        if opened["credential_id"] != proof.credential_id:
            return VerificationResult(ok=False, reason="presentation credential id does not match")
        if opened["revealed"] != proof.revealed:
            return VerificationResult(
                ok=False,
                reason="revealed claims do not match the presentation",
            )
        if not proof.revealed:
            return VerificationResult(ok=False, reason="no claims revealed")
        return VerificationResult(ok=True, reason="SD-JWT signature and disclosure digests checked")


class _UnimplementedScheme(DisclosureScheme):
    """A named scheme with no implementation."""

    detail: str

    def present(self, credential: VerifiableCredential, reveal: list[str]) -> DisclosureProof:
        raise NotImplementedError(self.detail)

    def verify(
        self,
        proof: DisclosureProof,
        *,
        trusted_issuers: set[str],
    ) -> VerificationResult:
        raise NotImplementedError(self.detail)


class BbsPlusScheme(_UnimplementedScheme):
    """BBS+ can derive an unlinkable proof of a subset of signed messages.

    The verifier would check that derivation against the issuer's public key.
    This platform does not implement it. SD-JWT is the default.
    """

    name = "bbs+"
    detail = "BBS+ is not implemented. SD-JWT is the default disclosure scheme."


class SnarkPredicateScheme(_UnimplementedScheme):
    """A zk-SNARK (circom or otherwise) proves a predicate without revealing the value.

    Example: a number is inside a band. This platform does not ship a circuit.
    SD-JWT reveals the claim instead.
    """

    name = "zk-snark"
    detail = (
        "zk-SNARK predicate proofs are not implemented. "
        "SD-JWT is the default disclosure scheme."
    )


_SCHEMES: dict[str, type[DisclosureScheme]] = {
    SdJwtScheme.name: SdJwtScheme,
    BbsPlusScheme.name: BbsPlusScheme,
    "bbs": BbsPlusScheme,
    SnarkPredicateScheme.name: SnarkPredicateScheme,
    "snark": SnarkPredicateScheme,
}


def scheme_for(name: str | None = None) -> DisclosureScheme:
    """Return a scheme instance. The default is SD-JWT."""
    key = name or DEFAULT_SCHEME
    try:
        return _SCHEMES[key]()
    except KeyError as exc:
        raise ValueError(f"unknown disclosure scheme: {key}") from exc


class SelectiveDisclosureProver:
    """Present claims with the default scheme, or one named by the caller."""

    def __init__(self, scheme: DisclosureScheme | None = None) -> None:
        self.scheme = scheme or scheme_for()

    def prove(self, credential: VerifiableCredential, reveal: list[str]) -> DisclosureProof:
        return self.scheme.present(credential, reveal)


class SelectiveDisclosureVerifier:
    """Check a presentation. The issuer allow-list is supplied by the caller."""

    def __init__(self, scheme: DisclosureScheme | None = None) -> None:
        self.scheme = scheme or scheme_for()

    def verify(
        self,
        proof: DisclosureProof,
        *,
        trusted_issuers: set[str],
    ) -> VerificationResult:
        if proof.scheme != self.scheme.name:
            return VerificationResult(ok=False, reason="unsupported disclosure scheme")
        return self.scheme.verify(proof, trusted_issuers=trusted_issuers)
