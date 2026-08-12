# AI Context Index

This directory is durable, selectively loaded context for AI-assisted work on **PlusAI** (`plusai.art`), a product-led Open WebUI fork. It separates the inherited technical baseline from confirmed product direction and planned capabilities; it is not a replacement for inspecting current source.

## Freshness

- Baseline commit: `01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`
- Baseline branch: `main`
- Reviewed: 2026-08-12
- Repository version at review: `0.11.0`
- External reference: [official Open WebUI documentation](https://docs.openwebui.com/)

If `git rev-parse HEAD` differs from the baseline, treat paths and behavior here as navigation hints and verify them in the current checkout. Update this metadata when the bundle is deliberately re-audited, not for every feature change.

## Load by task

| Task                                                    | Read                                                                               |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Any implementation                                      | Root [`AGENTS.md`](../../AGENTS.md), then the relevant row below                   |
| Understand components, requests, storage, or extensions | [`architecture.md`](architecture.md)                                               |
| Set up, run, test, format, migrate, or deploy           | [`development.md`](development.md)                                                 |
| Add product behavior or modify inherited code           | [`customization.md`](customization.md) and [`product-brief.md`](product-brief.md)  |
| Make product or UX decisions                            | [`product-brief.md`](product-brief.md); stop if a required decision is still blank |

Avoid loading every file automatically. Read only the sections needed for the current task, then inspect the corresponding source.

## Keeping this context trustworthy

- Update context in the same change when an architectural boundary, canonical workflow, or command changes.
- Prefer stable symbols and directories over brittle line numbers.
- Label planned behavior as planned; do not describe it as implemented.
- Do not store raw tool output, logs, secrets, personal data, or transient task notes here.
- Keep one source for each fact and link to it rather than duplicating long explanations.

## Official references

- [Development setup](https://docs.openwebui.com/getting-started/advanced-topics/development/)
- [Environment-variable configuration](https://docs.openwebui.com/reference/env-configuration/)
- [Tools and Functions security](https://docs.openwebui.com/features/extensibility/plugin/)
- [Troubleshooting](https://docs.openwebui.com/troubleshooting/)

Repository code and manifests take precedence if upstream documentation describes a different release.
