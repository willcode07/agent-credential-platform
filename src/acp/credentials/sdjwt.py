"""Minimal SD-JWT presentations (IETF selective-disclosure JWT).

A disclosure is base64url(JSON ``[salt, name, value]``). Its digest is
base64url(SHA-256 of that ASCII disclosure). The issuer JWT carries every
digest in ``_sd`` and does not carry the claim values. The holder appends
only the disclosures they choose to reveal. There is no key-binding JWT.

The signature is HS256 under a process-wide dev key. That makes the
presentation checkable in tests. It is not the issuer's DID key.

# OPEN QUESTION: sign with a verification method resolved from the issuer
# DID (did:web, did:key, or did:wba) instead of ``DEV_ISSUER_KEY``, and
# split issuance from presentation. ``disclose_claims`` currently does both.
"""

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any

DEV_ISSUER_KEY = b"acp-dev-issuer-key-not-for-production"
SD_ALG = "sha-256"


class SdJwtError(ValueError):
    """The presentation is not a valid SD-JWT under the dev issuer key."""


def issue_presentation(
    *,
    issuer: str,
    holder: str | None,
    credential_id: str,
    subject: dict[str, Any],
    reveal: list[str],
) -> tuple[str, dict[str, Any]]:
    """Sign an SD-JWT for every subject claim and disclose only ``reveal``."""
    unknown = [name for name in reveal if name not in subject]
    if unknown:
        raise SdJwtError(f"claims not in credential {credential_id}: {', '.join(unknown)}")
    by_name: dict[str, str] = {}
    digests: list[str] = []
    for name, value in subject.items():
        disclosure = _disclosure(name, value)
        by_name[name] = disclosure
        digests.append(_digest(disclosure))
    payload = {
        "_sd": digests,
        "_sd_alg": SD_ALG,
        "credential_id": credential_id,
        "iss": issuer,
        "sub": holder,
    }
    token = _sign(payload)
    selected = [by_name[name] for name in reveal]
    presentation = token + "~" + "~".join(selected) + "~"
    revealed = {name: subject[name] for name in reveal}
    return presentation, revealed


def read_presentation(presentation: str) -> dict[str, Any]:
    """Verify the dev-key signature and return the claims the holder opened."""
    if not presentation.endswith("~"):
        raise SdJwtError("SD-JWT presentation must end with '~' when there is no key binding")
    pieces = presentation[:-1].split("~")
    if not pieces or not pieces[0]:
        raise SdJwtError("SD-JWT presentation is missing the issuer JWT")
    token, *disclosures = pieces
    payload = _verify(token)
    if payload.get("_sd_alg") != SD_ALG:
        raise SdJwtError("unsupported _sd_alg")
    committed = payload.get("_sd")
    if not isinstance(committed, list):
        raise SdJwtError("SD-JWT payload is missing _sd")
    if len(disclosures) != len(set(disclosures)):
        raise SdJwtError("duplicate disclosure")
    revealed: dict[str, Any] = {}
    for disclosure in disclosures:
        digest = _digest(disclosure)
        if digest not in committed:
            raise SdJwtError("disclosure is not committed in _sd")
        name, value = _open(disclosure)
        if name in revealed:
            raise SdJwtError(f"claim disclosed twice: {name}")
        revealed[name] = value
    return {
        "issuer": payload.get("iss"),
        "holder": payload.get("sub"),
        "credential_id": payload.get("credential_id"),
        "revealed": revealed,
    }


def _disclosure(name: str, value: Any) -> str:
    salt = _b64encode(secrets.token_bytes(16))
    encoded = json.dumps([salt, name, value], separators=(",", ":"), ensure_ascii=False)
    return _b64encode(encoded.encode("utf-8"))


def _digest(disclosure: str) -> str:
    return _b64encode(hashlib.sha256(disclosure.encode("ascii")).digest())


def _open(disclosure: str) -> tuple[str, Any]:
    try:
        decoded = json.loads(_b64decode(disclosure))
    except (json.JSONDecodeError, ValueError) as exc:
        raise SdJwtError("disclosure is not base64url JSON") from exc
    if not isinstance(decoded, list) or len(decoded) != 3:
        raise SdJwtError("disclosure must be [salt, name, value]")
    name = decoded[1]
    if not isinstance(name, str) or not name or name.startswith("_"):
        raise SdJwtError("illegal disclosure claim name")
    return name, decoded[2]


def _sign(payload: dict[str, Any]) -> str:
    header_json = json.dumps({"alg": "HS256", "typ": "sd-jwt"}, separators=(",", ":"))
    header = _b64encode(header_json.encode())
    body = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{header}.{body}".encode("ascii")
    signature = hmac.new(DEV_ISSUER_KEY, signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64encode(signature)}"


def _verify(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise SdJwtError("issuer JWT must have three segments")
    header_b, body_b, signature_b = parts
    signing_input = f"{header_b}.{body_b}".encode("ascii")
    expected = hmac.new(DEV_ISSUER_KEY, signing_input, hashlib.sha256).digest()
    try:
        actual = _b64decode(signature_b)
    except ValueError as exc:
        raise SdJwtError("issuer JWT signature is not base64url") from exc
    if len(actual) != len(expected) or not hmac.compare_digest(expected, actual):
        raise SdJwtError("issuer JWT signature check failed")
    try:
        header = json.loads(_b64decode(header_b))
        payload = json.loads(_b64decode(body_b))
    except (json.JSONDecodeError, ValueError) as exc:
        raise SdJwtError("issuer JWT is not JSON") from exc
    if header.get("alg") != "HS256":
        raise SdJwtError("issuer JWT alg must be HS256 for this dev key")
    if not isinstance(payload, dict):
        raise SdJwtError("issuer JWT payload must be an object")
    return payload


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)
