# ADR 004: SQLAlchemy with Multi-Database Support

> **Status:** Accepted
> **Date:** Foundational decision
> **Deciders:** Open WebUI core team

## Context

Open WebUI needs persistent storage for:
- User accounts and authentication
- Chat history and messages
- Uploaded files metadata
- Configuration and settings
- Knowledge bases and RAG metadata

Deployment scenarios vary widely:
- **Personal use:** Single user, minimal infrastructure (SQLite preferred)
- **Team deployment:** Multiple users, moderate scale (PostgreSQL)
- **Enterprise:** High availability, scaling requirements (PostgreSQL/MySQL cluster)

## Decision

Use **SQLAlchemy 2.0** as the ORM with support for multiple database backends:
- **SQLite** (default): Zero-configuration for personal deployments
- **PostgreSQL**: Recommended for production multi-user deployments
- **MySQL**: Alternative production option

Key design choices:
- SQLAlchemy Core + ORM for flexibility
- Alembic for schema migrations
- Database URL configuration via environment
- JSON fields for flexible schema where appropriate

## Consequences

### Positive
- **Deployment flexibility:** Same codebase works from laptop to enterprise
- **Migration safety:** Alembic tracks schema changes across deployments
- **Query optimization:** SQLAlchemy enables database-specific optimizations
- **Type safety:** ORM models provide IDE support and validation

### Negative
- **Abstraction leakage:** Some queries need database-specific handling
- **JSON field differences:** SQLite JSON1 vs PostgreSQL JSONB have different capabilities
- **Migration complexity:** Must test migrations across all supported databases
- **Connection management:** Pool configuration differs per database

### Neutral
- Learning curve for SQLAlchemy 2.0 async patterns
- Need for database-specific testing in CI

## Implementation

**Database configuration:**

```python
# env.py
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/webui.db")

# Or build from components
DATABASE_URL = f"{DATABASE_TYPE}://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
```

**Engine setup:**

```python
# internal/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Handle stale connections
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Model pattern:**

```python
# models/users.py
from sqlalchemy import Column, String, BigInteger
from open_webui.internal.db import Base, JSONField

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    settings = Column(JSONField, default={})  # Handles SQLite/PostgreSQL differences
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
```

**Migration pattern:**

```python
# migrations/versions/xxx_add_feature.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('new_field', sa.String()))

def downgrade():
    op.drop_column('users', 'new_field')
```

## Alternatives Considered

### Raw SQL
- Maximum performance and control
- No abstraction overhead
- Requires manual migration management
- No database portability
- Rejected due to maintenance burden

### MongoDB
- Schema flexibility for evolving data
- Good for document-oriented data
- Adds significant deployment complexity
- Less suitable for relational queries (user→chats→messages)
- Rejected due to relational nature of data

### Prisma (via Python bindings)
- Modern ORM with great DX
- Limited Python support
- Lock-in to Prisma ecosystem
- Rejected due to ecosystem maturity

### Tortoise ORM
- Python async-native ORM
- Smaller ecosystem than SQLAlchemy
- Less mature migration tooling
- Rejected for SQLAlchemy's maturity

## Testing Strategy

| Database | Test Environment |
|----------|------------------|
| SQLite | Unit tests (fast, in-memory) |
| PostgreSQL | Integration tests (Docker) |
| MySQL | Integration tests (Docker) |

## Related Documents

- `DATABASE_SCHEMA.md` — Field-level schema reference
- `DATA_MODEL.md` — Entity relationships
- `DIRECTIVE_database_migration.md` — How to modify schema
- `ADR_010_query_optimization.md` — N+1 elimination patterns

---

*Last updated: 2026-02-03*
