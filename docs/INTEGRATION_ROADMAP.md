# Open WebUI - Integration Roadmap for Advanced AI Features

> **Version:** 1.0
> **Last Updated:** 2025-11-05
> **Purpose:** Strategic roadmap for integrating MCP UI, AG-UI, Bolt.diy, Flowise, and screenshot-to-code

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Integration Overview](#2-integration-overview)
- [3. MCP (Model Context Protocol) Integration](#3-mcp-model-context-protocol-integration)
- [4. AG-UI (Agentic UI Protocol) Integration](#4-ag-ui-agentic-ui-protocol-integration)
- [5. Bolt.diy Integration](#5-boltdiy-integration)
- [6. Flowise Integration](#6-flowise-integration)
- [7. screenshot-to-code Integration](#7-screenshot-to-code-integration)
- [8. Unified Architecture Vision](#8-unified-architecture-vision)
- [9. Implementation Phases](#9-implementation-phases)
- [10. Technical Requirements](#10-technical-requirements)
- [11. Security & Compliance](#11-security--compliance)
- [12. Testing Strategy](#12-testing-strategy)

---

## 1. Executive Summary

This document outlines a comprehensive integration strategy for adding five advanced AI capabilities to Open WebUI:

1. **MCP (Model Context Protocol)** - Standardized AI context sharing
2. **AG-UI (Agentic UI Protocol)** - Real-time agentic frontend interactions
3. **Bolt.diy** - AI-powered full-stack web development
4. **Flowise** - Visual LLM workflow builder
5. **screenshot-to-code** - Image-to-code generation

### Strategic Goals

- **Enhance Open WebUI** with cutting-edge AI capabilities
- **Maintain architectural integrity** while adding new features
- **Ensure seamless user experience** across all integrations
- **Provide extensibility** for future innovations
- **Preserve security** and privacy guarantees

### High-Level Approach

All integrations will follow Open WebUI's existing **plugin/tool architecture**:

```
Integration Method:
├── Pipelines (HTTP-based middleware)
├── Custom Functions (Python sandbox)
├── External Tools (API endpoints)
└── Native Modules (core features)
```

---

## 2. Integration Overview

### 2.1 Integration Matrix

| Feature | Integration Type | Complexity | Priority | Estimated Effort |
|---------|-----------------|------------|----------|------------------|
| **MCP** | Native Module + Tool | Medium | High | 2-3 weeks |
| **AG-UI** | Pipeline + WebSocket | High | Medium | 3-4 weeks |
| **Bolt.diy** | External Tool + Iframe | Medium | High | 2-3 weeks |
| **Flowise** | External Tool + API | Low | Medium | 1-2 weeks |
| **screenshot-to-code** | Custom Function + Pipeline | Medium | High | 2-3 weeks |

### 2.2 Integration Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                       OPEN WEBUI CORE                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Frontend (SvelteKit)                                      │  │
│  │  - Chat UI                                                 │  │
│  │  - Workspace UI (Models, Prompts, Functions, Knowledge)   │  │
│  │  - Admin Panel                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Backend (FastAPI)                                         │  │
│  │  - API Routers (26 modules)                               │  │
│  │  - RAG Engine                                              │  │
│  │  - Auth & RBAC                                             │  │
│  │  - Plugin System (Pipelines)                              │  │
│  │  - Function Execution (RestrictedPython)                  │  │
│  │  - WebSocket Server (Socket.IO)                           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    INTEGRATION LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │     MCP      │  │    AG-UI     │  │   Bolt.diy   │           │
│  │   Client     │  │   Protocol   │  │   Service    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │   Flowise    │  │ screenshot-  │                             │
│  │   Client     │  │  to-code     │                             │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ MCP Servers  │  │ AG-UI Agents │  │ Bolt.diy API │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Flowise API  │  │ Vision Models│                             │
│  └──────────────┘  └──────────────┘                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. MCP (Model Context Protocol) Integration

### 3.1 Overview

**MCP (Model Context Protocol)** is an open standard for AI context sharing, introduced by Anthropic and adopted by OpenAI, Google DeepMind, and major IDEs.

**Purpose:** Enable Open WebUI to:
- Connect to MCP servers for context retrieval
- Share project context with LLMs
- Access external tools via MCP
- Standardize context management

### 3.2 Current State in Open WebUI

**Status:** Scaffolded
**Location:** `backend/utils/mcp/client.py`
**Current Implementation:** Basic MCP client structure exists but not fully integrated

### 3.3 Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MCP INTEGRATION ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────┘

1. MCP Client Module (backend/utils/mcp/)
   ├── client.py         # MCP client implementation
   ├── servers.py        # MCP server registry
   ├── resources.py      # Resource handlers
   └── tools.py          # MCP tool wrappers

2. MCP Router (backend/routers/mcp.py)
   ├── GET /api/mcp/servers           # List configured servers
   ├── POST /api/mcp/servers          # Add MCP server
   ├── GET /api/mcp/resources         # List available resources
   ├── POST /api/mcp/resources/read   # Read resource
   └── POST /api/mcp/tools/call       # Call MCP tool

3. Frontend UI (src/routes/(app)/workspace/mcp/)
   ├── ServerConfig.svelte   # Configure MCP servers
   ├── ResourceBrowser.svelte # Browse MCP resources
   └── ToolExecutor.svelte   # Execute MCP tools

4. Chat Integration
   - Use `@mcp:resource` syntax to reference MCP resources
   - Auto-inject MCP context into chat
```

### 3.4 MCP Client Implementation

```python
# backend/utils/mcp/client.py

import httpx
import json
from typing import List, Dict, Any

class MCPClient:
    """Model Context Protocol client"""

    def __init__(self, server_url: str, auth_token: str = None):
        self.server_url = server_url
        self.auth_token = auth_token
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        )

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from MCP server"""
        resp = await self.client.get(f"{self.server_url}/resources")
        resp.raise_for_status()
        return resp.json()["resources"]

    async def read_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Read resource content"""
        resp = await self.client.post(
            f"{self.server_url}/resources/read",
            json={"uri": resource_uri}
        )
        resp.raise_for_status()
        return resp.json()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        resp = await self.client.get(f"{self.server_url}/tools")
        resp.raise_for_status()
        return resp.json()["tools"]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool"""
        resp = await self.client.post(
            f"{self.server_url}/tools/call",
            json={"name": tool_name, "arguments": arguments}
        )
        resp.raise_for_status()
        return resp.json()

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts"""
        resp = await self.client.get(f"{self.server_url}/prompts")
        resp.raise_for_status()
        return resp.json()["prompts"]

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get prompt with arguments"""
        resp = await self.client.post(
            f"{self.server_url}/prompts/get",
            json={"name": prompt_name, "arguments": arguments or {}}
        )
        resp.raise_for_status()
        return resp.json()
```

### 3.5 MCP Server Registry

```python
# backend/models/mcp.py

class MCPServer(Base):
    __tablename__ = "mcp_server"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    name = Column(String)
    url = Column(String)
    auth_type = Column(String)  # "none", "bearer", "oauth"
    auth_config = Column(JSON)
    is_active = Column(Boolean, default=True)
    is_global = Column(Boolean, default=False)  # Admin-only
    created_at = Column(Integer)
    updated_at = Column(Integer)
```

### 3.6 Chat Integration with MCP

```python
# Example: Auto-inject MCP context
async def process_chat_message(message: str, user_id: str):
    # Parse MCP references (@mcp:resource)
    mcp_refs = extract_mcp_references(message)

    contexts = []
    for ref in mcp_refs:
        # e.g., "@mcp:file:///project/README.md"
        server_id, resource_uri = parse_mcp_ref(ref)

        # Get MCP server
        mcp_server = MCPServers.get_by_id(server_id)
        client = MCPClient(mcp_server.url, mcp_server.auth_token)

        # Read resource
        resource = await client.read_resource(resource_uri)
        contexts.append(resource["content"])

    # Inject into LLM prompt
    enhanced_message = f"""
Context from MCP resources:
{'\n\n'.join(contexts)}

User Query: {message}
"""

    return enhanced_message
```

### 3.7 Implementation Steps

**Phase 1: Core MCP Client (Week 1)**
1. Complete MCP client implementation
2. Add MCP server registry (database model)
3. Create MCP router with CRUD operations
4. Add authentication support (Bearer, OAuth)

**Phase 2: Tool Integration (Week 2)**
5. Integrate MCP tools with Open WebUI function system
6. Create tool execution endpoint
7. Add resource browser API

**Phase 3: UI & Chat Integration (Week 3)**
8. Build MCP server configuration UI
9. Add resource browser component
10. Implement `@mcp:resource` syntax in chat
11. Auto-inject MCP context into conversations

### 3.8 Configuration

```yaml
# .env or config
MCP_ENABLED=true
MCP_DEFAULT_SERVERS=["http://localhost:3100", "http://mcp-server:8080"]
MCP_AUTH_TYPE=bearer  # or oauth
MCP_AUTH_TOKEN=secret_token
```

### 3.9 Benefits

- **Standardized Context**: Use industry-standard protocol
- **Tool Ecosystem**: Access MCP tool marketplace
- **IDE Integration**: Share context between IDEs and Open WebUI
- **Future-Proof**: Adopted by OpenAI, Anthropic, Google

---

## 4. AG-UI (Agentic UI Protocol) Integration

### 4.1 Overview

**AG-UI** is an open protocol for real-time agent-to-frontend communication, enabling dynamic UI generation and state synchronization.

**Purpose:** Enable Open WebUI to:
- Stream agent state in real-time
- Render dynamic UI components from agents
- Support human-in-the-loop workflows
- Enable multi-agent coordination

### 4.2 Integration Architecture

```
┌──────────────────────────────────────────────────────────┐
│  AG-UI INTEGRATION ARCHITECTURE                          │
└──────────────────────────────────────────────────────────┘

1. AG-UI Protocol Handler (backend/utils/agui/)
   ├── protocol.py       # AG-UI protocol implementation
   ├── events.py         # Event types (16 standard events)
   ├── components.py     # UI component definitions
   └── state.py          # State management

2. AG-UI Router (backend/routers/agui.py)
   ├── POST /api/agui/agents          # Create agent session
   ├── GET /api/agui/agents/:id       # Get agent state
   ├── POST /api/agui/agents/:id/action  # Send user action
   └── WS /api/agui/agents/:id/stream   # WebSocket stream

3. WebSocket Integration (backend/socket/agui.py)
   - Real-time event streaming
   - State synchronization
   - Component updates

4. Frontend Components (src/lib/components/agui/)
   ├── AgentSession.svelte    # AG-UI session manager
   ├── ComponentRenderer.svelte # Render AG-UI components
   ├── StateViewer.svelte     # Visualize agent state
   └── ActionPanel.svelte     # Human-in-the-loop actions
```

### 4.3 AG-UI Protocol Implementation

```python
# backend/utils/agui/protocol.py

from typing import Literal, Dict, Any, List
from pydantic import BaseModel

# AG-UI Event Types
class AGUIEventType:
    AGENT_STATE_DELTA = "agent_state_delta"
    COMPONENT_RENDER = "component_render"
    COMPONENT_UPDATE = "component_update"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    USER_INPUT_REQUEST = "user_input_request"
    USER_INPUT = "user_input"
    DELEGATION_START = "delegation_start"
    DELEGATION_END = "delegation_end"
    ERROR = "error"
    COMPLETION = "completion"
    # ... 6 more event types

class AGUIEvent(BaseModel):
    """AG-UI protocol event"""
    type: str
    timestamp: str
    data: Dict[str, Any]
    agent_id: str = None

class AGUIComponent(BaseModel):
    """UI component definition"""
    id: str
    type: Literal["text", "button", "form", "chart", "code", "iframe"]
    props: Dict[str, Any]
    children: List["AGUIComponent"] = []

class AGUIState(BaseModel):
    """Agent state (event-sourced)"""
    agent_id: str
    state: Dict[str, Any]
    version: int
```

### 4.4 AG-UI WebSocket Handler

```python
# backend/socket/agui.py

@sio.event
async def agui_start_agent(sid, data):
    """Start AG-UI agent session"""

    agent_id = data["agent_id"]
    user_id = (await sio.get_session(sid))["user_id"]

    # Create agent session
    session = AgentSessions.create(
        id=agent_id,
        user_id=user_id,
        agent_type=data["agent_type"],
        config=data.get("config", {})
    )

    # Join room
    await sio.enter_room(sid, f"agui:{agent_id}")

    # Initialize agent
    agent = create_agent(data["agent_type"], data.get("config", {}))

    # Stream events
    async for event in agent.run(data["input"]):
        await sio.emit("agui_event", event.dict(), room=f"agui:{agent_id}")

@sio.event
async def agui_send_action(sid, data):
    """Send user action to agent"""

    agent_id = data["agent_id"]
    action = data["action"]

    # Get agent session
    agent = get_agent_session(agent_id)

    # Send action
    await agent.handle_action(action)
```

### 4.5 Frontend AG-UI Component

```svelte
<!-- src/lib/components/agui/AgentSession.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { socket } from '$lib/stores';
  import ComponentRenderer from './ComponentRenderer.svelte';

  export let agentId: string;
  export let agentType: string;
  export let input: any;

  let state = {};
  let components = [];
  let events = [];

  onMount(() => {
    // Start agent session
    $socket.emit('agui_start_agent', {
      agent_id: agentId,
      agent_type: agentType,
      input: input
    });

    // Listen for events
    $socket.on('agui_event', (event) => {
      events = [...events, event];

      if (event.type === 'agent_state_delta') {
        // Merge state delta
        state = { ...state, ...event.data.delta };
      } else if (event.type === 'component_render') {
        // Add component
        components = [...components, event.data.component];
      } else if (event.type === 'component_update') {
        // Update component
        const idx = components.findIndex(c => c.id === event.data.component_id);
        if (idx !== -1) {
          components[idx] = { ...components[idx], ...event.data.updates };
        }
      }
    });
  });

  function sendAction(action) {
    $socket.emit('agui_send_action', {
      agent_id: agentId,
      action: action
    });
  }
</script>

<div class="agent-session">
  <h3>Agent: {agentType}</h3>

  <!-- Render components -->
  <div class="components">
    {#each components as component}
      <ComponentRenderer {component} on:action={e => sendAction(e.detail)} />
    {/each}
  </div>

  <!-- State viewer -->
  <details>
    <summary>Agent State</summary>
    <pre>{JSON.stringify(state, null, 2)}</pre>
  </details>

  <!-- Event log -->
  <details>
    <summary>Event Log ({events.length})</summary>
    {#each events as event}
      <div class="event">[{event.type}] {JSON.stringify(event.data)}</div>
    {/each}
  </details>
</div>
```

### 4.6 Implementation Steps

**Phase 1: Protocol Foundation (Week 1)**
1. Implement AG-UI protocol handler
2. Create AG-UI router and WebSocket handlers
3. Add agent session management (database)

**Phase 2: Agent Integration (Week 2)**
4. Integrate with existing Open WebUI agents/functions
5. Implement event streaming
6. Add state synchronization

**Phase 3: UI Components (Week 3)**
7. Build ComponentRenderer for AG-UI components
8. Create agent session UI
9. Add human-in-the-loop controls

**Phase 4: Framework Integration (Week 4)**
10. Integrate LangGraph agents
11. Add CrewAI support
12. Implement multi-agent delegation

### 4.7 Configuration

```yaml
# .env
AGUI_ENABLED=true
AGUI_SUPPORTED_FRAMEWORKS=["langgraph", "crewai", "mastra"]
AGUI_MAX_DELEGATION_DEPTH=3
AGUI_ENABLE_STATE_PERSISTENCE=true
```

### 4.8 Benefits

- **Real-Time Agent UI**: Dynamic component rendering
- **Human-in-the-Loop**: Pause, approve, edit agent actions
- **Multi-Agent**: Coordinate multiple agents
- **Framework Agnostic**: Works with LangGraph, CrewAI, etc.

---

## 5. Bolt.diy Integration

### 5.1 Overview

**Bolt.diy** is an open-source AI-powered full-stack web development tool that generates complete applications from prompts.

**Purpose:** Enable Open WebUI users to:
- Generate full-stack applications via chat
- Edit and deploy web apps
- Integrate generated code into knowledge base
- Preview apps in Open WebUI

### 5.2 Integration Architecture

```
┌──────────────────────────────────────────────────────────┐
│  BOLT.DIY INTEGRATION ARCHITECTURE                       │
└──────────────────────────────────────────────────────────┘

1. Bolt.diy Client (backend/utils/bolt/)
   ├── client.py         # API client
   ├── generator.py      # Code generation
   └── deployer.py       # Deployment handler

2. Bolt.diy Tool (backend/routers/tools.py)
   - POST /api/tools/bolt/generate    # Generate app
   - GET /api/tools/bolt/preview/:id  # Preview app
   - POST /api/tools/bolt/deploy      # Deploy app

3. Frontend Integration
   ├── Chat command: "/bolt Generate a todo app"
   ├── Preview iframe in chat
   └── Deploy to Netlify/Vercel

4. Function Registration
   - Register as custom function for LLM tool calling
```

### 5.3 Bolt.diy Client Implementation

```python
# backend/utils/bolt/client.py

import httpx
from typing import Dict, Any

class BoltClient:
    """Bolt.diy API client"""

    def __init__(self, bolt_url: str = "http://localhost:5173"):
        self.bolt_url = bolt_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout

    async def generate_app(
        self,
        prompt: str,
        model: str = "claude-sonnet-3.7",
        framework: str = "react"
    ) -> Dict[str, Any]:
        """Generate application from prompt"""

        resp = await self.client.post(
            f"{self.bolt_url}/api/generate",
            json={
                "prompt": prompt,
                "model": model,
                "framework": framework  # react, vue, svelte, etc.
            }
        )
        resp.raise_for_status()

        return resp.json()  # {project_id, files, preview_url}

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details"""
        resp = await self.client.get(f"{self.bolt_url}/api/projects/{project_id}")
        resp.raise_for_status()
        return resp.json()

    async def update_file(
        self,
        project_id: str,
        file_path: str,
        content: str
    ):
        """Update file in project"""
        resp = await self.client.patch(
            f"{self.bolt_url}/api/projects/{project_id}/files",
            json={"path": file_path, "content": content}
        )
        resp.raise_for_status()

    async def deploy(
        self,
        project_id: str,
        platform: str = "netlify"  # or vercel, github-pages
    ) -> Dict[str, Any]:
        """Deploy project"""
        resp = await self.client.post(
            f"{self.bolt_url}/api/deploy",
            json={"project_id": project_id, "platform": platform}
        )
        resp.raise_for_status()
        return resp.json()  # {deployment_url}
```

### 5.4 Chat Integration

```python
# Register as custom function for LLM tool calling

def register_bolt_function():
    """Register Bolt.diy as Open WebUI function"""

    function_code = """
async def generate_web_app(prompt: str, framework: str = "react"):
    \"\"\"
    Generate a full-stack web application from a text prompt.

    Args:
        prompt: Description of the app to generate
        framework: Frontend framework (react, vue, svelte)

    Returns:
        Dictionary with project_id and preview_url
    \"\"\"
    from open_webui.utils.bolt.client import BoltClient

    client = BoltClient()
    result = await client.generate_app(prompt, framework=framework)

    return {
        "project_id": result["project_id"],
        "preview_url": result["preview_url"],
        "message": f"Generated {framework} app! Preview: {result['preview_url']}"
    }
"""

    Functions.insert_new_function(
        id="bolt_generate_app",
        name="generate_web_app",
        type="function",
        content=function_code,
        is_global=True,
        is_active=True
    )
```

### 5.5 UI Integration (Chat Preview)

```svelte
<!-- src/lib/components/chat/Messages/BoltPreview.svelte -->
<script lang="ts">
  export let projectId: string;
  export let previewUrl: string;

  let showPreview = false;
</script>

<div class="bolt-preview">
  <div class="bolt-header">
    <span>🚀 Generated Web App</span>
    <button on:click={() => showPreview = !showPreview}>
      {showPreview ? 'Hide' : 'Show'} Preview
    </button>
  </div>

  {#if showPreview}
    <iframe
      src={previewUrl}
      title="Bolt.diy Preview"
      class="preview-iframe"
      sandbox="allow-scripts allow-same-origin"
    />
  {/if}

  <div class="actions">
    <a href={previewUrl} target="_blank">Open in New Tab</a>
    <button on:click={() => deployApp(projectId)}>Deploy to Netlify</button>
  </div>
</div>

<style>
  .preview-iframe {
    width: 100%;
    height: 600px;
    border: 1px solid #ccc;
    border-radius: 4px;
  }
</style>
```

### 5.6 Implementation Steps

**Phase 1: Core Integration (Week 1)**
1. Set up Bolt.diy service (Docker or local)
2. Implement BoltClient API wrapper
3. Create Bolt.diy router endpoints

**Phase 2: Function & Tool Registration (Week 2)**
4. Register as Open WebUI function
5. Add tool definition for LLM function calling
6. Implement chat command `/bolt`

**Phase 3: UI & Preview (Week 3)**
7. Build preview iframe component
8. Add deployment controls
9. Integrate with knowledge base (save generated code)

### 5.7 Configuration

```yaml
# .env
BOLT_ENABLED=true
BOLT_URL=http://localhost:5173
BOLT_DEFAULT_MODEL=claude-sonnet-3.7
BOLT_DEFAULT_FRAMEWORK=react
BOLT_DEPLOYMENT_PLATFORMS=["netlify", "vercel", "github-pages"]
```

### 5.8 Benefits

- **Rapid Prototyping**: Generate full apps from chat
- **Multi-Framework**: React, Vue, Svelte, etc.
- **Integrated Deployment**: Deploy directly from chat
- **Code Preservation**: Save to knowledge base

---

## 6. Flowise Integration

### 6.1 Overview

**Flowise** is a visual LLM workflow builder with drag-and-drop interface for creating AI applications.

**Purpose:** Enable Open WebUI users to:
- Create visual LLM workflows
- Execute Flowise flows from chat
- Embed Flowise chatflows
- Use Flowise as external agent

### 6.2 Integration Architecture

```
┌──────────────────────────────────────────────────────────┐
│  FLOWISE INTEGRATION ARCHITECTURE                        │
└──────────────────────────────────────────────────────────┘

1. Flowise Client (backend/utils/flowise/)
   ├── client.py         # API client
   ├── flows.py          # Flow management
   └── chatflow.py       # Chatflow wrapper

2. Flowise Tool (backend/routers/tools.py)
   - GET /api/tools/flowise/flows      # List flows
   - POST /api/tools/flowise/predict   # Execute flow
   - POST /api/tools/flowise/chatflows # Execute chatflow

3. OpenAI-Compatible Wrapper
   - Expose Flowise as OpenAI-compatible endpoint
   - Use in Open WebUI as "model"

4. Function Registration
   - Register flows as callable functions
```

### 6.3 Flowise Client Implementation

```python
# backend/utils/flowise/client.py

import httpx
from typing import Dict, Any, List

class FlowiseClient:
    """Flowise API client"""

    def __init__(self, flowise_url: str = "http://localhost:3000"):
        self.flowise_url = flowise_url
        self.client = httpx.AsyncClient()

    async def list_flows(self) -> List[Dict[str, Any]]:
        """List all Flowise flows"""
        resp = await self.client.get(f"{self.flowise_url}/api/v1/flows")
        resp.raise_for_status()
        return resp.json()

    async def get_flow(self, flow_id: str) -> Dict[str, Any]:
        """Get flow details"""
        resp = await self.client.get(f"{self.flowise_url}/api/v1/flows/{flow_id}")
        resp.raise_for_status()
        return resp.json()

    async def predict(
        self,
        flow_id: str,
        question: str,
        overrideConfig: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute flow prediction"""

        payload = {
            "question": question,
            "overrideConfig": overrideConfig or {}
        }

        resp = await self.client.post(
            f"{self.flowise_url}/api/v1/prediction/{flow_id}",
            json=payload
        )
        resp.raise_for_status()
        return resp.json()

    async def execute_chatflow(
        self,
        chatflow_id: str,
        message: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Execute chatflow"""

        payload = {
            "question": message,
            "chatId": session_id
        }

        resp = await self.client.post(
            f"{self.flowise_url}/api/v1/prediction/{chatflow_id}",
            json=payload
        )
        resp.raise_for_status()
        return resp.json()

    async def list_chatflows(self) -> List[Dict[str, Any]]:
        """List all chatflows"""
        resp = await self.client.get(f"{self.flowise_url}/api/v1/chatflows")
        resp.raise_for_status()
        return resp.json()
```

### 6.4 OpenAI-Compatible Wrapper

```python
# backend/routers/flowise.py

@router.post("/flowise/v1/chat/completions")
async def flowise_chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible endpoint for Flowise chatflows
    Allows using Flowise as a "model" in Open WebUI
    """

    # Extract chatflow ID from model name
    # e.g., model: "flowise:chatflow-id-123"
    chatflow_id = request.model.replace("flowise:", "")

    # Get last message
    last_message = request.messages[-1]["content"]

    # Call Flowise
    client = FlowiseClient()
    result = await client.execute_chatflow(
        chatflow_id=chatflow_id,
        message=last_message,
        session_id=request.user  # Use user ID as session
    )

    # Return OpenAI-compatible response
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": result["text"]
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
```

### 6.5 Function Registration

```python
# Register Flowise flows as callable functions

def register_flowise_flow_as_function(flow_id: str, flow_name: str):
    """Register a Flowise flow as Open WebUI function"""

    function_code = f"""
async def {flow_name}(question: str, config: dict = None):
    \"\"\"Execute Flowise flow: {flow_name}\"\"\"

    from open_webui.utils.flowise.client import FlowiseClient

    client = FlowiseClient()
    result = await client.predict(
        flow_id="{flow_id}",
        question=question,
        overrideConfig=config
    )

    return result
"""

    Functions.insert_new_function(
        id=f"flowise_{flow_id}",
        name=flow_name,
        type="function",
        content=function_code,
        is_global=True
    )
```

### 6.6 Implementation Steps

**Phase 1: Core Integration (Week 1)**
1. Deploy Flowise service (Docker)
2. Implement FlowiseClient
3. Create Flowise router

**Phase 2: Model Integration (Week 1-2)**
4. Create OpenAI-compatible wrapper
5. Register Flowise chatflows as "models" in Open WebUI
6. Test chat integration

**Phase 3: Function Integration (Week 2)**
7. Auto-register flows as functions
8. Add flow execution from chat
9. Add UI for flow management

### 6.7 Configuration

```yaml
# .env
FLOWISE_ENABLED=true
FLOWISE_URL=http://localhost:3000
FLOWISE_API_KEY=your_api_key
FLOWISE_AUTO_REGISTER_FLOWS=true
```

### 6.8 Benefits

- **Visual Workflow Builder**: Drag-and-drop LLM chains
- **Reusable Flows**: Create once, use everywhere
- **No-Code**: Build complex workflows without coding
- **Integration**: Use as model or function in Open WebUI

---

## 7. screenshot-to-code Integration

### 7.1 Overview

**screenshot-to-code** converts screenshots, mockups, and Figma designs into clean code (HTML, React, Vue, etc.).

**Purpose:** Enable Open WebUI users to:
- Upload screenshots and generate code
- Convert UI designs to components
- Rapid prototyping from images
- Enhance RAG with visual understanding

### 7.2 Integration Architecture

```
┌──────────────────────────────────────────────────────────┐
│  SCREENSHOT-TO-CODE INTEGRATION                          │
└──────────────────────────────────────────────────────────┘

1. screenshot-to-code Client (backend/utils/screenshot_to_code/)
   ├── client.py         # API client
   ├── converter.py      # Image-to-code conversion
   └── renderer.py       # Code preview

2. Custom Function
   - Function: "convert_screenshot_to_code"
   - Input: Image file upload
   - Output: Generated code (HTML/React/Vue)

3. Chat Integration
   - Upload image in chat
   - Auto-detect UI screenshot
   - Offer to convert to code

4. Vision Model Integration
   - Use Claude Sonnet 3.7 or GPT-4o Vision
   - Direct API calls for conversion
```

### 7.3 screenshot-to-code Client Implementation

```python
# backend/utils/screenshot_to_code/client.py

import httpx
import base64
from typing import Literal

class ScreenshotToCodeClient:
    """screenshot-to-code API client"""

    def __init__(self, service_url: str = "http://localhost:7001"):
        self.service_url = service_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def convert(
        self,
        image_path: str,
        output_format: Literal["html_tailwind", "react_tailwind", "vue_tailwind", "bootstrap", "ionic_tailwind", "svg"] = "react_tailwind",
        model: str = "claude-sonnet-3.7"
    ) -> Dict[str, Any]:
        """Convert screenshot to code"""

        # Read image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        payload = {
            "image": image_data,
            "format": output_format,
            "model": model
        }

        resp = await self.client.post(
            f"{self.service_url}/api/convert",
            json=payload
        )
        resp.raise_for_status()

        return resp.json()  # {code, preview_url}
```

### 7.4 Direct Vision Model Integration (No External Service)

```python
# backend/utils/screenshot_to_code/converter.py

from anthropic import AsyncAnthropic
import base64

async def convert_screenshot_to_code_direct(
    image_path: str,
    output_format: str = "react_tailwind",
    model: str = "claude-sonnet-4.0"
) -> str:
    """
    Convert screenshot to code using vision model directly
    No external service required
    """

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode()

    # Determine media type
    ext = image_path.split('.')[-1].lower()
    media_type_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    media_type = media_type_map.get(ext, 'image/png')

    # Prompt engineering
    format_instructions = {
        "html_tailwind": "Generate clean HTML with Tailwind CSS classes",
        "react_tailwind": "Generate a React component with Tailwind CSS",
        "vue_tailwind": "Generate a Vue 3 component with Tailwind CSS",
        "bootstrap": "Generate HTML with Bootstrap 5 classes",
        "ionic_tailwind": "Generate Ionic + Tailwind code",
        "svg": "Generate SVG code for this design"
    }

    prompt = f"""
You are an expert frontend developer. Convert the provided screenshot into production-ready code.

Output Format: {output_format}
Instructions: {format_instructions[output_format]}

Requirements:
1. Match the design as closely as possible
2. Use semantic HTML
3. Ensure responsive design
4. Include all visible text and elements
5. Use appropriate component structure
6. Add accessibility attributes (aria-labels, alt text)

Return ONLY the code, no explanations or markdown formatting.
"""

    # Call vision model (Claude)
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    message = await client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
    )

    return message.content[0].text
```

### 7.5 Function Registration

```python
# Register as custom function for LLM tool calling

def register_screenshot_to_code_function():
    """Register screenshot-to-code as Open WebUI function"""

    function_code = """
async def convert_screenshot_to_code(
    image_file_id: str,
    output_format: str = "react_tailwind",
    model: str = "claude-sonnet-4.0"
):
    \"\"\"
    Convert a screenshot or UI mockup to code.

    Args:
        image_file_id: File ID from Open WebUI file upload
        output_format: Output format (html_tailwind, react_tailwind, vue_tailwind, bootstrap, ionic_tailwind, svg)
        model: Vision model to use (claude-sonnet-4.0, gpt-4o)

    Returns:
        Dictionary with generated code and preview URL
    \"\"\"
    from open_webui.models.files import Files
    from open_webui.utils.screenshot_to_code.converter import convert_screenshot_to_code_direct

    # Get file
    file = Files.get_file_by_id(image_file_id)
    if not file:
        return {"error": "File not found"}

    # Convert
    code = await convert_screenshot_to_code_direct(
        image_path=file.path,
        output_format=output_format,
        model=model
    )

    # Save to file
    import uuid
    code_file_id = str(uuid.uuid4())
    Files.insert_new_file(
        id=code_file_id,
        filename=f"generated_code_{output_format}.{get_extension(output_format)}",
        path=f"/data/generated/{code_file_id}",
        user_id=file.user_id,
        data={"code": code, "source_image": image_file_id}
    )

    return {
        "code": code,
        "file_id": code_file_id,
        "message": f"Generated {output_format} code from screenshot!"
    }

def get_extension(format):
    if format.startswith("react") or format.startswith("vue"):
        return "jsx" if "react" in format else "vue"
    elif format == "svg":
        return "svg"
    else:
        return "html"
"""

    Functions.insert_new_function(
        id="screenshot_to_code",
        name="convert_screenshot_to_code",
        type="function",
        content=function_code,
        is_global=True,
        is_active=True
    )
```

### 7.6 Chat Integration (Auto-Detection)

```python
# Detect UI screenshots and offer conversion

async def process_image_upload(file_id: str, user_id: str):
    """Auto-detect UI screenshots"""

    file = Files.get_file_by_id(file_id)

    # Use vision model to detect if it's a UI screenshot
    is_ui_screenshot = await detect_ui_screenshot(file.path)

    if is_ui_screenshot:
        # Offer conversion
        return {
            "suggestion": "I detected this is a UI screenshot. Would you like me to convert it to code?",
            "actions": [
                {
                    "label": "Convert to React",
                    "function": "convert_screenshot_to_code",
                    "params": {"image_file_id": file_id, "output_format": "react_tailwind"}
                },
                {
                    "label": "Convert to Vue",
                    "function": "convert_screenshot_to_code",
                    "params": {"image_file_id": file_id, "output_format": "vue_tailwind"}
                },
                {
                    "label": "Convert to HTML",
                    "function": "convert_screenshot_to_code",
                    "params": {"image_file_id": file_id, "output_format": "html_tailwind"}
                }
            ]
        }
```

### 7.7 Implementation Steps

**Phase 1: Core Conversion (Week 1)**
1. Implement direct vision model integration (no external service)
2. Create converter utility
3. Test with Claude Sonnet 3.7 / GPT-4o Vision

**Phase 2: Function Registration (Week 2)**
4. Register as custom function
5. Add file upload handling
6. Implement code preview

**Phase 3: UI & Auto-Detection (Week 3)**
7. Build code preview component
8. Add auto-detection of UI screenshots
9. Add one-click conversion buttons in chat

### 7.8 Configuration

```yaml
# .env
SCREENSHOT_TO_CODE_ENABLED=true
SCREENSHOT_TO_CODE_DEFAULT_MODEL=claude-sonnet-4.0
SCREENSHOT_TO_CODE_DEFAULT_FORMAT=react_tailwind
SCREENSHOT_TO_CODE_AUTO_DETECT=true
```

### 7.9 Benefits

- **Rapid Prototyping**: Convert mockups to code instantly
- **Design-to-Code**: Bridge design and development
- **No External Service**: Direct vision model integration
- **Multi-Framework**: Support React, Vue, HTML, etc.

---

## 8. Unified Architecture Vision

### 8.1 Integration Synergies

```
┌─────────────────────────────────────────────────────────────┐
│  UNIFIED OPEN WEBUI WITH ADVANCED AI FEATURES               │
└─────────────────────────────────────────────────────────────┘

User Workflow Examples:

1. Design-to-App Pipeline:
   Screenshot → screenshot-to-code → Bolt.diy → Deploy
   "Convert this design to a React app and deploy it"

2. Context-Aware Development:
   MCP Resources → RAG → LLM → Bolt.diy
   "Use @mcp:project context to build a feature"

3. Agentic UI Workflows:
   AG-UI Agent → Flowise Flow → Human Approval → Execution
   "Create a data pipeline with visual workflow"

4. Visual Knowledge Base:
   screenshot-to-code → Knowledge → RAG → Code Generation
   "Reference this UI pattern from our design system"

5. Multi-Agent Coordination:
   AG-UI Agents + MCP Tools + Flowise Flows
   "Coordinate 3 agents to build, test, and deploy"
```

### 8.2 Unified Chat Interface

```
Chat Input Examples:

1. "/bolt Generate a todo app with Tailwind"
   → Bolt.diy generates app
   → Preview in chat
   → Deploy option

2. "Convert this screenshot to React [uploads image]"
   → screenshot-to-code processes
   → Shows generated code
   → Option to open in Bolt.diy

3. "@mcp:file:///project/README.md Build a feature described here"
   → MCP loads context
   → LLM generates plan
   → Bolt.diy creates code

4. "/flowise run customer_support_flow with question: ..."
   → Flowise executes flow
   → Returns result

5. "Create an agent to monitor our database @agui"
   → AG-UI agent starts
   → Real-time state updates
   → Human-in-the-loop approvals
```

### 8.3 Architectural Layers

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: USER INTERFACE                                    │
│  - Chat UI (unified commands)                               │
│  - Component previews (iframe, code blocks)                 │
│  - Agent state visualization                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: ORCHESTRATION                                     │
│  - Command router (/bolt, /flowise, @mcp, @agui)           │
│  - Function calling (LLM tools)                             │
│  - Workflow engine                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: INTEGRATION SERVICES                              │
│  - MCP Client                                               │
│  - AG-UI Protocol Handler                                   │
│  - Bolt.diy Client                                          │
│  - Flowise Client                                           │
│  - screenshot-to-code Converter                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: CORE OPEN WEBUI                                   │
│  - RAG Engine                                               │
│  - Auth & RBAC                                              │
│  - Database                                                 │
│  - Storage                                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 5: EXTERNAL SERVICES                                 │
│  - LLMs (OpenAI, Anthropic, Ollama)                        │
│  - MCP Servers                                              │
│  - Bolt.diy Service                                         │
│  - Flowise Service                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goals:**
- Set up infrastructure for all integrations
- Implement core clients
- Basic API endpoints

**Tasks:**
1. Deploy external services (Flowise, Bolt.diy - optional)
2. Implement MCP client (complete existing scaffolding)
3. Implement Flowise client
4. Implement Bolt.diy client
5. Implement screenshot-to-code converter (direct vision)
6. Create database models for new entities
7. Set up configuration management

**Deliverables:**
- All client libraries functional
- Database schema updated
- Configuration documented

### Phase 2: Core Integrations (Weeks 3-5)

**Goals:**
- Integrate services with Open WebUI core
- Function registration
- API endpoints

**Tasks:**
1. Complete MCP integration (tools, resources, prompts)
2. Register Flowise flows as functions
3. Register Bolt.diy as function/tool
4. Register screenshot-to-code as function
5. Create routers for each integration
6. Implement OpenAI-compatible wrappers where needed
7. Add WebSocket handlers for AG-UI

**Deliverables:**
- All services callable from backend
- Function calling works
- API endpoints tested

### Phase 3: UI & UX (Weeks 6-7)

**Goals:**
- Build user interfaces
- Chat integration
- Component previews

**Tasks:**
1. Build MCP resource browser UI
2. Build AG-UI agent session UI
3. Build Bolt.diy preview iframe
4. Build Flowise flow selector
5. Build screenshot-to-code uploader and code preview
6. Implement chat commands (`/bolt`, `/flowise`, etc.)
7. Add auto-detection and suggestions

**Deliverables:**
- Complete UI for all integrations
- Chat commands working
- Preview components functional

### Phase 4: AG-UI Protocol (Weeks 8-9)

**Goals:**
- Full AG-UI protocol implementation
- Real-time agent state
- Multi-agent coordination

**Tasks:**
1. Implement AG-UI protocol handler
2. Add event streaming (16 event types)
3. Build component renderer
4. Integrate with LangGraph/CrewAI
5. Add human-in-the-loop controls
6. Implement state persistence

**Deliverables:**
- AG-UI fully functional
- Agent sessions working
- Real-time updates

### Phase 5: Polish & Documentation (Weeks 10-11)

**Goals:**
- Testing
- Documentation
- Examples

**Tasks:**
1. Write integration tests
2. Write E2E tests
3. Create user documentation
4. Create developer documentation
5. Build example workflows
6. Performance optimization
7. Security audit

**Deliverables:**
- Comprehensive test coverage
- User guides
- API documentation
- Example projects

### Phase 6: Advanced Features (Weeks 12+)

**Goals:**
- Advanced workflows
- Optimization
- Community feedback

**Tasks:**
1. Workflow automation (chaining integrations)
2. Templates and presets
3. Analytics and monitoring
4. Community integrations
5. Plugin marketplace preparation

**Deliverables:**
- Advanced features documented
- Optimization complete
- Ready for community use

---

## 10. Technical Requirements

### 10.1 Infrastructure Requirements

**Services to Deploy:**

```yaml
# docker-compose.yml for all services

version: '3.8'
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      - MCP_ENABLED=true
      - AGUI_ENABLED=true
      - BOLT_ENABLED=true
      - FLOWISE_ENABLED=true
      - SCREENSHOT_TO_CODE_ENABLED=true
      - FLOWISE_URL=http://flowise:3000
      - BOLT_URL=http://bolt:5173
    volumes:
      - open-webui-data:/app/backend/data

  flowise:
    image: flowiseai/flowise:latest
    ports:
      - "3001:3000"
    environment:
      - DATABASE_PATH=/data/flowise.db
    volumes:
      - flowise-data:/data

  bolt:
    image: stackblitz/bolt.diy:latest  # If available
    ports:
      - "5173:5173"
    volumes:
      - bolt-data:/app/projects

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

volumes:
  open-webui-data:
  flowise-data:
  bolt-data:
  ollama-data:
```

### 10.2 Dependencies

**Python Packages:**

```toml
# pyproject.toml additions

[tool.poetry.dependencies]
# MCP
mcp-client = "^0.1.0"  # If available, else custom

# AG-UI
agui-protocol = "^0.1.0"  # If available, else custom

# Vision models (already included)
anthropic = "^0.42.0"
openai = "^1.59.7"

# Additional utilities
aiofiles = "^24.1.0"  # Async file I/O
```

**Frontend Packages:**

```json
// package.json additions
{
  "dependencies": {
    // AG-UI
    "@ag-ui/client": "^0.1.0",  // If available

    // Yjs (already included)
    "yjs": "^13.6.27",
    "y-websocket": "^1.5.0"
  }
}
```

### 10.3 Database Schema Updates

```sql
-- MCP Servers
CREATE TABLE mcp_server (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    auth_type TEXT,
    auth_config JSON,
    is_active BOOLEAN DEFAULT 1,
    is_global BOOLEAN DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- AG-UI Agent Sessions
CREATE TABLE agui_session (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    config JSON,
    state JSON,
    state_version INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- Bolt.diy Projects
CREATE TABLE bolt_project (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    framework TEXT,
    files JSON,
    preview_url TEXT,
    deployment_url TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- Flowise Flows (if managing internally)
CREATE TABLE flowise_flow (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    flow_id TEXT NOT NULL,  -- Flowise flow ID
    name TEXT NOT NULL,
    description TEXT,
    config JSON,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

---

## 11. Security & Compliance

### 11.1 Security Considerations

**1. External Service Communication:**
- Use HTTPS for all external service calls
- Validate SSL certificates
- Implement request timeouts
- Rate limiting on external API calls

**2. Code Execution:**
- RestrictedPython sandbox for all user code
- Resource limits (CPU, memory, time)
- Network isolation for code execution
- Admin approval for global functions

**3. Data Privacy:**
- User consent for sending data to external services
- Option to use self-hosted services only
- Data retention policies
- GDPR compliance

**4. Authentication:**
- API key management for external services
- Encrypted storage of credentials
- User-level vs admin-level service access
- OAuth for service-to-service auth

### 11.2 Compliance Checklist

- [ ] User consent for external service usage
- [ ] Data processing agreements (if using cloud services)
- [ ] Privacy policy update
- [ ] Terms of service update
- [ ] Security audit of new code
- [ ] Penetration testing
- [ ] GDPR compliance review
- [ ] SOC 2 compliance (if required)

---

## 12. Testing Strategy

### 12.1 Unit Tests

```python
# tests/test_mcp_client.py
async def test_mcp_client_list_resources():
    client = MCPClient("http://localhost:3100")
    resources = await client.list_resources()
    assert isinstance(resources, list)

# tests/test_bolt_client.py
async def test_bolt_generate_app():
    client = BoltClient()
    result = await client.generate_app("Create a todo app")
    assert "project_id" in result
    assert "preview_url" in result

# tests/test_flowise_client.py
async def test_flowise_execute_flow():
    client = FlowiseClient()
    result = await client.predict(flow_id="123", question="Test")
    assert "text" in result

# tests/test_screenshot_to_code.py
async def test_screenshot_conversion():
    result = await convert_screenshot_to_code_direct(
        "test_image.png",
        output_format="react_tailwind"
    )
    assert "import React" in result
```

### 12.2 Integration Tests

```python
# tests/integration/test_mcp_integration.py
async def test_mcp_chat_integration():
    # Test @mcp:resource syntax in chat
    response = await process_chat_message(
        "@mcp:file:///README.md Summarize this",
        user_id="test_user"
    )
    assert "context" in response.lower()

# tests/integration/test_bolt_integration.py
async def test_bolt_function_calling():
    # Test LLM calling bolt function
    result = await execute_function(
        "generate_web_app",
        {"prompt": "Todo app", "framework": "react"}
    )
    assert result["project_id"]

# tests/integration/test_agui_protocol.py
async def test_agui_event_streaming():
    # Test AG-UI event stream
    events = []
    async for event in agent.run("Test task"):
        events.append(event)
    assert len(events) > 0
    assert events[0].type in AGUIEventType.__dict__.values()
```

### 12.3 E2E Tests

```typescript
// cypress/e2e/integrations.cy.ts

describe('MCP Integration', () => {
  it('should list MCP servers', () => {
    cy.visit('/workspace/mcp');
    cy.contains('MCP Servers');
    cy.get('[data-testid="mcp-server-list"]').should('exist');
  });

  it('should use @mcp syntax in chat', () => {
    cy.visit('/c/new');
    cy.get('[data-testid="chat-input"]').type('@mcp:test');
    cy.get('[data-testid="mcp-autocomplete"]').should('be.visible');
  });
});

describe('Bolt.diy Integration', () => {
  it('should generate app from chat', () => {
    cy.visit('/c/new');
    cy.get('[data-testid="chat-input"]').type('/bolt Generate a todo app{enter}');
    cy.contains('Generated React app', { timeout: 60000 });
    cy.get('[data-testid="bolt-preview-iframe"]').should('exist');
  });
});
```

---

## Conclusion

This integration roadmap provides a comprehensive plan for adding five advanced AI features to Open WebUI:

1. **MCP** - Standardized context protocol
2. **AG-UI** - Real-time agentic UI
3. **Bolt.diy** - AI-powered web development
4. **Flowise** - Visual LLM workflows
5. **screenshot-to-code** - Image-to-code generation

### Key Success Factors

1. **Incremental Implementation**: Phased rollout over 12 weeks
2. **Architectural Integrity**: Use existing plugin/tool patterns
3. **User Experience**: Seamless chat integration
4. **Security**: Sandboxed execution, user consent
5. **Extensibility**: Open for future integrations

### Next Steps

1. Review and approve roadmap
2. Set up development environment
3. Begin Phase 1 implementation
4. Establish testing protocols
5. Create feedback loops with community

---

**Document Version:** 1.0
**Last Updated:** 2025-11-05
**Maintained by:** Open WebUI Team

**For questions or contributions:**
- GitHub: https://github.com/open-webui/open-webui
- Documentation: https://docs.openwebui.com
- Discord: https://discord.gg/5rJgQTnV4s
