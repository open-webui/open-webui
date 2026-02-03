# Directive: Database Migration with Alembic

> **Pattern type:** Database schema change
> **Complexity:** Medium
> **Files touched:** 2-4

---

## Prerequisites

- `ADR_004_sqlalchemy_multi_db.md` — Database architecture
- `DATA_MODEL.md` — Entity relationships
- `DATABASE_SCHEMA.md` — Current schema reference

---

## Structural Pattern

When modifying the database schema, use Alembic migrations to:

1. **Create a migration file** describing the schema change
2. **Implement upgrade()** for applying the change
3. **Implement downgrade()** for reverting the change
4. **Test across supported databases** (SQLite, PostgreSQL, MySQL)

| Component | Location | Purpose |
|-----------|----------|---------|
| Migration file | `backend/open_webui/migrations/versions/{hash}_{name}.py` | Schema change |
| Model update | `backend/open_webui/models/{entity}.py` | ORM definition |
| Alembic config | `backend/open_webui/alembic.ini` | Migration settings |
| Env config | `backend/open_webui/migrations/env.py` | Runtime setup |

**Migration types:**
- **Add table:** `op.create_table()`
- **Add column:** `op.add_column()`
- **Add index:** `op.create_index()`
- **Modify column:** `op.alter_column()`
- **Drop column:** `op.drop_column()`
- **Data migration:** Raw SQL in `op.execute()`

---

## Illustrative Application

The channel table migration (`backend/open_webui/migrations/versions/57c599a3cb57_add_channel_table.py`) demonstrates this pattern:

### Step 1: Create Migration File

```bash
# Generate migration (from backend directory)
cd backend
alembic revision -m "add_feature_table"
```

This creates: `migrations/versions/{hash}_add_feature_table.py`

### Step 2: Implement Migration

```python
# migrations/versions/{hash}_add_feature_table.py
"""add feature table

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2026-02-03 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "abc123def456"
down_revision = "previous_revision_id"
branch_labels = None
depends_on = None


def upgrade():
    # Create new table
    op.create_table(
        "features",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True, default={}),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Add indexes
    op.create_index("ix_features_user_id", "features", ["user_id"])
    op.create_index("ix_features_created_at", "features", ["created_at"])

    # Add foreign key (optional, depending on DB)
    # op.create_foreign_key(
    #     "fk_features_user_id",
    #     "features", "users",
    #     ["user_id"], ["id"]
    # )


def downgrade():
    # Remove in reverse order
    op.drop_index("ix_features_created_at")
    op.drop_index("ix_features_user_id")
    op.drop_table("features")
```

### Step 3: Update SQLAlchemy Model

```python
# backend/open_webui/models/features.py
from sqlalchemy import Column, String, Text, Boolean, BigInteger
from open_webui.internal.db import Base, JSONField
from pydantic import BaseModel
from typing import Optional
import time
import uuid


class Feature(Base):
    __tablename__ = "features"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    data = Column(JSONField, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, default=lambda: int(time.time()))


class FeatureModel(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    data: Optional[dict] = {}
    is_active: bool = True
    created_at: int
    updated_at: int

    class Config:
        from_attributes = True


class Features:
    @staticmethod
    def get_features_by_user(user_id: str, db) -> list[FeatureModel]:
        return [
            FeatureModel.model_validate(f)
            for f in db.query(Feature).filter(Feature.user_id == user_id).all()
        ]

    @staticmethod
    def insert_feature(feature: FeatureModel, db) -> FeatureModel:
        db_feature = Feature(**feature.model_dump())
        db.add(db_feature)
        db.commit()
        db.refresh(db_feature)
        return FeatureModel.model_validate(db_feature)
```

### Step 4: Run Migration

```bash
# Apply migration
cd backend
alembic upgrade head

# Verify
alembic current
```

---

## Transfer Prompt

**When you need to modify the database schema:**

1. **Generate migration file:**
   ```bash
   cd backend
   alembic revision -m "descriptive_name"
   ```

2. **Edit the generated file** with your changes:
   - `upgrade()`: Apply the change
   - `downgrade()`: Revert the change

3. **For adding a table:**
   ```python
   def upgrade():
       op.create_table(
           "table_name",
           sa.Column("id", sa.String(), primary_key=True),
           sa.Column("user_id", sa.String(), nullable=False),
           # ... more columns
           sa.Column("created_at", sa.BigInteger()),
           sa.Column("updated_at", sa.BigInteger()),
       )
       op.create_index("ix_table_user_id", "table_name", ["user_id"])

   def downgrade():
       op.drop_index("ix_table_user_id")
       op.drop_table("table_name")
   ```

4. **For adding a column:**
   ```python
   def upgrade():
       op.add_column("table_name", sa.Column("new_column", sa.String()))

   def downgrade():
       op.drop_column("table_name", "new_column")
   ```

5. **For data migration:**
   ```python
   def upgrade():
       # Add column
       op.add_column("table", sa.Column("new", sa.String()))

       # Migrate data
       connection = op.get_bind()
       connection.execute(
           text("UPDATE table SET new = old_column")
       )

       # Drop old column
       op.drop_column("table", "old_column")
   ```

6. **Update SQLAlchemy model** to match schema

7. **Run migration:**
   ```bash
   alembic upgrade head
   ```

**Important considerations:**
- Always implement both `upgrade()` and `downgrade()`
- Use `BigInteger` for timestamps (Unix epoch)
- Use `JSONField` from `open_webui.internal.db` for JSON columns
- Test on SQLite and PostgreSQL if possible
- Large data migrations should be batched

**Signals that this pattern applies:**
- Adding a new feature that needs persistence
- Changing data structure of existing entity
- Adding indexes for performance
- Normalizing or denormalizing data

---

## Related Documents

- `ADR_004_sqlalchemy_multi_db.md` — Database architecture
- `DATABASE_SCHEMA.md` — Schema reference
- `ADR_010_query_optimization.md` — Index strategies

---

*Last updated: 2026-02-03*
