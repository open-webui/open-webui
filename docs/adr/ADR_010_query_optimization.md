# ADR 010: Database Query Optimization Standards

> **Status:** Accepted
> **Date:** 2026-01 (commits: aac9812, 68e2578, e686554, ee27fd8, baef422)
> **Deciders:** Open WebUI contributors

## Context

As Open WebUI deployments grew, several database performance issues emerged:
- **N+1 queries:** Fetching related data in loops
- **Redundant lookups:** Same data queried multiple times
- **Missing indexes:** Full table scans for filtered queries
- **Inefficient joins:** Multiple queries where one join would suffice

Performance profiling revealed these patterns across:
- Function filtering and access control checks
- User authentication flows
- Group membership lookups
- Memory and feedback operations

## Decision

Establish **database query optimization standards** and systematically refactor existing code:

1. **Batch fetching:** Replace loops with `IN` clauses
2. **JOINs over lookups:** Single query with JOIN vs multiple queries
3. **Eager loading:** Fetch related data in initial query when needed
4. **Index coverage:** Ensure filtered columns are indexed

## Consequences

### Positive
- **Performance:** Significant reduction in database round-trips
- **Scalability:** Better performance as data grows
- **Consistency:** Established patterns for future development
- **Observability:** Easier to identify slow queries

### Negative
- **Complexity:** Some queries become more complex
- **Memory:** Batch fetching may load more data into memory
- **Refactoring effort:** Systematic review of existing code

### Neutral
- Requires understanding of SQLAlchemy query optimization
- May need database-specific tuning

## Implementation

### Pattern 1: Batch Fetching

**Before (N+1):**
```python
def get_functions_with_access_check(user_id: str, function_ids: list):
    results = []
    for func_id in function_ids:
        func = Functions.get_function_by_id(func_id)  # N queries
        if has_access(user_id, func):
            results.append(func)
    return results
```

**After (batch):**
```python
def get_functions_with_access_check(user_id: str, function_ids: list):
    # Single query with IN clause
    functions = db.query(Function).filter(
        Function.id.in_(function_ids)
    ).all()

    # Filter in memory
    return [f for f in functions if has_access(user_id, f)]
```

### Pattern 2: JOIN Over Multiple Lookups

**Before (double lookup):**
```python
def authenticate_user_by_email(email: str):
    user = Users.get_user_by_email(email)  # Query 1
    if user:
        auth = Auths.get_auth_by_id(user.id)  # Query 2
        return user, auth
```

**After (single JOIN):**
```python
def authenticate_user_by_email(email: str):
    result = db.query(User, Auth).join(
        Auth, User.id == Auth.id
    ).filter(
        User.email == email
    ).first()

    return result  # Single query
```

### Pattern 3: Eliminate Redundant Queries

**Before (query after update):**
```python
def update_memory(memory_id: str, content: str):
    memory = Memories.get_by_id(memory_id)  # Query 1
    memory.content = content
    db.commit()
    return Memories.get_by_id(memory_id)  # Query 2 (redundant)
```

**After (return updated object):**
```python
def update_memory(memory_id: str, content: str):
    memory = Memories.get_by_id(memory_id)
    memory.content = content
    db.commit()
    db.refresh(memory)  # Refresh in place
    return memory  # No second query
```

### Pattern 4: SCIM Group Lookup Optimization

**Before (N+1 in user lookup):**
```python
def group_to_scim(group: Group):
    members = []
    for member in group.members:
        user = Users.get_user_by_id(member.user_id)  # N queries
        members.append({"value": user.id, "display": user.name})
    return {"members": members}
```

**After (eager load):**
```python
def group_to_scim(group: Group):
    # Query with joined load
    group = db.query(Group).options(
        joinedload(Group.members).joinedload(GroupMember.user)
    ).filter(Group.id == group.id).first()

    return {
        "members": [
            {"value": m.user.id, "display": m.user.name}
            for m in group.members
        ]
    }
```

## Index Recommendations

Ensure these columns are indexed:

| Table | Column(s) | Index Type |
|-------|-----------|------------|
| `users` | `email` | Unique |
| `users` | `oauth_sub` | Non-unique |
| `chats` | `user_id` | Non-unique |
| `chats` | `updated_at` | Non-unique |
| `chat_messages` | `model_id` | Non-unique |
| `chat_messages` | `created_at` | Non-unique |
| `group_members` | `(group_id, user_id)` | Unique composite |
| `functions` | `user_id` | Non-unique |

## Code Review Checklist

When reviewing database code:

- [ ] No queries inside loops (N+1)
- [ ] Related data fetched with JOINs or eager loading
- [ ] No redundant queries for same data
- [ ] Filtered columns have appropriate indexes
- [ ] Batch operations use `IN` clauses
- [ ] `EXPLAIN` analyzed for complex queries

## Alternatives Considered

### ORM Query Caching
- Cache query results at ORM level
- Adds complexity, cache invalidation issues
- Rejected for simplicity

### Database Query Caching (Redis)
- Cache frequent queries in Redis
- Additional infrastructure
- Overkill for current scale
- Considered for future if needed

### Database Read Replicas
- Route reads to replicas
- Significant infrastructure change
- Rejected for operational complexity

## Related Documents

- `ADR_004_sqlalchemy_multi_db.md` — Database architecture
- `DATABASE_SCHEMA.md` — Schema and indexes
- `TESTING_STRATEGY.md` — Performance test requirements

---

*Last updated: 2026-02-03*
