"""In-memory credential store shared by the demo and the MCP server.

# OPEN QUESTION: where do credentials live in production (holder wallet,
# school-operated store, or a split), and how long is a disclosure retained
# after a match task completes?
"""

from acp.credentials.models import VerifiableCredential


class CredentialNotFoundError(KeyError):
    """No credential is stored under that id."""


class CredentialStore:
    """Process-local map of credential id to credential."""

    def __init__(self) -> None:
        self._items: dict[str, VerifiableCredential] = {}

    def put(self, credential: VerifiableCredential) -> VerifiableCredential:
        self._items[credential.id] = credential
        return credential

    def get(self, credential_id: str) -> VerifiableCredential:
        try:
            return self._items[credential_id]
        except KeyError as exc:
            raise CredentialNotFoundError(credential_id) from exc

    def summaries_for_holder(self, holder_did: str) -> list[dict[str, str]]:
        return [
            item.summary()
            for item in self._items.values()
            if item.holder_did() == holder_did
        ]
