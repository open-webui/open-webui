# Architecture
This diagram illustrates the architecture of OpenWebUI and its integration with GAIA. 

The architecture consists of two main components:

1. **Frontend**: Built with Svelte, providing various interface views:
    - Home View
    - Chat View
    - Authentication View
    - Other custom views

2. **Backend**: A Python-based API with specialized modules:
    - Connections Module: Handles external API communication with GAIA
    - Logging Module: Manages system logs and events
    - Additional modules for extended functionality

The OpenWebUI system communicates internally via HTTP/REST API calls between frontend and backend components. The Connections Module integrates closely with GAIA, which serves as the core foundation providing various endpoints for modules, connections, ASR/TTS (Automatic Speech Recognition/Text-to-Speech), and other essential services. While architecturally distinct, OpenWebUI and GAIA function as a cohesive system with tight integration.

This architecture enables a clean separation of concerns while maintaining efficient communication between user interface components and backend services.


```mermaid
graph TB
    %% OpenWebUI System
    subgraph OpenWebUI["OpenWebUI"]
        %% Frontend Section
        subgraph Frontend["Frontend (Svelte)"]
            subgraph FrontendViews["Views"]
                HomeView[Home View]
                ChatView[Chat View]
                AuthView[Auth View]
                OtherViews[Views ...]
            end
            
            SvelteCore[Svelte Core]
            
            FrontendViews --> SvelteCore
        end
        
        %% Backend Section
        subgraph Backend["Backend (Python API)"]
            subgraph BackendModules["Modules"]
                Connections[Connections Module]
                Logging[Logging Module]
                Modules[Modules ...]
            end
            
            APICore[API Core]
            
            BackendModules --> APICore
        end
        
        %% Internal Communication
        SvelteCore <-->|HTTP/REST API| APICore
    end
    
    %% GAIA System
    subgraph GAIA["GAIA"]
        ModuleEndpoints[Module Endpoints]
        ConnectionEndpoints[Connection Endpoints]
        ASR_TTS[ASR/TTS Endpoints]
        OtherEndpoints[Endpoints ...]
    end
    
    %% Communication between systems
    Connections <-->|External API| GAIA
    
    %% Styling
    classDef frontendNodes fill:#FF9900,stroke:#333,stroke-width:2px
    classDef backendNodes fill:#6699FF,stroke:#333,stroke-width:2px
    classDef coreNodes fill:#BBBBBB,stroke:#333,stroke-width:2px
    classDef groupNodes fill:none,stroke:#666,stroke-dasharray: 5 5
    classDef gaiaNodes fill:#337755,stroke:#333,stroke-width:2px
    
    class HomeView,ChatView,AuthView frontendNodes
    class Connections,Logging backendNodes
    class SvelteCore,APICore coreNodes
    class FrontendViews,BackendModules groupNodes
    class ModuleEndpoints,ConnectionEndpoints,ASR_TTS gaiaNodes
```