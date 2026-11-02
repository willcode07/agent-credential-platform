"""Smoke tests for credential models, the DID resolver, and mock disclosure."""

import pytest

from acp.credentials.did import DIDDocument, DIDNotFoundError, MockDIDResolver
from acp.credentials.models import VerifiableCredential
from acp.credentials.zkp import SelectiveDisclosureProver, SelectiveDisclosureVerifier
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
    result = SelectiveDisclosureVerifier().verify(proof, trusted_issuers={STATE_BOARD})
    assert result.ok


def test_verifier_rejects_an_untrusted_issuer() -> None:
    credential = education_credentials()[0]
    proof = SelectiveDisclosureProver().prove(credential, ["license_status"])
    result = SelectiveDisclosureVerifier().verify(proof, trusted_issuers={"did:example:other"})
    assert not result.ok


def test_prover_rejects_unknown_claim_names() -> None:
    credential = education_credentials()[0]
    with pytest.raises(ValueError, match="salary"):
        SelectiveDisclosureProver().prove(credential, ["salary"])


def test_mock_resolver_synthesizes_did_example_and_misses_other_methods() -> None:
    resolver = MockDIDResolver()
    document = resolver.resolve("did:example:state-board")
    assert document.id == "did:example:state-board"
    assert document.verification_method[0]["controller"] == document.id
    resolver.register(DIDDocument(id="did:web:issuer.example"))
    assert resolver.resolve("did:web:issuer.example").id == "did:web:issuer.example"
    with pytest.raises(DIDNotFoundError):
        resolver.resolve("did:web:missing.example")
