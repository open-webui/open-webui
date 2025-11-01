# Open WebUI Automation Features - Architecture

## Overview

This document describes the architecture of three new automation features for Open WebUI:

1. **N8N Integration**: Workflow automation via N8N webhooks
2. **Auto Memory**: Automatic conversation fact extraction using NER
3. **AutoTool Filter**: Semantic tool matching and suggestion

---

## System Architecture

### High-Level Component Diagram

```mermaid
graph TB
    subgraph "Open WebUI Frontend"
        UI[User Interface]
        Chat[Chat Component]
    end

    subgraph "Open WebUI Backend"
        API[FastAPI Router]
        Functions[Functions/Filters]
        LLM[LLM Integration]
    end

    subgraph "Automation Features"
        AutoTool[AutoTool Filter<br/>Inlet]
        N8N[N8N Integration<br/>Router]
        AutoMem[Auto Memory<br/>Outlet]
    end

    subgraph "External Services"
        N8NServer[N8N Server]
        HuggingFace[HuggingFace Models]
    end

    subgraph "Data Layer"
        DB[(SQLite/PostgreSQL)]
        ChromaDB[(ChromaDB)]
    end

    UI --> Chat
    Chat --> API
    API --> AutoTool
    AutoTool --> LLM
    LLM --> AutoMem
    AutoMem --> API

    API --> N8N
    N8N --> N8NServer

    AutoTool --> HuggingFace
    AutoMem --> HuggingFace

    N8N --> DB
    AutoMem --> ChromaDB
```

---

## Request Flow

### Complete Request/Response Cycle

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant AutoTool
    participant LLM
    participant AutoMemory
    participant ChromaDB
    participant N8N

    User->>Frontend: Send message
    Frontend->>API: POST /api/chat

    Note over API: Inlet Filter Phase
    API->>AutoTool: Process query
    AutoTool->>AutoTool: Rank tools by similarity
    AutoTool-->>API: Suggestions/injected tools

    Note over API: LLM Processing
    API->>LLM: Generate response (with tools)
    LLM-->>API: Assistant response

    Note over API: Outlet Filter Phase
    API->>AutoMemory: Extract entities
    AutoMemory->>AutoMemory: NER extraction
    AutoMemory->>ChromaDB: Store memories
    ChromaDB-->>AutoMemory: Confirmation
    AutoMemory-->>API: Metadata added

    API-->>Frontend: Complete response + metadata
    Frontend-->>User: Display message

    alt N8N Workflow Triggered
        User->>API: POST /api/n8n/trigger/{id}
        API->>N8N: Execute workflow
        N8N->>N8N: HTTP call to N8N server
        N8N-->>API: Execution result
        API-->>User: Workflow complete
    end
```

---

## N8N Integration Architecture

### Component Structure

```mermaid
graph LR
    subgraph "FastAPI Router"
        Router[n8n_integration.py]
    end

    subgraph "Database Models"
        Models[n8n_config.py]
        ConfigDB[(n8n_config)]
        ExecDB[(n8n_executions)]
    end

    subgraph "N8N Server"
        Webhook[Webhook Endpoint]
        Workflow[Workflow Execution]
    end

    Router --> Models
    Models --> ConfigDB
    Models --> ExecDB
    Router --> Webhook
    Webhook --> Workflow
```

### N8N Trigger Flow (Non-Streaming)

```mermaid
sequenceDiagram
    participant Client
    participant Router
    participant HTTP[HTTP Client Pool]
    participant N8N[N8N Server]
    participant DB[Database]

    Client->>Router: POST /api/n8n/trigger/{id}
    Router->>DB: Get configuration
    DB-->>Router: Config with webhook_id

    Note over Router: Retry Loop (max 3)
    loop Retry with backoff
        Router->>HTTP: Get pooled connection
        HTTP->>N8N: POST /webhook/{webhook_id}

        alt Success
            N8N-->>HTTP: 200 OK + response
            HTTP-->>Router: Response data
            Router->>DB: Record success
        else HTTP Error
            N8N-->>HTTP: 4xx/5xx error
            HTTP-->>Router: Error
            Router->>Router: Wait exponential backoff
        else Timeout
            HTTP-->>Router: Timeout
            Router->>Router: Wait exponential backoff
        end
    end

    Router->>DB: Store execution record
    Router-->>Client: Execution result
```

### N8N Streaming Flow (SSE)

```mermaid
sequenceDiagram
    participant Client
    participant Router
    participant N8N[N8N Server]
    participant DB[Database]

    Client->>Router: POST /api/n8n/trigger/{id}/stream
    Router->>DB: Get configuration
    Router->>N8N: Stream POST request

    Note over Router,N8N: SSE Stream Active
    Router-->>Client: data: {"type": "connected"}

    loop Workflow Execution
        N8N-->>Router: Chunk of data
        Router-->>Client: data: {"type": "progress", ...}
    end

    N8N-->>Router: Final result
    Router-->>Client: data: {"type": "completed"}

    Router->>DB: Record execution
    Router-->>Client: [Stream closed]
```

### Database Schema

```mermaid
erDiagram
    N8N_CONFIG ||--o{ N8N_EXECUTIONS : "has many"

    N8N_CONFIG {
        string id PK
        string user_id FK
        string name
        string n8n_url
        string webhook_id
        string api_key
        boolean is_active
        boolean is_streaming
        integer timeout_seconds
        json retry_config
        json metadata
        bigint created_at
        bigint updated_at
    }

    N8N_EXECUTIONS {
        string id PK
        string config_id FK
        string user_id FK
        text prompt
        text response
        string status
        integer duration_ms
        text error_message
        json metadata
        bigint created_at
    }
```

---

## Auto Memory Architecture

### Component Structure

```mermaid
graph TB
    subgraph "Auto Memory Filter"
        Filter[auto_memory.py]
        NER[Spacy NER]
        Dedup[Deduplication Cache]
    end

    subgraph "Vector Database"
        ChromaDB[(ChromaDB)]
        Collections[User Collections]
    end

    Filter --> NER
    Filter --> Dedup
    Filter --> ChromaDB
    ChromaDB --> Collections
```

### Memory Extraction Flow

```mermaid
sequenceDiagram
    participant LLM
    participant Filter[Auto Memory]
    participant Spacy[Spacy NER]
    participant Cache[Dedup Cache]
    participant Chroma[ChromaDB]

    LLM->>Filter: Assistant response
    Filter->>Spacy: Load model (lazy)
    Spacy-->>Filter: Model ready

    Filter->>Filter: Extract entities

    loop For each entity
        Filter->>Filter: Check confidence threshold

        alt Confidence >= threshold
            Filter->>Cache: Check if duplicate
            Cache-->>Filter: Not duplicate

            Filter->>Chroma: Store memory
            Note over Chroma: Collection: user-memory-{user_id}
            Chroma-->>Filter: Stored

            Filter->>Cache: Update cache
        else Low confidence or duplicate
            Filter->>Filter: Skip
        end
    end

    Filter->>Filter: Add metadata to response
    Filter-->>LLM: Response with metadata
```

### Entity Extraction Process

```mermaid
flowchart TD
    Start[Text Input] --> Parse[Spacy Parse]
    Parse --> Entities[Extract Entities]
    Entities --> Filter{Entity Type<br/>in config?}

    Filter -->|Yes| Confidence{Confidence >= <br/>threshold?}
    Filter -->|No| Skip1[Skip]

    Confidence -->|Yes| Context[Get Sentence Context]
    Confidence -->|No| Skip2[Skip]

    Context --> Truncate{Context > <br/>max length?}
    Truncate -->|Yes| Trim[Truncate + '...']
    Truncate -->|No| Keep[Keep full context]

    Trim --> Build[Build Entity Object]
    Keep --> Build

    Build --> Dedup{Already in<br/>cache?}
    Dedup -->|No| Store[Store in ChromaDB]
    Dedup -->|Yes| Skip3[Skip duplicate]

    Store --> Cache[Update cache]
    Cache --> End[Return metadata]

    Skip1 --> End
    Skip2 --> End
    Skip3 --> End
```

### ChromaDB Storage Structure

```mermaid
graph TB
    subgraph "ChromaDB Instance"
        subgraph "Collection: user-memory-user-123"
            Doc1[Document 1<br/>PERSON: John]
            Meta1[Metadata:<br/>type, entity, context, confidence]
            Embed1[Embedding Vector<br/>384 dimensions]
        end

        subgraph "Collection: user-memory-user-456"
            Doc2[Document 2<br/>ORG: Google]
            Meta2[Metadata:<br/>type, entity, context, confidence]
            Embed2[Embedding Vector<br/>384 dimensions]
        end
    end

    Doc1 --- Meta1
    Doc1 --- Embed1
    Doc2 --- Meta2
    Doc2 --- Embed2
```

---

## AutoTool Filter Architecture

### Component Structure

```mermaid
graph TB
    subgraph "AutoTool Filter"
        Filter[auto_tool_filter.py]
        Encoder[Sentence Transformer]
        Cache[Embedding Cache]
        Similarity[Cosine Similarity]
    end

    subgraph "Tool Database"
        UserTools[(User Tools)]
        GlobalTools[(Global Tools)]
    end

    Filter --> Encoder
    Filter --> Cache
    Filter --> Similarity
    Filter --> UserTools
    Filter --> GlobalTools
```

### Tool Matching Flow

```mermaid
sequenceDiagram
    participant User
    participant Filter[AutoTool Filter]
    participant Model[Sentence Transformer]
    participant Cache[Embedding Cache]
    participant DB[Tools Database]

    User->>Filter: User query
    Filter->>DB: Get available tools
    DB-->>Filter: User tools + Global tools

    Filter->>Model: Lazy load model
    Model-->>Filter: Model ready

    Filter->>Model: Encode query
    Model-->>Filter: Query embedding

    loop For each tool
        Filter->>Cache: Check cache

        alt Cache hit
            Cache-->>Filter: Tool embedding
        else Cache miss
            Filter->>Model: Encode tool description
            Model-->>Filter: Tool embedding
            Filter->>Cache: Store embedding
        end

        Filter->>Filter: Compute cosine similarity

        alt Similarity >= threshold
            Filter->>Filter: Add to results
        else Below threshold
            Filter->>Filter: Skip
        end
    end

    Filter->>Filter: Sort by score descending
    Filter->>Filter: Take top-K results

    alt auto_select = true
        Filter->>Filter: Inject tools into request
    else auto_select = false
        Filter->>Filter: Add to metadata as suggestions
    end

    Filter-->>User: Modified request
```

### Similarity Computation

```mermaid
flowchart LR
    Query[User Query] --> QEmbed[Query Embedding<br/>384 dimensions]
    Tool[Tool Description] --> TEmbed[Tool Embedding<br/>384 dimensions]

    QEmbed --> Cosine[Cosine Similarity]
    TEmbed --> Cosine

    Cosine --> Score[Similarity Score<br/>0.0 - 1.0]
    Score --> Threshold{Score >=<br/>threshold?}

    Threshold -->|Yes| Match[Include in results]
    Threshold -->|No| Reject[Exclude]
```

### Cache Eviction Strategy

```mermaid
flowchart TD
    Add[New Tool Embedding] --> Check{Cache size<br/>< 500?}

    Check -->|Yes| Store[Store in cache]
    Check -->|No| Evict[Remove oldest entry<br/>FIFO]

    Evict --> Store
    Store --> End[Cache updated]
```

---

## Integration Points

### Filter Execution Order

```mermaid
graph LR
    Request[HTTP Request] --> Inlet[Inlet Filters]

    subgraph Inlet Filters
        AutoTool[AutoTool Filter]
        Custom1[Custom Inlet Filter 1]
        Custom2[Custom Inlet Filter 2]
    end

    Inlet --> LLM[LLM Processing]
    LLM --> Outlet[Outlet Filters]

    subgraph Outlet Filters
        AutoMem[Auto Memory]
        Custom3[Custom Outlet Filter 1]
        Custom4[Custom Outlet Filter 2]
    end

    Outlet --> Response[HTTP Response]
```

### Database Integration

```mermaid
graph TB
    subgraph "Open WebUI Database"
        Users[(Users Table)]
        Tools[(Tools Table)]
        N8NConfig[(n8n_config Table)]
        N8NExec[(n8n_executions Table)]
    end

    subgraph "ChromaDB"
        Memory1[(user-memory-user-1)]
        Memory2[(user-memory-user-2)]
        MemoryN[(user-memory-user-n)]
    end

    Users --> N8NConfig
    Users --> N8NExec
    Users --> Memory1
    Users --> Memory2
    Users --> MemoryN

    Users --> Tools
    Tools --> AutoTool[AutoTool Filter]
```

---

## Performance Characteristics

### Latency Breakdown

```mermaid
gantt
    title Request Processing Timeline (typical)
    dateFormat X
    axisFormat %L ms

    section AutoTool Filter
    Get tools from DB    :a1, 0, 20ms
    Encode query         :a2, after a1, 50ms
    Compute similarities :a3, after a2, 30ms

    section LLM Processing
    LLM API call        :b1, after a3, 1000ms

    section Auto Memory
    NER extraction      :c1, after b1, 150ms
    ChromaDB storage    :c2, after c1, 50ms
```

### Memory Usage

| Component | Memory | Notes |
|-----------|--------|-------|
| Spacy Model (`en_core_web_sm`) | ~40MB | Lazy loaded |
| Sentence Transformer (`all-MiniLM-L6-v2`) | ~80MB | Lazy loaded |
| Auto Memory Cache | ~100KB | Max 1000 entries |
| AutoTool Cache | ~750KB | Max 500 entries, 384-dim vectors |
| N8N HTTP Client | ~5MB | Connection pool |
| **Total Overhead** | **~125MB** | Per worker process |

---

## Scaling Considerations

### Horizontal Scaling

```mermaid
graph TB
    LB[Load Balancer]

    subgraph "Open WebUI Instance 1"
        API1[FastAPI]
        Worker1[Gunicorn Worker]
    end

    subgraph "Open WebUI Instance 2"
        API2[FastAPI]
        Worker2[Gunicorn Worker]
    end

    subgraph "Open WebUI Instance 3"
        API3[FastAPI]
        Worker3[Gunicorn Worker]
    end

    LB --> API1
    LB --> API2
    LB --> API3

    API1 --> SharedDB[(Shared Database)]
    API2 --> SharedDB
    API3 --> SharedDB

    API1 --> SharedChroma[(Shared ChromaDB)]
    API2 --> SharedChroma
    API3 --> SharedChroma

    API1 --> SharedN8N[Shared N8N Server]
    API2 --> SharedN8N
    API3 --> SharedN8N
```

### Caching Strategy

```mermaid
graph TB
    Request[Request] --> L1[L1: In-Memory Cache<br/>Tool/Memory embeddings]
    L1 -->|Miss| L2[L2: ChromaDB<br/>Persistent vectors]
    L2 -->|Miss| Compute[Compute Embedding<br/>Sentence Transformer]

    Compute --> UpdateL2[Update L2]
    UpdateL2 --> UpdateL1[Update L1]
    UpdateL1 --> Response[Response]

    L1 -->|Hit| Response
    L2 -->|Hit| UpdateL1
```

---

## Security Architecture

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API[FastAPI]
    participant Auth[Authentication Middleware]
    participant Router[Feature Router]
    participant DB[Database]

    Client->>API: Request + Bearer Token
    API->>Auth: Validate token
    Auth->>Auth: Verify JWT signature

    alt Valid token
        Auth->>Auth: Extract user_id
        Auth->>Router: Request + user object

        Router->>DB: Query user-owned resources

        alt User owns resource
            DB-->>Router: Resource data
            Router-->>Client: 200 OK
        else User doesn't own
            Router-->>Client: 403 Forbidden
        end
    else Invalid token
        Auth-->>Client: 401 Unauthorized
    end
```

### Data Isolation

```mermaid
graph TB
    subgraph "User A"
        A_Request[Request]
        A_N8N[N8N Configs]
        A_Memory[ChromaDB Collection]
    end

    subgraph "User B"
        B_Request[Request]
        B_N8N[N8N Configs]
        B_Memory[ChromaDB Collection]
    end

    subgraph "Database"
        DB[(Database)]
    end

    subgraph "ChromaDB"
        Chroma[(ChromaDB)]
    end

    A_Request --> A_N8N
    A_Request --> A_Memory
    B_Request --> B_N8N
    B_Request --> B_Memory

    A_N8N --> DB
    B_N8N --> DB
    A_Memory --> Chroma
    B_Memory --> Chroma

    A_N8N -.x B_N8N
    A_Memory -.x B_Memory

    style A_N8N fill:#e1f5e1
    style A_Memory fill:#e1f5e1
    style B_N8N fill:#ffe1e1
    style B_Memory fill:#ffe1e1
```

---

## Deployment Architecture

### Production Deployment

```mermaid
graph TB
    subgraph "Frontend (Nginx)"
        Nginx[Nginx Reverse Proxy]
    end

    subgraph "Backend Cluster"
        API1[Open WebUI Instance 1]
        API2[Open WebUI Instance 2]
        API3[Open WebUI Instance 3]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Primary)]
        PG_Replica[(PostgreSQL<br/>Replica)]
        ChromaCluster[(ChromaDB Cluster)]
    end

    subgraph "External Services"
        N8N[N8N Server]
        HF[HuggingFace API]
    end

    Nginx --> API1
    Nginx --> API2
    Nginx --> API3

    API1 --> PG
    API2 --> PG
    API3 --> PG

    API1 --> PG_Replica
    API2 --> PG_Replica
    API3 --> PG_Replica

    API1 --> ChromaCluster
    API2 --> ChromaCluster
    API3 --> ChromaCluster

    API1 --> N8N
    API2 --> N8N
    API3 --> N8N

    API1 --> HF
    API2 --> HF
    API3 --> HF
```

---

## Error Handling

### N8N Retry Flow

```mermaid
flowchart TD
    Start[Trigger Workflow] --> Attempt1[Attempt 1: Immediate]

    Attempt1 --> Success1{Success?}
    Success1 -->|Yes| Done[Return Success]
    Success1 -->|No| Wait1[Wait 2^0 = 1s]

    Wait1 --> Attempt2[Attempt 2: After 1s]
    Attempt2 --> Success2{Success?}
    Success2 -->|Yes| Done
    Success2 -->|No| Wait2[Wait 2^1 = 2s]

    Wait2 --> Attempt3[Attempt 3: After 2s]
    Attempt3 --> Success3{Success?}
    Success3 -->|Yes| Done
    Success3 -->|No| Wait3[Wait 2^2 = 4s]

    Wait3 --> Attempt4[Attempt 4: After 4s]
    Attempt4 --> Success4{Success?}
    Success4 -->|Yes| Done
    Success4 -->|No| Failed[Return Failed]

    Failed --> Record[Record execution with error]
    Record --> End[End]

    Done --> Record2[Record execution as success]
    Record2 --> End
```

---

## Monitoring & Observability

### Metrics Collection Points

```mermaid
graph TB
    subgraph "Request Metrics"
        ReqRate[Request Rate]
        ReqLatency[Request Latency]
        ReqErrors[Error Rate]
    end

    subgraph "N8N Metrics"
        N8NSuccess[Success Rate]
        N8NLatency[Workflow Duration]
        N8NRetries[Retry Count]
    end

    subgraph "Auto Memory Metrics"
        MemExtracted[Entities Extracted]
        MemStored[Entities Stored]
        MemDedup[Deduplications]
    end

    subgraph "AutoTool Metrics"
        ToolSuggestions[Suggestions Made]
        ToolInjections[Auto-Injections]
        ToolCacheHits[Cache Hit Rate]
    end

    subgraph "Monitoring Stack"
        Prometheus[Prometheus]
        Grafana[Grafana Dashboard]
    end

    ReqRate --> Prometheus
    ReqLatency --> Prometheus
    ReqErrors --> Prometheus
    N8NSuccess --> Prometheus
    N8NLatency --> Prometheus
    N8NRetries --> Prometheus
    MemExtracted --> Prometheus
    MemStored --> Prometheus
    MemDedup --> Prometheus
    ToolSuggestions --> Prometheus
    ToolInjections --> Prometheus
    ToolCacheHits --> Prometheus

    Prometheus --> Grafana
```

---

## Future Enhancements

### Roadmap Architecture

```mermaid
timeline
    title Feature Roadmap

    section Q1 2025
        Multi-Language Support : Auto Memory NER for non-English
                                : AutoTool multi-language queries

    section Q2 2025
        Advanced Analytics : N8N workflow insights dashboard
                          : Memory relationship graph

    section Q3 2025
        Performance : Persistent embedding cache
                    : GPU acceleration for NER

    section Q4 2025
        AI Enhancements : LLM-powered tool selection
                        : Semantic memory search
```

---

## Conclusion

This architecture provides:

✅ **Modularity**: Each feature is independent and can be disabled
✅ **Scalability**: Horizontal scaling with shared data layer
✅ **Performance**: Caching and connection pooling optimize latency
✅ **Security**: User isolation and authentication at all layers
✅ **Extensibility**: Easy to add new filters or integrations

---

**Version**: 1.0.0
**Last Updated**: 2025-11-01
**Author**: Claude Code + Parker Dunn
