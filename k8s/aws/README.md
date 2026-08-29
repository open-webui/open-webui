# Artha OpenWebUI AWS Deployment

This deploys OpenWebUI to the existing `artha-ai` namespace and exposes it at
`https://chat.artha.vc`.

## Runtime

- Namespace: `artha-ai`
- Public host: `chat.artha.vc`
- Ollama URL: `http://ollama.artha-ai.svc.cluster.local:11434`
- PR Knowledge MCP URL: `http://pr-knowledge-mcp.artha-ai.svc.cluster.local:8010/mcp`
- Qdrant URL: `http://qdrant-pr-knowledge.artha-ai.svc.cluster.local:6333`

## Database

Use the existing Aurora PostgreSQL cluster through `DATABASE_URL`; do not use DocumentDB for
OpenWebUI because OpenWebUI expects a relational SQL database.

The recommended production layout is:

```text
Aurora host: artha-prod-aps1-aurora.cluster-c3s00kkeqp20.ap-south-1.rds.amazonaws.com
Database: existing production database chosen for shared app metadata
Schema: open_webui
User: open_webui
```

OpenWebUI will create its own tables inside the `open_webui` schema on first boot/migration.

Create `open-webui-secrets` from `secret.example.yaml` with:

- `WEBUI_SECRET_KEY`
- `OAUTH_CLIENT_SECRET`
- `DATABASE_URL`
- `DATABASE_SCHEMA`

The Keycloak redirect URI must be:

```text
https://chat.artha.vc/oauth/oidc/callback
```

## Rollback

LibreChat deploy assets are left intact. To roll back, restore the previous LibreChat Helm
release/ingress for the chat host.
