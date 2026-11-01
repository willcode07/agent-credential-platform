# Open questions

Search the tree for `# OPEN QUESTION:` to see these in context. They are
product and architecture choices, not bugs in the scaffold.

## 1. Which disclosure scheme is the launch default?

`src/acp/credentials/zkp.py` sketches three real options and implements none
of them:

* BBS+ for unlinkable disclosure of signed claims
* SD-JWT for salted-hash disclosure inside a JWT
* a zk-SNARK (circom or otherwise) when the school needs a predicate, such
  as "grade is in 9–12", rather than the grade itself

A school match may need both claim disclosure and a predicate. Picking one
as the default decides the issuer format, the wallet, and what the verifier
has to ship.

## 2. DID methods and trusted issuers

`MockDIDResolver` accepts anything under `did:example` and refuses every
other method until it is registered. A launch has to name the methods
(`did:web`, `did:key`, others) and the issuer DIDs that may sign a teaching
license or an enrollment credential. The same trust list is what the
verifier checks today, as a plain set of strings.

## 3. Who may see a full credential?

The MCP server exposes `disclose_claims` and also `read_credential`, which
returns every claim. That second tool is a stand-in for the holder's own
agent. A counterparty, or a model acting for the school, must not be able to
call it. The open choice is how the store authenticates the holder (DID
auth, a wallet session, something else) and how tools are partitioned
between the holder and everyone else.

Related: MCP 2.x renamed `FastMCP` to `MCPServer`. This repo depends on
`mcp>=2,<3`. Pin `mcp<2` instead if a host still imports `FastMCP`.

## 4. One agent or several, and A2A versus ANP

The running placeholder is a single matching agent with one Agent Card.
The launch story also has a school agent, a teacher agent, and a student
agent. Those could be three A2A peers plus a private MCP store each, or one
process with three cards.

ANP would identify each of them with a DID on an Agent Description document
(ANP-07). `ANPAdapter` does not decide whether that document or the A2A
Agent Card is canonical when both exist. The JSON-RPC URL is agent-declared (`/a2a/v1` on the card, with
`/rpc` only as the alias from the spec's example). The public origin of
that URL is also unset: `acp serve` writes the bind address into the card,
which is wrong behind TLS or a proxy.

## 5. Retention, tenancy, and a second market

Tasks and credentials live in process memory. A shared deployment needs a
store, a tenant boundary so one school cannot list another's tasks, and a
rule for how long a disclosure is kept after a task reaches a terminal
state.

The matcher encodes a US-style grade 1–12 and a license boolean. That is
enough for the school launch. An HR or executive-screening product should
not silently reuse the same rules: the claims an employer may require, and
how long a screening artifact is kept, are a separate policy even if the
protocol adapters stay.

The grade scale itself is an open choice for schools outside that 1–12 model.
