# Jawafdehi OpenWebUI Config-as-Code

This directory stores Jawafdehi-specific OpenWebUI configuration as version-controlled files.

## Structure

```
configs/
├── README.md                           # This file
├── models/
│   └── jawafdehi-caseworker.json       # Jawafdehi Caseworker model preset
├── knowledge/                          # Knowledge Base doc collections (see knowledge/collections.json)
│   ├── legal-framework/               # Nepali legal documents
│   ├── caseworker-guides/             # Caseworker operational guides
│   └── court-reference/               # Court system reference docs
└── collections.json                    # KB collection metadata
scripts/
└── bootstrap-config.sh                 # Idempotent script to apply configs via OpenWebUI API
```

## How it works

1. Config files are committed to the Jawafdehi `open-webui` fork
2. `bootstrap-config.sh` reads all configs and applies them to the running OpenWebUI instance
3. The bootstrap script is idempotent — it checks if each item already exists before creating it
4. On a fresh deploy, the script creates everything; on restart, it's a no-op

## Model Configuration

The `jawafdehi-caseworker.json` model is based on "Damo's custom Model" from chat.jawafdehi.org.
Update `base_model_id` in the JSON to match the upstream model ID before deploying.

## Adding Knowledge Base docs

Place Markdown documents below `configs/knowledge/` and register them in `collections.json`.
The bootstrap script uploads them via the OpenWebUI Knowledge API.
