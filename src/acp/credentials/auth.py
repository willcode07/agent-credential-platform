"""Holder authentication for full credential reads.

Denied unless the caller presents the holder's proof. The mock proof is the
literal string ``holder:<did>``. Anything else, including a missing proof,
is rejected. Counterparties never use this path; they call ``disclose_claims``.

# OPEN QUESTION: replace ``holder:<did>`` with a signature over a challenge
# from a did:key or did:wba verification method.
"""

import hmac


class HolderAuthError(PermissionError):
    """The caller did not prove they are the holder."""


def holder_proof_for(holder_did: str) -> str:
    """The mock proof a holder's own agent would send."""
    return f"holder:{holder_did}"


def require_holder(holder_did: str, holder_proof: str | None) -> None:
    """Raise ``HolderAuthError`` unless ``holder_proof`` matches the holder."""
    if not holder_did or holder_proof is None:
        raise HolderAuthError("holder authentication required")
    expected = holder_proof_for(holder_did).encode()
    actual = holder_proof.encode()
    if len(expected) != len(actual) or not hmac.compare_digest(expected, actual):
        raise HolderAuthError("holder authentication required")
