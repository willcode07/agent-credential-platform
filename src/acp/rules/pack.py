"""Load a market rule pack.

A pack names the tenant, how long a disclosure is kept, which issuers are
trusted for each credential type, and the opportunities (required and
weighted claim requirements). The matcher does not know the market. Storage
copies ``tenant_id`` and the pack id onto each record.

Decided 2026-11-02: markets are pluggable packs. Education is the first one.
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from acp.matching.profiles import Opportunity


class CredentialTypeRule(BaseModel):
    """Issuers allowed to sign one credential type in this pack."""

    trusted_issuers: list[str] = Field(min_length=1)


class RulePack(BaseModel):
    """One market's policy. JSON on disk, this object in memory."""

    id: str
    tenant_id: str
    retention_days: int = Field(ge=0)
    credential_types: dict[str, CredentialTypeRule]
    opportunities: list[Opportunity]

    def trusted_issuers(self, credential_type: str) -> list[str]:
        rule = self.credential_types.get(credential_type)
        if rule is None:
            return []
        return list(rule.trusted_issuers)

    def opportunity(self, opportunity_id: str) -> Opportunity:
        for item in self.opportunities:
            if item.id == opportunity_id:
                return item
        raise KeyError(opportunity_id)


def load_rule_pack(path: Path) -> RulePack:
    """Read a JSON rule pack. YAML is not parsed; packs are JSON."""
    return RulePack.model_validate(json.loads(path.read_text(encoding="utf-8")))
