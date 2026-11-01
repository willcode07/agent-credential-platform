# Protocols

This scaffold speaks three agent protocols on purpose. MCP and A2A are the
ones with running placeholders. ANP is an adapter seam. Verifiable
credentials and selective disclosure sit underneath them; they are not a
fourth agent protocol.

Versions below were checked against public specs while the repository was
scaffolded (November 2026). Where a document disagrees with itself, that is
called out.

## MCP — private context

MCP (Model Context Protocol) is how a holder's agent reaches a credential
store without putting that store on a public agent-to-agent channel.

The official Python SDK is the `mcp` package. As of 2.x (current release
when this repo was created, 2.3.0), the high-level server class is
`MCPServer`:

```python
from mcp.server import MCPServer
```

In 1.x that class was `FastMCP` (`from mcp.server.fastmcp import FastMCP`).
The 2.x line removes the old import. This repo depends on `mcp>=2,<3` and
uses `MCPServer`. The placeholder registers:

* `list_credentials(holder_did)` — ids and types only
* `disclose_claims(credential_id, reveal)` — mock selective disclosure
* resource `credential://{credential_id}` — full credential, meant as a
  stand-in for the holder's own agent

`acp mcp` defaults to stdio, which is how local MCP hosts start a server.
`--transport streamable-http` matches the SDK's current HTTP transport.
SSE is the older HTTP transport and is not used here.

## A2A — agent collaboration

A2A (Agent2Agent) is how a school agent discovers the matcher and gives it
work. The placeholder follows the **1.0.0** specification published at
<https://a2a-protocol.org/latest/specification/> (same text as
`a2aproject/A2A` on the `v1.0.1` / `main` docs at the time of writing).

Checked details:

| Item | What this repo does | Source |
| --- | --- | --- |
| Agent Card path | `GET /.well-known/agent-card.json` | Spec section 8.2. Renamed from `/.well-known/agent.json` in 0.3.0 (2025-07-30, A2A changelog, spec PR 841). The old path is not served. |
| Card fields | `name`, `description`, `supportedInterfaces`, `version`, `capabilities`, `defaultInputModes`, `defaultOutputModes`, `skills` | Spec section 4.4.1. `supportedInterfaces` replaced a single URL in the 1.0 data model. |
| Interface binding | `protocolBinding: "JSONRPC"`, `protocolVersion: "1.0"` | Spec section 4.4.6. Core bindings are `JSONRPC`, `GRPC`, and `HTTP+JSON`. |
| JSON-RPC methods | `SendMessage`, `GetTask`, `ListTasks`, `CancelTask` | Spec section 5.3 and section 9.4. PascalCase, not the earlier `message/send` and `tasks/get` names. |
| Task result of `SendMessage` | `{ "task": { ... } }` | `SendMessageResponse` is a one-of `task` or `message`. |
| Task states | `TASK_STATE_COMPLETED`, `TASK_STATE_WORKING`, `TASK_STATE_CANCELED`, … | Spec section 4.1.3. ProtoJSON enum strings. |
| Roles | `ROLE_USER`, `ROLE_AGENT` | Spec section 4.1.5. |
| JSON names | camelCase (`contextId`, `messageId`, `nextPageToken`) | Spec section 5.5. |
| List response | `tasks`, `nextPageToken`, `pageSize`, `totalSize` | Spec section 10.4.4. Artifacts omitted unless `includeArtifacts` is true. |
| Errors | `-32001` task not found, `-32002` not cancelable, `-32004` unsupported | Spec section 5.4. |

The JSON-RPC **path is not well-known**. Section 9.2 shows an example
`POST /rpc`. Sample cards point `supportedInterfaces[].url` at an
agent-chosen URL such as `https://example.com/a2a/v1`. This app serves the
URL it publishes (`/a2a/v1`) and also `/rpc` so the section 9.2 example
hits the same handler.

Not implemented, and answered with JSON-RPC `-32004`: streaming
(`SendStreamingMessage`, `SubscribeToTask`), push notification configs, and
`GetExtendedAgentCard`.

Two spec nits this code does not follow, because they contradict the
normative tables:

* Section 9.3's skeleton still shows `"method": "category/action"`.
  Sections 9.1 and 9.4, and the method mapping table, require PascalCase
  (`SendMessage`). Requests that use the old `message/send` form get
  "method not found".
* Section 9.2's sample request still sends `A2A-Version: 0.3`, while the
  released spec is 1.0.0 and sample cards use `protocolVersion: "1.0"`.
  The card advertises `"1.0"`. The handler does not require the header.

The normative data model is `spec/a2a.proto` in the A2A repository. This
scaffold was checked against the rendered specification, not by compiling
that proto.

## ANP and DIDs — long-term direction

ANP (Agent Network Protocol) is the long-term discovery direction. The
document checked while scaffolding was ANP-07, the Agent Description
Protocol, marked version 1.2 at
<https://agent-network-protocol.com/specs/agent-description.html>. An agent
publishes a JSON Agent Description (`protocolType` `ANP`, `type`
`AgentDescription`). Authentication is the DID flow from ANP-02; that text
names `did:wba` and native `did:web`. Sample documents set
`protocolVersion` to `1.0.0` while the document revision is 1.2. This
scaffold does not choose between those version strings and does not emit an
Agent Description.

A2A identifies an agent with an Agent Card instead. `ANPAdapter.project_did`
returns a stub that points a DID at the A2A card path and marks itself
`not_implemented`. `MockDIDResolver` satisfies the `DIDResolver` interface
offline for `did:example` identifiers. No ANP document is parsed and no DID
method is fetched.

Supporting both means keeping the adapter boundary: matching and disclosure
do not import A2A or ANP types. A later ANP adapter can project its
description into the same Agent Card builder, or the reverse, once a human
picks which document is canonical.

## Credentials: DID, VC, selective disclosure

Credentials are a small pydantic reading of W3C Verifiable Credentials 2.0:
`@context` of `https://www.w3.org/ns/credentials/v2`, `type`, `issuer`,
`validFrom`, `credentialSubject`. There is no proof block and no status list.

The prover/verifier in `src/acp/credentials/zkp.py` is a sketch:

* **BBS+** signs a list of messages and lets the holder derive an unlinkable
  proof of a subset. Closest match for "reveal these claims from a signed
  credential."
* **SD-JWT** puts a salted hash of each claim in a signed JWT and lets the
  holder open some of them. Easier to deploy, weaker unlinkability.
* **zk-SNARK / circom** proves a predicate (a grade band, a threshold)
  without revealing the number. Heavier, and a different product question
  than claim disclosure.

The mock returns revealed claims plus a SHA-256 commitment of the hidden
ones. It is not bound to an issuer key. The verifier checks the issuer
allow-list and the shape of the envelope only.
