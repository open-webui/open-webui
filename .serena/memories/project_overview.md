# Open WebUI Project Overview

## Purpose

Open WebUI is an extensible, feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline. It supports various LLM runners like Ollama and OpenAI-compatible APIs, with built-in inference engine for RAG, making it a powerful AI deployment solution.

## Key Features

- Effortless setup with Docker or Kubernetes
- Ollama/OpenAI API integration
- Granular permissions and user groups
- Responsive design with PWA support
- Full Markdown and LaTeX support
- Voice/video call functionality
- Model builder for custom models
- Native Python function calling
- Local RAG integration
- Web search capabilities
- Image generation integration
- Multi-model conversations
- Role-based access control (RBAC)
- Multilingual support
- Plugin framework with Pipelines

## Tech Stack

- **Backend**: Python 3.11+ with FastAPI
- **Frontend**: SvelteKit with TypeScript
- **Database**: SQLAlchemy with support for PostgreSQL, MySQL, SQLite
- **Vector Database**: Chroma, Milvus, Qdrant, OpenSearch, Elasticsearch, PGVector, Pinecone
- **Deployment**: Docker, Kubernetes
- **Build Tools**: Vite, Node.js
- **Styling**: Tailwind CSS
- **Testing**: Pytest (backend), Vitest (frontend), Cypress (e2e)

## Architecture

The project follows a modern full-stack architecture:

- **Backend**: Python FastAPI application serving REST APIs and WebSocket connections
- **Frontend**: SvelteKit SPA that communicates with the backend APIs
- **Database Layer**: SQLAlchemy ORM with Alembic migrations
- **Vector Storage**: Pluggable vector database support for RAG functionality
- **Authentication**: JWT-based authentication with OAuth support
- **Real-time**: WebSocket support for live features
- **File Storage**: Configurable storage providers (Local, S3, GCS, Azure)
