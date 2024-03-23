# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.114] - 2024-03-20

### Added

- **🔗 Webhook Integration**: Now you can subscribe to new user sign-up events via webhook. Simply navigate to the admin panel > admin settings > webhook URL.
- **🛡️ Enhanced Model Filtering**: Alongside Ollama, OpenAI proxy model whitelisting, we've added model filtering functionality for LiteLLM proxy.
- **🌍 Expanded Language Support**: Spanish, Catalan, and Vietnamese languages are now available, with improvements made to others.

### Fixed

- **🔧 Input Field Spelling**: Resolved issue with spelling mistakes in input fields.
- **🖊️ Light Mode Styling**: Fixed styling issue with light mode in document adding.

### Changed

- **🔄 Language Sorting**: Languages are now sorted alphabetically by their code for improved organization.

## [0.1.113] - 2024-03-18

### Added

- 🌍 **Localization**: You can now change the UI language in Settings > General. We support Ukrainian, German, Farsi (Persian), Traditional and Simplified Chinese and French translations. You can help us to translate the UI into your language! More info in our [CONTRIBUTION.md](https://github.com/open-webui/open-webui/blob/main/docs/CONTRIBUTING.md#-translations-and-internationalization).
- 🎨 **System-wide Theme**: Introducing a new system-wide theme for enhanced visual experience.

### Fixed

- 🌑 **Dark Background on Select Fields**: Improved readability by adding a dark background to select fields, addressing issues on certain browsers/devices.
- **Multiple OPENAI_API_BASE_URLS Issue**: Resolved issue where multiple base URLs caused conflicts when one wasn't functioning.
- **RAG Encoding Issue**: Fixed encoding problem in RAG.
- **npm Audit Fix**: Addressed npm audit findings.
- **Reduced Scroll Threshold**: Improved auto-scroll experience by reducing the scroll threshold from 50px to 5px.

### Changed

- 🔄 **Sidebar UI Update**: Updated sidebar UI to feature a chat menu dropdown, replacing two icons for improved navigation.

## [0.1.112] - 2024-03-15

### Fixed

- 🗨️ Resolved chat malfunction after image generation.
- 🎨 Fixed various RAG issues.
- 🧪 Rectified experimental broken GGUF upload logic.

## [0.1.111] - 2024-03-10

### Added

- 🛡️ **Model Whitelisting**: Admins now have the ability to whitelist models for users with the 'user' role.
- 🔄 **Update All Models**: Added a convenient button to update all models at once.
- 📄 **Toggle PDF OCR**: Users can now toggle PDF OCR option for improved parsing performance.
- 🎨 **DALL-E Integration**: Introduced DALL-E integration for image generation alongside automatic1111.
- 🛠️ **RAG API Refactoring**: Refactored RAG logic and exposed its API, with additional documentation to follow.

### Fixed

- 🔒 **Max Token Settings**: Added max token settings for anthropic/claude-3-sonnet-20240229 (Issue #1094).
- 🔧 **Misalignment Issue**: Corrected misalignment of Edit and Delete Icons when Chat Title is Empty (Issue #1104).
- 🔄 **Context Loss Fix**: Resolved RAG losing context on model response regeneration with Groq models via API key (Issue #1105).
- 📁 **File Handling Bug**: Addressed File Not Found Notification when Dropping a Conversation Element (Issue #1098).
- 🖱️ **Dragged File Styling**: Fixed dragged file layover styling issue.

## [0.1.110] - 2024-03-06

### Added

- **🌐 Multiple OpenAI Servers Support**: Enjoy seamless integration with multiple OpenAI-compatible APIs, now supported natively.

### Fixed

- **🔍 OCR Issue**: Resolved PDF parsing issue caused by OCR malfunction.
- **🚫 RAG Issue**: Fixed the RAG functionality, ensuring it operates smoothly.
- **📄 "Add Docs" Model Button**: Addressed the non-functional behavior of the "Add Docs" model button.

## [0.1.109] - 2024-03-06

### Added

- **🔄 Multiple Ollama Servers Support**: Enjoy enhanced scalability and performance with support for multiple Ollama servers in a single WebUI. Load balancing features are now available, providing improved efficiency (#788, #278).
- **🔧 Support for Claude 3 and Gemini**: Responding to user requests, we've expanded our toolset to include Claude 3 and Gemini, offering a wider range of functionalities within our platform (#1064).
- **🔍 OCR Functionality for PDF Loader**: We've augmented our PDF loader with Optical Character Recognition (OCR) capabilities. Now, extract text from scanned documents and images within PDFs, broadening the scope of content processing (#1050).

### Fixed

- **🛠️ RAG Collection**: Implemented a dynamic mechanism to recreate RAG collections, ensuring users have up-to-date and accurate data (#1031).
- **📝 User Agent Headers**: Fixed issue of RAG web requests being sent with empty user_agent headers, reducing rejections from certain websites. Realistic headers are now utilized for these requests (#1024).
- **⏹️ Playground Cancel Functionality**: Introducing a new "Cancel" option for stopping Ollama generation in the Playground, enhancing user control and usability (#1006).
- **🔤 Typographical Error in 'ASSISTANT' Field**: Corrected a typographical error in the 'ASSISTANT' field within the GGUF model upload template for accuracy and consistency (#1061).

### Changed

- **🔄 Refactored Message Deletion Logic**: Streamlined message deletion process for improved efficiency and user experience, simplifying interactions within the platform (#1004).
- **⚠️ Deprecation of `OLLAMA_API_BASE_URL`**: Deprecated `OLLAMA_API_BASE_URL` environment variable; recommend using `OLLAMA_BASE_URL` instead. Refer to our documentation for further details.

## [0.1.108] - 2024-03-02

### Added

- **🎮 Playground Feature (Beta)**: Explore the full potential of the raw API through an intuitive UI with our new playground feature, accessible to admins. Simply click on the bottom name area of the sidebar to access it. The playground feature offers two modes text completion (notebook) and chat completion. As it's in beta, please report any issues you encounter.
- **🛠️ Direct Database Download for Admins**: Admins can now download the database directly from the WebUI via the admin settings.
- **🎨 Additional RAG Settings**: Customize your RAG process with the ability to edit the TOP K value. Navigate to Documents > Settings > General to make changes.
- **🖥️ UI Improvements**: Tooltips now available in the input area and sidebar handle. More tooltips will be added across other parts of the UI.

### Fixed

- Resolved input autofocus issue on mobile when the sidebar is open, making it easier to use.
- Corrected numbered list display issue in Safari (#963).
- Restricted user ability to delete chats without proper permissions (#993).

### Changed

- **Simplified Ollama Settings**: Ollama settings now don't require the `/api` suffix. You can now utilize the Ollama base URL directly, e.g., `http://localhost:11434`. Also, an `OLLAMA_BASE_URL` environment variable has been added.
- **Database Renaming**: Starting from this release, `ollama.db` will be automatically renamed to `webui.db`.

## [0.1.107] - 2024-03-01

### Added

- **🚀 Makefile and LLM Update Script**: Included Makefile and a script for LLM updates in the repository.

### Fixed

- Corrected issue where links in the settings modal didn't appear clickable (#960).
- Fixed problem with web UI port not taking effect due to incorrect environment variable name in run-compose.sh (#996).
- Enhanced user experience by displaying chat in browser title and enabling automatic scrolling to the bottom (#992).

### Changed

- Upgraded toast library from `svelte-french-toast` to `svelte-sonner` for a more polished UI.
- Enhanced accessibility with the addition of dark mode on the authentication page.

## [0.1.106] - 2024-02-27

### Added

- **🎯 Auto-focus Feature**: The input area now automatically focuses when initiating or opening a chat conversation.

### Fixed

- Corrected typo from "HuggingFace" to "Hugging Face" (Issue #924).
- Resolved bug causing errors in chat completion API calls to OpenAI due to missing "num_ctx" parameter (Issue #927).
- Fixed issues preventing text editing, selection, and cursor retention in the input field (Issue #940).
- Fixed a bug where defining an OpenAI-compatible API server using 'OPENAI_API_BASE_URL' containing 'openai' string resulted in hiding models not containing 'gpt' string from the model menu. (Issue #930)

## [0.1.105] - 2024-02-25

### Added

- **📄 Document Selection**: Now you can select and delete multiple documents at once for easier management.

### Changed

- **🏷️ Document Pre-tagging**: Simply click the "+" button at the top, enter tag names in the popup window, or select from a list of existing tags. Then, upload files with the added tags for streamlined organization.

## [0.1.104] - 2024-02-25

### Added

- **🔄 Check for Updates**: Keep your system current by checking for updates conveniently located in Settings > About.
- **🗑️ Automatic Tag Deletion**: Unused tags on the sidebar will now be deleted automatically with just a click.

### Changed

- **🎨 Modernized Styling**: Enjoy a refreshed look with updated styling for a more contemporary experience.

## [0.1.103] - 2024-02-25

### Added

- **🔗 Built-in LiteLLM Proxy**: Now includes LiteLLM proxy within Open WebUI for enhanced functionality.

  - Easily integrate existing LiteLLM configurations using `-v /path/to/config.yaml:/app/backend/data/litellm/config.yaml` flag.
  - When utilizing Docker container to run Open WebUI, ensure connections to localhost use `host.docker.internal`.

- **🖼️ Image Generation Enhancements**: Introducing Advanced Settings with Image Preview Feature.
  - Customize image generation by setting the number of steps; defaults to A1111 value.

### Fixed

- Resolved issue with RAG scan halting document loading upon encountering unsupported MIME types or exceptions (Issue #866).

### Changed

- Ollama is no longer required to run Open WebUI.
- Access our comprehensive documentation at [Open WebUI Documentation](https://docs.openwebui.com/).

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
