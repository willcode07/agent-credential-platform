"""DID resolver interface and an offline stand-in.

A production resolver would fetch a DID document (for example ``did:web``
or ``did:key``) and return verification methods the ZKP verifier can use.
This mock never touches the network.

# OPEN QUESTION: which DID methods are in scope for the school launch
# (``did:web``, ``did:key``, ``did:ion``, something else), and which issuer
# DIDs are trusted for a teaching license?
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


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


class MockDIDResolver(DIDResolver):
    """In-memory resolver.

    Unregistered ``did:example`` DIDs get a synthetic document so local demos
    run offline. Any other method is a miss until someone registers it.
    """

    def __init__(self, documents: dict[str, DIDDocument] | None = None) -> None:
        self._documents = dict(documents or {})

    def register(self, document: DIDDocument) -> None:
        self._documents[document.id] = document

    def resolve(self, did: str) -> DIDDocument:
        if not did.startswith("did:"):
            raise DIDNotFoundError(f"not a DID: {did}")
        found = self._documents.get(did)
        if found is not None:
            return found
        if did.startswith("did:example:"):
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
        raise DIDNotFoundError(did)
