# Product Brief

> Status: **product direction confirmed; detailed decisions remain incomplete**. Confirmed statements are requirements or roadmap direction. `_TBD_` items and open decisions must not be inferred, fabricated, or silently locked by agents.

Complete the relevant open decisions before work that depends on audience, routing policy, permissions, branding, deployment, or success metrics. Technical maintenance and clearly inherited behavior can proceed using the other context files.

## Product identity

- Product name: PlusAI
- Public domain: [plusai.art](https://plusai.art/)
- One-sentence purpose: An all-in-one AI chatbot that gives users one easy conversation experience across AI models and capabilities.
- Relationship to Open WebUI: Product-led fork and technical foundation. Substantial feature and UX divergence is expected; upstream compatibility is retained selectively when useful.
- Deployment/distribution model: _TBD_
- Brand name and approved assets: _TBD_

## Users and problems

- Primary users: _TBD_
- Secondary users/administrators: _TBD_
- Problems to solve:
  - Users should not need separate chat products to access different AI models and modalities.
  - Selecting or changing the right model should be easy.
  - Users who do not want to choose a model should be able to rely on automatic model selection.
- Current alternatives/workarounds: Switching among separate model-provider, search, image, and video products; manually deciding which model fits each request.
- Accessibility, locale, or device requirements: _TBD_

## Core workflows

These workflows are confirmed at the intent level. Their detailed interaction, permissions, failure handling, and acceptance metrics remain to be specified feature by feature.

1. **Manual model choice and switching:** a user can easily choose a model and switch models as their needs change without leaving the main chat experience.
2. **Automatic model selection:** a user can let the system select an appropriate available model for the request.
3. **Capability use from chat:** a user can access capabilities such as web search, image generation, and eventually video generation as part of the unified product experience.

## Capability roadmap

This table describes product direction, not implementation completion.

| Capability              | Product status       | Baseline observation                                                                 |
| ----------------------- | -------------------- | ------------------------------------------------------------------------------------ |
| Unified AI chat         | Core                 | Inherited chat foundation exists and will be substantially customized                |
| Manual model selection  | Core                 | Inherited model selection/multi-model foundations exist                              |
| Automatic model routing | Required, design TBD | No product routing policy has been defined; arena/random selection is not equivalent |
| Web search              | Planned capability   | Inherited retrieval and web-search foundations exist                                 |
| Image generation        | Planned capability   | Inherited image-generation routes, tools, and integrations exist                     |
| Video generation        | Planned capability   | No reviewed first-class video-generation subsystem exists                            |

## Requirements and priorities

| Priority | Requirement                                                        | Acceptance signal                                                             |
| -------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Must     | Provide one coherent AI chatbot experience across supported models | Users can access supported models without changing products                   |
| Must     | Make manual model selection and switching easy                     | Users can deliberately choose and change the active model                     |
| Must     | Support automatic model selection                                  | Users can delegate model choice and receive a response from an eligible model |
| Planned  | Integrate web search, image generation, and video generation       | Each shipped capability works through the unified product experience          |

## Non-goals

- _TBD_

## Domain language

| Term                      | Product meaning                                                             | Avoid/conflicts with                                                 |
| ------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Manual model selection    | The user deliberately chooses the model used for a request or conversation  | Do not describe automatic routing as a manual choice                 |
| Automatic model selection | The system chooses an eligible model using a product routing policy         | Not equivalent to random arena selection or provider fallback        |
| Capability                | A user-facing ability such as search, image generation, or video generation | Do not assume every capability maps one-to-one to an Open WebUI Tool |

Do not rename inherited concepts such as Tools, Functions, Skills, Models, Chats, Channels, or Knowledge until the product terminology mapping is explicit.

## Data, security, and operations

- Data classification and retention: _TBD_
- Tenant model and isolation expectations: _TBD_
- Roles and permissions: _TBD_
- Required identity providers: _TBD_
- External services and model providers: _TBD_
- Hosting regions/compliance obligations: _TBD_
- Availability, backup, and recovery targets: _TBD_
- Analytics/telemetry policy: _TBD_

## Experience and design

- Brand direction and approved assets: _TBD_
- Key navigation/information architecture: _TBD_
- Model-selection experience: Switching models must feel easy; detailed controls, placement, and persistence behavior are _TBD_.
- Automatic-selection experience: Entry point, status visibility, explanation, and override behavior are _TBD_.
- Responsive/browser targets: _TBD_
- Empty, loading, error, and onboarding expectations: _TBD_
- Internationalization requirements: _TBD_

## Success and release

- Success metrics: _TBD_
- Initial release boundary: _TBD_
- Rollout/migration plan: _TBD_
- Launch acceptance criteria: _TBD_
- Owners/decision-makers: _TBD_

## Open decisions for automatic model selection

These decisions materially affect architecture and must be resolved before implementing the routing policy:

- Routing objective and precedence among quality, task fit, latency, cost, privacy, context length, modality, tool support, and provider availability.
- Whether selection happens per conversation, per user message, or both.
- Eligible model configuration and administrator/user controls.
- Whether users see the chosen model, the reason, estimated cost, or a confirmation step.
- User override, retry, fallback, outage, and no-eligible-model behavior.
- Data sent to a router/classifier and the privacy boundary for that decision.
- Evaluation dataset, success metrics, feedback loop, and safe rollout strategy.

## Open decisions for media capabilities

- Whether image/video generation is invoked explicitly, automatically, or both.
- Supported providers, model selection, parameters, editing, regeneration, and progress/cancellation behavior.
- Storage, retention, download/share permissions, moderation/safety policy, quotas, and cost controls.
- How generated media appears in message history and remains portable across model/provider changes.

## Decision log

Record durable decisions with date, owner, rationale, alternatives, and consequences. Link to implementation artifacts rather than copying transient task discussions.

| Date       | Decision                                                                        | Owner         | Rationale / consequence                                                              |
| ---------- | ------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------ |
| 2026-08-12 | Name the product PlusAI and use `plusai.art` as its public domain               | Product owner | Establishes the canonical product name and domain for future product and design work |
| 2026-08-12 | Build an all-in-one AI chatbot with manual and automatic model selection        | Product owner | Establishes the unified chat and model-choice direction; routing details remain open |
| 2026-08-12 | Include web search, image generation, and video generation in product direction | Product owner | Records capability roadmap without claiming all capabilities are implemented         |
