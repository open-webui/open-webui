name: "Multi-Agent System: Research Agent with Email Draft Sub-Agent"
description: |

## Purpose
Build a Pydantic AI multi-agent system where a primary Research Agent uses Brave Search API and has an Email Draft Agent (using Gmail API) as a tool. This demonstrates agent-as-tool pattern with external API integrations.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance

---

## Goal
Create a production-ready multi-agent system where users can research topics via CLI, and the Research Agent can delegate email drafting tasks to an Email Draft Agent. The system should support multiple LLM providers and handle API authentication securely.

## Why
- **Business value**: Automates research and email drafting workflows
- **Integration**: Demonstrates advanced Pydantic AI multi-agent patterns
- **Problems solved**: Reduces manual work for research-based email communications

## What
A CLI-based application where:
- Users input research queries
- Research Agent searches using Brave API
- Research Agent can invoke Email Draft Agent to create Gmail drafts
- Results stream back to the user in real-time

### Success Criteria
- [ ] Research Agent successfully searches via Brave API
- [ ] Email Agent creates Gmail drafts with proper authentication
- [ ] Research Agent can invoke Email Agent as a tool
- [ ] CLI provides streaming responses with tool visibility
- [ ] All tests pass and code meets quality standards

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://ai.pydantic.dev/agents/
  why: Core agent creation patterns
  
- url: https://ai.pydantic.dev/multi-agent-applications/
  why: Multi-agent system patterns, especially agent-as-tool
  
- url: https://developers.google.com/gmail/api/guides/sending
  why: Gmail API authentication and draft creation
  
- url: https://api-dashboard.search.brave.com/app/documentation
  why: Brave Search API REST endpoints
  
- file: examples/agent/agent.py
  why: Pattern for agent creation, tool registration, dependencies
  
- file: examples/agent/providers.py
  why: Multi-provider LLM configuration pattern
  
- file: examples/cli.py
  why: CLI structure with streaming responses and tool visibility

- url: https://github.com/googleworkspace/python-samples/blob/main/gmail/snippet/send%20mail/create_draft.py
  why: Official Gmail draft creation example
```

### Current Codebase tree
```bash
.
├── examples/
│   ├── agent/
│   │   ├── agent.py
│   │   ├── providers.py
│   │   └── ...
│   └── cli.py
├── PRPs/
│   └── templates/
│       └── prp_base.md
├── INITIAL.md
├── CLAUDE.md
└── requirements.txt
```

### Desired Codebase tree with files to be added
```bash
.
├── agents/
│   ├── __init__.py               # Package init
│   ├── research_agent.py         # Primary agent with Brave Search
│   ├── email_agent.py           # Sub-agent with Gmail capabilities
│   ├── providers.py             # LLM provider configuration
│   └── models.py                # Pydantic models for data validation
├── tools/
│   ├── __init__.py              # Package init
│   ├── brave_search.py          # Brave Search API integration
│   └── gmail_tool.py            # Gmail API integration
├── config/
│   ├── __init__.py              # Package init
│   └── settings.py              # Environment and config management
├── tests/
│   ├── __init__.py              # Package init
│   ├── test_research_agent.py   # Research agent tests
│   ├── test_email_agent.py      # Email agent tests
│   ├── test_brave_search.py     # Brave search tool tests
│   ├── test_gmail_tool.py       # Gmail tool tests
│   └── test_cli.py              # CLI tests
├── cli.py                       # CLI interface
├── .env.example                 # Environment variables template
├── requirements.txt             # Updated dependencies
├── README.md                    # Comprehensive documentation
└── credentials/.gitkeep         # Directory for Gmail credentials
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Pydantic AI requires async throughout - no sync functions in async context
# CRITICAL: Gmail API requires OAuth2 flow on first run - credentials.json needed
# CRITICAL: Brave API has rate limits - 2000 req/month on free tier
# CRITICAL: Agent-as-tool pattern requires passing ctx.usage for token tracking
# CRITICAL: Gmail drafts need base64 encoding with proper MIME formatting
# CRITICAL: Always use absolute imports for cleaner code
# CRITICAL: Store sensitive credentials in .env, never commit them
```

## Implementation Blueprint

### Data models and structure

```python
# models.py - Core data structures
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ResearchQuery(BaseModel):
    query: str = Field(..., description="Research topic to investigate")
    max_results: int = Field(10, ge=1, le=50)
    include_summary: bool = Field(True)

class BraveSearchResult(BaseModel):
    title: str
    url: str
    description: str
    score: float = Field(0.0, ge=0.0, le=1.0)

class EmailDraft(BaseModel):
    to: List[str] = Field(..., min_items=1)
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None

class ResearchEmailRequest(BaseModel):
    research_query: str
    email_context: str = Field(..., description="Context for email generation")
    recipient_email: str
```

### List of tasks to be completed

```yaml
Task 1: Setup Configuration and Environment
CREATE config/settings.py:
  - PATTERN: Use pydantic-settings like examples use os.getenv
  - Load environment variables with defaults
  - Validate required API keys present

CREATE .env.example:
  - Include all required environment variables with descriptions
  - Follow pattern from examples/README.md

Task 2: Implement Brave Search Tool
CREATE tools/brave_search.py:
  - PATTERN: Async functions like examples/agent/tools.py
  - Simple REST client using httpx (already in requirements)
  - Handle rate limits and errors gracefully
  - Return structured BraveSearchResult models

Task 3: Implement Gmail Tool
CREATE tools/gmail_tool.py:
  - PATTERN: Follow OAuth2 flow from Gmail quickstart
  - Store token.json in credentials/ directory
  - Create draft with proper MIME encoding
  - Handle authentication refresh automatically

Task 4: Create Email Draft Agent
CREATE agents/email_agent.py:
  - PATTERN: Follow examples/agent/agent.py structure
  - Use Agent with deps_type pattern
  - Register gmail_tool as @agent.tool
  - Return EmailDraft model

Task 5: Create Research Agent
CREATE agents/research_agent.py:
  - PATTERN: Multi-agent pattern from Pydantic AI docs
  - Register brave_search as tool
  - Register email_agent.run() as tool
  - Use RunContext for dependency injection

Task 6: Implement CLI Interface
CREATE cli.py:
  - PATTERN: Follow examples/cli.py streaming pattern
  - Color-coded output with tool visibility
  - Handle async properly with asyncio.run()
  - Session management for conversation context

Task 7: Add Comprehensive Tests
CREATE tests/:
  - PATTERN: Mirror examples test structure
  - Mock external API calls
  - Test happy path, edge cases, errors
  - Ensure 80%+ coverage

Task 8: Create Documentation
CREATE README.md:
  - PATTERN: Follow examples/README.md structure
  - Include setup, installation, usage
  - API key configuration steps
  - Architecture diagram
```

### Per task pseudocode

```python
# Task 2: Brave Search Tool
async def search_brave(query: str, api_key: str, count: int = 10) -> List[BraveSearchResult]:
    # PATTERN: Use httpx like examples use aiohttp
    async with httpx.AsyncClient() as client:
        headers = {"X-Subscription-Token": api_key}
        params = {"q": query, "count": count}
        
        # GOTCHA: Brave API returns 401 if API key invalid
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
            timeout=30.0  # CRITICAL: Set timeout to avoid hanging
        )
        
        # PATTERN: Structured error handling
        if response.status_code != 200:
            raise BraveAPIError(f"API returned {response.status_code}")
        
        # Parse and validate with Pydantic
        data = response.json()
        return [BraveSearchResult(**result) for result in data.get("web", {}).get("results", [])]

# Task 5: Research Agent with Email Agent as Tool
@research_agent.tool
async def create_email_draft(
    ctx: RunContext[AgentDependencies],
    recipient: str,
    subject: str,
    context: str
) -> str:
    """Create email draft based on research context."""
    # CRITICAL: Pass usage for token tracking
    result = await email_agent.run(
        f"Create an email to {recipient} about: {context}",
        deps=EmailAgentDeps(subject=subject),
        usage=ctx.usage  # PATTERN from multi-agent docs
    )
    
    return f"Draft created with ID: {result.data}"
```

### Integration Points
```yaml
ENVIRONMENT:
  - add to: .env
  - vars: |
      # LLM Configuration
      LLM_PROVIDER=openai
      LLM_API_KEY=sk-...
      LLM_MODEL=gpt-4
      
      # Brave Search
      BRAVE_API_KEY=BSA...
      
      # Gmail (path to credentials.json)
      GMAIL_CREDENTIALS_PATH=./credentials/credentials.json
      
CONFIG:
  - Gmail OAuth: First run opens browser for authorization
  - Token storage: ./credentials/token.json (auto-created)
  
DEPENDENCIES:
  - Update requirements.txt with:
    - google-api-python-client
    - google-auth-httplib2
    - google-auth-oauthlib
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check . --fix              # Auto-fix style issues
mypy .                          # Type checking

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```python
# test_research_agent.py
async def test_research_with_brave():
    """Test research agent searches correctly"""
    agent = create_research_agent()
    result = await agent.run("AI safety research")
    assert result.data
    assert len(result.data) > 0

async def test_research_creates_email():
    """Test research agent can invoke email agent"""
    agent = create_research_agent()
    result = await agent.run(
        "Research AI safety and draft email to john@example.com"
    )
    assert "draft_id" in result.data

# test_email_agent.py  
def test_gmail_authentication(monkeypatch):
    """Test Gmail OAuth flow handling"""
    monkeypatch.setenv("GMAIL_CREDENTIALS_PATH", "test_creds.json")
    tool = GmailTool()
    assert tool.service is not None

async def test_create_draft():
    """Test draft creation with proper encoding"""
    agent = create_email_agent()
    result = await agent.run(
        "Create email to test@example.com about AI research"
    )
    assert result.data.get("draft_id")
```

```bash
# Run tests iteratively until passing:
pytest tests/ -v --cov=agents --cov=tools --cov-report=term-missing

# If failing: Debug specific test, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test CLI interaction
python cli.py

# Expected interaction:
# You: Research latest AI safety developments
# 🤖 Assistant: [Streams research results]
# 🛠 Tools Used:
#   1. brave_search (query='AI safety developments', limit=10)
#
# You: Create an email draft about this to john@example.com  
# 🤖 Assistant: [Creates draft]
# 🛠 Tools Used:
#   1. create_email_draft (recipient='john@example.com', ...)

# Check Gmail drafts folder for created draft
```

## Final Validation Checklist
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No linting errors: `ruff check .`
- [ ] No type errors: `mypy .`
- [ ] Gmail OAuth flow works (browser opens, token saved)
- [ ] Brave Search returns results
- [ ] Research Agent invokes Email Agent successfully
- [ ] CLI streams responses with tool visibility
- [ ] Error cases handled gracefully
- [ ] README includes clear setup instructions
- [ ] .env.example has all required variables

---

## Anti-Patterns to Avoid
- ❌ Don't hardcode API keys - use environment variables
- ❌ Don't use sync functions in async agent context
- ❌ Don't skip OAuth flow setup for Gmail
- ❌ Don't ignore rate limits for APIs
- ❌ Don't forget to pass ctx.usage in multi-agent calls
- ❌ Don't commit credentials.json or token.json files

## Confidence Score: 9/10

High confidence due to:
- Clear examples to follow from the codebase
- Well-documented external APIs
- Established patterns for multi-agent systems
- Comprehensive validation gates

Minor uncertainty on Gmail OAuth first-time setup UX, but documentation provides clear guidance.