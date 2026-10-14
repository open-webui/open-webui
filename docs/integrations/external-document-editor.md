# External document editor integration

> Draft design document for the OpenWebUI external document-editor integration.
>
> This document describes the contract under development. It does not claim that
> the end-to-end integration is complete.

## Goal

Allow a generated OpenWebUI file to expose two independent actions:

1. download the file through the authenticated OpenWebUI file route;
2. open the same logical file in a configured external editor, such as
   ONLYOFFICE through an Explorer-compatible handoff.

The OpenWebUI side must remain provider-neutral. It must not contain a specific
homelab hostname, storage path, token, cookie, JWT, or provider-specific secret.

## Proposed contract

```text
OpenWebUI file_id
  -> configured editor handoff URL
  -> authenticated, short-lived handoff
  -> external editor/provider
  -> association callback
  -> persisted logical document identity
```

The `file_id` is the stable OpenWebUI identity. The external provider may store
its own path and version, but OpenWebUI must not guess a file by recency.

## Configuration direction

Names are provisional until the implementation is aligned with the project's
configuration conventions. Expected settings include:

```env
EXTERNAL_DOCUMENT_EDITOR_ENABLED=false
EXTERNAL_DOCUMENT_EDITOR_PROVIDER=
EXTERNAL_DOCUMENT_EDITOR_HANDOFF_URL=
EXTERNAL_DOCUMENT_EDITOR_ASSOCIATION_URL=
EXTERNAL_DOCUMENT_EDITOR_ALLOWED_ORIGINS=
EXTERNAL_DOCUMENT_EDITOR_HANDOFF_TTL_SECONDS=300
```

Secrets must be supplied through the existing secret/configuration mechanism and
must never be rendered into HTML, Markdown, logs, DOM attributes, or client-side
JavaScript.

## Persistence and continuity

The implementation must preserve an explicit association between:

- OpenWebUI `file_id`;
- logical filename and version (`_v1`, `_v2`, `_v3`);
- external-provider document identity;
- latest saved version;
- optional chat association.

A subsequent prompt must be able to reuse the associated file without requiring
the user to upload it again. Explicit user attachments retain priority over
implicit continuity.

## Security requirements

- Require the authenticated OpenWebUI session for file download.
- Use a short-lived, single-purpose handoff or an equivalent authenticated flow.
- Validate origin and destination configuration server-side.
- Do not expose bearer tokens, cookies, JWTs, or internal filesystem paths.
- Do not use `sandbox:/...` or `/mnt/...` as browser-facing URLs.
- Enforce per-user file access before creating or reading an association.
- Fail closed when the association is missing, expired, or unauthorized.

## Versioning rules

- Preserve the logical base name.
- Use deterministic incremental versions such as `document_v1.pptx`.
- Do not create timestamp-prefixed anonymous copies.
- Reopening an associated document must not import a second copy.
- Create `_v2`, `_v3`, and later versions only after an explicit new generation
  or versioning action.

## Draft implementation checklist

- [ ] Define provider-neutral configuration schema.
- [ ] Add the external-editor action to the supported file response/UI path.
- [ ] Add authenticated handoff generation and validation.
- [ ] Persist and retrieve the file-to-editor association.
- [ ] Reuse the association in later prompts and conversations.
- [ ] Add unit tests for authorization, expiry, duplicate prevention, and versioning.
- [ ] Add integration coverage with a mock editor provider.
- [ ] Document migration and rollback behavior.
- [ ] Validate the real OpenWebUI -> Explorer -> ONLYOFFICE flow before marking
      this PR ready for review.

## Non-goals

- Making ONLYOFFICE the only supported external editor.
- Embedding provider credentials in OpenWebUI.
- Replacing OpenWebUI's normal file-download route.
- Selecting an arbitrary "most recent" file when no explicit association exists.
