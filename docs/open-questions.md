# Decisions and open questions

Search the tree for `# OPEN QUESTION:` to see what is still open. The five
items below were decided on Nov 2, 2026.

## Decided

### 1. Disclosure scheme — Nov 2, 2026

SD-JWT is the default. `DisclosureScheme` in
`src/acp/credentials/disclosure.py` is the plug point. BBS+ and zk-SNARK
predicate proofs are named stubs and raise `NotImplementedError`. The
working SD-JWT (`src/acp/credentials/sdjwt.py`) commits a salted SHA-256
digest of every subject claim and attaches only the disclosures the holder
chose. It is signed with a development HMAC key.

### 2. DID methods and trusted issuers — Nov 2, 2026

The resolver supports `did:web`, `did:key`, and ANP `did:wba`. `did:key` is
decoded offline. `did:web` and `did:wba` compute the HTTPS document URL and
return a document only when one was cached. `did:example` is a sample
stand-in, not a fourth production method. Trusted issuers are configuration
on the rule pack, per credential type. They are not hard-coded.

### 3. Who may see a full credential — Nov 2, 2026

`read_credential` requires holder authentication. The mock proof is the
literal `holder:<did>`. A missing or wrong proof is denied, including the
default empty proof. Counterparties receive claim values only through
`disclose_claims`. There is no unauthenticated credential resource.

### 4. One matching agent — Nov 2, 2026

There is one matching agent. The A2A Agent Card is the source of truth.
ANP stays a stub: `ANPAdapter.project_card` derives an unsigned Agent
Description from the card, and does not resolve a DID.

### 5. Markets are rule packs — Nov 2, 2026

The core stays industry-agnostic. Each market is a JSON rule pack plus an
optional module (`src/acp/rules/pack.py`). A pack defines accepted
credential types, trusted issuers, required versus weighted claim
requirements, and the disclosure retention period. Education is the first
pack (`src/acp/verticals/education.rules.json`). Storage stays in memory.
Every credential record and disclosure record carries `tenant_id` and a
rule-pack id, and a disclosure records `retain_until`, so a durable store
can enforce per-pack retention without a rewrite. Tasks on the matching
agent carry the same two ids.

## Still open

These are not the five decisions above.

* **Issuer key for SD-JWT.** Presentations are HS256 under
  `DEV_ISSUER_KEY`. Signing with a verification method from the issuer DID,
  and splitting issuance from presentation, is still open
  (`src/acp/credentials/sdjwt.py`).
* **DID documents on the network.** `did:web` and `did:wba` are not fetched,
  and their document proofs are not checked. A `did:key` multikey is not
  expanded into a JWK the SD-JWT verifier can use
  (`src/acp/credentials/did.py`).
* **Holder authentication.** The `holder:<did>` string is a stub. A
  signature over a challenge from `did:key` or `did:wba` would replace it
  (`src/acp/credentials/auth.py`).
* **Durable storage.** Credentials, disclosures, and tasks are process-local
  dicts. Which store replaces them is open. The tenancy and retention fields
  are already on the records (`src/acp/credentials/store.py`,
  `src/acp/protocols/a2a/tasks.py`).
* **MCP major version.** This repo depends on `mcp>=2,<3` and uses
  `MCPServer`. Pin `mcp<2` if a host still imports `FastMCP`
  (`src/acp/protocols/mcp/server.py`).
* **Public origin of the Agent Card.** `acp serve` writes the bind address
  into `supportedInterfaces[].url`, which is wrong behind TLS or a proxy
  (`src/acp/protocols/a2a/card.py`, `src/acp/cli.py`).
* **Credential envelope.** Stored credentials follow VC Data Model 2.0.
  Whether to also accept a JWT or SD-JWT that has no `@context` is open
  (`src/acp/credentials/models.py`). SD-JWT here is the presentation of
  claims from a VC, not a second stored envelope.
* **Requirement language.** The matcher operators (`equals`, `one_of`,
  `contains`, `in_range`, `overlaps`, `present`) may be too small. A policy
  language is open. A predicate that hides the value is the zk-SNARK stub,
  not a matcher feature (`src/acp/matching/matcher.py`).
* **Cross-adapter requests.** Whether one user request may read a credential
  over MCP and then open an A2A task, or each adapter stays a separate entry
  point, is open (`src/acp/protocols/base.py`).
