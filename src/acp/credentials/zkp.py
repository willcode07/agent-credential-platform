"""Mock selective disclosure.

The prover returns the claims the holder chose to reveal and a SHA-256
commitment of the rest. That is a sketch of the *shape* of a presentation,
not a proof. A verifier that does not already know the hidden claims cannot
recompute the commitment, and nothing here is bound to an issuer signature.
Do not use this to decide access to anything real.

How the three families we are choosing among actually work:

* BBS+ (and BBS) signatures sign a list of messages. The holder can later
  derive an unlinkable proof that reveals some messages and hides the
  others, and the verifier checks that proof against the issuer's public
  key. This is the usual fit for "show these claims from a signed
  credential."
* SD-JWT (Selective Disclosure for JWTs) commits to each claim with a
  salted hash inside a signed JWT. The holder sends the JWT plus the
  disclosures they want to open. Verification is ordinary JWT signature
  checking plus hash comparison. It is simpler to deploy than BBS and is
  not unlinkable in the same way.
* zk-SNARK circuits (often written in circom and proved with groth16 or
  similar) can prove a *predicate*, such as ``years_experience >= 5`` or
  a value inside a band, without revealing the value. They cost
  a circuit, a trusted setup or a transparent alternative, and a much
  larger implementation.

# OPEN QUESTION: which scheme is the default? Claim disclosure (BBS+ or
# SD-JWT) and predicate proofs (SNARK) answer different product questions,
# and a market may need both.
"""

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from acp.credentials.models import VerifiableCredential

MOCK_SCHEME = "mock-sha256-commitment"


class DisclosureProof(BaseModel):
    """A non-cryptographic selective-disclosure envelope."""

    scheme: str = MOCK_SCHEME
    credential_id: str
    issuer: str
    holder: str | None = None
    revealed: dict[str, Any]
    hidden_commitment: str
    note: str = (
        "Mock commitment only. A real proof would be a BBS+ derivation, "
        "an SD-JWT presentation, or a SNARK over the signed claims."
    )


class VerificationResult(BaseModel):
    """Outcome of the mock verifier. ``ok`` does not mean cryptographically sound."""

    ok: bool
    reason: str


class SelectiveDisclosureProver:
    """Build a ``DisclosureProof`` from a credential the holder already has."""

    def prove(self, credential: VerifiableCredential, reveal: list[str]) -> DisclosureProof:
        subject = credential.credential_subject
        unknown = [name for name in reveal if name not in subject]
        if unknown:
            raise ValueError(f"claims not in credential {credential.id}: {', '.join(unknown)}")
        revealed = {name: subject[name] for name in reveal}
        hidden = {name: value for name, value in subject.items() if name not in revealed}
        commitment = hashlib.sha256(_canonical(hidden).encode("utf-8")).hexdigest()
        return DisclosureProof(
            credential_id=credential.id,
            issuer=credential.issuer,
            holder=credential.holder_did(),
            revealed=revealed,
            hidden_commitment=commitment,
        )


class SelectiveDisclosureVerifier:
    """Check the shape of a mock proof and whether the issuer is trusted.

    This does not check knowledge of the hidden claims. A real verifier
    checks a signature or a SNARK against the issuer's public key from a
    DID document.
    """

    def verify(
        self,
        proof: DisclosureProof,
        *,
        trusted_issuers: set[str],
    ) -> VerificationResult:
        if proof.issuer not in trusted_issuers:
            return VerificationResult(ok=False, reason="issuer is not trusted")
        if proof.scheme != MOCK_SCHEME:
            return VerificationResult(ok=False, reason="unsupported disclosure scheme")
        if not proof.revealed:
            return VerificationResult(ok=False, reason="no claims revealed")
        if not _is_sha256_hex(proof.hidden_commitment):
            return VerificationResult(ok=False, reason="hidden commitment is malformed")
        return VerificationResult(
            ok=True,
            reason="mock proof is well formed; hidden claims were not checked",
        )


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _is_sha256_hex(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)
