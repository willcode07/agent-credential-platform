"""Selective disclosure entry points.

SD-JWT is the default scheme (decided 2026-11-02). BBS+ and zk-SNARK
predicate proofs are stubs behind the same interface. The implementation
lives in ``acp.credentials.disclosure`` and ``acp.credentials.sdjwt``.
"""

from acp.credentials.disclosure import (
    DEFAULT_SCHEME,
    BbsPlusScheme,
    DisclosureProof,
    DisclosureScheme,
    SdJwtScheme,
    SelectiveDisclosureProver,
    SelectiveDisclosureVerifier,
    SnarkPredicateScheme,
    VerificationResult,
    scheme_for,
)

__all__ = [
    "DEFAULT_SCHEME",
    "BbsPlusScheme",
    "DisclosureProof",
    "DisclosureScheme",
    "SdJwtScheme",
    "SelectiveDisclosureProver",
    "SelectiveDisclosureVerifier",
    "SnarkPredicateScheme",
    "VerificationResult",
    "scheme_for",
]
