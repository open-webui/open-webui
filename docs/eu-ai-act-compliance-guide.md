# EU AI Act Compliance Guide for Open WebUI Deployers

Open WebUI is MIT-licensed open-source software. Under Article 25(4) of the EU AI Act, open-source providers are generally exempt from provider obligations. That exemption does not extend to you if you deploy Open WebUI as your organization's AI interface. Once you put it in front of users, you are a **deployer** under Article 3, and several obligations apply.

This guide maps deployer obligations to Open WebUI's existing features: what you already have, what needs configuration, and what requires additional work.

## Check Your Risk Classification First

Determine whether your use case falls under Annex III (high-risk AI systems). If you are using Open WebUI for HR screening, medical triage, legal advice, educational assessment, or any Annex III category, you face substantially heavier obligations. The guidance below covers general-purpose deployment. High-risk deployers should treat this as a starting point, not a finish line.

## Article 50: User Disclosure

This is the single most important obligation for Open WebUI deployments. Article 50 requires deployers to inform users that they are interacting with an AI system. Every chat response a user sees comes from an LLM. They need to know that.

Open WebUI displays model names alongside responses (e.g., "llama3.1:8b" or "gpt-4o"), which partially satisfies this. Model name visibility alone may not be sufficient depending on context. Consider:

- Adding a persistent banner or footer stating that all responses are AI-generated
- Including disclosure in your onboarding flow or terms of use
- Ensuring the model label is visible and not hidden behind a collapsed UI element

If your deployment generates images, audio, or video through tool integrations, Article 50(2) requires marking that content as artificially generated.

## Article 12: Record-Keeping

Deployers must maintain logs of AI system activity. The EU AI Act requires a minimum six-month retention period for deployers.

Open WebUI stores chat history by default, which gives you a baseline. To meet Article 12, verify the following in your deployment:

- **Chat logs** are retained for at least six months (check your database retention policies)
- **Model selection** per conversation is recorded (Open WebUI tracks this)
- **RAG retrieval sources** are logged when knowledge bases are queried
- **Tool calls and function executions** are captured with their inputs and outputs
- **User identity** is associated with conversations (relevant if you have authentication enabled)

If you are running Open WebUI with an external database, ensure your backup and retention policies align with the six-month floor.

## Article 13: Transparency

Deployers must provide users with enough information to interpret AI system output. For Open WebUI, this means documenting:

- Which models are available and their general capabilities
- Which knowledge bases (RAG sources) are connected and what they contain
- What tools and functions are enabled and what they can do
- Any system prompts or behavioral constraints applied to models

This does not mean exposing proprietary system prompts verbatim. It means giving users enough context to understand what shapes the responses they receive. A settings or documentation page listing available models, connected knowledge sources, and active tools satisfies the core requirement.

## Article 26: Deployer Obligations for High-Risk Use

If you deploy Open WebUI for a purpose listed in Annex III, or if you substantially modify the system's intended purpose, Article 26(1)(b) can elevate you to provider-equivalent status. This means you inherit obligations normally reserved for the model provider.

Concrete example: connecting Open WebUI to a medical knowledge base and deploying it as a clinical decision support tool means you are no longer just running a chat interface. You have created a high-risk AI system and must conduct a fundamental rights impact assessment, implement human oversight, and register in the EU database.

The threshold is whether you changed the system's purpose, not whether you changed its code.

## Tooling

For automated compliance checking of conversation logs against Article 12 requirements, see [ai-trace-auditor](https://github.com/BipinRimal314/ai-trace-auditor). It parses conversation exports and flags gaps in record-keeping fields that deployers are expected to maintain.

---

*Reflects the EU AI Act as published in the Official Journal (2024). Article 50 transparency obligations apply from August 2025; full deployer obligations phase through August 2027. This is not legal advice.*
