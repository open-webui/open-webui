# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.103] - 2024-02-24

### Added

- **🔗 Built-in LiteLLM Proxy**: Open WebUI now ships with LiteLLM proxy built-in.
  - Mount existing LiteLLM config.yaml using `-v /path/to/config.yaml:/app/backend/data/litellm/config.yaml` flag
- **🖼️ Image Generation Enhancements**: Advanced Settings + Image Preview Feature.
  - Allows setting number of steps for image generation; defaults to A1111 default value.

### Fixed

- Issue with RAG scan that stops loading documents as soon as it reaches a file with unsupported mime type (or any other exceptions). (#866)

### Changed

- Ollama is no longer required to run Open WebUI.
- Our documentation can be found here: [Open WebUI Documentation](https://docs.openwebui.com/)

## [0.1.102] - 2024-02-22

### Added

- **🖼️ Image Generation**: Generate Images using the AUTOMATIC1111/stable-diffusion-webui API. You can set this up in Settings > Images.
- **📝 Change title generation prompt**: Change the prompt used to generate titles for your chats. You can set this up in the Settings > Interface.
- **🤖 Change embedding model**: Change the embedding model used to generate embeddings for your chats in the Dockerfile. Use any sentence transformer model from huggingface.co.
- **📢 CHANGELOG.md/Popup**: This popup will show you the latest changes.

## [0.1.101] - 2024-02-22

### Fixed

- LaTex output formatting issue (#828)

### Changed

- Instead of having the previous 1.0.0-alpha.101, we switched to semantic versioning as a way to respect global conventions.
