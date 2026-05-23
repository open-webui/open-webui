# Model Context Protocol — Engineering Reference

> Researched against MCP revision **`2025-11-25`** (the current `latest`) as of **2026-05-21**.
> Source of truth for the protocol is the TypeScript schema in
> [`schema/2025-11-25/schema.ts`](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-11-25/schema.ts);
> the Markdown specification lives under
> [`modelcontextprotocol.io/specification/2025-11-25/`](https://modelcontextprotocol.io/specification/2025-11-25/).
> Where this document references RFC text it cites the IETF Datatracker HTML view.

---

## 1. What MCP is and why

The **Model Context Protocol** is an open, JSON-RPC 2.0-based protocol for connecting "LLM applications" (hosts) to external **tools, data, and prompt templates** (servers). It was announced by Anthropic on **November 25, 2024** ([anthropic.com/news/model-context-protocol](https://www.anthropic.com/news/model-context-protocol)), released simultaneously with a specification, SDKs in Python and TypeScript, support in the Claude Desktop app, and reference servers for Google Drive, Slack, GitHub, Git, Postgres and Puppeteer.

The problem statement from the announcement: "even the most sophisticated models are constrained by their isolation from data—trapped behind information silos and legacy systems. Every new data source requires its own custom implementation, making truly connected systems difficult to scale." MCP solves this by defining one wire protocol that any host can speak to any server.

The spec positions MCP as analogous to the **Language Server Protocol** for IDEs: "MCP takes some inspiration from the Language Server Protocol, which standardizes how to add support for programming languages across a whole ecosystem of development tools. In a similar way, MCP standardizes how to integrate additional context and tools into the ecosystem of AI applications." ([Specification overview](https://modelcontextprotocol.io/specification/2025-11-25)).

### What MCP is *not*

- **Not a model API.** "MCP focuses solely on the protocol for context exchange — it does not dictate how AI applications use LLMs or manage the provided context." ([Architecture overview](https://modelcontextprotocol.io/docs/learn/architecture)). The host decides how to assemble MCP-provided context into a prompt and how (and whether) to invoke an LLM.
- **Not a function-calling API.** MCP defines how a *host* discovers and invokes tools that a *server* exposes. The mapping between LLM tool-use messages and `tools/call` is performed by the host; the LLM never speaks MCP directly. Servers do not call the model. (The `sampling/createMessage` primitive in §7 is the only way a server can request a model completion, and it does so by asking the *client* to run the completion on its behalf.)
- **Not transport-locked.** "The protocol is transport-agnostic and can be implemented over any communication channel that supports bidirectional message exchange." ([Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#custom-transports)).

### Where it sits in the stack

```
+-------------------------------------------+
| Host application (AI app: e.g. Claude     |
| Desktop, Claude Code, Cursor, VS Code)    |
|                                           |
|  +-----+   +-----+   +-----+              |
|  |Cli 1|   |Cli 2|   |Cli 3|   one client |
|  +-----+   +-----+   +-----+   per server |
+-----|-------|--------|--------------------+
      |       |        |
      v       v        v
    Server  Server   Server    JSON-RPC 2.0 over
    A       B        C         stdio or Streamable HTTP
```

The host instantiates one **client** object per **server** connection ([Architecture](https://modelcontextprotocol.io/specification/2025-11-25/architecture)). Hosts may connect to many servers; each client is paired 1:1 with a single server session.

---

## 2. Architecture and roles

[`/specification/2025-11-25/architecture`](https://modelcontextprotocol.io/specification/2025-11-25/architecture) defines three roles:

- **Host** — "Creates and manages multiple client instances. Controls client connection permissions and lifecycle. Enforces security policies and consent requirements. Handles user authorization decisions. Coordinates AI/LLM integration and sampling. Manages context aggregation across clients."
- **Client** — "Each client is created by the host and maintains an isolated server connection. Establishes one stateful session per server. Handles protocol negotiation and capability exchange. Routes protocol messages bidirectionally. Manages subscriptions and notifications. Maintains security boundaries between servers." Crucially: **"A host application creates and manages multiple clients, with each client having a 1:1 relationship with a particular server."**
- **Server** — "Expose resources, tools and prompts via MCP primitives. Operate independently with focused responsibilities. Request sampling through client interfaces. Must respect security constraints. Can be local processes or remote services."

### Design principles (from the spec)

The architecture page commits to four:

1. **Servers should be extremely easy to build.** Host owns orchestration; servers are narrow.
2. **Servers should be highly composable.**
3. **Servers should not be able to read the whole conversation, nor "see into" other servers.** "Servers receive only necessary contextual information. Full conversation history stays with the host. Each server connection maintains isolation. Cross-server interactions are controlled by the host."
4. **Features can be added to servers and clients progressively** (capability negotiation; backwards compatibility).

### Trust boundaries

- **Host ↔ user.** The host is responsible for consent: "Users must explicitly consent to and understand all data access and operations" ([overview](https://modelcontextprotocol.io/specification/2025-11-25)).
- **Host ↔ client.** Each client is sandboxed within the host; the host decides what to expose to which client.
- **Client ↔ server.** This is the network boundary. Local stdio servers inherit the trust of the user that launched them. Remote HTTP servers are mutually distrustful and require OAuth 2.1 (§9).
- **Server ↔ downstream.** A server that proxies a third-party API is itself an OAuth *client* to that API; it MUST NOT reuse the token issued by its MCP client (the "token passthrough" anti-pattern, §13).

---

## 3. Wire protocol

All MCP messages are **JSON-RPC 2.0** ([jsonrpc.org/specification](https://www.jsonrpc.org/specification)) and **MUST be UTF-8 encoded** ([Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)).

The spec defines three message shapes ([Base protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic)):

### Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": { "cursor": "optional-cursor-value" }
}
```

- "Requests **MUST** include a string or integer ID."
- "Unlike base JSON-RPC, the ID **MUST NOT** be `null`."
- "The request ID **MUST NOT** have been previously used by the requestor within the same session."

### Result response

```json
{ "jsonrpc": "2.0", "id": 1, "result": { /* ... */ } }
```

### Error response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": { "code": -32602, "message": "Invalid params" }
}
```

- "Error codes **MUST** be integers." Error response IDs match the request, "except in error cases where the ID could not be read due [to] a malformed request."

### Notification

```json
{ "jsonrpc": "2.0", "method": "notifications/initialized" }
```

- "Notifications **MUST NOT** include an ID." The receiver "**MUST NOT** send a response."

### Batching: **removed**

JSON-RPC 2.0 defines [batch requests](https://www.jsonrpc.org/specification#batch) as an array of requests. MCP **added batching support in revision `2025-03-26`** (changelog: "Added support for JSON-RPC batching (PR #228)") and **then removed it in `2025-06-18`**. The `2025-06-18` changelog reads: **"Remove support for JSON-RPC batching (PR [#416](https://github.com/modelcontextprotocol/specification/pull/416))"** ([2025-06-18 changelog](https://modelcontextprotocol.io/specification/2025-06-18/changelog)). In the current revision (`2025-11-25`) batches are **not** part of the protocol; implementations must send each request as an individual JSON-RPC message.

### `_meta`

MCP reserves a `_meta` property/parameter on most types for protocol-level and vendor metadata. Key names have an optional reverse-DNS prefix terminated by `/`, e.g. `io.modelcontextprotocol/related-task`. Prefixes whose second label is `modelcontextprotocol` or `mcp` are reserved for the protocol itself ([Base protocol §General fields](https://modelcontextprotocol.io/specification/2025-11-25/basic)).

### JSON Schema dialect

"When a schema does not include a `$schema` field, it defaults to **JSON Schema 2020-12** … Implementations **MUST** support at least 2020-12 and **SHOULD** document which additional dialects they support. Implementors are RECOMMENDED to use JSON Schema 2020-12." This was formalized as the default in `2025-11-25` via [SEP-1613](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1613).

---

## 4. Lifecycle

A session has three phases ([Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)): **Initialization → Operation → Shutdown**.

### `initialize` request (client → server)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {},
      "elicitation": { "form": {}, "url": {} },
      "tasks": {
        "requests": {
          "elicitation": { "create": {} },
          "sampling":    { "createMessage": {} }
        }
      }
    },
    "clientInfo": {
      "name": "ExampleClient",
      "title": "Example Client Display Name",
      "version": "1.0.0",
      "description": "An example MCP client application",
      "websiteUrl": "https://example.com"
    }
  }
}
```

### `initialize` response (server → client)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "logging": {},
      "prompts":   { "listChanged": true },
      "resources": { "subscribe": true, "listChanged": true },
      "tools":     { "listChanged": true },
      "tasks": {
        "list": {}, "cancel": {},
        "requests": { "tools": { "call": {} } }
      }
    },
    "serverInfo": {
      "name": "ExampleServer",
      "title": "Example Server Display Name",
      "version": "1.0.0"
    },
    "instructions": "Optional instructions for the client"
  }
}
```

### `notifications/initialized` (client → server, after the response)

```json
{ "jsonrpc": "2.0", "method": "notifications/initialized" }
```

Ordering rules (spec, verbatim):
- "The client **SHOULD NOT** send requests other than pings before the server has responded to the `initialize` request."
- "The server **SHOULD NOT** send requests other than pings and logging before receiving the `initialized` notification."

### Capability keys

Per [Lifecycle §Capability Negotiation](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle#capability-negotiation):

| Side    | Key            | Meaning                                                              |
|---------|----------------|----------------------------------------------------------------------|
| Client  | `roots`        | Can expose filesystem/URI roots to servers.                          |
| Client  | `sampling`     | Can serve `sampling/createMessage` requests (LLM completion).        |
| Client  | `elicitation`  | Can serve `elicitation/create` requests; sub-keys `form`, `url`.     |
| Client  | `tasks`        | Supports task-augmented client-side requests (experimental).         |
| Client  | `experimental` | Non-standard features.                                               |
| Server  | `prompts`      | Exposes prompt templates.                                            |
| Server  | `resources`    | Exposes resources. Sub-keys: `subscribe`, `listChanged`.             |
| Server  | `tools`        | Exposes tools. Sub-key: `listChanged`.                               |
| Server  | `logging`      | Emits `notifications/message`.                                       |
| Server  | `completions`  | Supports `completion/complete`.                                      |
| Server  | `tasks`        | Supports task-augmented server-side requests (experimental).         |
| Server  | `experimental` | Non-standard features.                                               |

Sub-capabilities `listChanged` (signals list-change notifications) and `subscribe` (resources only) are explicitly called out.

### Version negotiation

- "The client **MUST** send a protocol version it supports. This **SHOULD** be the *latest* version supported by the client."
- "If the server supports the requested protocol version, it **MUST** respond with the same version. Otherwise, the server **MUST** respond with another protocol version it supports."
- "If the client does not support the version in the server's response, it **SHOULD** disconnect."

Example mismatch error (verbatim from the spec):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Unsupported protocol version",
    "data": { "supported": ["2024-11-05"], "requested": "1.0.0" }
  }
}
```

On HTTP transports the negotiated value MUST be carried as an `MCP-Protocol-Version` header on every subsequent request (§5).

### Shutdown

No shutdown JSON-RPC message exists. For stdio: "Close the input stream to the child process … wait for the server to exit, or send `SIGTERM` … `SIGKILL` if the server does not exit within a reasonable time after `SIGTERM`." For HTTP: close the HTTP connection(s) and optionally `DELETE` the MCP endpoint with the session header (§5).

### Timeouts

"Implementations **SHOULD** establish timeouts for all sent requests" and **SHOULD** cancel via `notifications/cancelled` when they fire. Progress notifications **MAY** reset the timer, but a maximum timeout MUST still be enforced.

---

## 5. Transports

[`/specification/2025-11-25/basic/transports`](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) defines two standard transports — **stdio** and **Streamable HTTP** — plus custom transports as an open extension point. "Clients **SHOULD** support stdio whenever possible."

### 5.1 stdio

Process model:
- "The client launches the MCP server as a subprocess."
- The server reads JSON-RPC from `stdin`, writes JSON-RPC to `stdout`.

Framing rules (verbatim):
- "Messages are individual JSON-RPC requests, notifications, or responses."
- "Messages are delimited by newlines, and **MUST NOT** contain embedded newlines."
- "The server **MUST NOT** write anything to its `stdout` that is not a valid MCP message."
- "The client **MUST NOT** write anything to the server's `stdin` that is not a valid MCP message."

**No `Content-Length` header** is used; this is line-framed JSON-RPC, *not* LSP-style header framing. The only delimiter is `\n`.

`stderr` is for diagnostics: "The server **MAY** write UTF-8 strings to its standard error (`stderr`) for any logging purposes including informational, debug, and error messages." This was clarified in `2025-11-25` (PR [#670](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/670)) — before that it was implied to be "error" only. "The client **MAY** capture, forward, or ignore the server's `stderr` output and **SHOULD NOT** assume `stderr` output indicates error conditions."

Environment variables are the *de facto* mechanism for handing the server credentials, since the auth spec explicitly excludes stdio (§10).

Lifecycle is owned by the client — the client launches, monitors, and signals the child process to exit.

### 5.2 Streamable HTTP

Streamable HTTP **replaces** the older "HTTP+SSE" two-endpoint transport (§5.3). Introduced in revision `2025-03-26` (changelog: "Replaced the previous HTTP+SSE transport with a more flexible **Streamable HTTP transport** (PR [#206](https://github.com/modelcontextprotocol/specification/pull/206))").

Endpoint model:
- The server exposes "a single HTTP endpoint path (hereafter referred to as the **MCP endpoint**) that supports both POST and GET methods. For example, this could be a URL like `https://example.com/mcp`."

Security gates:
- "Servers **MUST** validate the `Origin` header on all incoming connections to prevent DNS rebinding attacks." Invalid Origin → **HTTP 403 Forbidden** (made explicit in `2025-11-25`, PR [#1439](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1439)). The 403 body **MAY** be a JSON-RPC error with no `id`.
- "When running locally, servers **SHOULD** bind only to localhost (127.0.0.1) rather than all network interfaces (0.0.0.0)."
- "Servers **SHOULD** implement proper authentication for all connections." (See §9.)

#### POST — client → server messages

- "Every JSON-RPC message sent from the client **MUST** be a new HTTP POST request to the MCP endpoint."
- "The client **MUST** include an `Accept` header, listing both `application/json` and `text/event-stream` as supported content types."
- "The body of the POST request **MUST** be a single JSON-RPC *request*, *notification*, or *response*." (Singular — recall batching is gone.)

Server responses to POST:
- For a JSON-RPC *notification* or *response* (i.e. no reply expected): **HTTP 202 Accepted with no body** on success, or a 4xx with an optional JSON-RPC error body that has no `id`.
- For a JSON-RPC *request*: the server MUST return **either** `Content-Type: application/json` with a single JSON-RPC result, **or** `Content-Type: text/event-stream` to begin an SSE stream. "The client **MUST** support both these cases."

When the server upgrades a POST to SSE it MAY interleave server→client requests and notifications related to the original request before sending the final response event, and the stream SHOULD terminate after the response is delivered.

#### GET — server → client streams

- "The client **MAY** issue an HTTP GET to the MCP endpoint." This opens an SSE stream the server can use for unsolicited messages.
- "The client **MUST** include an `Accept` header, listing `text/event-stream` as a supported content type."
- The server replies with `Content-Type: text/event-stream` **or** **`HTTP 405 Method Not Allowed`** if it does not offer an SSE stream at this endpoint.

#### `Mcp-Session-Id`

- "A server using the Streamable HTTP transport **MAY** assign a session ID at initialization time, by including it in an `Mcp-Session-Id` header on the HTTP response containing the `InitializeResult`."
- "The session ID **SHOULD** be globally unique and cryptographically secure (e.g., a securely generated UUID, a JWT, or a cryptographic hash)."
- "The session ID **MUST** only contain visible ASCII characters (ranging from 0x21 to 0x7E)."
- Clients with an assigned session ID "**MUST** include it in the `Mcp-Session-Id` header on all of their subsequent HTTP requests."
- "Servers that require a session ID **SHOULD** respond to requests without an `Mcp-Session-Id` header (other than initialization) with **HTTP 400 Bad Request**."
- A server "**MAY** terminate the session at any time, after which it **MUST** respond to requests containing that session ID with **HTTP 404 Not Found**." On 404, the client "**MUST** start a new session by sending a new `InitializeRequest` without a session ID attached."
- A client "**SHOULD** send an HTTP **DELETE** to the MCP endpoint with the `Mcp-Session-Id` header, to explicitly terminate the session." Server **MAY** answer with **HTTP 405 Method Not Allowed** if it disallows client-side termination.

#### `MCP-Protocol-Version` header

- "The client **MUST** include the `MCP-Protocol-Version: <protocol-version>` HTTP header on all subsequent requests to the MCP server."
- Example: `MCP-Protocol-Version: 2025-11-25`.
- For backwards compatibility, "if the server does *not* receive an `MCP-Protocol-Version` header, and has no other way to identify the version … the server **SHOULD** assume protocol version `2025-03-26`."
- "If the server receives a request with an invalid or unsupported `MCP-Protocol-Version`, it **MUST** respond with `400 Bad Request`."

#### Resumability and `Last-Event-ID`

When SSE event IDs are emitted, the client may resume after disconnect with the standard [`Last-Event-ID`](https://html.spec.whatwg.org/multipage/server-sent-events.html#the-last-event-id-header) header:

- "Servers **MAY** attach an `id` field to their SSE events… If present, the ID **MUST** be globally unique across all streams within that session — or all streams with that specific client, if session management is not in use. Event IDs **SHOULD** encode sufficient information to identify the originating stream."
- To resume: "issue an HTTP GET to the MCP endpoint, and include the `Last-Event-ID` header to indicate the last event ID it received. The server **MAY** use this header to replay messages that would have been sent after the last event ID, *on the stream that was disconnected*."
- **Servers MUST NOT replay messages from a different stream onto a resumption.** "Resumption is always via HTTP GET with `Last-Event-ID`."

#### When may a POST be upgraded to an SSE stream?

Whenever the request body is a JSON-RPC *request* (not a notification or response). The server decides between a one-shot JSON response and an SSE stream. SSE is appropriate when the server expects to send progress, log, or server-initiated request messages before producing the final response — for example to make use of `sampling/createMessage`, `elicitation/create`, or progress notifications mid-call.

A clarification added in `2025-11-25` (SEP-1699) explicitly allows servers to **close the underlying connection without terminating the logical stream** in order to avoid holding long-lived sockets — the client SHOULD then reconnect via GET with `Last-Event-ID` ("poll the SSE stream"). The server SHOULD send a `retry` SSE field before closing.

### 5.3 Deprecated HTTP+SSE transport (revision `2024-11-05`)

Documented for backwards compatibility at [`/specification/2024-11-05/basic/transports#http-with-sse`](https://modelcontextprotocol.io/specification/2024-11-05/basic/transports#http-with-sse). Two endpoints:

1. An **SSE endpoint** for the client to GET and receive an SSE stream. The first event the server sends **MUST** be an `endpoint` event whose data is the URI of the second endpoint.
2. An **HTTP POST endpoint** at the URI returned in the `endpoint` event. The client sends *all* outbound JSON-RPC as POSTs there; the server delivers responses as SSE `message` events back over the first stream.

This was superseded in `2025-03-26` by Streamable HTTP because the two-endpoint design forced long-lived SSE connections, made stateful session resumption awkward, complicated load balancing across replicas, and prevented servers from answering simple requests with a single HTTP response. The current spec retains a [§Backwards Compatibility](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#backwards-compatibility) section: servers wanting to support old clients keep both old endpoints alongside the new MCP endpoint; new clients first POST a probe `InitializeRequest` and fall back to the old SSE flow on 400/404/405.

### 5.4 WebSocket

Not part of the standard. The Python SDK ships a `websocket.py` transport ([`src/mcp/client/websocket.py`](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/websocket.py)) as a non-spec extension allowed by the "Custom Transports" escape hatch.

---

## 6. Server-side primitives

### 6.1 Tools

[`/specification/2025-11-25/server/tools`](https://modelcontextprotocol.io/specification/2025-11-25/server/tools). Tools are "model-controlled" — the LLM picks when to call them, although hosts SHOULD insert a human-in-the-loop confirmation.

Capability advertisement:

```json
{ "capabilities": { "tools": { "listChanged": true } } }
```

#### `tools/list` → paginated list of tools

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "get_weather",
        "title": "Weather Information Provider",
        "description": "Get current weather information for a location",
        "inputSchema": {
          "type": "object",
          "properties": {
            "location": { "type": "string", "description": "City name or zip code" }
          },
          "required": ["location"]
        },
        "execution": { "taskSupport": "optional" }
      }
    ],
    "nextCursor": "next-page-cursor"
  }
}
```

Tool fields:
- `name` — programmatic ID (1–128 chars; `A–Z a–z 0–9 _ - .`; case-sensitive; SHOULD be unique within the server).
- `title` — optional human display name.
- `description` — human-readable.
- `inputSchema` — JSON Schema object (MUST be a valid JSON Schema object; defaults to 2020-12). Spec recommends `{ "type": "object", "additionalProperties": false }` for no-argument tools.
- `outputSchema` — optional JSON Schema describing structured output; servers MUST emit conforming `structuredContent`, clients SHOULD validate.
- `annotations` — see below; **MUST be considered untrusted** unless from a trusted server.
- `execution.taskSupport` — `"forbidden"` (default), `"optional"`, or `"required"`; controls task-augmentation (§4 capabilities, §6.4 tasks).
- `icons` — optional icon array (`src`, `mimeType`, `sizes`, `theme`).

#### `tools/call`

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": { "location": "New York" }
  }
}
```

Result shape:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      { "type": "text", "text": "Current weather in New York:\nTemperature: 72°F\nConditions: Partly cloudy" }
    ],
    "isError": false
  }
}
```

#### Content types in tool results

All five share an optional `annotations` block (`audience: ["user" | "assistant"]`, `priority: 0..1`, `lastModified: ISO8601`).

- **`text`** — `{ "type": "text", "text": "..." }`
- **`image`** — `{ "type": "image", "data": "<base64>", "mimeType": "image/png" }`
- **`audio`** — `{ "type": "audio", "data": "<base64>", "mimeType": "audio/wav" }` (added in `2025-03-26`).
- **`resource_link`** — `{ "type": "resource_link", "uri": "file:///…", "name": "…", "mimeType": "…" }` (added in `2025-06-18`; PR [#603](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/603)). Note: "Resource links returned by tools are not guaranteed to appear in the results of a `resources/list` request."
- **Embedded resource** — `{ "type": "resource", "resource": { "uri": "...", "mimeType": "...", "text": "...", /* or */ "blob": "..." } }`

#### Structured output

Added in `2025-06-18`. Tools may return a `structuredContent` JSON object in addition to the `content` array. "For backwards compatibility, a tool that returns structured content SHOULD also return the serialized JSON in a TextContent block." Output schema enforcement is mandatory on the server: "Servers **MUST** provide structured results that conform to this schema. Clients **SHOULD** validate structured results against this schema."

Example with output schema (abbreviated):

```json
{
  "result": {
    "content": [
      { "type": "text", "text": "{\"temperature\": 22.5, \"conditions\": \"Partly cloudy\", \"humidity\": 65}" }
    ],
    "structuredContent": { "temperature": 22.5, "conditions": "Partly cloudy", "humidity": 65 }
  }
}
```

#### `isError` vs. JSON-RPC error

This is the single most important error-model distinction in MCP:

- **Protocol errors** (unknown tool, malformed request, server crash) are reported as **JSON-RPC error responses** (`error.code`, see §11).
- **Tool execution errors** (validation failure, upstream API failure, business-logic error) are reported as a **successful JSON-RPC `result` with `isError: true`** and the error text in the `content` array.

The reason, clarified in `2025-11-25` (SEP-1303): "Tool Execution Errors contain actionable feedback that language models can use to self-correct and retry with adjusted parameters. Protocol Errors indicate issues with the request structure itself that models are less likely to be able to fix."

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [
      { "type": "text", "text": "Invalid departure date: must be in the future. Current date is 08/08/2025." }
    ],
    "isError": true
  }
}
```

#### Tool annotations

Optional and untrusted-by-default. From the [Tool type definition](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#tool):

- `title` — display name.
- `readOnlyHint` — boolean; tool does not modify external state.
- `destructiveHint` — boolean; calling the tool may destroy data.
- `idempotentHint` — boolean; repeated calls have the same effect.
- `openWorldHint` — boolean; the tool may have side effects outside the host's universe.

Spec warning: **"Clients MUST consider tool annotations to be untrusted unless they come from trusted servers."** Annotations are advisory UI hints, not security boundaries.

#### `notifications/tools/list_changed`

```json
{ "jsonrpc": "2.0", "method": "notifications/tools/list_changed" }
```

Sent only when the server advertised `tools.listChanged: true`.

### 6.2 Resources

[`/specification/2025-11-25/server/resources`](https://modelcontextprotocol.io/specification/2025-11-25/server/resources). Resources are **application-driven** — the host picks what to include in context.

Capabilities (`subscribe` and `listChanged` are independently optional):

```json
{ "capabilities": { "resources": { "subscribe": true, "listChanged": true } } }
```

#### `resources/list`

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resources": [
      {
        "uri": "file:///project/src/main.rs",
        "name": "main.rs",
        "title": "Rust Software Application Main File",
        "description": "Primary application entry point",
        "mimeType": "text/x-rust"
      }
    ],
    "nextCursor": "next-page-cursor"
  }
}
```

#### `resources/read`

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "resources/read",
  "params": { "uri": "file:///project/src/main.rs" }
}
```

Result `contents` is an array of either:

```json
{ "uri": "file:///example.txt", "mimeType": "text/plain", "text": "Resource content" }
```

or for binary:

```json
{ "uri": "file:///example.png", "mimeType": "image/png", "blob": "<base64>" }
```

#### URI templates — `resources/templates/list`

Resources may be parameterized with [RFC 6570](https://datatracker.ietf.org/doc/html/rfc6570) URI templates:

```json
{
  "result": {
    "resourceTemplates": [
      {
        "uriTemplate": "file:///{path}",
        "name": "Project Files",
        "description": "Access files in the project directory",
        "mimeType": "application/octet-stream"
      }
    ]
  }
}
```

The `{path}` parameter is fillable via the completion API (§6.3) by sending a `completion/complete` with `ref: { type: "ref/resource", uri: "file:///{path}" }`.

#### `resources/subscribe` / `resources/unsubscribe`

```json
{ "jsonrpc": "2.0", "id": 4, "method": "resources/subscribe",
  "params": { "uri": "file:///project/src/main.rs" } }
```

Server emits:

```json
{ "jsonrpc": "2.0", "method": "notifications/resources/updated",
  "params": { "uri": "file:///project/src/main.rs" } }
```

#### `notifications/resources/list_changed`

Emitted when `resources.listChanged: true` and the server's resource set changes.

#### URI schemes

The spec defines `https://`, `file://`, `git://`, and allows custom schemes per [RFC 3986](https://datatracker.ietf.org/doc/html/rfc3986). `https://` is reserved for resources "the client is able to fetch and load … directly from the web on its own — that is, it doesn't need to read the resource via the MCP server." Server-rendered content should use a different scheme.

Resource-not-found uses an MCP-flavored JSON-RPC code:

```json
{ "jsonrpc": "2.0", "id": 5, "error": { "code": -32002, "message": "Resource not found", "data": { "uri": "file:///nonexistent.txt" } } }
```

### 6.3 Prompts

[`/specification/2025-11-25/server/prompts`](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts). Prompts are **user-controlled** (e.g. slash commands).

#### `prompts/list`

```json
{
  "result": {
    "prompts": [
      {
        "name": "code_review",
        "title": "Request Code Review",
        "description": "Asks the LLM to analyze code quality and suggest improvements",
        "arguments": [
          { "name": "code", "description": "The code to review", "required": true }
        ]
      }
    ],
    "nextCursor": "next-page-cursor"
  }
}
```

#### `prompts/get`

```json
{ "method": "prompts/get",
  "params": { "name": "code_review", "arguments": { "code": "def hello():\n    print('world')" } } }
```

Returns a list of `PromptMessage` objects (each `role` ∈ `{user, assistant}`, each `content` one of the same content types as tool results: text, image, audio, embedded resource):

```json
{
  "result": {
    "description": "Code review prompt",
    "messages": [
      { "role": "user",
        "content": { "type": "text", "text": "Please review this Python code:\ndef hello():\n    print('world')" } }
    ]
  }
}
```

#### Argument completion — `completion/complete`

[`/specification/2025-11-25/server/utilities/completion`](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/completion). Server capability `completions: {}`.

```json
{
  "method": "completion/complete",
  "params": {
    "ref": { "type": "ref/prompt", "name": "code_review" },
    "argument": { "name": "language", "value": "py" },
    "context": { "arguments": { /* previously resolved args */ } }
  }
}
```

Response:

```json
{
  "result": {
    "completion": { "values": ["python", "pytorch", "pyside"], "total": 10, "hasMore": true }
  }
}
```

`ref.type` is `"ref/prompt"` (by name) or `"ref/resource"` (by URI template). Max **100 items per response**. The `context.arguments` field (added `2025-06-18`, PR [#598](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/598)) carries previously resolved arguments so the server can produce dependent suggestions.

#### `notifications/prompts/list_changed`

Sent when `prompts.listChanged: true`.

---

## 7. Client-side primitives (server → client requests)

These flow *from* server *to* client. The client decides whether to satisfy them (typically by asking the user).

### 7.1 Sampling — `sampling/createMessage`

[`/specification/2025-11-25/client/sampling`](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling). A server asks the client to run an LLM completion on its behalf — useful when a tool implementation wants to "use the model" without bundling an LLM SDK or knowing the user's API key.

Capability:

```json
{ "capabilities": { "sampling": {} } }
```

Sub-keys (in `2025-11-25`):
- `sampling.tools` — client supports tool-use within sampling (added in `2025-11-25` via [SEP-1577](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1577)).
- `sampling.context` — soft-deprecated; was for `includeContext: "thisServer" | "allServers"`.

Basic request:

```json
{
  "jsonrpc": "2.0", "id": 1,
  "method": "sampling/createMessage",
  "params": {
    "messages": [
      { "role": "user", "content": { "type": "text", "text": "What is the capital of France?" } }
    ],
    "modelPreferences": {
      "hints": [ { "name": "claude-3-sonnet" } ],
      "intelligencePriority": 0.8,
      "speedPriority": 0.5
    },
    "systemPrompt": "You are a helpful assistant.",
    "maxTokens": 100
  }
}
```

Response:

```json
{
  "result": {
    "role": "assistant",
    "content": { "type": "text", "text": "The capital of France is Paris." },
    "model": "claude-3-sonnet-20240307",
    "stopReason": "endTurn"
  }
}
```

#### Model preferences

`modelPreferences` lets servers express *intent* without naming a specific model the client may not have:

- `costPriority`, `speedPriority`, `intelligencePriority` — three normalized 0..1 priorities.
- `hints: [{ name: string }, …]` — soft model-name substrings; "Clients **MAY** map hints to equivalent models from different providers."
- "Hints are advisory — clients make final model selection."

#### Tool use in sampling (new in `2025-11-25`)

Servers may pass a `tools: […]` array and `toolChoice: { mode: "auto"|"required"|"none" }`. The client routes through its LLM, and may answer with `stopReason: "toolUse"` and a content array containing `ToolUseContent`. The server executes the tools and submits results back via another `sampling/createMessage` with appended `ToolResultContent` items (matched by `toolUseId`). Strict rules:

- "When a user message contains tool results (`type: tool_result`), it **MUST** contain ONLY tool results."
- "Every assistant message containing `ToolUseContent` blocks **MUST** be followed by a user message that consists entirely of `ToolResultContent` blocks, with each tool use (e.g. with `id: $id`) matched by a corresponding tool result (with `toolUseId: $id`)."

These constraints exist to map cleanly onto OpenAI's `tool` role, Gemini's `function` role, and Anthropic's tool-use messages.

#### Human-in-the-loop

The sampling page contains the strongest user-consent language in the spec:

> "For trust & safety and security, there **SHOULD** always be a human in the loop with the ability to deny sampling requests. Applications **SHOULD**: Provide UI that makes it easy and intuitive to review sampling requests; Allow users to view and edit prompts before sending; Present generated responses for review before delivery."

Servers see only what the client lets them see. The architecture principle "Servers should not be able to read the whole conversation" (§2) is concretely enforced here: the host decides what messages to forward to the LLM, and whether to mask any output before returning it.

A user-rejection is represented as a JSON-RPC error with **code `-1`** in the sampling response:

```json
{ "jsonrpc": "2.0", "id": 3, "error": { "code": -1, "message": "User rejected sampling request" } }
```

### 7.2 Roots — `roots/list`

[`/specification/2025-11-25/client/roots`](https://modelcontextprotocol.io/specification/2025-11-25/client/roots). Roots define the filesystem/URI boundaries the client is willing to let the server see.

Capability (client side):

```json
{ "capabilities": { "roots": { "listChanged": true } } }
```

Request (server → client):

```json
{ "jsonrpc": "2.0", "id": 1, "method": "roots/list" }
```

Response:

```json
{
  "result": {
    "roots": [
      { "uri": "file:///home/user/projects/myproject", "name": "My Project" }
    ]
  }
}
```

- `uri` **MUST** currently be a `file://` URI (per the data-types section).
- A client that does not support roots returns `-32601` (Method not found).

`notifications/roots/list_changed`:

```json
{ "jsonrpc": "2.0", "method": "notifications/roots/list_changed" }
```

### 7.3 Elicitation — `elicitation/create`

[`/specification/2025-11-25/client/elicitation`](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation). Added in `2025-06-18` (PR [#382](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/382)). Extended in `2025-11-25` with **URL mode** (PR [#887](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/887)).

Capability (client side):

```json
{ "capabilities": { "elicitation": { "form": {}, "url": {} } } }
```

For backwards compatibility, `"elicitation": {}` is equivalent to `"elicitation": { "form": {} }`. Clients declaring `elicitation` **MUST** support at least one of `form` or `url`. Servers **MUST NOT** send a mode the client did not declare.

#### Form mode

In-band structured data with a flat-object JSON-Schema subset (strings, numbers, booleans, enums — single- and multi-select, with or without titles). Example:

```json
{
  "method": "elicitation/create",
  "params": {
    "mode": "form",
    "message": "Please provide your GitHub username",
    "requestedSchema": {
      "type": "object",
      "properties": { "name": { "type": "string" } },
      "required": ["name"]
    }
  }
}
```

Response uses a tri-state action model:

```json
{
  "result": {
    "action": "accept",   // or "decline" or "cancel"
    "content": { "name": "octocat" }
  }
}
```

- `accept` — user submitted (form data in `content`).
- `decline` — user explicitly said no.
- `cancel` — user dismissed without choosing (e.g. closed the dialog).

**Servers MUST NOT request sensitive information (passwords, API keys, etc.) via form mode.**

#### URL mode

For out-of-band interactions that must not pass through the MCP client (OAuth flows, payment, sensitive credentials). Example:

```json
{
  "method": "elicitation/create",
  "params": {
    "mode": "url",
    "elicitationId": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://mcp.example.com/ui/set_api_key",
    "message": "Please provide your API key to continue."
  }
}
```

`accept` here means the user consented to navigate; the actual interaction completes out-of-band. The server may then notify:

```json
{ "jsonrpc": "2.0", "method": "notifications/elicitation/complete",
  "params": { "elicitationId": "550e8400-e29b-41d4-a716-446655440000" } }
```

Servers can also embed a URL mode elicitation in a JSON-RPC error to signal "this request requires a URL elicitation first":

```json
{
  "jsonrpc": "2.0", "id": 2,
  "error": {
    "code": -32042,
    "message": "This request requires more information.",
    "data": {
      "elicitations": [
        { "mode": "url", "elicitationId": "550e8400…",
          "url": "https://mcp.example.com/connect?elicitationId=550e8400…",
          "message": "Authorization is required to access your Example Co files." }
      ]
    }
  }
}
```

`-32042` is the only MCP-specific error code in the schema (constant name `URL_ELICITATION_REQUIRED`).

URL-mode clients **MUST NOT** auto-fetch or auto-open the URL; **MUST** display the full URL; **MUST** open it in an isolated surface that cannot inspect content (e.g. iOS `SFSafariViewController`, *not* `WKWebView`). Servers **MUST NOT** pre-authenticate the URL, **MUST NOT** include user PII in it, and **MUST** verify the user who completes the flow is the user who started it (anti-phishing).

URL mode is *not* a substitute for MCP authorization (§9); it's the mechanism for **third-party** authorization where the MCP server acts as an OAuth client to some other service on behalf of the user.

---

## 8. Notifications — complete list

From the [`2025-11-25` schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-11-25/schema.ts):

| Method                                   | Direction         | Purpose                                                                  |
|------------------------------------------|-------------------|--------------------------------------------------------------------------|
| `notifications/initialized`              | client → server   | Sent once, after the `initialize` response, before normal operation.     |
| `notifications/cancelled`                | both              | Cancel an in-flight request by ID. `params: { requestId, reason? }`. **Initialize MUST NOT be cancelled.** ([§Cancellation](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)) |
| `notifications/progress`                 | both              | Progress for a request that carried a `progressToken` in `_meta`. `params: { progressToken, progress, total?, message? }`. Progress **MUST** increase monotonically. ([§Progress](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress)) |
| `notifications/message`                  | server → client   | Structured log entry. `params: { level, logger?, data }` where `level` is one of the 8 RFC 5424 severities (`debug, info, notice, warning, error, critical, alert, emergency`). ([§Logging](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging)) |
| `notifications/resources/updated`        | server → client   | A subscribed resource changed. `params: { uri }`.                        |
| `notifications/resources/list_changed`   | server → client   | The list of resources changed (server has `resources.listChanged`).      |
| `notifications/tools/list_changed`       | server → client   | The list of tools changed (server has `tools.listChanged`).              |
| `notifications/prompts/list_changed`     | server → client   | The list of prompts changed (server has `prompts.listChanged`).          |
| `notifications/roots/list_changed`       | client → server   | Roots changed (client has `roots.listChanged`).                          |
| `notifications/elicitation/complete`     | server → client   | URL-mode elicitation has completed out-of-band. `params: { elicitationId }`. |
| `notifications/tasks/status`             | both              | Optional status update for a task (experimental, §6.4).                  |

Verbosity is controlled by `logging/setLevel`:

```json
{ "method": "logging/setLevel", "params": { "level": "info" } }
```

After which the server SHOULD suppress messages below `info`.

---

## 9. Authorization — remote (HTTP) MCP servers

The auth spec ([`/specification/2025-11-25/basic/authorization`](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)) is normative for HTTP transports and explicitly out of scope for stdio. It is the densest part of MCP — read it twice.

### 9.1 OAuth 2.1 baseline

The spec composes the following IETF/OAuth documents (verbatim from §Standards Compliance):

- **OAuth 2.1** — IETF draft [`draft-ietf-oauth-v2-1-13`](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13).
- **OAuth 2.0 Authorization Server Metadata** — [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414).
- **OAuth 2.0 Dynamic Client Registration Protocol** — [RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591).
- **OAuth 2.0 Protected Resource Metadata** — [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728).
- **OAuth Client ID Metadata Documents** — [`draft-ietf-oauth-client-id-metadata-document-00`](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00) (new recommended client-registration approach in `2025-11-25`).
- **PKCE** — [RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636).
- **Resource Indicators for OAuth 2.0** — [RFC 8707](https://www.rfc-editor.org/rfc/rfc8707.html).

OAuth 2.1 hardens OAuth 2.0 in three concrete ways relevant here:

1. **PKCE is mandatory.** OAuth 2.1 §4.1.1: "Clients MUST use `code_challenge` and `code_verifier` and authorization servers MUST enforce their use except under the conditions described in Section 7.5.1." The MCP spec doubles down: MCP clients **MUST** verify PKCE support by inspecting `code_challenge_methods_supported` in the AS metadata before proceeding, and **MUST** use `S256` when technically capable.
2. **Implicit grant is removed.** OAuth 2.1 §10.1 ("Removal of the OAuth 2.0 Implicit grant").
3. **Resource owner password credentials grant is removed.** OAuth 2.1 omits it entirely.

OAuth 2.1 §1.5 also requires HTTPS for all endpoints except `localhost` loopback redirects.

### 9.2 Roles

- **MCP server = OAuth 2.1 resource server** ([`draft-ietf-oauth-v2-1-13` §Roles](https://www.ietf.org/archive/id/draft-ietf-oauth-v2-1-13.html#name-roles)).
- **MCP client = OAuth 2.1 client.**
- **Authorization server (AS)** is a *separate* entity. It "may be hosted with the resource server or a separate entity." MCP servers point clients at the AS through Protected Resource Metadata (below).

### 9.3 Discovery flow

The canonical flow (verbatim from the spec, condensed):

1. Client makes an unauthenticated MCP request → server returns **`401 Unauthorized`**, optionally with a `WWW-Authenticate` header.
2. Client extracts the Protected Resource Metadata URL from the header **or** falls back to well-known probing.
3. Client fetches Protected Resource Metadata → identifies one or more authorization servers.
4. Client fetches AS metadata (OAuth or OpenID Connect Discovery).
5. Client registers (or reuses prior credentials) and runs the OAuth 2.1 authorization-code flow with PKCE.
6. Client uses the access token as `Authorization: Bearer …` on subsequent MCP requests.

#### `WWW-Authenticate` parsing

Per RFC 9728 §5.1 and MCP §Protected Resource Metadata Discovery, a 401 response looks like:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource",
                         scope="files:read"
```

Notes:
- `resource_metadata` carries the absolute URL of the Protected Resource Metadata document.
- `scope` (RFC 6750 §3) is the **scope guidance** the client should request — possibly distinct from `scopes_supported`. "Clients **MUST** treat the scopes provided in the challenge as authoritative for satisfying the current request."
- Spec change in `2025-11-25`: the `WWW-Authenticate` header is now **optional** with mandatory fallback to well-known probing ([SEP-985](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/985), aligning with RFC 9728).

#### Well-known fallback for Protected Resource Metadata

If `WWW-Authenticate` lacks `resource_metadata`, the client tries (in order):

1. If the MCP endpoint is at `https://example.com/public/mcp`, fetch `https://example.com/.well-known/oauth-protected-resource/public/mcp`.
2. Then fetch `https://example.com/.well-known/oauth-protected-resource` (root form).

Default well-known path: `/.well-known/oauth-protected-resource` ([RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728)).

#### Protected Resource Metadata document

Per RFC 9728, this is a JSON document including (at minimum) the `authorization_servers` array — a list of issuer URLs the client should use to obtain tokens for this resource. The MCP spec requires `authorization_servers` and notes that selection between multiple ASes follows [RFC 9728 §7.6](https://datatracker.ietf.org/doc/html/rfc9728#section-7.6).

```json
{
  "resource": "https://mcp.example.com",
  "authorization_servers": ["https://auth.example.com"],
  "scopes_supported": ["mcp:tools-basic", "files:read", "files:write"],
  "bearer_methods_supported": ["header"]
}
```

#### AS metadata discovery (RFC 8414 / OIDC Discovery 1.0)

`2025-11-25` added OIDC Discovery as a co-equal mechanism (PR [#797](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/797)). For issuer `https://auth.example.com/tenant1` the client tries, in order:

1. `https://auth.example.com/.well-known/oauth-authorization-server/tenant1` — RFC 8414 §3.1 "path insertion."
2. `https://auth.example.com/.well-known/openid-configuration/tenant1` — OIDC with path insertion.
3. `https://auth.example.com/tenant1/.well-known/openid-configuration` — OIDC path appending (legacy form).

For issuer `https://auth.example.com` (no path), the order is:

1. `https://auth.example.com/.well-known/oauth-authorization-server`
2. `https://auth.example.com/.well-known/openid-configuration`

The AS metadata response (RFC 8414 §2) must include at minimum `issuer` (HTTPS, no query/fragment), `authorization_endpoint`, `response_types_supported`, and almost always `token_endpoint`. For MCP additionally:

- `code_challenge_methods_supported` MUST be present (and SHOULD include `S256`) — MCP clients **MUST refuse to proceed** if it is missing.
- `registration_endpoint` if Dynamic Client Registration is offered.
- `client_id_metadata_document_supported: true` if Client ID Metadata Documents are offered.

### 9.4 Client registration

`2025-11-25` introduces a priority order for registration:

1. **Pre-registered credentials** when the client already has them.
2. **Client ID Metadata Documents** (new in `2025-11-25` via [SEP-991](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/991)) — client hosts a JSON metadata document at an HTTPS URL and uses that URL as its `client_id`. AS fetches the URL, validates that `client_id` inside equals the URL, and uses the document's `redirect_uris`. Example document:

   ```json
   {
     "client_id": "https://app.example.com/oauth/client-metadata.json",
     "client_name": "Example MCP Client",
     "redirect_uris": ["http://127.0.0.1:3000/callback", "http://localhost:3000/callback"],
     "grant_types": ["authorization_code"],
     "response_types": ["code"],
     "token_endpoint_auth_method": "none"
   }
   ```

3. **Dynamic Client Registration ([RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591))** — fallback for backwards compatibility. The client POSTs JSON to `registration_endpoint` with at least `redirect_uris`, `client_name`, `grant_types`, `response_types`, `token_endpoint_auth_method`; the server returns `client_id` (required), `client_secret` (optional), `client_id_issued_at` (optional), and `client_secret_expires_at` (required if a secret was issued). HTTP **201 Created** on success.

### 9.5 PKCE flow ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636))

End-to-end:

1. Client generates `code_verifier`: a cryptographically random 43–128-character string of `[A-Z][a-z][0-9]-._~`. Minimum 256 bits of entropy recommended.
2. Client computes `code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))` for `code_challenge_method=S256`. MCP **MUST** use `S256` when capable.
3. Authorization request to `authorization_endpoint`:

   ```
   GET /authorize?
       response_type=code
       &client_id=<client_id>
       &redirect_uri=<registered_uri>
       &state=<random>
       &code_challenge=<challenge>
       &code_challenge_method=S256
       &scope=<scopes>
       &resource=https%3A%2F%2Fmcp.example.com
   ```

4. User authenticates and consents; AS redirects to `redirect_uri` with `code=<authz_code>&state=<random>`. Client verifies `state`.
5. Token request to `token_endpoint`:

   ```
   POST /token  HTTP/1.1
   Content-Type: application/x-www-form-urlencoded

   grant_type=authorization_code
   &code=<authz_code>
   &redirect_uri=<registered_uri>
   &client_id=<client_id>
   &code_verifier=<verifier>
   &resource=https%3A%2F%2Fmcp.example.com
   ```

6. AS responds:

   ```json
   {
     "access_token": "eyJhbGciOi...",
     "token_type": "Bearer",
     "expires_in": 3600,
     "refresh_token": "...",
     "scope": "files:read"
   }
   ```

### 9.6 Token usage

Per OAuth 2.1 §5.1.1 and MCP §Access Token Usage:

- "MCP client **MUST** use the Authorization request header field … `Authorization: Bearer <access-token>`."
- "Authorization **MUST** be included in every HTTP request from client to server, even if they are part of the same logical session."
- "Access tokens **MUST NOT** be included in the URI query string."

Example:

```http
GET /mcp HTTP/1.1
Host: mcp.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Mcp-Session-Id: 1868a90c-…
MCP-Protocol-Version: 2025-11-25
```

### 9.7 Audience binding ([RFC 8707](https://www.rfc-editor.org/rfc/rfc8707.html))

This is the single most important security primitive for remote MCP servers. RFC 8707 defines a `resource` parameter sent in both the authorization request and the token request to indicate the protected resource the token will be presented to. The AS then audience-restricts the issued token (typically by placing an `aud` claim in a JWT).

MCP requirements (§Resource Parameter Implementation):

- The `resource` parameter **MUST** be included in **both** authorization and token requests.
- It **MUST** identify the MCP server the client intends to use the token with.
- It **MUST** use the canonical URI (RFC 8707 §2): absolute URI, lowercase scheme/host, no fragment. Examples: `https://mcp.example.com/mcp`, `https://mcp.example.com:8443`, `https://mcp.example.com/server/mcp`. Invalid: `mcp.example.com` (no scheme), `https://mcp.example.com#fragment`.
- "MCP clients **MUST** send this parameter regardless of whether authorization servers support it."

On the server side:

- "MCP servers, acting in their role as an OAuth 2.1 resource server, **MUST** validate access tokens as described in OAuth 2.1 §5.2."
- "MCP servers **MUST** validate that access tokens were issued specifically for them as the intended audience, according to RFC 8707 §2."
- "MCP servers **MUST NOT** accept or transit any other tokens."

Why this matters — confused-deputy: if an MCP server accepted a token issued for service Y, an attacker could obtain a token for service Y (e.g. by tricking a user into installing a malicious MCP client) and replay it against the MCP server, which would dutifully forward authorized actions. Audience-binding makes this attack fail at the token-validation step.

### 9.8 Refresh tokens, scopes, revocation

- **Refresh tokens**: OAuth 2.1 §4.3.1. "Authorization servers **SHOULD** issue short-lived access tokens to reduce the impact of leaked tokens. For public clients, authorization servers **MUST** rotate refresh tokens" (i.e. new refresh on every refresh exchange).
- **Scopes**: MCP defines a scope selection strategy. "MCP clients **SHOULD** request only the scopes necessary." Priority order: (1) use the `scope` from the latest `WWW-Authenticate`, (2) otherwise use `scopes_supported` from Protected Resource Metadata, (3) otherwise omit. The `scopes_supported` set "is intended to represent the minimal set of scopes necessary for basic functionality"; broader scopes are obtained incrementally via step-up flows.
- **Step-up authorization**: when the client's token lacks a scope, the server returns:

  ```http
  HTTP/1.1 403 Forbidden
  WWW-Authenticate: Bearer error="insufficient_scope",
                           scope="files:read files:write user:profile",
                           resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource",
                           error_description="Additional file write permission required"
  ```

  Client parses, requests a new token with the elevated scope set, and retries.
- **Revocation**: [RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009). Token revocation endpoint accepts a `POST` of `application/x-www-form-urlencoded` with `token=<token>&token_type_hint=access_token|refresh_token`. Server responds **HTTP 200** regardless of whether the token was valid. Revoking a refresh token SHOULD revoke its associated access tokens.

### 9.9 401 / 403 semantics

| Code | Use                                                                                                                 |
|------|---------------------------------------------------------------------------------------------------------------------|
| 401  | Authorization required or token invalid/expired. Always with a `WWW-Authenticate: Bearer …` header.                 |
| 403  | Token is otherwise valid but the scopes are insufficient — `WWW-Authenticate: Bearer error="insufficient_scope"`.   |
| 400  | Malformed authorization request.                                                                                    |

Behavior on 401: re-run discovery + auth flow. On 403: step-up scopes. Re-auth is a permanent failure path after a small number of retries — "Clients **SHOULD** implement retry limits and **SHOULD** track scope upgrade attempts to avoid repeated failures for the same resource and operation combination."

### 9.10 Separation of AS and RS

The MCP server is the resource server. The authorization server is typically a separate identity provider (Auth0, Okta, Workspace, Entra, GitHub, an in-house IdP, …) — "It may be hosted with the resource server or a separate entity." The implementation details of the AS are explicitly out of MCP's scope; the MCP spec only constrains the discovery hand-off (RFC 9728 → RFC 8414/OIDC) and the audience binding (RFC 8707).

### 9.11 Reference: Python SDK implementation

Cross-checked against [`src/mcp/client/auth/oauth2.py`](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py). The `async_auth_flow` HTTPX flow does, in order: parse `WWW-Authenticate` for `resource_metadata` (`extract_resource_metadata_from_www_auth`), probe `.well-known/oauth-protected-resource` URLs (`build_protected_resource_metadata_discovery_urls`), then probe OAuth and OIDC AS metadata (`build_oauth_authorization_server_metadata_discovery_urls`), generate PKCE (`PKCEParameters.generate()` with a 128-char verifier and `base64.urlsafe_b64encode(SHA256(verifier))` for `S256`), include `resource=…` on auth and token requests (`should_include_resource_param`), exchange code via `_exchange_token_authorization_code`, attach `Authorization: Bearer …` via `_add_auth_header`, and optionally Dynamic-Client-Register via `create_client_registration_request` → `handle_registration_response`. This is the authoritative reference implementation and confirms the spec is implementable as written.

---

## 10. Authorization — local (stdio) MCP servers

The auth spec is explicit: **"Implementations using an STDIO transport SHOULD NOT follow this specification, and instead retrieve credentials from the environment."**

This is a deliberate non-feature. The reasoning:

- A stdio server is a child process of the client. Its trust boundary is the OS process boundary of the user who launched the client. There is no remote attacker to authenticate against.
- The transport has no header surface, no in-band metadata channel, and no clear UI for OAuth flows.
- Local file-system access, shell-out, and process privileges all already follow user-level OS permissions.

In practice:

- **API keys / third-party tokens** are passed to the server via environment variables — set in the client's MCP server config (Claude Desktop's `claude_desktop_config.json`, VS Code's `mcp.json`, etc.). The MCP spec does not standardize the config format, but every host implements an `env: { … }` map.
- **User-level credentials** (the MCP server connecting on behalf of the user to something like GitHub) typically use the system keychain via the server's own code, or they re-run an OAuth flow with the user's browser as the user-agent and persist tokens to a per-user file. None of that is MCP.
- **Multi-tenancy** does not apply: a stdio server is launched per host instance per user.

This is also why the Security Best Practices document covers "Local MCP Server Compromise" separately ([§Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)): the risk is *the server itself being malicious* (npm package compromise, supply-chain attack, malicious startup command in a shared config), not network impersonation. Hosts MUST present a consent dialog with the exact command line before launching a one-click local MCP server. See §13.

---

## 11. Error model

### Standard JSON-RPC base codes

From the schema and from [JSON-RPC 2.0 §5.1](https://www.jsonrpc.org/specification#error_object):

| Constant            | Code      | Meaning                                                       |
|---------------------|-----------|---------------------------------------------------------------|
| `PARSE_ERROR`       | `-32700`  | Invalid JSON received.                                        |
| `INVALID_REQUEST`   | `-32600`  | Not a valid request object.                                   |
| `METHOD_NOT_FOUND`  | `-32601`  | Method does not exist or unsupported by capability.           |
| `INVALID_PARAMS`    | `-32602`  | Invalid method parameters (also: missing args, bad cursor).   |
| `INTERNAL_ERROR`    | `-32603`  | Internal JSON-RPC error / generic server-side failure.        |

JSON-RPC reserves `-32000` to `-32099` for implementation-defined server errors.

### MCP-specific codes

- **`-32042` (`URL_ELICITATION_REQUIRED`)** — server signaling "this request requires a URL-mode elicitation to complete first" (§7.3).
- **`-32002`** — used by `resources/read` for "Resource not found" (with `data.uri`). Not a global MCP constant but a documented convention in [the Resources spec](https://modelcontextprotocol.io/specification/2025-11-25/server/resources#error-handling).
- **`-1`** — convention for "User rejected sampling request" ([Sampling §Error Handling](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling#error-handling)). This is outside the JSON-RPC reserved range; treat it as protocol convention rather than a formal MCP-defined code.

### Protocol errors vs. tool execution errors

Already discussed in §6.1. To recap:

- **Protocol error** → JSON-RPC error response. Examples: unknown tool name, bad params, server crash, transport-level failure.
- **Tool execution error** → JSON-RPC *result* response with `isError: true` and human-readable explanation in `content`. Examples: input validation, upstream API error, business rule violation. Designed for LLM self-correction.

Clients SHOULD pass tool execution errors back to the LLM; they MAY pass protocol errors, but "these are less likely to result in successful recovery."

---

## 12. Versioning and revisions

`protocolVersion` is a date string (`YYYY-MM-DD`) negotiated at `initialize`:

> "In the `initialize` request, the client **MUST** send a protocol version it supports. This **SHOULD** be the *latest* version supported by the client. If the server supports the requested protocol version, it **MUST** respond with the same version. Otherwise, the server **MUST** respond with another protocol version it supports. This **SHOULD** be the *latest* version supported by the server. If the client does not support the version in the server's response, it **SHOULD** disconnect." ([Lifecycle §Version Negotiation](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle#version-negotiation))

In practice this is *not* a "pick the highest mutually supported" — the client proposes one, the server either accepts or counter-proposes one (typically the server's highest), and the client decides whether to accept that counter-proposal or disconnect. Two well-behaved peers each picking "latest" therefore converge in two rounds.

### Known revisions

| Date         | Headline changes                                                                                                                                                                                                                                                                                                                                                            |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `2024-11-05` | Initial public revision. Tools, resources, prompts, sampling, roots. stdio + HTTP+SSE transports. No authorization in spec. ([overview](https://modelcontextprotocol.io/specification/2024-11-05/)) |
| `2025-03-26` | Added OAuth 2.1 authorization framework (PR [#133](https://github.com/modelcontextprotocol/specification/pull/133)). Replaced HTTP+SSE with **Streamable HTTP** (PR [#206](https://github.com/modelcontextprotocol/specification/pull/206)). Added JSON-RPC batching (PR [#228](https://github.com/modelcontextprotocol/specification/pull/228)). Added tool **annotations** (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) (PR [#185](https://github.com/modelcontextprotocol/specification/pull/185)). Added `audio` content type. Added `completions` capability. Added `message` field to `ProgressNotification`. ([changelog](https://modelcontextprotocol.io/specification/2025-03-26/changelog)) |
| `2025-06-18` | **Removed JSON-RPC batching** (PR [#416](https://github.com/modelcontextprotocol/specification/pull/416)). Added structured tool output (`outputSchema`, `structuredContent`). Classified MCP servers as **OAuth Resource Servers** and required RFC 9728 Protected Resource Metadata. **Required RFC 8707 Resource Indicators** in clients. Added [Security Best Practices](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices). Added **elicitation** (form mode). Added `resource_link` content type in tool results. Required `MCP-Protocol-Version` header on subsequent HTTP requests. Added `title` field for human-friendly display names alongside programmatic `name`. Added `context` field to `CompletionRequest`. ([changelog](https://modelcontextprotocol.io/specification/2025-06-18/changelog)) |
| `2025-11-25` | Added **URL mode** elicitation (PR [#887](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/887)). Added tool-use within sampling (`tools`, `toolChoice`; [SEP-1577](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1577)). Added **OAuth Client ID Metadata Documents** ([SEP-991](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/991)). Added **OIDC Discovery 1.0** as a co-equal AS-discovery mechanism (PR [#797](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/797)). Added incremental scope consent via `WWW-Authenticate` ([SEP-835](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/835)). Made `WWW-Authenticate` header optional with mandatory well-known fallback ([SEP-985](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/985)). Added experimental **tasks** primitive ([SEP-1686](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1686)). Added `icons` metadata across tools/resources/prompts ([SEP-973](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/973)). Established **JSON Schema 2020-12** as the default dialect ([SEP-1613](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1613)). Clarified that stdio `stderr` may carry all log levels (PR [#670](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/670)). Clarified that Streamable HTTP servers MUST return 403 on invalid `Origin` (PR [#1439](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1439)). Allowed servers to disconnect SSE streams at will to support polling ([SEP-1699](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1699)). Added default values to elicitation schema primitives ([SEP-1034](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1034)). Reframed enum schemas to support titled/untitled, single-/multi-select ([SEP-1330](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1330)). Decoupled request payloads from RPC method definitions in the schema ([SEP-1319](https://github.com/modelcontextprotocol/specification/issues/1319)). ([full changelog](https://modelcontextprotocol.io/specification/2025-11-25/changelog)) |

The Streamable HTTP `MCP-Protocol-Version` rules also encode a one-step backwards-compatibility default: when a server receives an HTTP request *without* the header, it SHOULD assume `2025-03-26` (the first revision that defined Streamable HTTP).

---

## 13. Security considerations

The auth spec and the dedicated [Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices) page together enumerate the threat model. Key items:

### 13.1 Confused deputy

When an MCP "proxy server" sits in front of a third-party API as an OAuth client and uses a *static* third-party `client_id` while letting MCP clients *dynamically register* their own MCP-side `client_id`s, an attacker can chain a stale consent cookie to obtain an MCP authorization code without user consent. Mitigation: per-MCP-client consent screens *before* forwarding to the third-party AS, `__Host-`-prefixed signed consent cookies bound to MCP `client_id`, exact `redirect_uri` matching, cryptographic `state` parameter validated at the callback, and `state` cookies set only *after* explicit consent. See the spec for the full sequence diagram.

### 13.2 Token theft and audience hijack

Two failure modes:

1. **Audience validation failure** — an MCP server accepts a token issued for some other service. Mitigation: validate `aud` per [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068.html) (when JWTs are used) or equivalent introspection.
2. **Token passthrough** — an MCP server reuses the client's token to call an upstream API. **Forbidden:** "If the MCP server makes requests to upstream APIs, it may act as an OAuth client to them. The access token used at the upstream API is a separate token, issued by the upstream authorization server. The MCP server **MUST NOT** pass through the token it received from the MCP client."

The defense-in-depth requirement: clients **MUST** include `resource` (RFC 8707) on every auth and token request, and servers **MUST** reject tokens whose audience doesn't match.

### 13.3 Prompt injection via tool descriptions and resource content

The spec does not deeply specify this — it is an LLM-layer concern rather than a protocol-layer one — but flags it through the "untrusted annotations" requirement and the host's responsibility to expose tools' descriptions to the user before invocation: "Clients **SHOULD** prompt for user confirmation on sensitive operations; show tool inputs to the user before calling the server, to avoid malicious or accidental data exfiltration; validate tool results before passing to LLM."

In practice, hosts should treat tool descriptions, tool names, resource contents, and prompt templates received from a server as **untrusted input** that may try to manipulate the model. Sandboxing the model's interpretation (e.g., spotlighting), explicit allow-listing of file paths and URLs, and human-in-the-loop confirmation on destructive operations are mitigations the protocol expects but cannot enforce.

### 13.4 Sampling consent UX

`sampling/createMessage` is the largest privilege a server can request. The spec mandates ([§User Interaction Model](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling#user-interaction-model)):

- The user can deny.
- The user can view/edit the prompt before it is sent to the model.
- The user can review the generated response before it is returned to the server.
- "The protocol intentionally limits server visibility into prompts" — i.e. the host MAY rewrite or redact what the server sees, and SHOULD never let a server's `includeContext` reach across other servers' conversations.

### 13.5 Root scope leak

If the host exposes too-broad roots (e.g. `file:///`), it surrenders the entire filesystem to the server. Spec guidance: "Clients **MUST**: Only expose roots with appropriate permissions; Validate all root URIs to prevent path traversal; Implement proper access controls; Monitor root accessibility." Hosts SHOULD ask the user for consent before exposing roots and SHOULD allow per-server scoping.

### 13.6 Session hijacking on Streamable HTTP

Two attacks: session ID disclosure leading to impersonation, and session-keyed event queues being injected into by an attacker. Spec MUSTs:

- "MCP servers that implement authorization **MUST** verify all inbound requests. MCP Servers **MUST NOT** use sessions for authentication."
- "MCP servers **MUST** use secure, non-deterministic session IDs."
- "MCP servers **SHOULD** bind session IDs to user-specific information" (e.g. queue keys of the form `<user_id>:<session_id>`).

### 13.7 SSRF on OAuth metadata fetches

A malicious MCP server can return `resource_metadata` or `authorization_servers` URLs pointing at internal network resources (cloud metadata `169.254.169.254`, internal admin endpoints, etc.). Clients **SHOULD** enforce HTTPS (except for loopback dev), block private IP ranges (`10/8`, `172.16/12`, `192.168/16`, `127/8`, `169.254/16`, IPv6 `fc00::/7`, `fe80::/10`), validate redirect targets, and route OAuth discovery through an egress proxy on server-side deployments.

### 13.8 DNS rebinding on local servers

Local Streamable HTTP servers MUST validate `Origin` and return 403 on mismatch; SHOULD bind to `127.0.0.1` only.

### 13.9 Scope minimization

`scopes_supported` should be a *minimal* baseline, not a catalog. Wildcard scopes (`*`, `all`, `full-access`) and bundled "preemptive" scopes are anti-patterns. Use the step-up flow to elevate as needed.

---

## 14. Ecosystem snapshot

### Official SDKs (under [github.com/modelcontextprotocol](https://github.com/modelcontextprotocol))

| Language    | Repository                                                                  | Maintainer collaboration            |
|-------------|-----------------------------------------------------------------------------|-------------------------------------|
| TypeScript  | [`typescript-sdk`](https://github.com/modelcontextprotocol/typescript-sdk)  | Anthropic                           |
| Python      | [`python-sdk`](https://github.com/modelcontextprotocol/python-sdk)          | Anthropic                           |
| Java        | [`java-sdk`](https://github.com/modelcontextprotocol/java-sdk)              | Spring AI                           |
| Kotlin      | [`kotlin-sdk`](https://github.com/modelcontextprotocol/kotlin-sdk)          | —                                   |
| C#          | [`csharp-sdk`](https://github.com/modelcontextprotocol/csharp-sdk)          | Microsoft                           |
| Go          | [`go-sdk`](https://github.com/modelcontextprotocol/go-sdk)                  | Google                              |
| PHP         | [`php-sdk`](https://github.com/modelcontextprotocol/php-sdk)                | PHP Foundation                      |
| Ruby        | [`ruby-sdk`](https://github.com/modelcontextprotocol/ruby-sdk)              | —                                   |
| Rust        | [`rust-sdk`](https://github.com/modelcontextprotocol/rust-sdk)              | —                                   |
| Swift       | [`swift-sdk`](https://github.com/modelcontextprotocol/swift-sdk)            | —                                   |

### Infrastructure

- **Specification & docs** — [`modelcontextprotocol/modelcontextprotocol`](https://github.com/modelcontextprotocol/modelcontextprotocol).
- **MCP Inspector** — [`modelcontextprotocol/inspector`](https://github.com/modelcontextprotocol/inspector). Official testing/debugging tool with a React UI (defaults to `http://localhost:6274`) and a CLI mode. Connects to MCP servers over stdio, HTTP+SSE, or Streamable HTTP.
- **MCP Registry** — [`modelcontextprotocol/registry`](https://github.com/modelcontextprotocol/registry). Official, preview-status (v0.1 as of Sept 2025) registry service; "an app store for MCP servers." Supports GitHub OAuth/OIDC, DNS-, and HTTP-verification for namespace ownership.
- **Reference servers** — [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers). Reference implementations (filesystem, fetch, etc.).

### Notable host implementations

From the official [Example Clients](https://modelcontextprotocol.io/clients) page (non-exhaustive; entries reflect features the host advertises):

| Host                  | Homepage                                                                                                | Notable supported features                                                                       |
|-----------------------|---------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| Claude Desktop        | [claude.ai/download](https://www.claude.ai/download)                                                    | Local (stdio) MCP integration.                                                                  |
| Claude Code           | [claude.com/product/claude-code](https://claude.com/product/claude-code)                                | Resources, Prompts, Tools, Roots, Elicitation, Instructions, Discovery, DCR.                    |
| Claude.ai (web)       | [claude.ai](https://claude.ai)                                                                          | Remote MCP servers, Apps, CIMD, DCR.                                                            |
| ChatGPT               | [chatgpt.com](https://chatgpt.com)                                                                      | Remote MCP servers (Tools, Apps), CIMD, DCR. ([developer docs](https://platform.openai.com/docs/guides/developer-mode)) |
| OpenAI Codex CLI      | [github.com/openai/codex](https://github.com/openai/codex)                                              | Resources, Tools, Elicitation.                                                                  |
| GitHub Copilot CLI    | [github.com/features/copilot/cli](https://github.com/features/copilot/cli/)                             | Tools, Discovery, Instructions, Sampling, Elicitation, DCR, OAuth Client Credentials, Tasks.    |
| VS Code (Copilot)     | [code.visualstudio.com/docs/copilot/chat/mcp-servers](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) | Tools, Resources, Prompts, Apps. Stdio and HTTP transports.                                     |
| Cursor                | [cursor.com/docs](https://cursor.com/docs) (formerly docs.cursor.com)                                   | Prompts, Tools, Roots, Elicitation, DCR.                                                        |
| Zed                   | [zed.dev/docs/ai/mcp](https://zed.dev/docs/ai/mcp)                                                      | Prompts, Tools.                                                                                  |
| Cline                 | [github.com/cline/cline](https://github.com/cline/cline)                                                | Resources, Tools, Discovery.                                                                    |
| Continue              | [github.com/continuedev/continue](https://github.com/continuedev/continue)                              | Resources, Prompts, Tools, Apps.                                                                |
| Warp                  | [warp.dev](https://www.warp.dev/)                                                                       | Resources, Tools, Discovery.                                                                    |
| Replit                | [replit.com/products/agent](https://replit.com/products/agent)                                          | Tools, DCR.                                                                                     |
| Goose (Block)         | [github.com/block/goose](https://github.com/block/goose)                                                | Full spec support including Sampling, Elicitation, Roots, Apps, DCR.                            |
| Gemini CLI            | [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)                      | Prompts, Tools, Instructions, DCR.                                                              |

### Remote hosting

Notable platforms documenting first-class remote MCP support:

- **Cloudflare** — [developers.cloudflare.com/agents/model-context-protocol](https://developers.cloudflare.com/agents/model-context-protocol/) hosts remote MCP servers over Streamable HTTP with OAuth.
- **VS Code** documents both `"type": "http"` (remote) and `"type": "stdio"` (local) MCP server configs.

---

## 15. Common implementation pitfalls

A short, opinionated list of issues that recur across SDK issue trackers, the spec PR history, and the changelogs above.

1. **Forgetting `MCP-Protocol-Version` after the handshake.** On Streamable HTTP, every subsequent client request MUST carry `MCP-Protocol-Version: <negotiated>`. Servers that strictly enforce it return `400 Bad Request`. The spec falls back to `2025-03-26` if absent, which is silently surprising — a 2025-06-18-only feature will fail in mysterious ways.
2. **Session ID handling across reconnects.** A 404 in response to a request carrying an `Mcp-Session-Id` is a *signal to start a new session*, not a network error. Clients that retry blindly on a different replica without resetting state get into infinite-401 / 404 loops. Likewise, attempting to *resume* by GET with `Last-Event-ID` after a `DELETE` is wrong — the session is gone.
3. **Cross-stream replay on resumption.** When emitting SSE event IDs, the server MUST encode the originating stream identity in the ID and MUST refuse to replay events from a different stream on a `Last-Event-ID` request. This was made explicit in `2025-11-25` ([SEP-1699 clarification](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1847)) because some early Streamable HTTP servers were leaking events from another concurrent stream.
4. **Capability omission breaking older clients.** Adding a new capability sub-key (e.g. `elicitation: { url: {} }`) is backwards-compatible only if older clients ignore unknown keys — but a server that *requires* a capability the client did not advertise (e.g. sending a `mode: "url"` elicitation to a client that only declared `{}`) MUST get rejected with `-32602`. Servers should branch on declared client capabilities, not assume.
5. **JSON Schema dialect mismatch.** Pre-`2025-11-25` SDKs did not have a defined default dialect. Tools whose `inputSchema` uses 2020-12 features (e.g. `$dynamicRef`, `prefixItems`) will fail validation in clients still bound to draft-07. The fix is to either declare `$schema` explicitly or align to 2020-12 (now the default).
6. **stdio newline framing.** Newlines inside JSON-RPC messages are forbidden. JSON serializers that pretty-print or include embedded `\n` in strings break the framing. Use compact serialization. Conversely, clients reading stdio MUST handle arbitrarily large single-line JSON (multi-MB tool responses are common).
7. **stderr misuse.** Clients that fail or alert on any stderr output crash on healthy servers — `2025-11-25` explicitly says stderr is for all log levels, not just errors. Clients SHOULD parse it as a diagnostic stream.
8. **Character encoding over stdio.** Messages **MUST** be UTF-8. Servers that emit a BOM, that use the platform's default code page on Windows, or that write `latin-1` strings on stdout produce silent decode errors. Set `PYTHONIOENCODING=utf-8` for Python servers; set `process.stdout.setDefaultEncoding('utf8')` is not enough in Node — write bytes.
9. **Re-using request IDs.** Within one session, request IDs MUST be unique. Long-running clients that wrap around a 32-bit counter or reset IDs after reconnect (without the server having ended the session) violate this. Generate UUIDs or use a monotonic 64-bit counter.
10. **`Authorization: Bearer` missing on the initialization request.** OAuth 2.1 §5 says auth headers go on *every* request. Some clients skip the header on the very first `initialize` POST, expecting the server to challenge with 401 — which is correct *only* the very first time, before the client has a token. After the discovery dance, *every* request including `initialize` (in a new session) MUST carry the token.
11. **Audience binding (`resource`) omitted on the token request.** RFC 8707 requires the `resource` parameter on *both* the authorization request and the token request. Omitting it from the token request silently makes the issued token unbound; an MCP server that validates audience strictly will then reject the token.
12. **Treating tool annotations as security boundaries.** `readOnlyHint`, `destructiveHint`, etc. are *hints* from an untrusted server. A client that grants automatic approval to anything claiming `readOnlyHint: true` is exploitable. Annotations are for UI; consent must come from policy or the user.
13. **Confusing `isError: true` with a protocol error.** A tool returning `result: { isError: true, content: [...] }` is a *successful* JSON-RPC exchange that the LLM should see in order to self-correct. SDK wrappers that throw on `isError` and never surface the content defeat the model's recovery loop.
14. **Cancelling `initialize`.** The cancellation spec says "The `initialize` request **MUST NOT** be cancelled by clients." Some clients do anyway when a user hits Esc during connection setup, leaving the server in a half-initialized state.
15. **Forgetting that `notifications/cancelled` is best-effort.** Cancellation is racy. A client that immediately frees state after sending `notifications/cancelled` and ignores subsequent responses is correct per spec ("the sender **SHOULD** ignore any response to the request that arrives afterward"), but servers MUST still tolerate the race the other way.
16. **Roots without a `file://` scheme.** Roots in the current revision require `file://` URIs. Non-`file://` schemes are reserved for future use and SHOULD be rejected by servers.

---

## 17. Authorization in practice

§9–§10 cover what the spec says. This section covers what production hosts and servers actually ship today (verified as of `2026-05-21`). The short version: the spec defines a single ladder — OAuth 2.1 + PKCE + RFC 9728 + RFC 8707 — but the real ecosystem runs five parallel ladders in parallel, and the most common production path is still a static `Authorization: Bearer …` header that has nothing to do with OAuth.

### 17.1 Static Bearer tokens / pre-shared secrets

The pattern that dominates real deployments: the server accepts a long-lived API key in the `Authorization` header (or, less commonly, an `X-API-Key` / vendor-prefixed header). The MCP "OAuth dance" is bypassed entirely. There is no discovery, no PKCE, no audience binding — just a token that the user pastes from a vendor dashboard.

**GitHub MCP Server.** The official [`github/github-mcp-server`](https://github.com/github/github-mcp-server) accepts a GitHub Personal Access Token (PAT) via either `GITHUB_PERSONAL_ACCESS_TOKEN` (stdio) or `Authorization: Bearer <token>` (remote). Claude Code's docs show the remote variant verbatim:

```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/ \
  --header "Authorization: Bearer YOUR_GITHUB_PAT"
```

([Claude Code MCP docs](https://code.claude.com/docs/en/mcp)). The same server can also be run locally over stdio as a Docker container with the PAT in `env`:

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
               "ghcr.io/github/github-mcp-server"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_token}" }
    }
  }
}
```

The same `Authorization: Bearer …` URL also supports an OAuth dance for hosts that implement it (`VS Code 1.101+`, Claude Desktop, Cursor, Windsurf per the README).

**Sentry MCP Server.** [`mcp.sentry.dev/mcp`](https://docs.sentry.io/product/sentry-mcp/) is the canonical "modern remote MCP": HTTP transport with OAuth on the cloud endpoint, plus a stdio fallback (`npx @sentry/mcp-server`) that takes a static `SENTRY_ACCESS_TOKEN` env var. The cloud path uses device-code login on first run and caches the token at `~/.sentry/mcp.json`. The stdio path requires the user to mint a Sentry user-auth token with explicit scopes (`org:read`, `project:read`, `project:write`, `team:read`, `team:write`, `event:write`) and paste it into config:

```json
{
  "mcpServers": {
    "sentry": {
      "command": "npx",
      "args": ["@sentry/mcp-server"],
      "env": { "SENTRY_ACCESS_TOKEN": "snntrys_…" }
    }
  }
}
```

For self-hosted Sentry, `SENTRY_HOST` is added; for non-OAuth-capable clients, the OAuth flow is short-circuited entirely.

**Anthropic Directory connectors.** Most of the connectors listed at [claude.ai/directory](https://claude.ai/directory) use OAuth; the small set that don't (typically internal tools, dev-time servers) use either a static header or a stdio shim around a CLI tool that already has its own credentials on disk. Claude Code's `claude mcp add --header "Authorization: Bearer …"` is the canonical client-side wiring.

**Host UI surface.** Different hosts expose this in very different ways:

- **VS Code** prompts via `inputs:` (§18) and then uses the resulting variable in `headers` on the HTTP server. There is no built-in "Bearer" field in the UI; you write JSON.
- **Cursor** exposes `headers` directly in `~/.cursor/mcp.json` for HTTP servers:
  ```json
  {
    "mcpServers": {
      "remote-server": {
        "url": "https://api.example.com/mcp",
        "headers": { "Authorization": "Bearer ${env:MY_SERVICE_TOKEN}" }
      }
    }
  }
  ```
  ([Cursor MCP docs](https://cursor.com/docs/context/mcp)).
- **Claude Code** has first-class `--header` flag and a `headersHelper` mechanism (§17.9) for dynamic header generation.
- **Claude Desktop** has no remote-HTTP transport in the file format at all — Bearer-authenticated remote servers are consumed via `mcp-remote` (§17.5) as stdio shims.
- **Zed** allows a `headers` object on URL-form servers; if no header is configured, Zed kicks off the standard OAuth flow ([Zed docs](https://zed.dev/docs/ai/mcp)).

### 17.2 Cloudflare's remote-MCP deployment pattern

Cloudflare drove much of the early remote-MCP rollout. The architecture has stabilized into a recognizable pattern:

1. **Worker as the MCP server.** Either via `createMcpHandler()` (stateless) or the `McpAgent` class backed by a Durable Object (stateful, per-session, supports elicitation). See [Build a Remote MCP Server](https://developers.cloudflare.com/agents/guides/remote-mcp-server/).
2. **`workers-oauth-provider` library wraps the Worker.** TypeScript library, [announced March 25, 2025](https://blog.cloudflare.com/remote-model-context-protocol-servers-mcp/), that implements the OAuth 2.1 *provider* side — `/authorize`, `/token`, `/register` endpoints, PKCE enforcement, RFC 8707 audience binding — and mounts the MCP server behind it:
   ```typescript
   export default new OAuthProvider({
     apiRoute: "/sse",
     apiHandler: MyMCPServer.mount('/sse'),
     defaultHandler: MyAuthHandler,
     authorizeEndpoint: "/authorize",
     tokenEndpoint:     "/token",
     clientRegistrationEndpoint: "/register",
   });
   ```
3. **Identity delegated to an external authorization server.** The Worker is its own OAuth provider but defers actual *user* authentication to a delegated provider. Cloudflare's [Authorization page](https://developers.cloudflare.com/agents/model-context-protocol/authorization/) enumerates four paths:
   - **Cloudflare Access** — identity aggregator fronting external IdPs.
   - **Direct third-party OAuth** — GitHub, Google, Slack.
   - **Bring-your-own AS** — Stytch, Auth0, WorkOS, Descope.
   - **Worker-native** — Worker handles the whole OAuth flow itself.
4. **The Worker re-issues its own token.** Critical detail: even with a delegated provider, the Worker generates and issues its own MCP-scoped token to the client. The third-party token is used by the Worker to authenticate the *user*, then exchanged for a token whose `aud` is the MCP server. This satisfies RFC 8707 audience binding.
5. **Token validation via JWKS.** The Worker validates incoming bearer tokens by fetching the AS's JWKS (typically via the `jose` library, e.g. `createRemoteJWKSet(new URL('https://authkit_domain/oauth2/jwks'))`), then verifying `iss`, `aud`, and `exp` claims before any tool dispatch.
6. **RFC 9728 Protected Resource Metadata at the Worker.** The Worker exposes `/.well-known/oauth-protected-resource` with `authorization_servers` pointing at the delegated AS, so any RFC-9728-aware client (Claude Code, Codex CLI, VS Code) hits a 401, reads the metadata, and discovers the AS automatically.

A canonical implementation (WorkOS):

```js
app.get('/.well-known/oauth-protected-resource', (req, res) =>
  res.json({
    resource: 'https://mcp.example.com',
    authorization_servers: ['https://authkit.example.com'],
    bearer_methods_supported: ['header'],
  }),
);
```

The user-facing token-validation middleware (also WorkOS-flavored, from their [AuthKit MCP guide](https://workos.com/docs/authkit/mcp)):

```js
import { jwtVerify, createRemoteJWKSet } from 'jose';
const JWKS = createRemoteJWKSet(new URL('https://authkit.example.com/oauth2/jwks'));

async function bearerTokenMiddleware(req, res, next) {
  const token = req.headers.authorization?.match(/^Bearer (.+)$/)?.[1];
  if (!token) {
    return res
      .set('WWW-Authenticate',
        'Bearer error="unauthorized", resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"')
      .status(401).json({ error: 'No token provided.' });
  }
  const { payload } = await jwtVerify(token, JWKS, {
    issuer:   'https://authkit.example.com',
    audience: 'https://mcp.example.com',
  });
  req.userId = payload.sub;
  next();
}
```

For mass-distribution (one server, many tenant configurations) Cloudflare adds a tenant-aware `McpAgent` that pulls per-user secrets from KV / D1 at session start; the Worker treats the OAuth `sub` claim as the per-tenant key. See [the Durable Objects free-tier announcement](https://blog.cloudflare.com/building-ai-agents-with-mcp-authn-authz-and-durable-objects/) for the architecture rationale (per-session state, low-latency token cache, region-pinned tenants).

### 17.3 Reverse-proxy / edge-auth patterns

A common pragmatic shortcut: front an *unauthenticated* MCP server with a generic reverse-proxy that enforces identity at the edge. The MCP server itself is unaware of authentication; the proxy injects identity headers (or doesn't, and just gates access).

Patterns observed in production:

- **Cloudflare Access.** Configure a Zero Trust application in front of the MCP server URL, attached to an existing IdP (Okta, Google Workspace, GitHub). The user's first MCP request fires a standard Access OAuth dance in the browser; Access issues a JWT cookie; subsequent requests are bearer-equivalent at the edge. From the MCP client's perspective this looks like an OAuth flow against `*.cloudflareaccess.com`.
- **Tailscale Funnel / Serve.** Expose a localhost MCP server via Tailscale's HTTPS funnel; gate access by Tailscale ACLs. No HTTP-layer auth at the MCP server.
- **ngrok with `--basic-auth` / OAuth.** ngrok's edge plug-ins implement HTTP Basic, OAuth, OIDC, JWT validation before forwarding to localhost.
- **Identity-Aware Proxy (Google Cloud).** Same shape: IAP fronts a Cloud Run-hosted MCP server.

The trade-off is significant. Edge auth gives you *host-scoped trust* — anyone past the gate can call any tool — without per-request audience binding (RFC 8707) or scope-level enforcement. It is fine for internal tooling where the trust boundary is "is this employee logged in," but it deliberately defeats the threat model that MCP's OAuth profile is designed for (delegated, scoped, audience-bound tokens that don't grant lateral movement).

### 17.4 Identity providers documenting MCP integration

By mid-2026 every major IdP has shipped an "OAuth for MCP" guide. Two are worth reading end-to-end:

**WorkOS AuthKit.** [`workos.com/docs/authkit/mcp`](https://workos.com/docs/authkit/mcp) is the most explicit walk-through. AuthKit exposes standard OAuth 2.0 endpoints under `/oauth2/` (`/oauth2/authorize`, `/oauth2/token`, `/oauth2/jwks`, `/oauth2/register`, `/oauth2/introspection`) and a discoverable metadata document at `/.well-known/oauth-authorization-server`. MCP-specific touches:

- Enable **Client ID Metadata Documents** in the dashboard (Connect → Configuration) — this is the November-2025-onwards recommended client-registration approach ([SEP-991](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/991)), preferred over DCR for hosted clients with stable redirect URIs.
- Register your MCP server URL as a valid **Resource Indicator** so tokens carry the right `aud`.
- The legacy-compat tip: if a client doesn't follow `WWW-Authenticate.resource_metadata` and only knows `/.well-known/oauth-authorization-server`, proxy that path through your MCP server to AuthKit. This makes pre-`2025-06-18` clients work.

**Stytch Connected Apps.** [`stytch.com/docs/guides/connected-apps/mcp-servers`](https://stytch.com/docs/guides/connected-apps/mcp-servers). Stytch positions Connected Apps as MCP-native: it ships DCR (RFC 7591), CIMD, audience-bound JWTs, refresh-token rotation, and a built-in consent UX out of the box. Validation is identical to WorkOS — fetch JWKS, verify `iss` / `aud` / `exp` / `scope`. The Cloudflare integration is documented end-to-end ([`stytch.com/blog/building-an-mcp-server-oauth-cloudflare-workers`](https://stytch.com/blog/building-an-mcp-server-oauth-cloudflare-workers/)).

Two others worth a one-line mention:

- **Auth0**: per [`auth0.com/blog/secure-and-deploy-remote-mcp-servers-with-auth0-and-cloudflare`](https://auth0.com/blog/secure-and-deploy-remote-mcp-servers-with-auth0-and-cloudflare/), `.dev.vars` pattern with `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_AUDIENCE`, `AUTH0_SCOPE=openid email profile offline_access …`. Token refresh handled transparently by `workers-oauth-provider`.
- **Descope**: [`docs.descope.com/mcp`](https://docs.descope.com/mcp) ships an `mcp-express-sdk` TypeScript Express middleware that handles AS metadata, JWT validation, scope enforcement, and DCR in one drop-in. Tool-level scopes (`mcp:invoice.create`, `mcp:calendar.write`, …) are the recommended granularity.

What's MCP-specific in these vs. generic OAuth 2.1: the `WWW-Authenticate` header with `resource_metadata` parameter (RFC 9728), the requirement that the `aud` claim equals the canonical MCP server URI (RFC 8707), CIMD as a preferred alternative to DCR for hosted clients, and the convention of returning 403 + `insufficient_scope` for step-up flows. Everything else (PKCE, refresh rotation, JWKS, JWT verification) is plain OAuth 2.1.

### 17.5 The `mcp-remote` shim

[`github.com/geelen/mcp-remote`](https://github.com/geelen/mcp-remote) (also on npm as [`mcp-remote`](https://www.npmjs.com/package/mcp-remote), `0.1.38` as of May 2026, actively maintained by `geelen` and `threepointone`) is the de-facto bridge between stdio-only hosts (Claude Desktop, older Cursor builds, Windsurf) and OAuth-protected remote MCP servers. It runs as a local stdio MCP server and proxies all JSON-RPC traffic to a remote Streamable HTTP (or legacy SSE) endpoint, handling the full OAuth dance transparently.

Canonical usage in Claude Desktop's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.linear.app/sse"]
    }
  }
}
```

Behavior:

1. **First run** — `mcp-remote` calls the remote endpoint, gets a 401 with `WWW-Authenticate: Bearer …`, runs the RFC 9728 / RFC 8414 discovery, and opens the user's default browser to the AS's `/authorize` endpoint.
2. **Loopback redirect URI** — `mcp-remote` listens on `http://127.0.0.1:3334/oauth/callback` by default (port configurable as a positional arg, host configurable via `--host`). The AS redirects here with `code=…&state=…`.
3. **Token exchange and persist** — Tokens (access + refresh) are written to `~/.mcp-auth/<server_hash>/`. Each unique `(URL, --resource, --header)` triple gets its own cache directory. The cache layout is JSON files keyed by client/server identifiers; debug logs land at `~/.mcp-auth/<server_hash>_debug.log` when `--debug` is passed.
4. **Refresh on expiry** — When the access token expires `mcp-remote` runs the refresh-token grant transparently and rotates the cached refresh token in place. If refresh fails (revoked, AS down) it falls back to the full browser dance on the next request.
5. **Custom headers** — `--header "Authorization: Bearer ${TOKEN}"` injects static headers and bypasses OAuth entirely; useful for servers that prefer pre-shared secrets.
6. **Tool filtering** — `--ignore-tool <pattern>` removes tools from the advertised list before forwarding to the host (a host-side allow-list workaround).

The shim is required because Claude Desktop's config schema has *no* `url`/`headers`/`type: "http"` fields — only `command`/`args`/`env`. Until Anthropic adds first-class remote HTTP support to the desktop app, `mcp-remote` is how every OAuth remote MCP is wired in. Claude.ai (web) and Claude Code don't need it; both implement OAuth directly.

### 17.6 Token storage on the client

Where hosts actually persist OAuth tokens (verified from docs and source, May 2026):

| Host                 | Storage location                                                                                  | Notes                                                                                                                |
|----------------------|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| Claude Code          | System keychain on macOS; credentials file on Linux/Windows. Confirmed in [Claude Code MCP docs](https://code.claude.com/docs/en/mcp): "Authentication tokens are stored securely and refreshed automatically" and "the client secret is stored securely in your system keychain (macOS) or a credentials file." | Token refresh is automatic; `/mcp` menu has "Clear authentication" to revoke. |
| Claude Desktop       | Via `mcp-remote` shim → `~/.mcp-auth/<server_hash>/` on disk (plaintext JSON).                    | First-party remote-MCP support is not in the desktop app; OAuth happens via the shim.                                |
| Claude.ai (web)      | Server-side, in Anthropic's infrastructure. The remote MCP connection originates from Anthropic's cloud, not the user's browser, per the [Claude Help Center](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp). | Users never touch tokens; OAuth flow happens server-to-server with the user's browser as user-agent for consent.     |
| VS Code (Copilot)    | Tokens are surfaced via VS Code's standard secret-storage API (OS keychain backed) per the [VS Code MCP servers guide](https://code.visualstudio.com/docs/copilot/customization/mcp-servers). | `inputs` of `type: "password"` go to secret storage too.                                                             |
| Cursor               | OAuth callback hits `cursor://anysphere.cursor-mcp/oauth/callback`; tokens persisted in Cursor's settings store. | Effective storage depends on the platform's keychain bindings.                                                       |
| Zed                  | Settings store; not separately documented.                                                         | Standard MCP OAuth flow on first connect to a URL-form server with no static `headers`.                              |
| `mcp-remote`         | `~/.mcp-auth/` (plaintext JSON).                                                                   | Override with `MCP_REMOTE_CONFIG_DIR`.                                                                               |

The Claude Desktop / `mcp-remote` plaintext-on-disk path is the weakest link in the common stack: anyone with read access to the user's home directory can lift the refresh token and replay the OAuth grant. This is why production deployments increasingly skip Claude Desktop in favor of Claude.ai-with-remote-connectors or Claude Code for OAuth-protected servers.

### 17.7 Token refresh and mid-call expiry

The Python SDK's [`src/mcp/client/auth/oauth2.py`](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py) implements the canonical client-side flow inside an HTTPX `async_auth_flow`. The behavior is:

1. **Pre-request check** — Before every outbound HTTP request, the client calls `self.context.is_token_valid()`, which verifies an access token exists and hasn't passed the locally cached `expires_in`-derived expiry.
2. **Proactive refresh** — If the token is expired but a refresh token exists (`can_refresh_token()`), the client builds and yields a refresh-token grant request *before* sending the user's MCP request. On 200, the new token is swapped in and the original request proceeds.
3. **Failed refresh resets state** — If the refresh response is non-200, `_handle_refresh_response` clears stored tokens and sets `_initialized = False`. The next request triggers a full re-discovery + browser-driven authorization grant.
4. **Reactive on 401** — A 401 response *after* sending a request triggers the same full re-auth path (re-discover PRM, re-discover AS metadata, parse new `WWW-Authenticate` scope hints, re-register if needed, re-authorize). This is not just a refresh — it's full reset.
5. **Reactive on 403 with `insufficient_scope`** — Step-up flow: the client extends its scope set from the 403 header's `scope` parameter and re-runs the authorization grant without clearing the client registration.

The mid-call expiry path is therefore *not* fully transparent. If a streaming `tools/call` over SSE has been open for an hour and the access token expires while the server is mid-response, the next *outbound* request from the client will get caught by the pre-request check and refresh cleanly. But the *in-flight* response stream depends on the server's tolerance for stale tokens on already-authenticated streams — the spec is silent here, and implementations differ. Cloudflare's `workers-oauth-provider`, for example, validates the bearer token on each HTTP request, not per SSE event, so a long-lived POST→SSE stream from a single request will outlive token expiry (until the stream closes); subsequent requests will fail 401 and trigger refresh. Servers that re-validate per event will close the stream — which the client treats as a network failure and retries.

The TypeScript SDK ([`typescript-sdk`](https://github.com/modelcontextprotocol/typescript-sdk)) implements the same pattern.

### 17.8 Client-credentials / service-account flows

OAuth 2.1 supports client-credentials grants (machine-to-machine, no user). MCP is *not* designed for this. The spec is built around delegated user access — the AS issues tokens on behalf of a human who clicks through a consent screen, and tool calls run with that human's permissions. Use cases where it appears:

- **GitHub Copilot CLI** advertises "OAuth Client Credentials" support per the [Example Clients list](https://modelcontextprotocol.io/clients), specifically for CI/CD contexts where a workflow runs an MCP server without an interactive user.
- **Internal infra MCP servers** in large engineering orgs sometimes accept a service-account JWT instead of a user token; this is implemented via the same `Authorization: Bearer` static-token shape (§17.1), not a true client-credentials grant against an AS.

Most production MCPs do not implement this. If you need machine-to-machine MCP, prefer a static Bearer token over a real client-credentials flow — there's no consent UX to drive, so the extra OAuth ceremony buys nothing.

### 17.9 Arbitrary header passthrough

For non-OAuth MCP servers, hosts let users configure arbitrary HTTP headers — usually `Authorization: Token …`, `X-API-Key: …`, or vendor-specific schemes.

- **VS Code** — `headers` object on `type: "http"` servers; values can use `${input:…}` for prompted secrets.
- **Cursor** — `headers` object on URL-form servers; values can use `${env:…}`. See `~/.cursor/mcp.json` schema (§18.1).
- **Zed** — `headers` object on URL-form servers; literal values only.
- **Claude Code** — `--header "Authorization: Bearer …"` on `claude mcp add`, and a `headersHelper` field in `.mcp.json` that executes a shell command at connection time and merges its stdout-JSON into the headers. This is the workaround for short-lived tokens (Kerberos, internal SSO) that don't fit OAuth:
  ```json
  {
    "mcpServers": {
      "internal-api": {
        "type": "http",
        "url": "https://mcp.internal.example.com",
        "headersHelper": "/opt/bin/get-mcp-auth-headers.sh"
      }
    }
  }
  ```
  The helper must emit `{"Authorization": "Bearer xyz"}` on stdout; Claude Code reads it with a 10-second timeout, fresh per connection (no caching). The host sets `CLAUDE_CODE_MCP_SERVER_NAME` and `CLAUDE_CODE_MCP_SERVER_URL` in the helper's environment.
- **Claude Desktop** — No native header field. Use `mcp-remote --header` as a workaround.

Security caveats: any header containing a secret is visible to (a) the host process and any plugin running in it, (b) any host-side logging that captures HTTP request lines, (c) anyone with read access to the config file on disk. None of the hosts redact `Authorization` headers from telemetry by default; assume any token written to config is host-internal-exposed. For repository-checked-in `.mcp.json`, the consensus is to put `${env:…}` references in config and the actual tokens in a `.env` file outside source control (or in `~/.zshrc`).

### 17.10 What "auth" looks like inside Claude.ai / Claude Desktop in practice

Walking through a remote-MCP add in Claude.ai (Pro/Max plans, per the [help-center article](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)):

1. User goes to `Customize → Connectors → + → Add custom connector`.
2. User pastes the MCP server URL (e.g., `https://mcp.linear.app/sse`).
3. Optional: click "Advanced settings" and enter a pre-registered OAuth `client_id` and `client_secret` if the upstream AS doesn't support DCR/CIMD. For servers that do, this section is empty and Anthropic's runtime registers dynamically.
4. Click "Add".
5. On first use, Claude opens a browser tab (or a popup, depending on the surface) pointing at the AS's `/authorize` endpoint with `redirect_uri=https://claude.ai/api/mcp/auth_callback`. The user signs in to the AS (often via their existing identity provider) and consents.
6. The AS redirects to `https://claude.ai/api/mcp/auth_callback?code=…&state=…`. Anthropic's backend exchanges the code for a token, stores it server-side keyed to the user's Claude account, and the connector goes "Connected" in the UI.

Important: in Claude.ai, the OAuth dance happens between *Anthropic's infrastructure* and the AS, with the user's browser as the user-agent only for the `/authorize` redirect. The MCP server is contacted from Anthropic's cloud, not from the user's browser. This means the MCP server's allow-list and rate-limit configs need to expect requests from Anthropic's egress IP ranges, not the user.

In Claude Desktop, by contrast, MCP servers run as local subprocesses; remote MCPs are accessed via `mcp-remote`, which runs the browser-driven OAuth dance from the user's machine. Tokens are stored locally (§17.6). The MCP server sees requests from the user's IP.

In Claude Code, the flow is closer to Claude Desktop: `/mcp` opens the user's browser, the loopback callback (`http://localhost:<port>/callback`) catches the code, the CLI exchanges it, and the token is stored in the OS keychain (macOS) or a credentials file (Linux/Windows). `--callback-port` pins the port to match a pre-registered redirect URI; `--client-id` + `--client-secret` pre-configure credentials for ASes that don't support DCR. The `oauth.authServerMetadataUrl`, `oauth.scopes`, and (since v2.1.64) override-discovery options let you bypass the standard well-known chain entirely. See the [Claude Code MCP docs](https://code.claude.com/docs/en/mcp).

---

## 18. Non-HTTP transports in practice

§5 covers what the spec says about stdio and Streamable HTTP. This section covers how hosts and servers actually package and launch stdio servers — every host has invented its own JSON shape for the same protocol — plus the operational reality of WebSocket and HTTP+SSE deployments.

### 18.1 stdio config schemas, side by side

Every host that supports stdio servers reads a JSON config file and spawns `command` with `args` and `env`. The differences are in the wrapping schema, env-var substitution syntax, secret-prompting story, and HTTP/SSE support.

**Claude Desktop** ([`claude_desktop_config.json`](https://modelcontextprotocol.io/docs/develop/connect-local-servers)). Top-level `mcpServers` map; no `type` field; no remote transport. Paths:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json` (per community docs; the Anthropic install path on Linux is unofficial).
- Windows MSIX builds: a virtualized path under `%LOCALAPPDATA%\Packages\Claude_<hash>\LocalCache\Roaming\Claude\` may apply ([issue #26073](https://github.com/anthropics/claude-code/issues/26073)).

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "/Users/alice/Desktop", "/Users/alice/Downloads"]
    },
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
               "ghcr.io/github/github-mcp-server"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_…" }
    },
    "linear": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.linear.app/sse"]
    }
  }
}
```

No env-var substitution; literal values only. Secrets are pasted directly. Edit-via-UI button under Settings → Developer. A restart is required to pick up changes (the app starts servers at launch, not on config save).

**VS Code** ([`code.visualstudio.com/docs/copilot/chat/mcp-servers`](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)). Workspace-scoped at `.vscode/mcp.json`; user-scoped at the user `mcp.json` (opened via the `MCP: Open User Configuration` command). Top-level `servers` (not `mcpServers`). Includes a `type` field with values `"stdio" | "http" | "sse"`. Includes an `inputs` array for prompted secrets.

```json
{
  "inputs": [
    { "id": "github_pat", "type": "password",
      "description": "GitHub Personal Access Token" }
  ],
  "servers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "${workspaceFolder}"]
    },
    "github": {
      "type": "stdio",
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
               "ghcr.io/github/github-mcp-server"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_pat}" }
    },
    "sentry-remote": {
      "type": "http",
      "url": "https://mcp.sentry.dev/mcp"
    }
  }
}
```

Substitution syntax: `${input:<id>}` (from the `inputs` block; password inputs are stored in OS secret storage), `${env:VAR}` (process env), `${workspaceFolder}`. VS Code prompts on first launch for `inputs` and persists answers. There is also a `sandboxEnabled`/`sandbox` block for macOS/Linux that hard-caps the server's filesystem and network access — unique to VS Code.

**Cursor** ([`cursor.com/docs/context/mcp`](https://cursor.com/docs/context/mcp)). Global at `~/.cursor/mcp.json`; project-scoped at `.cursor/mcp.json`. Top-level `mcpServers` (matches Claude Desktop's name). `type` field with values `"stdio" | "http" | "sse"`. Includes an `envFile` shortcut to load env from `.env`.

```json
{
  "mcpServers": {
    "local-postgres": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres",
               "postgresql://localhost/mydb"],
      "envFile": ".env"
    },
    "remote-server": {
      "url": "https://api.example.com/mcp",
      "headers": { "Authorization": "Bearer ${env:MY_SERVICE_TOKEN}" }
    },
    "oauth-server": {
      "url": "https://api.example.com/mcp",
      "auth": {
        "CLIENT_ID":     "${env:MCP_CLIENT_ID}",
        "CLIENT_SECRET": "${env:MCP_CLIENT_SECRET}",
        "scopes":        ["read", "write"]
      }
    }
  }
}
```

Substitution: `${env:VAR}`, `${userHome}`, `${workspaceFolder}`, `${workspaceFolderBasename}`, `${pathSeparator}` (alias `${/}`). OAuth callback URI: `cursor://anysphere.cursor-mcp/oauth/callback`. No `inputs`-style prompt mechanism — secrets live in `envFile` or shell env.

**Zed** ([`zed.dev/docs/ai/mcp`](https://zed.dev/docs/ai/mcp)). Single section in user `settings.json`:

```json
{
  "context_servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "env": {}
    },
    "linear": {
      "url": "https://mcp.linear.app/mcp"
    },
    "internal": {
      "url": "https://mcp.internal.example.com",
      "headers": { "Authorization": "Bearer ${ENV_NOT_SUPPORTED}" }
    }
  }
}
```

URL-form servers without `headers` trigger the standard MCP OAuth flow on connect. No env-var substitution syntax is documented; literal values only. Zed handles `notifications/tools/list_changed` without restart.

**Continue.dev / Windsurf.** Continue's MCP config lives in its standard `~/.continue/config.json` under an `mcpServers` map with the same `command`/`args`/`env` shape; not separately documented in a public spec page as of May 2026. Windsurf ([`docs.windsurf.com/windsurf/cascade/mcp`](https://docs.windsurf.com/windsurf/cascade/mcp)) stores config at `~/.codeium/windsurf/mcp_config.json` with `mcpServers`, supports both `command`-based stdio and `serverUrl`/`url`-based remote HTTP/SSE servers, and exposes two interpolation patterns: `${env:VAR_NAME}` and `${file:/path}` (the latter reads the file's content into the field — useful for token files mounted by external secret stores).

**Claude Code** ([`code.claude.com/docs/en/mcp`](https://code.claude.com/docs/en/mcp)). Three scopes: local (`~/.claude.json`), project (`.mcp.json` in repo root, designed to be checked in), user (`~/.claude.json`). Project-scoped `.mcp.json` is the most-used format for team sharing:

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${GITHUB_PAT}" }
    },
    "shared-server": {
      "command": "node",
      "args": ["${CLAUDE_PROJECT_DIR}/tools/mcp-server.js"],
      "env": { "WORKSPACE": "${CLAUDE_PROJECT_DIR}" }
    }
  }
}
```

Substitution: `${VAR}` (env), `${VAR:-default}` (env with default). The `type` field accepts `"stdio" | "http" | "sse" | "streamable-http"` (the last is an alias for `"http"` so configs copied verbatim from server READMEs work). Claude Code injects `CLAUDE_PROJECT_DIR` into every stdio server's env; references to it in `command`/`args` from a checked-in `.mcp.json` need `${CLAUDE_PROJECT_DIR:-.}` because the value isn't in the host's env at config-parse time. Project-scoped servers prompt the user for approval before first launch.

### 18.2 Launch patterns

Real-world `command`/`args` combinations:

```json
{ "command": "npx",   "args": ["-y", "@modelcontextprotocol/server-filesystem", "./scratch"] }
{ "command": "uvx",   "args": ["mcp-server-fetch"] }
{ "command": "python","args": ["-m", "mcp_server_foo"] }
{ "command": "docker","args": ["run", "--rm", "-i", "ghcr.io/owner/server:tag"] }
{ "command": "node",  "args": ["/usr/local/lib/my-mcp-server/index.js"] }
```

Trade-offs in practice:

- **`npx -y …`** — the Claude Desktop and Cursor default. First launch downloads the package and can take 30+ seconds; subsequent launches are sub-second (npm cache). Pinning a version (`@1.2.3`) is essential — `npx -y` resolves the latest version each time the host starts, which can break things mid-week. Cross-platform-reliable on macOS/Linux/WSL; on bare Windows the `npx` shim sometimes fails to spawn (use full path or `cmd /c npx`).
- **`uvx`** — Python equivalent via Astral's `uv`. Same UX as `npx` but for Python-packaged MCP servers (`mcp-server-fetch`, `mcp-server-git`). Faster cold start than pip. Less mature on Windows.
- **`python -m mcp_server_foo`** — used when the server is installed system-wide (`pip install …`) or by a virtualenv-aware host. Requires the host to know the right interpreter; environment-variable handling differs across platforms (set `PYTHONIOENCODING=utf-8` on Windows or stdio framing breaks).
- **`docker run --rm -i ghcr.io/…`** — the GitHub MCP server's preferred local form. Provides dependency isolation and reproducible env. Cost: ~1–3 seconds of container startup per session, and the host has to manage Docker Desktop liveness (Claude Desktop on a Mac that hasn't started Docker shows a generic "server failed to start" with no useful diagnostics).
- **Compiled binary** — a bare executable path. Fastest start, no runtime dependency on Node/Python/Docker. Used by Anthropic's `claude mcp serve` and by Go-SDK servers.

Reference servers are at [`github.com/modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers): `Everything`, `Fetch`, `Filesystem`, `Git`, `Memory`, `Sequential Thinking`, `Time`. The READMEs show both the `npx -y @modelcontextprotocol/server-…` and `uvx mcp-server-…` invocation styles. The README explicitly notes "these are reference implementations" — production users typically vendor or wrap them.

### 18.3 Secrets and env vars in practice

Four patterns, varying degrees of safety:

- **Hardcoded literals in config.** Most common. The user pastes `"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_abc123…"` into `claude_desktop_config.json`. Secret is on disk in plaintext, often syncable via OS-level cloud backup. Almost universally what guides tell beginners to do.
- **`${env:VAR}` / `${input:foo}` substitution.** VS Code, Cursor, Claude Code, Windsurf all support `${env:VAR}` in some form. VS Code adds `${input:foo}` to prompt-and-cache via secret-storage. This is the recommended pattern for checked-in `.mcp.json` files in a team repo.
- **Prompt-on-launch via VS Code `inputs:`.** The cleanest UX: the user is prompted once, the value is stored in VS Code's secret storage, the MCP server gets it via `env`. No secret in the JSON file at all.
- **External secret-manager wrappers.** Power users wrap the entire `command` line in `op run -- npx -y …` (1Password CLI), `pass --` (passwordstore.org), `aws-vault exec …`, etc. The host launches the wrapper; the wrapper injects env vars from the secret store; the MCP server inherits them. This works in any host because it only relies on `command`/`args`/`env`.

There is no MCP-standard secret-handling mechanism. The closest is VS Code's `inputs`, which is a VS-Code-only convention.

### 18.4 One-click / deeplink installation

A growing pattern: web pages offer "Install in Cursor" / "Install in VS Code" buttons that open a custom URL scheme registered with the host, which then prompts the user before adding the server to config.

**Cursor** ([`cursor.com/docs/context/mcp/install-links`](https://cursor.com/docs/context/mcp/install-links)). URL scheme:

```
cursor://anysphere.cursor-deeplink/mcp/install?name=<SERVER_NAME>&config=<BASE64_JSON>
```

Where `<BASE64_JSON>` is the base64-encoded JSON of the server's config object (without the wrapping `mcpServers` map). Example for a Postgres server:

Source config:

```json
{
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres",
           "postgresql://localhost/mydb"]
}
```

Resulting deeplink:

```
cursor://anysphere.cursor-deeplink/mcp/install?name=postgres&config=eyJjb21tYW5kIjoibnB4IiwiYXJncyI6WyIteSIsIkBtb2RlbGNvbnRleHRwcm90b2NvbC9zZXJ2ZXItcG9zdGdyZXMiLCJwb3N0Z3Jlc3FsOi8vbG9jYWxob3N0L215ZGIiXX0=
```

Cursor prompts before persisting to `~/.cursor/mcp.json`.

**VS Code** ([`code.visualstudio.com/api/extension-guides/ai/mcp`](https://code.visualstudio.com/api/extension-guides/ai/mcp)). URL scheme:

```
vscode:mcp/install?<urlencoded-json-config>
```

The payload is JSON-stringified then URL-encoded (no base64). Insiders builds use `vscode-insiders:`. Example for `{"name":"server-name","command":"node","args":["./server.js"]}`:

```
vscode:mcp/install?%7B%22name%22%3A%22server-name%22%2C%22command%22%3A%22node%22%2C%22args%22%3A%5B%22.%2Fserver.js%22%5D%7D
```

Both hosts show a confirmation dialog before adding; the user can inspect the command being installed before approving (mitigates the "drive-by config injection" risk that prompted [CursorJack-style concerns](https://www.proofpoint.com/us/blog/threat-insight/cursorjack-weaponizing-deeplinks-exploit-cursor-ide)).

Claude Desktop has no install URL scheme. Claude.ai's "Connect" buttons in the Directory at [claude.ai/directory](https://claude.ai/directory) are app-internal navigation, not OS-level deeplinks.

### 18.5 Process lifecycle and crash recovery

Per-host behavior on stdio server failure:

- **Claude Desktop** — server crashes are silently logged to `~/Library/Logs/Claude/mcp-server-<name>.log` (macOS) with no in-UI notification. The server stays marked as "running" until the next restart. There is no automatic restart. The user's recourse is to quit and relaunch the app.
- **VS Code** — surfaces a notification when an MCP server exits. Offers a "Restart" button. Per [the docs](https://code.visualstudio.com/docs/copilot/customization/mcp-servers), the trust prompt re-fires when restarting a server after a config change.
- **Cursor** — similar to VS Code: the MCP panel shows server state (connected/failed/loading); users can manually restart.
- **Claude Code** — distinct behavior for stdio vs. HTTP: "Stdio servers are local processes and are not reconnected automatically" ([Claude Code MCP docs](https://code.claude.com/docs/en/mcp)). For HTTP/SSE servers, Claude Code retries with exponential backoff: up to five attempts, 1s/2s/4s/8s/16s delays. Initial connect retries are capped at 3. Auth errors and 404s are not retried.
- **Zed** — restarts on `notifications/tools/list_changed`; otherwise relies on user-initiated reconnect.

In-flight tool calls: when a stdio server exits mid-call, the host's read loop encounters EOF on stdout and treats outstanding request IDs as failed. The host returns a synthetic JSON-RPC error to its own internal callback for each pending request. The user sees "MCP server disconnected" or similar in the surface; the underlying LLM call may or may not surface this depending on the host. No host re-issues the tool call after a restart; that's the LLM's job to decide via context.

### 18.6 The deprecated HTTP+SSE two-endpoint transport in practice

The `2024-11-05`-revision HTTP+SSE transport — two endpoints, server-pushed `endpoint` event, all POSTs to the second endpoint, all responses as SSE on the first — was superseded by Streamable HTTP in `2025-03-26`. Who still ships it (May 2026):

- **A small set of servers pinned to `2024-11-05`** for legacy host support. Sentry's remote endpoint at `mcp.sentry.dev` and Linear's at `mcp.linear.app/sse` historically used the SSE path; both have migrated to Streamable HTTP at the `/mcp` URL but kept the `/sse` URL as a compatibility alias (which is why `mcp-remote https://mcp.linear.app/sse` still works).
- **`mcp-remote`'s `--transport sse-first` and `sse-only` modes** — explicitly there to bridge old servers.
- **Python SDK's `sse_client`** — still present alongside `streamablehttp_client` in [`python-sdk`](https://github.com/modelcontextprotocol/python-sdk) for backwards compatibility. Servers can ship the deprecated transport via `mcp.server.sse` modules.

Compatibility shims in client SDKs work as follows: the client first POSTs an `InitializeRequest` to the URL. If it gets 200 with a single JSON-RPC response, it's a Streamable HTTP server. If it gets 200 with `Content-Type: text/event-stream`, it's also Streamable HTTP but using SSE upgrade. If it gets 4xx (400/404/405), it falls back to opening a GET to the URL and waiting for the first `endpoint` event — the deprecated HTTP+SSE shape. This pattern is documented in the [§Backwards Compatibility](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#backwards-compatibility) of the current spec.

Failure modes when an old client meets a new server: the old client GETs and waits for `endpoint`, which never comes (the new server replies 405 to a GET that doesn't carry `Accept: text/event-stream`, or returns an SSE stream with no `endpoint` event). The client hangs or errors out. The fix is to upgrade the client; new servers should not be asked to also ship the deprecated transport.

### 18.7 WebSocket transport

The Python SDK includes [`src/mcp/client/websocket.py`](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/websocket.py) — a bidirectional WebSocket transport that uses the `mcp` subprotocol on the WebSocket handshake. It spawns two `anyio` tasks (a reader that pulls JSON from the socket, validates via Pydantic, and forwards to a memory stream; a writer that serializes outbound `SessionMessage`s and pushes them to the socket) and exposes the standard `read_stream`/`write_stream` pair that the rest of the SDK consumes.

It is functional, clean code, and present in the canonical SDK. It is also approximately *not used in production*. As of May 2026 there is no major host that documents WebSocket support, no major remote MCP service that exposes a WebSocket endpoint, and no traction in the spec PR history toward making it normative. The TypeScript SDK does not even ship a WebSocket transport file.

The original motivation — long-lived bidirectional streams — was largely subsumed by Streamable HTTP's POST→SSE-upgrade design and its `Last-Event-ID` resumption story. Treat WebSocket as a "custom transport" escape-hatch the spec allows but the ecosystem has not picked up.

### 18.8 `mcp-remote`'s role for non-HTTP-native hosts

Cross-referencing §17.5: `mcp-remote` is what lets a stdio-only host transparently consume an OAuth-protected remote MCP server. The mechanics:

1. The host launches `npx mcp-remote https://remote.example.com/mcp` as a normal stdio MCP server.
2. `mcp-remote` connects to `https://remote.example.com/mcp` over Streamable HTTP (or SSE if the server is `2024-11-05`-shaped, via `--transport sse-first`).
3. On 401, `mcp-remote` runs the OAuth dance — discovers PRM, discovers AS metadata, registers via DCR or CIMD, listens on `http://127.0.0.1:3334/oauth/callback`, opens the user's browser, exchanges the code for tokens, caches in `~/.mcp-auth/<server_hash>/`.
4. For every JSON-RPC message the host writes to `mcp-remote`'s stdin, `mcp-remote` translates to an HTTP POST with `Authorization: Bearer <access_token>` and `MCP-Protocol-Version: <negotiated>`. SSE streams from the server are demultiplexed and written back to stdout as line-framed JSON-RPC.
5. On token expiry, `mcp-remote` refreshes transparently; on refresh failure it re-runs the browser dance the next time it's needed.

This means Claude Desktop, which only speaks stdio, can use OAuth-protected remote MCPs at all — at the cost of an extra process, an extra `node`/`npx` startup, and tokens-on-disk in `~/.mcp-auth/`. The same pattern works for any host that supports stdio: Windsurf, older Cursor builds, Claude Code (which doesn't need it but can still use it), and small IDE plug-ins that haven't implemented the OAuth dance themselves.

---

## 19. Primary references

### Spec & official docs

- MCP home — https://modelcontextprotocol.io/
- Specification index (latest = `2025-11-25`) — https://modelcontextprotocol.io/specification/
- Architecture — https://modelcontextprotocol.io/specification/2025-11-25/architecture
- Base protocol — https://modelcontextprotocol.io/specification/2025-11-25/basic
- Lifecycle — https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
- Transports — https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- Authorization — https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- Security Best Practices — https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices
- Tools — https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- Resources — https://modelcontextprotocol.io/specification/2025-11-25/server/resources
- Prompts — https://modelcontextprotocol.io/specification/2025-11-25/server/prompts
- Completion — https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/completion
- Logging — https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging
- Pagination — https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination
- Sampling — https://modelcontextprotocol.io/specification/2025-11-25/client/sampling
- Roots — https://modelcontextprotocol.io/specification/2025-11-25/client/roots
- Elicitation — https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation
- Cancellation — https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation
- Progress — https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress
- Ping — https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/ping
- Tasks (experimental) — https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks
- Changelog `2025-11-25` — https://modelcontextprotocol.io/specification/2025-11-25/changelog
- Changelog `2025-06-18` — https://modelcontextprotocol.io/specification/2025-06-18/changelog
- Changelog `2025-03-26` — https://modelcontextprotocol.io/specification/2025-03-26/changelog
- Initial revision `2024-11-05` — https://modelcontextprotocol.io/specification/2024-11-05
- HTTP+SSE (deprecated) — https://modelcontextprotocol.io/specification/2024-11-05/basic/transports#http-with-sse
- Spec repository — https://github.com/modelcontextprotocol/modelcontextprotocol
- TypeScript schema (source of truth) — https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-11-25/schema.ts
- Example clients list — https://modelcontextprotocol.io/clients

### Official SDKs & infrastructure

- TypeScript SDK — https://github.com/modelcontextprotocol/typescript-sdk
- Python SDK — https://github.com/modelcontextprotocol/python-sdk
- Python SDK OAuth client (`auth/oauth2.py`) — https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py
- Java SDK — https://github.com/modelcontextprotocol/java-sdk
- Kotlin SDK — https://github.com/modelcontextprotocol/kotlin-sdk
- C# SDK — https://github.com/modelcontextprotocol/csharp-sdk
- Go SDK — https://github.com/modelcontextprotocol/go-sdk
- PHP SDK — https://github.com/modelcontextprotocol/php-sdk
- Ruby SDK — https://github.com/modelcontextprotocol/ruby-sdk
- Rust SDK — https://github.com/modelcontextprotocol/rust-sdk
- Swift SDK — https://github.com/modelcontextprotocol/swift-sdk
- MCP Inspector — https://github.com/modelcontextprotocol/inspector
- MCP Registry — https://github.com/modelcontextprotocol/registry
- Reference servers — https://github.com/modelcontextprotocol/servers

### RFCs and IETF drafts

- OAuth 2.1 — https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13
- RFC 7591 — OAuth 2.0 Dynamic Client Registration — https://datatracker.ietf.org/doc/html/rfc7591
- RFC 7636 — PKCE — https://datatracker.ietf.org/doc/html/rfc7636
- RFC 7009 — OAuth 2.0 Token Revocation — https://datatracker.ietf.org/doc/html/rfc7009
- RFC 8414 — OAuth 2.0 Authorization Server Metadata — https://datatracker.ietf.org/doc/html/rfc8414
- RFC 8707 — Resource Indicators for OAuth 2.0 — https://www.rfc-editor.org/rfc/rfc8707.html
- RFC 9728 — OAuth 2.0 Protected Resource Metadata — https://datatracker.ietf.org/doc/html/rfc9728
- RFC 9068 — JWT Profile for OAuth 2.0 Access Tokens — https://www.rfc-editor.org/rfc/rfc9068.html
- RFC 9700 — OAuth 2.0 Security Best Current Practice — https://datatracker.ietf.org/doc/html/rfc9700
- RFC 6570 — URI Templates — https://datatracker.ietf.org/doc/html/rfc6570
- RFC 6750 — Bearer Token Usage — https://datatracker.ietf.org/doc/html/rfc6750
- RFC 5424 — Syslog Severity Levels — https://datatracker.ietf.org/doc/html/rfc5424
- RFC 3986 — URI Generic Syntax — https://datatracker.ietf.org/doc/html/rfc3986
- OAuth Client ID Metadata Documents draft — https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00
- JSON-RPC 2.0 — https://www.jsonrpc.org/specification
- SSE (HTML living standard) — https://html.spec.whatwg.org/multipage/server-sent-events.html

### Announcements and vendor documentation

- Anthropic announcement (Nov 25, 2024) — https://www.anthropic.com/news/model-context-protocol
- Cloudflare announcement of remote MCP servers (Mar 25, 2025) — https://blog.cloudflare.com/remote-model-context-protocol-servers-mcp/
- Cloudflare "Piecing together the Agent puzzle" — https://blog.cloudflare.com/building-ai-agents-with-mcp-authn-authz-and-durable-objects/
- Auth0 + Cloudflare MCP guide — https://auth0.com/blog/secure-and-deploy-remote-mcp-servers-with-auth0-and-cloudflare/
- Stytch "Building an MCP server with OAuth and Cloudflare Workers" — https://stytch.com/blog/building-an-mcp-server-oauth-cloudflare-workers/

### Host docs

- Claude Desktop — connect local servers — https://modelcontextprotocol.io/docs/develop/connect-local-servers
- Claude Code MCP integration — https://code.claude.com/docs/en/mcp
- Claude Code settings — https://code.claude.com/docs/en/settings
- Claude.ai — remote MCP connectors help article — https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- Claude.ai — building custom MCP connectors — https://claude.com/docs/connectors/building
- VS Code MCP servers (chat / Copilot) — https://code.visualstudio.com/docs/copilot/chat/mcp-servers
- VS Code MCP servers (customization page) — https://code.visualstudio.com/docs/copilot/customization/mcp-servers
- VS Code MCP developer guide (incl. `vscode:mcp/install` URL scheme) — https://code.visualstudio.com/api/extension-guides/ai/mcp
- Cursor MCP docs — https://cursor.com/docs/context/mcp
- Cursor MCP install deeplinks (`cursor://`) — https://cursor.com/docs/context/mcp/install-links
- Cursor Deeplinks general — https://cursor.com/docs/integrations/deeplinks
- Zed AI / MCP — https://zed.dev/docs/ai/mcp
- Windsurf MCP — https://docs.windsurf.com/windsurf/cascade/mcp
- OpenAI ChatGPT developer mode (MCP) — https://platform.openai.com/docs/guides/developer-mode

### Remote-MCP hosting and OAuth provider docs

- Cloudflare MCP hosting overview — https://developers.cloudflare.com/agents/model-context-protocol/
- Cloudflare "Build a Remote MCP server" guide — https://developers.cloudflare.com/agents/guides/remote-mcp-server/
- Cloudflare MCP authorization overview — https://developers.cloudflare.com/agents/model-context-protocol/authorization/
- Cloudflare MCP transport docs — https://developers.cloudflare.com/agents/model-context-protocol/transport/
- WorkOS AuthKit for MCP — https://workos.com/docs/authkit/mcp
- WorkOS "Secure auth for MCP servers" — https://workos.com/mcp
- Stytch Connected Apps for MCP — https://stytch.com/docs/guides/connected-apps/mcp-servers
- Stytch Connected Apps overview — https://stytch.com/docs/guides/connected-apps/mcp-server-overview
- Descope MCP Authorization — https://docs.descope.com/mcp
- Descope MCP Express SDK — https://docs.descope.com/mcp/mcp-express-sdk

### MCP servers cited

- Reference servers (filesystem, fetch, git, memory, …) — https://github.com/modelcontextprotocol/servers
- GitHub MCP Server — https://github.com/github/github-mcp-server
- Sentry MCP Server — https://github.com/getsentry/sentry-mcp
- Sentry MCP docs — https://docs.sentry.io/product/sentry-mcp/

### Bridges and tooling

- `mcp-remote` (stdio ↔ remote OAuth bridge) — https://github.com/geelen/mcp-remote
- `mcp-remote` on npm — https://www.npmjs.com/package/mcp-remote
- Python SDK WebSocket transport — https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/websocket.py
