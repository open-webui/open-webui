# Black Formatting Guide

This document explains how Black formatting errors were identified and fixed in this codebase, providing both human-readable guidance and machine-readable patterns for future reference.

## Overview

The backend codebase uses [Black](https://black.readthedocs.io/) as the Python code formatter. The GitHub Actions workflow `format-backend.yaml` enforces Black formatting by:

1. Running `black` on all Python files in `backend/`
2. Checking for uncommitted changes with `git diff --exit-code`
3. Failing the CI build if any formatting changes are detected

## Identifying Formatting Issues

### In CI/CD

When the "Format Backend" workflow fails, check the logs for the "Check for changes after format" step. The output will show a `git diff` indicating what Black wants to change.

**Example error output:**

```
diff --git a/backend/open_webui/routers/workflow.py b/backend/open_webui/routers/workflow.py
@@ -268,10 +268,14 @@ async def mark_instructions_complete(
-        return InstructionsCompleteResponse(status="success", message="Instructions marked complete")
+        return InstructionsCompleteResponse(
+            status="success", message="Instructions marked complete"
+        )
```

### Locally

Run Black in check mode to see what would change:

```bash
cd backend
npm run format:backend
# or directly:
black backend/ --check --diff
```

## Common Formatting Patterns and Fixes

### 1. Long Function Calls and Return Statements

**Issue:** Function calls or return statements exceeding Black's line length (default 88 characters).

**Pattern:**

```python
# ❌ Too long
return WorkflowStateResponse(next_route=next_for_parent, substep=None, progress_by_section=progress)

# ✅ Fixed
return WorkflowStateResponse(
    next_route=next_for_parent,
    substep=None,
    progress_by_section=progress,
)
```

**Files affected:**

- `backend/open_webui/routers/workflow.py` (lines 268, 273, 197-201, etc.)
- `backend/open_webui/routers/moderation_scenarios.py`
- `backend/open_webui/main.py` (line 1475)

### 2. Long Import Statements

**Issue:** Import statements with multiple items exceeding line length.

**Pattern:**

```python
# ❌ Too long
from open_webui.models.workflow_draft import WorkflowDraft, get_draft, save_draft, delete_draft

# ✅ Fixed
from open_webui.models.workflow_draft import (
    WorkflowDraft,
    get_draft,
    save_draft,
    delete_draft,
)
```

**Files affected:**

- `backend/open_webui/routers/workflow.py` (line 26)

### 3. Long Log Statements

**Issue:** Logging statements with long f-strings exceeding line length.

**Pattern:**

```python
# ❌ Too long
log.debug(f"Using stored current_attempt_number for user {user_id}: {user_row.current_attempt_number}")

# ✅ Fixed
log.debug(
    f"Using stored current_attempt_number for user {user_id}: {user_row.current_attempt_number}"
)
```

**Files affected:**

- `backend/open_webui/routers/workflow.py` (lines 41, 62, 147, 149, 160, 183, etc.)
- `backend/open_webui/models/scenarios.py`

### 4. Long Ternary Assignments

**Issue:** Ternary operators (`x if condition else y`) exceeding line length.

**Pattern:**

```python
# ❌ Too long
next_for_parent = "/assignment-instructions" if is_prolific else "/parent"

# ✅ Fixed
next_for_parent = (
    "/assignment-instructions" if is_prolific else "/parent"
)
```

**Files affected:**

- `backend/open_webui/routers/workflow.py` (line 194)

### 5. Long Field Definitions in Pydantic Models

**Issue:** Field definitions with long comments or default values exceeding line length.

**Pattern:**

```python
# ❌ Too long
instructions_completed_at: Optional[int] = None  # when user completed assignment instructions
current_attempt_number: Optional[int] = None  # set on reset; next moderation/exit_quiz use this attempt

# ✅ Fixed
instructions_completed_at: Optional[int] = (
    None  # when user completed assignment instructions
)
current_attempt_number: Optional[int] = (
    None  # set on reset; next moderation/exit_quiz use this attempt
)
```

**Files affected:**

- `backend/open_webui/models/users.py` (lines 136-141)

### 6. Long SQLAlchemy Column Definitions

**Issue:** Column definitions with long comments exceeding line length.

**Pattern:**

```python
# ❌ Too long
current_attempt_number = Column(Integer, nullable=True)  # set on workflow reset; used for next session

# ✅ Fixed
current_attempt_number = Column(
    Integer, nullable=True
)  # set on workflow reset; used for next session
```

**Files affected:**

- `backend/open_webui/models/users.py` (line 92)
- `backend/open_webui/models/scenarios.py` (line 158)

### 7. Long Function Signatures

**Issue:** Function definitions with many parameters exceeding line length.

**Pattern:**

```python
# ❌ Too long
def get_draft(user_id: str, child_id: str, draft_type: str) -> Optional[WorkflowDraftModel]:

# ✅ Fixed
def get_draft(
    user_id: str, child_id: str, draft_type: str
) -> Optional[WorkflowDraftModel]:
```

**Files affected:**

- `backend/open_webui/models/workflow_draft.py` (lines 34, 48)

### 8. Long List Comprehensions

**Issue:** List comprehensions exceeding line length.

**Pattern:**

```python
# ❌ Too long
existing_indexes = [idx["name"] for idx in inspector.get_indexes("scenario_assignments")]

# ✅ Fixed
existing_indexes = [
    idx["name"] for idx in inspector.get_indexes("scenario_assignments")
]
```

**Files affected:**

- `backend/open_webui/migrations/versions/y11z22a33b44_add_attempt_number_to_scenario_assignments.py` (line 45)

### 9. Long Query Filter Statements

**Issue:** SQLAlchemy query filter calls exceeding line length.

**Pattern:**

```python
# ❌ Too long
query = query.filter(ScenarioAssignment.attempt_number == attempt_number)

# ✅ Fixed
query = query.filter(
    ScenarioAssignment.attempt_number == attempt_number
)
```

**Files affected:**

- `backend/open_webui/models/scenarios.py` (line 727)

### 10. Long Alembic Migration Column Definitions

**Issue:** `sa.Column()` calls in migrations exceeding line length.

**Pattern:**

```python
# ❌ Too long
sa.Column("draft_type", sa.Text(), nullable=False),  # "exit_survey" | "moderation"
sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),

# ✅ Fixed
sa.Column(
    "draft_type", sa.Text(), nullable=False
),  # "exit_survey" | "moderation"
sa.Column(
    "attempt_number", sa.Integer(), nullable=False, server_default="1"
),
```

**Files affected:**

- `backend/open_webui/migrations/versions/w99x00y11z22_add_instructions_and_workflow_draft.py` (line 44)
- `backend/open_webui/migrations/versions/y11z22a33b44_add_attempt_number_to_scenario_assignments.py` (line 37)

### 11. Trailing Whitespace

**Issue:** Trailing whitespace at the end of lines (Black removes it).

**Pattern:**

```python
# ❌ Has trailing whitespace
from open_webui.models.exit_quiz import ExitQuizResponse

with get_db() as db:

# ✅ Fixed (no trailing whitespace)
from open_webui.models.exit_quiz import ExitQuizResponse

with get_db() as db:
```

**Files affected:**

- `backend/open_webui/models/scenarios.py` (line 43)
- `backend/open_webui/models/workflow_draft.py` (line 25)
- `backend/open_webui/routers/exit_quiz.py` (line 63)
- `backend/open_webui/routers/moderation_scenarios.py` (lines 649, 654, 664)

### 12. Trailing Spaces in Docstrings

**Issue:** Trailing spaces at the end of docstring lines.

**Pattern:**

```python
# ❌ Has trailing space
"""Get exit quiz responses.
When attempt_number is provided, filter to that specific attempt.
"""

# ✅ Fixed
"""Get exit quiz responses.
When attempt_number is provided, filter to that specific attempt.
"""
```

**Files affected:**

- `backend/open_webui/models/exit_quiz.py` (line 97)
- `backend/open_webui/models/scenarios.py` (line 35)
- `backend/open_webui/routers/exit_quiz.py` (line 55)

### 13. Long Router Include Statements

**Issue:** `app.include_router()` calls exceeding line length.

**Pattern:**

```python
# ❌ Too long
app.include_router(moderation_scenarios.router, prefix="/api/v1", tags=["moderation_scenarios"])

# ✅ Fixed
app.include_router(
    moderation_scenarios.router, prefix="/api/v1", tags=["moderation_scenarios"]
)
```

**Files affected:**

- `backend/open_webui/main.py` (line 1475)

## Fixing Formatting Issues

### Automated Fix

The easiest way to fix formatting issues is to let Black do it automatically:

```bash
cd backend
npm run format:backend
# or directly:
black backend/
```

Then commit the changes:

```bash
git add backend/
git commit -m "fix: Apply Black formatting"
```

### Manual Fix

If you need to fix issues manually (e.g., for specific files):

1. **Identify the issue** from CI logs or by running `black --check --diff`
2. **Apply the pattern** from the examples above
3. **Verify** by running `black --check` on the file

## Prevention

### Pre-commit Hook (Recommended)

Add a pre-commit hook to automatically format code before commits:

1. Install pre-commit:

   ```bash
   pip install pre-commit
   ```

2. Create `.pre-commit-config.yaml`:

   ```yaml
   repos:
     - repo: https://github.com/psf/black
       rev: 23.12.1
       hooks:
         - id: black
           language_version: python3
           args: [--line-length=88]
   ```

3. Install the hook:
   ```bash
   pre-commit install
   ```

### Editor Integration

Configure your editor to format on save:

- **VS Code**: Install the "Black Formatter" extension and enable format on save
- **PyCharm**: Enable Black as the formatter in Settings → Tools → Black
- **Vim/Neovim**: Use plugins like `vim-black` or `nvim-black`

### CI/CD Check

The existing GitHub Actions workflow (`format-backend.yaml`) will catch formatting issues, but you can also run it locally:

```bash
# Check what would change
black backend/ --check --diff

# Apply changes
black backend/
```

## Machine-Readable Patterns

For automated tools or scripts, here are regex patterns to detect common issues:

### Long Lines (over 88 characters)

```regex
^.{89,}$
```

### Trailing Whitespace

```regex
[ \t]+$
```

### Long Function Calls (heuristic)

```regex
^[^=]+\([^)]{80,}\)
```

### Long Import Statements

```regex
^from .+ import .{80,}$
```

## Summary of Files Fixed

The following files were modified to fix Black formatting issues:

1. `backend/open_webui/routers/workflow.py` - Multiple long lines (returns, logs, assignments)
2. `backend/open_webui/routers/moderation_scenarios.py` - Trailing whitespace
3. `backend/open_webui/routers/exit_quiz.py` - Trailing whitespace, docstring trailing space
4. `backend/open_webui/models/users.py` - Long field definitions
5. `backend/open_webui/models/workflow_draft.py` - Long function signatures, trailing whitespace
6. `backend/open_webui/models/exit_quiz.py` - Docstring trailing space
7. `backend/open_webui/models/scenarios.py` - Long Column definitions, query filters, trailing whitespace, docstring trailing space
8. `backend/open_webui/main.py` - Long router include statement
9. `backend/open_webui/migrations/versions/w99x00y11z22_add_instructions_and_workflow_draft.py` - Long Column definition
10. `backend/open_webui/migrations/versions/y11z22a33b44_add_attempt_number_to_scenario_assignments.py` - Long Column definition, long list comprehension

## References

- [Black Documentation](https://black.readthedocs.io/)
- [Black GitHub Repository](https://github.com/psf/black)
- [Black Configuration Options](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#configuration-via-a-file)

## Last Updated

2026-02-15 - Initial documentation created after fixing all Black formatting issues in the backend codebase.
