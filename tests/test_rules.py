"""Rule packs, per-type issuers, and disclosure retention."""

from datetime import UTC, datetime

from acp.credentials.store import CredentialStore
from acp.credentials.zkp import SelectiveDisclosureProver, SelectiveDisclosureVerifier
from acp.verticals.education import (
    STATE_BOARD,
    education_credentials,
    education_pack,
)


def test_trusted_issuers_are_per_credential_type() -> None:
    pack = education_pack()
    assert pack.id == "education"
    assert pack.tenant_id == "example-tenant"
    assert pack.retention_days == 30
    assert pack.trusted_issuers("TeachingLicense") == [STATE_BOARD]
    assert pack.trusted_issuers("StudentEnrollment") == ["did:example:north-high"]
    assert pack.trusted_issuers("UnknownType") == []

    license_credential = education_credentials()[0]
    proof = SelectiveDisclosureProver().prove(license_credential, ["license_status"])
    school_issuers = set(pack.trusted_issuers("StudentEnrollment"))
    rejected = SelectiveDisclosureVerifier().verify(proof, trusted_issuers=school_issuers)
    assert not rejected.ok
    assert pack.opportunity("math-teacher-9-12").credential_type == "TeachingLicense"


def test_disclosure_records_carry_tenancy_and_expire() -> None:
    store = CredentialStore()
    credential = education_credentials()[0]
    store.put(
        credential,
        tenant_id="tenant-a",
        rule_pack_id="pack-a",
        retention_days=1,
    )
    created = datetime(2026, 11, 2, tzinfo=UTC)
    record = store.record_disclosure(credential.id, now=created)
    assert record.tenant_id == "tenant-a"
    assert record.rule_pack_id == "pack-a"
    assert record.retain_until == datetime(2026, 11, 3, tzinfo=UTC)
    noon = datetime(2026, 11, 2, 12, tzinfo=UTC)
    assert store.purge_disclosures(noon) == 0
    assert store.purge_disclosures(datetime(2026, 11, 3, tzinfo=UTC)) == 1
    assert store.disclosures() == []
    stored = store.get_record(credential.id)
    assert stored.tenant_id == "tenant-a"
    assert stored.rule_pack_id == "pack-a"
