"""Smoke tests for credential models, the DID resolver, and SD-JWT disclosure."""

import base64
import json

import pytest

from acp.credentials.auth import HolderAuthError, holder_proof_for, require_holder
from acp.credentials.did import DIDDocument, DIDNotFoundError, MockDIDResolver
from acp.credentials.models import VerifiableCredential
from acp.credentials.sdjwt import issue_presentation, read_presentation
from acp.credentials.zkp import (
    SelectiveDisclosureProver,
    SelectiveDisclosureVerifier,
    scheme_for,
)
from acp.verticals.education import ADA_HOME_ADDRESS, STATE_BOARD, education_credentials


def test_credential_round_trip_uses_vc_field_names() -> None:
    credential = education_credentials()[0]
    payload = credential.model_dump(by_alias=True)
    assert payload["@context"] == ["https://www.w3.org/ns/credentials/v2"]
    assert payload["credentialSubject"]["id"].startswith("did:")
    restored = VerifiableCredential.model_validate(payload)
    assert restored.id == credential.id
    assert restored.summary()["holder"] == credential.holder_did()
    assert "home_address" not in restored.summary()


def test_proof_hides_unrevealed_claims() -> None:
    credential = education_credentials()[0]
    proof = SelectiveDisclosureProver().prove(
        credential,
        ["license_status", "subjects"],
    )
    dumped = proof.model_dump()
    assert dumped["revealed"] == {
        "license_status": "active",
        "subjects": ["Mathematics"],
    }
    assert ADA_HOME_ADDRESS not in str(dumped)
    assert proof.scheme == "sd-jwt"
    assert "~" in proof.presentation
    result = SelectiveDisclosureVerifier().verify(proof, trusted_issuers={STATE_BOARD})
    assert result.ok
    tampered = proof.model_copy(
        update={
            "revealed": {
                "license_status": "expired",
                "subjects": proof.revealed["subjects"],
            }
        }
    )
    rejected = SelectiveDisclosureVerifier().verify(tampered, trusted_issuers={STATE_BOARD})
    assert not rejected.ok


def test_sdjwt_hides_unrevealed_claims_inside_the_issuer_jwt() -> None:
    credential = education_credentials()[0]
    presentation, revealed = issue_presentation(
        issuer=credential.issuer,
        holder=credential.holder_did(),
        credential_id=credential.id,
        subject=credential.credential_subject,
        reveal=["license_status"],
    )
    payload = _jwt_payload(presentation.split("~", 1)[0])
    assert payload["_sd_alg"] == "sha-256"
    assert "home_address" not in payload
    assert ADA_HOME_ADDRESS not in presentation
    assert read_presentation(presentation)["revealed"] == revealed
    assert revealed == {"license_status": "active"}


def test_holder_proof_is_denied_by_default() -> None:
    with pytest.raises(HolderAuthError, match="holder authentication required"):
        require_holder("did:example:teacher-ada", "")
    with pytest.raises(HolderAuthError):
        require_holder("did:example:teacher-ada", None)
    require_holder("did:example:teacher-ada", holder_proof_for("did:example:teacher-ada"))


def test_verifier_rejects_an_untrusted_issuer() -> None:
    credential = education_credentials()[0]
    proof = SelectiveDisclosureProver().prove(credential, ["license_status"])
    result = SelectiveDisclosureVerifier().verify(proof, trusted_issuers={"did:example:other"})
    assert not result.ok


def test_bbs_and_snark_schemes_are_stubs() -> None:
    credential = education_credentials()[0]
    with pytest.raises(NotImplementedError, match="SD-JWT"):
        scheme_for("bbs+").present(credential, ["license_status"])
    with pytest.raises(NotImplementedError, match="SD-JWT"):
        scheme_for("zk-snark").present(credential, ["license_status"])


def test_prover_rejects_unknown_claim_names() -> None:
    credential = education_credentials()[0]
    with pytest.raises(ValueError, match="salary"):
        SelectiveDisclosureProver().prove(credential, ["salary"])


def _jwt_payload(token: str) -> dict:
    body = token.split(".")[1]
    pad = "=" * (-len(body) % 4)
    return json.loads(base64.urlsafe_b64decode(body + pad))


def test_mock_resolver_synthesizes_did_example_and_misses_other_methods() -> None:
    resolver = MockDIDResolver()
    document = resolver.resolve("did:example:state-board")
    assert document.id == "did:example:state-board"
    assert document.verification_method[0]["controller"] == document.id
    resolver.register(DIDDocument(id="did:web:issuer.example"))
    assert resolver.resolve("did:web:issuer.example").id == "did:web:issuer.example"
    with pytest.raises(DIDNotFoundError):
        resolver.resolve("did:web:missing.example")
