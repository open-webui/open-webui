# Vector Database Configuration Guide

## Overview

Open WebUI supports multiple vector databases. The choice depends on your database setup:

- **ChromaDB** (default): Works with SQLite (local development)
- **Pgvector**: Requires PostgreSQL (production/OpenShift)

## Configuration

### Local Development (SQLite)

When using SQLite locally, use **ChromaDB**:

```yaml
# docker-compose.local.yaml
environment:
  - VECTOR_DB=chroma  # Works with SQLite
  # DATABASE_URL not set (defaults to SQLite)
```

**ChromaDB**:
- ✅ Works with SQLite
- ✅ No additional setup required
- ✅ Stores vectors in `{DATA_DIR}/vector_db`
- ✅ Perfect for local development

### Production (PostgreSQL/OpenShift)

When using PostgreSQL, use **Pgvector**:

```yaml
# Kubernetes/OpenShift
environment:
  - VECTOR_DB=pgvector
  - DATABASE_URL=postgresql://user:pass@host:5432/dbname
  - PGVECTOR_DB_URL=postgresql://user:pass@host:5432/dbname  # Optional, defaults to DATABASE_URL
```

**Pgvector**:
- ✅ Requires PostgreSQL with pgvector extension
- ✅ Uses the same database as the main app
- ✅ Better for production (shared database)
- ✅ Requires: `CREATE EXTENSION vector;` in PostgreSQL

## Available Vector Databases

| Vector DB | Works with SQLite? | Works with PostgreSQL? | Use Case |
|-----------|-------------------|----------------------|----------|
| **chroma** | ✅ Yes | ❌ No | Local development |
| **pgvector** | ❌ No | ✅ Yes | Production/OpenShift |
| **qdrant** | ✅ Yes | ✅ Yes | External service |
| **milvus** | ✅ Yes | ✅ Yes | External service |
| **opensearch** | ✅ Yes | ✅ Yes | External service |

## Automatic Detection

The codebase automatically:
- ✅ Uses **ChromaDB** by default (works with SQLite)
- ✅ Validates **Pgvector** requires PostgreSQL
- ✅ Falls back gracefully if configuration is invalid

## Error: "Pgvector requires setting PGVECTOR_DB_URL..."

**Cause**: `VECTOR_DB=pgvector` is set but `DATABASE_URL` is SQLite.

**Solution**: 
- For local development: Set `VECTOR_DB=chroma` (or leave unset)
- For production: Ensure `DATABASE_URL` starts with `postgresql://`

## Docker Compose Files

- `docker-compose.local.yaml`: Uses `VECTOR_DB=chroma` (SQLite)
- `docker-compose.local.m1.yaml`: Uses `VECTOR_DB=chroma` (SQLite)
- Production: Use `VECTOR_DB=pgvector` with PostgreSQL

## Migration Between Vector DBs

**From ChromaDB to Pgvector** (when moving to production):
1. Set `VECTOR_DB=pgvector`
2. Set `DATABASE_URL=postgresql://...`
3. Ensure PostgreSQL has pgvector extension: `CREATE EXTENSION vector;`
4. Re-upload files (vectors are stored separately per vector DB)

**Note**: Vector embeddings are not automatically migrated between vector databases. You'll need to re-process files.
