# Contributing to CANChat

🚀 **Welcome, Contributors!** 🚀

Your interest in contributing to CANChat is greatly appreciated. This document is here to guide you through the process, ensuring your contributions enhance the project effectively. Let's make CANChat even better, together!

---

## 🗂️ MCP SharePoint Integration — Adding a New Department

CANChat has a department-aware SharePoint RAG integration built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). It is designed so that **onboarding a new department requires zero changes to application code** — it is purely configuration-driven.

### What you need to do (two steps only)

1. **Add the department prefix** to the `SHAREPOINT_DEPARTMENTS` environment variable (comma-separated):

   ```
   SHAREPOINT_DEPARTMENTS=MPO,PMO,FIN
   ```

2. **Set department environment variables** in your `.env` / Azure Key Vault / IaC secret store:

   When `SHP_USE_DELEGATED_ACCESS=true` (production / delegated auth):

   ```
   {DEPT_UPPER}_SHP_SITE_URL=<SharePoint site URL>
   # Optional:
   {DEPT_UPPER}_SHP_ORG_NAME=<Human-readable department name>
   {DEPT_UPPER}_SHP_DOC_LIBRARY=<Default document library path>
   {DEPT_UPPER}_SHP_DEFAULT_SEARCH_FOLDERS=<Comma-separated folder paths>
   ```

   When `SHP_USE_DELEGATED_ACCESS=false` (local dev / application credentials):

   ```
   {DEPT_UPPER}_SHP_ID_APP=<Azure AD client ID>
   {DEPT_UPPER}_SHP_ID_APP_SECRET=<Azure AD client secret>
   {DEPT_UPPER}_SHP_TENANT_ID=<Azure AD tenant ID>
   {DEPT_UPPER}_SHP_SITE_URL=<SharePoint site URL>
   ```

   Global variables shared across all departments (`SHP_USE_DELEGATED_ACCESS`, `SHP_OBO_SCOPE`) are already configured.

That's it. On next startup all departments listed in `SHAREPOINT_DEPARTMENTS` are registered automatically — no new files, no image rebuild required.

### What happens automatically

| What                                         | Where                                                      |
| -------------------------------------------- | ---------------------------------------------------------- |
| Server process started                       | `backend/mcp_backend/management/mcp_manager.py`            |
| CrewAI adapter initialised                   | `backend/mcp_backend/integration/crew_mcp_integration.py`  |
| MCP API endpoint exposes the server          | `backend/mcp_backend/routers/mcp.py`                       |
| Admin UI lists and describes the server      | `src/lib/components/admin/Settings/MCP.svelte`             |
| Permissions UI shows a toggle for the server | `src/lib/components/admin/Users/Groups/Permissions.svelte` |
| Chat tool names/descriptions localised       | `src/lib/utils/mcp-tools.ts`                               |

### Naming convention

| Item                          | Pattern                          | Example                     |
| ----------------------------- | -------------------------------- | --------------------------- |
| MCP server name               | `{dept_lower}_sharepoint_server` | `fin_sharepoint_server`     |
| Env var prefix                | `{DEPT_UPPER}_SHP_`              | `FIN_SHP_`                  |
| Tool names exposed to the LLM | `{dept_lower}_{action}`          | `fin_search_documents_fast` |

---

## 📌 Key Points

### 🦙 Ollama vs. CANChat

It's crucial to distinguish between Ollama and CANChat:

- **CANChat** focuses on providing an intuitive and responsive web interface for chat interactions.
- **Ollama** is the underlying technology that powers these interactions.

If your issue or contribution pertains directly to the core Ollama technology, please direct it to the appropriate [Ollama project repository](https://ollama.com/). CANChat's repository is dedicated to the web interface aspect only.

### 🚨 Reporting Issues

Noticed something off? Have an idea? Check our [Issues tab](https://github.com/open-webui/open-webui/issues) to see if it's already been reported or suggested. If not, feel free to open a new issue. When reporting an issue, please follow our issue templates. These templates are designed to ensure that all necessary details are provided from the start, enabling us to address your concerns more efficiently.

> [!IMPORTANT]
>
> - **Template Compliance:** Please be aware that failure to follow the provided issue template, or not providing the requested information at all, will likely result in your issue being closed without further consideration. This approach is critical for maintaining the manageability and integrity of issue tracking.
> - **Detail is Key:** To ensure your issue is understood and can be effectively addressed, it's imperative to include comprehensive details. Descriptions should be clear, including steps to reproduce, expected outcomes, and actual results. Lack of sufficient detail may hinder our ability to resolve your issue.

### 🧭 Scope of Support

We've noticed an uptick in issues not directly related to CANChat but rather to the environment it's run in, especially Docker setups. While we strive to support Docker deployment, understanding Docker fundamentals is crucial for a smooth experience.

- **Docker Deployment Support**: CANChat supports Docker deployment. Familiarity with Docker is assumed. For Docker basics, please refer to the [official Docker documentation](https://docs.docker.com/get-started/overview/).

- **Advanced Configurations**: Setting up reverse proxies for HTTPS and managing Docker deployments requires foundational knowledge. There are numerous online resources available to learn these skills. Ensuring you have this knowledge will greatly enhance your experience with CANChat and similar projects.

## 💡 Contributing

Looking to contribute? Great! Here's how you can help:

### 🛠 Pull Requests

We welcome pull requests. Before submitting one, please:

1. Open a discussion regarding your ideas [here](https://github.com/open-webui/open-webui/discussions/new/choose).
2. Follow the project's coding standards and include tests for new features.
3. Update documentation as necessary.
4. Write clear, descriptive commit messages.
5. It's essential to complete your pull request in a timely manner. We move fast, and having PRs hang around too long is not feasible. If you can't get it done within a reasonable time frame, we may have to close it to keep the project moving forward.

#### Changelog Entries

Add user-facing changes to `CHANGELOG.md` under `## [Unreleased] - TBD` and to the corresponding unpublished section in `CHANGELOG-FR.md`. Reuse an existing section rather than adding one per PR, and keep both languages in sync.

Leave these entries unpublished when a PR is merged. As part of preparing a production release, the release owner replaces the unpublished heading with the actual version and release date in both files. Keep the English heading in `## [version] - date` format, including `## [Unreleased] - TBD`: the backend parses it when loading release notes.

### 📚 Documentation & Tutorials

Help us make CANChat more accessible by improving documentation, writing tutorials, or creating guides on setting up and optimizing the web UI.

### 🌐 Translations and Internationalization

Help us make CANChat available to a wider audience. In this section, we'll guide you through the process of adding new translations to the project.

We use JSON files to store translations. You can find the existing translation files in the `src/lib/i18n/locales` directory. Each directory corresponds to a specific language, for example, `en-US` for English (US), `fr-FR` for French (France) and so on. You can refer to [ISO 639 Language Codes](http://www.lingoes.net/en/translator/langcode.htm) to find the appropriate code for a specific language.

To add a new language:

- Create a new directory in the `src/lib/i18n/locales` path with the appropriate language code as its name. For instance, if you're adding translations for Spanish (Spain), create a new directory named `es-ES`.
- Copy the American English translation file(s) (from `en-US` directory in `src/lib/i18n/locale`) to this new directory and update the string values in JSON format according to your language. Make sure to preserve the structure of the JSON object.
- Add the language code and its respective title to languages file at `src/lib/i18n/locales/languages.json`.

### 🤔 Questions & Feedback

Got questions or feedback? Join our [Discord community](https://discord.gg/5rJgQTnV4s) or open an issue. We're here to help!

## 🙏 Thank You!

Your contributions, big or small, make a significant impact on CANChat. We're excited to see what you bring to the project!

Together, let's create an even more powerful tool for the community. 🌟
