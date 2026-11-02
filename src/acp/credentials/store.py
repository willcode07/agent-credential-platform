"""In-memory credential store.

Every record carries ``tenant_id`` and ``rule_pack_id``. Disclosure records
also carry ``retain_until``, computed from the rule pack's retention period.
Nothing is written to disk.

# OPEN QUESTION: which durable store replaces this dict? The fields above
# are the ones a later store has to keep so retention can be enforced
# per pack without a rewrite.
"""

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from acp.credentials.models import VerifiableCredential


class CredentialNotFoundError(KeyError):
    """No credential is stored under that id."""


class StoredCredential(BaseModel):
    """One credential plus the tenancy it was stored under."""

    tenant_id: str
    rule_pack_id: str
    retention_days: int
    credential: VerifiableCredential


class DisclosureRecord(BaseModel):
    """A disclosure the store has been asked to remember until ``retain_until``."""

    tenant_id: str
    rule_pack_id: str
    credential_id: str
    created_at: datetime
    retain_until: datetime


class CredentialStore:
    """Process-local credentials and disclosure records."""

    def __init__(self) -> None:
        self._items: dict[str, StoredCredential] = {}
        self._disclosures: list[DisclosureRecord] = []

    def put(
        self,
        credential: VerifiableCredential,
        *,
        tenant_id: str,
        rule_pack_id: str,
        retention_days: int,
    ) -> VerifiableCredential:
        self._items[credential.id] = StoredCredential(
            tenant_id=tenant_id,
            rule_pack_id=rule_pack_id,
            retention_days=retention_days,
            credential=credential,
        )
        return credential

    def get_record(self, credential_id: str) -> StoredCredential:
        try:
            return self._items[credential_id]
        except KeyError as exc:
            raise CredentialNotFoundError(credential_id) from exc

    def get(self, credential_id: str) -> VerifiableCredential:
        return self.get_record(credential_id).credential

    def summaries_for_holder(self, holder_did: str) -> list[dict[str, str]]:
        summaries: list[dict[str, str]] = []
        for record in self._items.values():
            if record.credential.holder_did() != holder_did:
                continue
            summary = record.credential.summary()
            summary["tenant_id"] = record.tenant_id
            summary["rule_pack_id"] = record.rule_pack_id
            summaries.append(summary)
        return summaries

    def record_disclosure(
        self,
        credential_id: str,
        *,
        now: datetime | None = None,
    ) -> DisclosureRecord:
        """Remember that a disclosure was made, until the pack's retention elapses."""
        stored = self.get_record(credential_id)
        created = now or datetime.now(UTC)
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        record = DisclosureRecord(
            tenant_id=stored.tenant_id,
            rule_pack_id=stored.rule_pack_id,
            credential_id=credential_id,
            created_at=created,
            retain_until=created + timedelta(days=stored.retention_days),
        )
        self._disclosures.append(record)
        return record

    def disclosures(self) -> list[DisclosureRecord]:
        return list(self._disclosures)

    def purge_disclosures(self, now: datetime | None = None) -> int:
        """Drop disclosure records whose ``retain_until`` is at or before ``now``."""
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        kept = [item for item in self._disclosures if item.retain_until > current]
        removed = len(self._disclosures) - len(kept)
        self._disclosures = kept
        return removed
