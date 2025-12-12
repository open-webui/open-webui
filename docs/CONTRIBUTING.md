# Contributing to Open WebUI

🚀 **Welcome, Contributors!** 🚀

Your interest in contributing to Open WebUI is greatly appreciated. This document is here to guide you through the process, ensuring your contributions enhance the project effectively. Let's make Open WebUI even better, together!

## 📌 Key Points

### 🦙 Ollama vs. Open WebUI

It's crucial to distinguish between Ollama and Open WebUI:

- **Open WebUI** focuses on providing an intuitive and responsive web interface for chat interactions.
- **Ollama** is the underlying technology that powers these interactions.

If your issue or contribution pertains directly to the core Ollama technology, please direct it to the appropriate [Ollama project repository](https://ollama.com/). Open WebUI's repository is dedicated to the web interface aspect only.

### 🚨 Reporting Issues

Noticed something off? Have an idea? Check our [Issues tab](https://github.com/open-webui/open-webui/issues) to see if it's already been reported or suggested. If not, feel free to open a new issue. When reporting an issue, please follow our issue templates. These templates are designed to ensure that all necessary details are provided from the start, enabling us to address your concerns more efficiently.

> [!IMPORTANT]
>
> - **Template Compliance:** Please be aware that failure to follow the provided issue template, or not providing the requested information at all, will likely result in your issue being closed without further consideration. This approach is critical for maintaining the manageability and integrity of issue tracking.
> - **Detail is Key:** To ensure your issue is understood and can be effectively addressed, it's imperative to include comprehensive details. Descriptions should be clear, including steps to reproduce, expected outcomes, and actual results. Lack of sufficient detail may hinder our ability to resolve your issue.

> [!WARNING]
> Reporting vulnerabilities is not wanted through Issues!
> Instead, [use the security reporting functionality](https://github.com/open-webui/open-webui/security) and ensure you comply with the outlined requirements.

### 🧭 Scope of Support

We've noticed an uptick in issues not directly related to Open WebUI but rather to the environment it's run in, especially Docker setups. While we strive to support Docker deployment, understanding Docker fundamentals is crucial for a smooth experience.

- **Docker Deployment Support**: Open WebUI supports Docker deployment. Familiarity with Docker is assumed. For Docker basics, please refer to the [official Docker documentation](https://docs.docker.com/get-started/overview/).

- **Advanced Configurations**: Setting up reverse proxies for HTTPS and managing Docker deployments requires foundational knowledge. There are numerous online resources available to learn these skills. Ensuring you have this knowledge will greatly enhance your experience with Open WebUI and similar projects.

- **Check the documentation and help improve it**: [Our documentation](https://docs.openwebui.com) has ever growing troubleshooting guides and detailed installation tutorials. Please verify if it is of help to your issue and help expand it by submitting issues and PRs on our [Docs Repository](https://github.com/open-webui/docs).

## 💡 Contributing

Looking to contribute? Great! Here's how you can help:

### 🛠 Pull Requests

We welcome pull requests. Before submitting one, please:

1. Open a discussion regarding your ideas [here](https://github.com/open-webui/open-webui/discussions/new/choose).
2. Follow the project's coding standards and include tests for new features.
3. Update documentation as necessary.
4. Write clear, descriptive commit messages.
5. It's essential to complete your pull request in a timely manner. We move fast, and having PRs hang around too long is not feasible. If you can't get it done within a reasonable time frame, we may have to close it to keep the project moving forward.

> [!NOTE]
> The Pull Request Template has various requirements outlined. Go through the PR-checklist one by one and ensure you completed all steps before submitting your PR for review (you can open it as draft otherwise!).

### 📚 Documentation & Tutorials

Help us make Open WebUI more accessible by improving the documentation, writing tutorials, or creating guides on setting up and optimizing the Web UI.

Help expand our documentation by submitting issues and PRs on our [Docs Repository](https://github.com/open-webui/docs).
We welcome tutorials, guides and other documentation improvements!

### 🌐 Translations and Internationalization

Help us make Open WebUI available to a wider audience. In this section, we'll guide you through the process of adding new translations to the project.

We use JSON files to store translations. You can find the existing translation files in the `src/lib/i18n/locales` directory. Each directory corresponds to a specific language, for example, `en-US` for English (US), `fr-FR` for French (France) and so on. You can refer to [ISO 639 Language Codes](http://www.lingoes.net/en/translator/langcode.htm) to find the appropriate code for a specific language.

To add a new language:

- Create a new directory in the `src/lib/i18n/locales` path with the appropriate language code as its name. For instance, if you're adding translations for Spanish (Spain), create a new directory named `es-ES`.
- Copy the American English translation file(s) (from `en-US` directory in `src/lib/i18n/locale`) to this new directory and update the string values in JSON format according to your language. Make sure to preserve the structure of the JSON object.
- Add the language code and its respective title to languages file at `src/lib/i18n/locales/languages.json`.

> [!NOTE]
> When adding new translations, do so in a standalone PR! Feature PRs or PRs fixing a bug should not contain translation updates. Always keep the scope of a PR narrow.

### 🤔 Questions & Feedback

Got questions or feedback? Join our [Discord community](https://discord.gg/5rJgQTnV4s) or open an issue or discussion. We're here to help!

## 🙏 Thank You!

Your contributions, big or small, make a significant impact on Open WebUI. We're excited to see what you bring to the project!

Together, let's create an even more powerful tool for the community. 🌟
