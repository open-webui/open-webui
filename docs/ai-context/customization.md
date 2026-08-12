# Product-Led Customization Policy

This fork uses Open WebUI as its technical starting point but is expected to receive substantial product and UX customization. Confirmed product requirements take priority over preserving upstream behavior. Divergence should still be deliberate, cohesive, tested, and documented so useful upstream changes can be adopted selectively.

## Default design choices

- Treat upstream Open WebUI as a foundation, not as a permanent product boundary.
- Extend at existing boundaries before modifying central orchestration when those boundaries support the product cleanly: components, API modules, routers, model/table methods, configuration keys, Tools, Functions, and Skills.
- Keep product-specific modules cohesive and visibly named. Avoid scattering brand or policy conditionals through shared chat, authentication, and persistence code.
- Prefer composition, adapters, feature flags, and additive routes/fields over copying upstream files or replacing whole subsystems.
- Preserve upstream endpoint paths, event names, payload fields, database representations, and environment-variable behavior when they remain useful or are externally consumed. Explicit product requirements may replace them, but only with a documented migration or compatibility decision.
- Reuse the existing access-control and configuration abstractions. Do not create parallel authentication, settings, database-session, file-storage, or provider-client frameworks without an approved architectural reason.
- Keep pure branding/theme assets separate from behavioral changes so upstream conflict resolution stays mechanical.
- Do not reproduce every upstream feature or UI choice automatically. Evaluate inherited behavior against the product brief before investing in compatibility or customization.

## Confirmed product direction

**PlusAI**, publicly identified by `plusai.art`, is an all-in-one AI chatbot centered on one approachable conversation experience across models and capabilities. Users must be able to select and switch models easily, while the system must also support automatic model selection. Web search, image generation, and video generation are part of the intended capability roadmap.

- Manual model selection and automatic selection are complementary modes; automatic routing must not silently remove user control.
- Open WebUI already provides foundations for model selection, web search, and image generation. Inspect and reuse them where they fit, but assess their UX and contracts against the product rather than assuming they are final.
- Video generation is planned product scope, not an implemented first-class subsystem in the reviewed baseline.
- Automatic model selection is a confirmed requirement, but its routing inputs, priorities, fallback behavior, explainability, and controls remain undecided in [`product-brief.md`](product-brief.md). Do not lock those policies incidentally while implementing adjacent work.
- Keep model/provider-specific behavior behind cohesive interfaces so chat UI and stored conversations do not become coupled to one provider or media engine.

## High-conflict areas

Changes in these surfaces require a wider trace and stronger tests because upstream evolves them frequently or they coordinate many subsystems:

- `src/lib/components/chat/Chat.svelte`
- `src/routes/+layout.svelte` and `src/routes/(app)/+layout.svelte`
- `backend/open_webui/main.py`
- `backend/open_webui/utils/middleware.py` and `backend/open_webui/utils/chat.py`
- `backend/open_webui/config.py`, `backend/open_webui/env.py`, and database/session setup
- chat persistence, migrations, authentication/access control, provider adapters, and Socket.IO event handling

When possible, put new logic behind a small helper/module and leave only narrow wiring changes in these files.

## Compatibility checklist

Before changing an inherited interface, identify all consumers and lock the intended compatibility behavior:

- HTTP: paths, methods, authentication, status codes, response envelopes, OpenAI/Ollama compatibility, streaming format, and error bodies.
- Events: Socket.IO rooms, event names, payload keys, sequencing, reconnect behavior, and terminal `done`/error states.
- Chat: temporary versus persisted history, parent/child message trees, regeneration, cancellation, queued prompts, multi-model `message_ids`, and `modelIdx`.
- Persistence: legacy chat JSON plus normalized `chat_message` dual writes, migrations, existing rows, indexes, and sharing/access grants.
- Configuration: environment names, defaults, persistent `ConfigVar` precedence, Admin UI editability, and secrets.
- Extensions: function/tool signatures, injected special arguments, valves/user valves, MCP/OpenAPI schema mapping, and privilege boundaries.

If incompatibility is required, document the old and new contracts, migration/rollout, and why an adapter was insufficient.

## Product feature workflow

1. Read [`product-brief.md`](product-brief.md). If the feature depends on a blank product decision, obtain it rather than inventing it.
2. Locate the current implementation with CodeGraph when available, then inspect its callers, storage, events, and tests.
3. Record whether the feature is additive, replaces inherited behavior, or intentionally diverges from upstream.
4. Implement the narrowest end-to-end slice using existing conventions.
5. Add focused regression coverage and validate every crossed boundary.
6. Update this context only when a durable architecture/workflow fact changed.

## Selective upstream upgrade audit

For each upstream merge, rebase, or selective backport:

1. Read upstream release notes and database migrations between the old and new bases.
2. Inventory product-owned modules and high-conflict files before resolving conflicts.
3. Resolve behavior, not just text: re-trace chat, authentication, configuration, storage, and extension paths affected on either side.
4. Confirm product requirements, feature flags/defaults, and product-specific modules are still wired; do not restore unwanted upstream behavior only because a merge applied cleanly.
5. Run migrations on a backed-up copy of representative data; do not test irreversible migration behavior on the only copy.
6. Run targeted checks plus a production build and smoke-test sign-in, model listing, chat streaming, history reload, files/tools, and admin settings.
7. Update the baseline commit and review date in [`README.md`](README.md) only after the context has been re-audited.
