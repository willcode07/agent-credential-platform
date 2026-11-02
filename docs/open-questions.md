# Open questions

Search the tree for `# OPEN QUESTION:` to see these in context. They are
product and architecture choices, not bugs in the scaffold.

## 1. Which disclosure scheme is the default?

`src/acp/credentials/zkp.py` sketches three real options and implements none
of them:

* BBS+ for unlinkable disclosure of signed claims
* SD-JWT for salted-hash disclosure inside a JWT
* a zk-SNARK (circom or otherwise) when a counterparty needs a predicate,
  such as "a number is above a threshold", rather than the number itself

A market may need both claim disclosure and a predicate. Picking one as the
default decides the issuer format, the wallet, and what the verifier has to
ship. The education example reveals grade values instead of proving a range.

## 2. DID methods and trusted issuers

`MockDIDResolver` accepts anything under `did:example` and refuses every
other method until it is registered. A deployment has to name the methods
(`did:web`, `did:key`, others) and, per credential type, which issuer DIDs
are trusted. The verifier's allow-list is that decision, expressed today as
a set of strings. The education example trusts a state board and a school;
another market would pass a different set.

## 3. Who may see a full credential?

The MCP server exposes `disclose_claims` and also `read_credential`, which
returns every claim. That second tool is a stand-in for the holder's own
agent. A counterparty must not be able to call it. The open choice is how
the store authenticates the holder (DID auth, a wallet session, something
else) and how tools are partitioned between the holder and everyone else.

Related: MCP 2.x renamed `FastMCP` to `MCPServer`. This repo depends on
`mcp>=2,<3`. Pin `mcp<2` instead if a host still imports `FastMCP`.

## 4. One agent or several, and A2A versus ANP

The running placeholder is a single matching agent with one Agent Card.
A deployment might also run separate holder, issuer, and counterparty
agents. Those could be distinct A2A peers, each with a private MCP store,
or one process with several cards. The education example uses a school, a
teacher, and a student as those roles; that split is not built in.

ANP would identify each of them with a DID on an Agent Description document
(ANP-07). `ANPAdapter` does not decide whether that document or the A2A
Agent Card is canonical when both exist. The JSON-RPC URL is agent-declared
(`/a2a/v1` on the card, with `/rpc` only as the alias from the spec's
example). The public origin of that URL is also unset: `acp serve` writes
the bind address into the card, which is wrong behind TLS or a proxy.

## 5. Retention, tenancy, and the requirement language

Tasks and credentials live in process memory. A shared deployment needs a
store, a tenant boundary so one counterparty cannot list another's tasks,
and a rule for how long a disclosure is kept after a task reaches a terminal
state.

The matcher applies whatever requirements a market hands it. The operator
list is small on purpose. Whether that struct is enough, or a market needs
a policy language, is open. So is which claims a counterparty may require:
the education example requires a subject, a grade band, a license, and a
placement; an HR or executive-screening market would require different
claims and keep artifacts for a different amount of time. Those policies
must not leak back into the matcher.
