# Jawafdehi OpenWebUI Config-as-Code

This directory stores Jawafdehi-specific OpenWebUI configuration as version-controlled files.

## Structure

```
configs/
├── README.md                           # This file
├── models/
│   └── jawafdehi-caseworker.json        # Deployed model config (full, not a skeleton)
└── knowledge/
    ├── collections.json                # KB collection metadata
    └── caseworker/                     # Skills (pulled from jawafdehi-meta at deploy)
```

## How it works

1. Config files are committed to the Jawafdehi `open-webui` fork
2. `bootstrap-config.sh` reads all configs and applies them to the running OpenWebUI instance
3. The bootstrap script is idempotent — it checks if each item already exists before creating it
4. On a fresh deploy, the script creates everything; on restart, it's a no-op

## Model Configuration

`jawafdehi-caseworker.json` is a snapshot of the deployed "Jawafdehi Caseworker"
configuration. It includes:

- `base_model_id`: `deepseek-v4-pro`
- System prompt for caseworker assistance
- Full capability set (file upload, web search, code interpreter, terminal, citations)
- MCP tool binding (`server:mcp:jawafdehi`)
- Caseworker skill binding (`jawafdehi-caseworker`)

This is a complete model config — not a skeleton. It can be applied directly
by the bootstrap script with no manual steps needed.

## Adding Knowledge Base docs

Place Markdown documents below `configs/knowledge/` and register them in `collections.json`.
The bootstrap script uploads them via the OpenWebUI Knowledge API.
