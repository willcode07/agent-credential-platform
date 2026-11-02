"""DID method helpers. Resolvers do not fetch the network."""

import pytest

from acp.credentials.did import (
    DIDMethodResolver,
    DIDNotFoundError,
    did_wba_url,
    did_web_url,
    resolve_did_key,
)

_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def test_did_urls_follow_the_method_path_rules() -> None:
    assert did_web_url("did:web:example.com") == "https://example.com/.well-known/did.json"
    alice = did_web_url("did:web:example.com:user:alice")
    assert alice == "https://example.com/user/alice/did.json"
    assert did_wba_url("did:wba:example.com") == "https://example.com/.well-known/did.json"
    port = did_web_url("did:web:example.com%3A8443")
    assert port == "https://example.com:8443/.well-known/did.json"


def test_did_key_decodes_ed25519_offline() -> None:
    raw = bytes((0xED, 0x01)) + b"\x11" * 32
    multibase = "z" + _b58encode(raw)
    did = f"did:key:{multibase}"
    method = resolve_did_key(did).verification_method[0]
    assert method["type"] == "Ed25519VerificationKey2020"
    assert method["publicKeyMultibase"] == multibase
    assert method["controller"] == did
    assert method["id"] == f"{did}#{multibase}"


def test_uncached_did_wba_names_the_url_it_would_fetch() -> None:
    with pytest.raises(DIDNotFoundError, match="https://example.com/.well-known/did.json"):
        DIDMethodResolver().resolve("did:wba:example.com")


def _b58encode(data: bytes) -> str:
    number = int.from_bytes(data, "big")
    chars: list[str] = []
    while number:
        number, remainder = divmod(number, 58)
        chars.append(_BASE58[remainder])
    pad = len(data) - len(data.lstrip(b"\x00"))
    return ("1" * pad) + "".join(reversed(chars))
