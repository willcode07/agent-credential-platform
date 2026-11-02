"""DID resolver interface for did:key, did:web, and did:wba.

``did:key`` is decoded offline into a verification method. ``did:web`` and
``did:wba`` only build the HTTPS URL the method specifies and return a
document if one was cached with ``register``. They do not perform a GET and
they do not verify a DID-document proof.

``did:example`` remains a local stand-in for sample issuers. It is not a
fourth production method.

Trusted issuer DIDs are not listed here. A rule pack names them per
credential type.

# OPEN QUESTION: fetch did:web and did:wba documents over HTTPS and verify
# the document proof. Expand a did:key multikey into a JWK the SD-JWT
# verifier can use.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
# multicodec ed25519-pub, varint 0xed, encoded as two bytes.
_ED25519_PREFIX = bytes((0xED, 0x01))


class DIDNotFoundError(LookupError):
    """Raised when a resolver has no document for a DID."""


class DIDDocument(BaseModel):
    """The handful of DID-document fields this scaffold actually reads."""

    id: str
    verification_method: list[dict[str, str]] = Field(default_factory=list)
    service: list[dict[str, str]] = Field(default_factory=list)


class DIDResolver(ABC):
    """Resolve a DID to a document. Implementations may cache or fetch."""

    @abstractmethod
    def resolve(self, did: str) -> DIDDocument:
        """Return the document for ``did`` or raise ``DIDNotFoundError``."""


class DIDMethodResolver(DIDResolver):
    """Dispatch did:key, did:web, did:wba, and cached or did:example documents."""

    def __init__(self, documents: dict[str, DIDDocument] | None = None) -> None:
        self._documents = dict(documents or {})

    def register(self, document: DIDDocument) -> None:
        self._documents[document.id] = document

    def resolve(self, did: str) -> DIDDocument:
        if not did.startswith("did:"):
            raise DIDNotFoundError(f"not a DID: {did}")
        cached = self._documents.get(did)
        if cached is not None:
            return cached
        if did.startswith("did:key:"):
            return resolve_did_key(did)
        if did.startswith("did:web:"):
            url = did_web_url(did)
            raise DIDNotFoundError(f"no cached did:web document for {did}; would GET {url}")
        if did.startswith("did:wba:"):
            url = did_wba_url(did)
            raise DIDNotFoundError(f"no cached did:wba document for {did}; would GET {url}")
        if did.startswith("did:example:"):
            return _example_document(did)
        raise DIDNotFoundError(did)


# Existing call sites use this name. It is the method resolver, not a fake.
MockDIDResolver = DIDMethodResolver


def did_web_url(did: str) -> str:
    """HTTPS URL of a did:web document. Does not fetch it.

    ``did:web:example.com`` becomes ``https://example.com/.well-known/did.json``.
    A path (``did:web:example.com:user:alice``) becomes
    ``https://example.com/user/alice/did.json``. ``%3A`` in the host is a port.
    """
    return _https_did_url(did, "did:web:")


def did_wba_url(did: str) -> str:
    """HTTPS URL of a did:wba document, using the same path rules as did:web.

    ``did:wba:example.com`` becomes ``https://example.com/.well-known/did.json``.
    """
    return _https_did_url(did, "did:wba:")


def resolve_did_key(did: str) -> DIDDocument:
    """Build a DID document from a did:key multibase identifier. No network."""
    if not did.startswith("did:key:z"):
        raise DIDNotFoundError(f"not a did:key: {did}")
    multibase = did.removeprefix("did:key:")
    try:
        raw = _b58decode(multibase[1:])
    except ValueError as exc:
        raise DIDNotFoundError(f"did:key multibase is not base58btc: {did}") from exc
    if len(raw) < 3:
        raise DIDNotFoundError(f"did:key key material is too short: {did}")
    key_type = "Ed25519VerificationKey2020" if raw.startswith(_ED25519_PREFIX) else "Multikey"
    return DIDDocument(
        id=did,
        verification_method=[
            {
                "id": f"{did}#{multibase}",
                "type": key_type,
                "controller": did,
                "publicKeyMultibase": multibase,
            }
        ],
    )


def _https_did_url(did: str, prefix: str) -> str:
    if not did.startswith(prefix):
        raise DIDNotFoundError(f"not a {prefix[:-1]} DID: {did}")
    specific = did[len(prefix) :]
    if not specific or specific.startswith(":") or specific.endswith(":"):
        raise DIDNotFoundError(f"DID is missing a host: {did}")
    parts = specific.split(":")
    host = parts[0].replace("%3A", ":").replace("%3a", ":")
    if not host:
        raise DIDNotFoundError(f"DID is missing a host: {did}")
    if len(parts) == 1:
        path = "/.well-known/did.json"
    else:
        path = "/" + "/".join(parts[1:]) + "/did.json"
    return f"https://{host}{path}"


def _example_document(did: str) -> DIDDocument:
    return DIDDocument(
        id=did,
        verification_method=[
            {
                "id": f"{did}#key-1",
                "type": "JsonWebKey2020",
                "controller": did,
            }
        ],
    )


def _b58decode(data: str) -> bytes:
    number = 0
    for char in data:
        index = _BASE58.find(char)
        if index < 0:
            raise ValueError(char)
        number = number * 58 + index
    pad = 0
    for char in data:
        if char != "1":
            break
        pad += 1
    if number == 0:
        body = b""
    else:
        body = number.to_bytes((number.bit_length() + 7) // 8, "big")
    return b"\x00" * pad + body
