Transports
==========

Copy page

Learn about MCP's communication mechanisms

Transports in the Model Context Protocol (MCP) provide the foundation for communication between clients and servers. A transport handles the underlying mechanics of how messages are sent and received.

[​

](https://modelcontextprotocol.io/docs/concepts/transports#message-format)
Message Format
---------------------------------------------------------------------------------------------

MCP uses [JSON-RPC](https://www.jsonrpc.org/) 2.0 as its wire format. The transport layer is responsible for converting MCP protocol messages into JSON-RPC format for transmission and converting received JSON-RPC messages back into MCP protocol messages.

There are three types of JSON-RPC messages used:

### [​

](https://modelcontextprotocol.io/docs/concepts/transports#requests)
Requests

Copy

```
{
  jsonrpc: "2.0",
  id: number | string,
  method: string,
  params?: object
}

```

### [​

](https://modelcontextprotocol.io/docs/concepts/transports#responses)
Responses

Copy

```
{
  jsonrpc: "2.0",
  id: number | string,
  result?: object,
  error?: {
    code: number,
    message: string,
    data?: unknown
  }
}

```

### [​

](https://modelcontextprotocol.io/docs/concepts/transports#notifications)
Notifications

Copy

```
{
  jsonrpc: "2.0",
  method: string,
  params?: object
}

```

[​

](https://modelcontextprotocol.io/docs/concepts/transports#built-in-transport-types)

-----------------------------------------------------------------------------------------
### Server-Sent Events (SSE)

SSE transport enables server-to-client streaming with HTTP POST requests for client-to-server communication.

Use SSE when:

-   Only server-to-client streaming is needed
-   Working with restricted networks
-   Implementing simple updates

#### [​

](https://modelcontextprotocol.io/docs/concepts/transports#security-warning%3A-dns-rebinding-attacks)
Security Warning: DNS Rebinding Attacks

SSE transports can be vulnerable to DNS rebinding attacks if not properly secured. To prevent this:

1.  **Always validate Origin headers** on incoming SSE connections to ensure they come from expected sources
2.  **Avoid binding servers to all network interfaces** (0.0.0.0) when running locally - bind only to localhost (127.0.0.1) instead
3.  **Implement proper authentication** for all SSE connections

Without these protections, attackers could use DNS rebinding to interact with local MCP servers from remote websites.

-   TypeScript (Client)

Copy

```
const client = new Client({
  name: "example-client",
  version: "1.0.0"
}, {
  capabilities: {}
});

const transport = new SSEClientTransport(
  new URL("http://localhost:3000/sse")
);
await client.connect(transport);
```