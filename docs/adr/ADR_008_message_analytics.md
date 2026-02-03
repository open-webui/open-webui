# ADR 008: Message-Level Analytics Architecture

> **Status:** Accepted
> **Date:** 2026-01 (commits: 599cd2e, a4ad348, 679e56c)
> **Deciders:** Open WebUI contributors

## Context

Open WebUI needed visibility into LLM usage patterns:
- Token consumption per user and model
- Model utilization trends over time
- Usage analytics for cost management
- Data for admin dashboards

The existing `chats` table stored all messages in a single JSON field (`chat`), making it impossible to efficiently query:
- Total tokens used by model X
- Messages per user per day
- Average response length

## Decision

Introduce a **separate `chat_messages` table** for analytics while maintaining the existing `chat` JSON structure for backward compatibility.

Key design:
- **Dual-write pattern:** Messages written to both `chat_messages` table AND `Chat.chat` JSON
- **Composite primary key:** `(chat_id, message_id)` for efficient chat-based queries
- **Usage tracking:** Store token counts per message
- **Time-series ready:** Timestamps enable daily/hourly aggregations

## Consequences

### Positive
- **Analytics capability:** Token usage, model utilization queries now possible
- **Backward compatibility:** Existing chat retrieval unchanged
- **Query performance:** Indexed columns enable fast filtering
- **Future flexibility:** Foundation for billing, quotas, detailed reporting

### Negative
- **Data duplication:** Messages stored twice (JSON + table)
- **Write overhead:** Every message requires two writes
- **Migration complexity:** Backfill script needed for existing data
- **Consistency risk:** Dual-write can diverge if one fails

### Neutral
- Additional storage requirements
- Migration needed for existing deployments

## Implementation

**New table schema:**

```python
# models/chat_messages.py
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    chat_id = Column(String, ForeignKey("chats.id"), primary_key=True)
    message_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    role = Column(String)  # user, assistant, system
    content = Column(Text)
    model_id = Column(String)
    usage = Column(JSON)  # {input_tokens, output_tokens, total_tokens}
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
```

**Dual-write pattern:**

```python
# When saving a message:
async def save_message(chat_id: str, message: dict, user_id: str):
    # 1. Update Chat.chat JSON (existing behavior)
    chat = Chats.get_chat_by_id(chat_id)
    chat.chat["history"]["messages"][message["id"]] = message
    Chats.update_chat(chat)

    # 2. Write to chat_messages table (new)
    ChatMessages.insert_message(
        chat_id=chat_id,
        message_id=message["id"],
        user_id=user_id,
        role=message["role"],
        content=message["content"],
        model_id=message.get("model"),
        usage=message.get("usage"),
    )
```

**Analytics API:**

```python
# routers/analytics.py
@router.get("/summary")
async def get_summary(
    start_date: Optional[int] = None,
    end_date: Optional[int] = None,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get aggregate statistics."""
    return {
        "total_messages": ChatMessages.count_messages(db, start_date, end_date),
        "total_tokens": ChatMessages.sum_tokens(db, start_date, end_date),
        "active_users": ChatMessages.count_unique_users(db, start_date, end_date),
    }

@router.get("/models")
async def get_model_analytics(start_date, end_date, user=Depends(get_admin_user)):
    """Get per-model statistics."""
    return ChatMessages.group_by_model(db, start_date, end_date)

@router.get("/daily")
async def get_daily_stats(start_date, end_date, user=Depends(get_admin_user)):
    """Get time-series data."""
    return ChatMessages.group_by_day(db, start_date, end_date)
```

**Migration for existing data:**

```python
# migrations/versions/xxx_backfill_chat_messages.py
def upgrade():
    # Create table
    op.create_table("chat_messages", ...)

    # Backfill from existing chats
    connection = op.get_bind()
    chats = connection.execute(text("SELECT id, user_id, chat FROM chats"))

    for chat in chats:
        messages = json.loads(chat.chat)["history"]["messages"]
        for msg_id, msg in messages.items():
            connection.execute(
                text("""
                    INSERT INTO chat_messages
                    (chat_id, message_id, user_id, role, content, created_at)
                    VALUES (:chat_id, :msg_id, :user_id, :role, :content, :created_at)
                """),
                {...}
            )
```

## Alternatives Considered

### Replace Chat.chat JSON entirely
- Clean architecture, single source of truth
- Requires rewriting all chat retrieval logic
- High risk migration
- Rejected for migration complexity

### Analytics via log aggregation
- Use application logs + ELK/similar
- No application changes needed
- Less precise, harder to query
- Rejected for query capability limitations

### Separate analytics database
- Write analytics to different DB (ClickHouse, TimescaleDB)
- Optimal for time-series queries
- Additional infrastructure complexity
- Rejected for operational simplicity

## Related Documents

- `DATABASE_SCHEMA.md` — chat_messages table schema
- `DATA_MODEL.md` — ChatMessage entity
- `DOMAIN_GLOSSARY.md` — ChatMessage, Usage terms

---

*Last updated: 2026-02-03*
