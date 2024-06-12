# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.4] - 2024-06-12

### Fixed

- **🔒 Mixed Content with HTTPS Issue**: Resolved a problem where mixed content (HTTP and HTTPS) was causing security warnings and blocking resources on HTTPS sites.
- **🔍 Web Search Issue**: Addressed the problem where web search functionality was not working correctly. The 'ENABLE_RAG_LOCAL_WEB_FETCH' option has been reintroduced to restore proper web searching capabilities.
- **💾 RAG Template Not Being Saved**: Fixed an issue where the RAG template was not being saved correctly, ensuring your custom templates are now preserved as expected.

## [0.3.3] - 2024-06-12

### Added

- **🛠️ Native Python Function Calling**: Introducing native Python function calling within Open WebUI. We’ve also included a built-in code editor to seamlessly develop and integrate function code within the 'Tools' workspace. With this, you can significantly enhance your LLM’s capabilities by creating custom RAG pipelines, web search tools, and even agent-like features such as sending Discord messages.
- **🌐 DuckDuckGo Integration**: Added DuckDuckGo as a web search provider, giving you more search options.
- **🌏 Enhanced Translations**: Improved translations for Vietnamese and Chinese languages, making the interface more accessible.

### Fixed

- **🔗 Web Search URL Error Handling**: Fixed the issue where a single URL error would disrupt the data loading process in Web Search mode. Now, such errors will be handled gracefully to ensure uninterrupted data loading.
- **🖥️ Frontend Responsiveness**: Resolved the problem where the frontend would stop responding if the backend encounters an error while downloading a model. Improved error handling to maintain frontend stability.
- **🔧 Dependency Issues in pip**: Fixed issues related to pip installations, ensuring all dependencies are correctly managed to prevent installation errors.

## [0.3.2] - 2024-06-10

### Added

- **🔍 Web Search Query Status**: The web search query will now persist in the results section to aid in easier debugging and tracking of search queries.
- **🌐 New Web Search Provider**: We have added Serply as a new option for web search providers, giving you more choices for your search needs.
- **🌏 Improved Translations**: We've enhanced translations for Chinese and Portuguese.

### Fixed

- **🎤 Audio File Upload Issue**: The bug that prevented audio files from being uploaded in chat input has been fixed, ensuring smooth communication.
- **💬 Message Input Handling**: Improved the handling of message inputs by instantly clearing images and text after sending, along with immediate visual indications when a response message is loading, enhancing user feedback.
- **⚙️ Parameter Registration and Validation**: Fixed the issue where parameters were not registering in certain cases and addressed the problem where users were unable to save due to invalid input errors.

## [0.3.1] - 2024-06-09

### Fixed

- **💬 Chat Functionality**: Resolved the issue where chat functionality was not working for specific models.

## [0.3.0] - 2024-06-09

### Added

- **📚 Knowledge Support for Models**: Attach documents directly to models from the models workspace, enhancing the information available to each model.
- **🎙️ Hands-Free Voice Call Feature**: Initiate voice calls without needing to use your hands, making interactions more seamless.
- **📹 Video Call Feature**: Enable video calls with supported vision models like Llava and GPT-4o, adding a visual dimension to your communications.
- **🎛️ Enhanced UI for Voice Recording**: Improved user interface for the voice recording feature, making it more intuitive and user-friendly.
- **🌐 External STT Support**: Now support for external Speech-To-Text services, providing more flexibility in choosing your STT provider.
- **⚙️ Unified Settings**: Consolidated settings including document settings under a new admin settings section for easier management.
- **🌑 Dark Mode Splash Screen**: A new splash screen for dark mode, ensuring a consistent and visually appealing experience for dark mode users.
- **📥 Upload Pipeline**: Directly upload pipelines from the admin settings > pipelines section, streamlining the pipeline management process.
- **🌍 Improved Language Support**: Enhanced support for Chinese and Ukrainian languages, better catering to a global user base.

### Fixed

- **🛠️ Playground Issue**: Fixed the playground not functioning properly, ensuring a smoother user experience.
- **🔥 Temperature Parameter Issue**: Corrected the issue where the temperature value '0' was not being passed correctly.
- **📝 Prompt Input Clearing**: Resolved prompt input textarea not being cleared right away, ensuring a clean slate for new inputs.
- **✨ Various UI Styling Issues**: Fixed numerous user interface styling problems for a more cohesive look.
- **👥 Active Users Display**: Fixed active users showing active sessions instead of actual users, now reflecting accurate user activity.
- **🌐 Community Platform Compatibility**: The Community Platform is back online and fully compatible with Open WebUI.

### Changed

- **📝 RAG Implementation**: Updated the RAG (Retrieval-Augmented Generation) implementation to use a system prompt for context, instead of overriding the user's prompt.
- **🔄 Settings Relocation**: Moved Models, Connections, Audio, and Images settings to the admin settings for better organization.
- **✍️ Improved Title Generation**: Enhanced the default prompt for title generation, yielding better results.
- **🔧 Backend Task Management**: Tasks like title generation and search query generation are now managed on the backend side and controlled only by the admin.
- **🔍 Editable Search Query Prompt**: You can now edit the search query generation prompt, offering more control over how queries are generated.
- **📏 Prompt Length Threshold**: Set the prompt length threshold for search query generation from the admin settings, giving more customization options.
- **📣 Settings Consolidation**: Merged the Banners admin setting with the Interface admin setting for a more streamlined settings area.

## [0.2.5] - 2024-06-05

### Added

- **👥 Active Users Indicator**: Now you can see how many people are currently active and what they are running. This helps you gauge when performance might slow down due to a high number of users.
- **🗂️ Create Ollama Modelfile**: The option to create a modelfile for Ollama has been reintroduced in the Settings > Models section, making it easier to manage your models.
- **⚙️ Default Model Setting**: Added an option to set the default model from Settings > Interface. This feature is now easily accessible, especially convenient for mobile users as it was previously hidden.
- **🌐 Enhanced Translations**: We've improved the Chinese translations and added support for Turkmen and Norwegian languages to make the interface more accessible globally.

### Fixed

- **📱 Mobile View Improvements**: The UI now uses dvh (dynamic viewport height) instead of vh (viewport height), providing a better and more responsive experience for mobile users.

## [0.2.4] - 2024-06-03

### Added

- **👤 Improved Account Pending Page**: The account pending page now displays admin details by default to avoid confusion. You can disable this feature in the admin settings if needed.
- **🌐 HTTP Proxy Support**: We have enabled the use of the 'http_proxy' environment variable in OpenAI and Ollama API calls, making it easier to configure network settings.
- **❓ Quick Access to Documentation**: You can now easily access Open WebUI documents via a question mark button located at the bottom right corner of the screen (available on larger screens like PCs).
- **🌍 Enhanced Translation**: Improvements have been made to translations.

### Fixed

- **🔍 SearxNG Web Search**: Fixed the issue where the SearxNG web search functionality was not working properly.

## [0.2.3] - 2024-06-03

### Added

- **📁 Export Chat as JSON**: You can now export individual chats as JSON files from the navbar menu by navigating to 'Download > Export Chat'. This makes sharing specific conversations easier.
- **✏️ Edit Titles with Double Click**: Double-click on titles to rename them quickly and efficiently.
- **🧩 Batch Multiple Embeddings**: Introduced 'RAG_EMBEDDING_OPENAI_BATCH_SIZE' to process multiple embeddings in a batch, enhancing performance for large datasets.
- **🌍 Improved Translations**: Enhanced the translation quality across various languages for a better user experience.

### Fixed

- **🛠️ Modelfile Migration Script**: Fixed an issue where the modelfile migration script would fail if an invalid modelfile was encountered.
- **💬 Zhuyin Input Method on Mac**: Resolved an issue where using the Zhuyin input method in the Web UI on a Mac caused text to send immediately upon pressing the enter key, leading to incorrect input.
- **🔊 Local TTS Voice Selection**: Fixed the issue where the selected local Text-to-Speech (TTS) voice was not being displayed in settings.

## [0.2.2] - 2024-06-02

### Added

- **🌊 Mermaid Rendering Support**: We've included support for Mermaid rendering. This allows you to create beautiful diagrams and flowcharts directly within Open WebUI.
- **🔄 New Environment Variable 'RESET_CONFIG_ON_START'**: Introducing a new environment variable: 'RESET_CONFIG_ON_START'. Set this variable to reset your configuration settings upon starting the application, making it easier to revert to default settings.

### Fixed

- **🔧 Pipelines Filter Issue**: We've addressed an issue with the pipelines where filters were not functioning as expected.

## [0.2.1] - 2024-06-02

### Added

- **🖱️ Single Model Export Button**: Easily export models with just one click using the new single model export button.
- **🖥️ Advanced Parameters Support**: Added support for 'num_thread', 'use_mmap', and 'use_mlock' parameters for Ollama.
- **🌐 Improved Vietnamese Translation**: Enhanced Vietnamese language support for a better user experience for our Vietnamese-speaking community.

### Fixed

- **🔧 OpenAI URL API Save Issue**: Corrected a problem preventing the saving of OpenAI URL API settings.
- **🚫 Display Issue with Disabled Ollama API**: Fixed the display bug causing models to appear in settings when the Ollama API was disabled.

### Changed

- **💡 Versioning Update**: As a reminder from our previous update, version 0.2.y will focus primarily on bug fixes, while major updates will be designated as 0.x from now on for better version tracking.

## [0.2.0] - 2024-06-01

### Added

- **🔧 Pipelines Support**: Open WebUI now includes a plugin framework for enhanced customization and functionality (https://github.com/open-webui/pipelines). Easily add custom logic and integrate Python libraries, from AI agents to home automation APIs.
- **🔗 Function Calling via Pipelines**: Integrate function calling seamlessly through Pipelines.
- **⚖️ User Rate Limiting via Pipelines**: Implement user-specific rate limits to manage API usage efficiently.
- **📊 Usage Monitoring with Langfuse**: Track and analyze usage statistics with Langfuse integration through Pipelines.
- **🕒 Conversation Turn Limits**: Set limits on conversation turns to manage interactions better through Pipelines.
- **🛡️ Toxic Message Filtering**: Automatically filter out toxic messages to maintain a safe environment using Pipelines.
- **🔍 Web Search Support**: Introducing built-in web search capabilities via RAG API, allowing users to search using SearXNG, Google Programmatic Search Engine, Brave Search, serpstack, and serper. Activate it effortlessly by adding necessary variables from Document settings > Web Params.
- **🗂️ Models Workspace**: Create and manage model presets for both Ollama/OpenAI API. Note: The old Modelfiles workspace is deprecated.
- **🛠️ Model Builder Feature**: Build and edit all models with persistent builder mode.
- **🏷️ Model Tagging Support**: Organize models with tagging features in the models workspace.
- **📋 Model Ordering Support**: Effortlessly organize models by dragging and dropping them into the desired positions within the models workspace.
- **📈 OpenAI Generation Stats**: Access detailed generation statistics for OpenAI models.
- **📅 System Prompt Variables**: New variables added: '{{CURRENT_DATE}}' and '{{USER_NAME}}' for dynamic prompts.
- **📢 Global Banner Support**: Manage global banners from admin settings > banners.
- **🗃️ Enhanced Archived Chats Modal**: Search and export archived chats easily.
- **📂 Archive All Button**: Quickly archive all chats from settings > chats.
- **🌐 Improved Translations**: Added and improved translations for French, Croatian, Cebuano, and Vietnamese.

### Fixed

- **🔍 Archived Chats Visibility**: Resolved issue with archived chats not showing in the admin panel.
- **💬 Message Styling**: Fixed styling issues affecting message appearance.
- **🔗 Shared Chat Responses**: Corrected the issue where shared chat response messages were not readonly.
- **🖥️ UI Enhancement**: Fixed the scrollbar overlapping issue with the message box in the user interface.

### Changed

- **💾 User Settings Storage**: User settings are now saved on the backend, ensuring consistency across all devices.
- **📡 Unified API Requests**: The API request for getting models is now unified to '/api/models' for easier usage.
- **🔄 Versioning Update**: Our versioning will now follow the format 0.x for major updates and 0.x.y for patches.
- **📦 Export All Chats (All Users)**: Moved this functionality to the Admin Panel settings for better organization and accessibility.

### Removed

- **🚫 Bundled LiteLLM Support Deprecated**: Migrate your LiteLLM config.yaml to a self-hosted LiteLLM instance. LiteLLM can still be added via OpenAI Connections. Download the LiteLLM config.yaml from admin settings > database > export LiteLLM config.yaml.

## [0.1.125] - 2024-05-19

### Added

- **🔄 Updated UI**: Chat interface revamped with chat bubbles. Easily switch back to the old style via settings > interface > chat bubble UI.
- **📂 Enhanced Sidebar UI**: Model files, documents, prompts, and playground merged into Workspace for streamlined access.
- **🚀 Improved Many Model Interaction**: All responses now displayed simultaneously for a smoother experience.
- **🐍 Python Code Execution**: Execute Python code locally in the browser with libraries like 'requests', 'beautifulsoup4', 'numpy', 'pandas', 'seaborn', 'matplotlib', 'scikit-learn', 'scipy', 'regex'.
- **🧠 Experimental Memory Feature**: Manually input personal information you want LLMs to remember via settings > personalization > memory.
- **💾 Persistent Settings**: Settings now saved as config.json for convenience.
- **🩺 Health Check Endpoint**: Added for Docker deployment.
- **↕️ RTL Support**: Toggle chat direction via settings > interface > chat direction.
- **🖥️ PowerPoint Support**: RAG pipeline now supports PowerPoint documents.
- **🌐 Language Updates**: Ukrainian, Turkish, Arabic, Chinese, Serbian, Vietnamese updated; Punjabi added.

### Changed

- **👤 Shared Chat Update**: Shared chat now includes creator user information.

## [0.1.124] - 2024-05-08

### Added

- **🖼️ Improved Chat Sidebar**: Now conveniently displays time ranges and organizes chats by today, yesterday, and more.
- **📜 Citations in RAG Feature**: Easily track the context fed to the LLM with added citations in the RAG feature.
- **🔒 Auth Disable Option**: Introducing the ability to disable authentication. Set 'WEBUI_AUTH' to False to disable authentication. Note: Only applicable for fresh installations without existing users.
- **📹 Enhanced YouTube RAG Pipeline**: Now supports non-English videos for an enriched experience.
- **🔊 Specify OpenAI TTS Models**: Customize your TTS experience by specifying OpenAI TTS models.
- **🔧 Additional Environment Variables**: Discover more environment variables in our comprehensive documentation at Open WebUI Documentation (https://docs.openwebui.com).
- **🌐 Language Support**: Arabic, Finnish, and Hindi added; Improved support for German, Vietnamese, and Chinese.

### Fixed

- **🛠️ Model Selector Styling**: Addressed styling issues for improved user experience.
- **⚠️ Warning Messages**: Resolved backend warning messages.

### Changed

- **📝 Title Generation**: Limited output to 50 tokens.
- **📦 Helm Charts**: Removed Helm charts, now available in a separate repository (https://github.com/open-webui/helm-charts).

## [0.1.123] - 2024-05-02

### Added

- **🎨 New Landing Page Design**: Refreshed design for a more modern look and optimized use of screen space.
- **📹 Youtube RAG Pipeline**: Introduces dedicated RAG pipeline for Youtube videos, enabling interaction with video transcriptions directly.
- **🔧 Enhanced Admin Panel**: Streamlined user management with options to add users directly or in bulk via CSV import.
- **👥 '@' Model Integration**: Easily switch to specific models during conversations; old collaborative chat feature phased out.
- **🌐 Language Enhancements**: Swedish translation added, plus improvements to German, Spanish, and the addition of Doge translation.

### Fixed

- **🗑️ Delete Chat Shortcut**: Addressed issue where shortcut wasn't functioning.
- **🖼️ Modal Closing Bug**: Resolved unexpected closure of modal when dragging from within.
- **✏️ Edit Button Styling**: Fixed styling inconsistency with edit buttons.
- **🌐 Image Generation Compatibility Issue**: Rectified image generation compatibility issue with third-party APIs.
- **📱 iOS PWA Icon Fix**: Corrected iOS PWA home screen icon shape.
- **🔍 Scroll Gesture Bug**: Adjusted gesture sensitivity to prevent accidental activation when scrolling through code on mobile; now requires scrolling from the leftmost side to open the sidebar.

### Changed

- **🔄 Unlimited Context Length**: Advanced settings now allow unlimited max context length (previously limited to 16000).
- **👑 Super Admin Assignment**: The first signup is automatically assigned a super admin role, unchangeable by other admins.
- **🛡️ Admin User Restrictions**: User action buttons from the admin panel are now disabled for users with admin roles.
- **🔝 Default Model Selector**: Set as default model option now exclusively available on the landing page.

## [0.1.122] - 2024-04-27

### Added

- **🌟 Enhanced RAG Pipeline**: Now with hybrid searching via 'BM25', reranking powered by 'CrossEncoder', and configurable relevance score thresholds.
- **🛢️ External Database Support**: Seamlessly connect to custom SQLite or Postgres databases using the 'DATABASE_URL' environment variable.
- **🌐 Remote ChromaDB Support**: Introducing the capability to connect to remote ChromaDB servers.
- **👨‍💼 Improved Admin Panel**: Admins can now conveniently check users' chat lists and last active status directly from the admin panel.
- **🎨 Splash Screen**: Introducing a loading splash screen for a smoother user experience.
- **🌍 Language Support Expansion**: Added support for Bangla (bn-BD), along with enhancements to Chinese, Spanish, and Ukrainian translations.
- **💻 Improved LaTeX Rendering Performance**: Enjoy faster rendering times for LaTeX equations.
- **🔧 More Environment Variables**: Explore additional environment variables in our documentation (https://docs.openwebui.com), including the 'ENABLE_LITELLM' option to manage memory usage.

### Fixed

- **🔧 Ollama Compatibility**: Resolved errors occurring when Ollama server version isn't an integer, such as SHA builds or RCs.
- **🐛 Various OpenAI API Issues**: Addressed several issues related to the OpenAI API.
- **🛑 Stop Sequence Issue**: Fixed the problem where the stop sequence with a backslash '\' was not functioning.
- **🔤 Font Fallback**: Corrected font fallback issue.

### Changed

- **⌨️ Prompt Input Behavior on Mobile**: Enter key prompt submission disabled on mobile devices for improved user experience.

## [0.1.121] - 2024-04-24

### Fixed

- **🔧 Translation Issues**: Addressed various translation discrepancies.
- **🔒 LiteLLM Security Fix**: Updated LiteLLM version to resolve a security vulnerability.
- **🖥️ HTML Tag Display**: Rectified the issue where the '< br >' tag wasn't displaying correctly.
- **🔗 WebSocket Connection**: Resolved the failure of WebSocket connection under HTTPS security for ComfyUI server.
- **📜 FileReader Optimization**: Implemented FileReader initialization per image in multi-file drag & drop to ensure reusability.
- **🏷️ Tag Display**: Corrected tag display inconsistencies.
- **📦 Archived Chat Styling**: Fixed styling issues in archived chat.
- **🔖 Safari Copy Button Bug**: Addressed the bug where the copy button failed to copy links in Safari.

## [0.1.120] - 2024-04-20

### Added

- **📦 Archive Chat Feature**: Easily archive chats with a new sidebar button, and access archived chats via the profile button > archived chats.
- **🔊 Configurable Text-to-Speech Endpoint**: Customize your Text-to-Speech experience with configurable OpenAI endpoints.
- **🛠️ Improved Error Handling**: Enhanced error message handling for connection failures.
- **⌨️ Enhanced Shortcut**: When editing messages, use ctrl/cmd+enter to save and submit, and esc to close.
- **🌐 Language Support**: Added support for Georgian and enhanced translations for Portuguese and Vietnamese.

### Fixed

- **🔧 Model Selector**: Resolved issue where default model selection was not saving.
- **🔗 Share Link Copy Button**: Fixed bug where the copy button wasn't copying links in Safari.
- **🎨 Light Theme Styling**: Addressed styling issue with the light theme.

## [0.1.119] - 2024-04-16

### Added

- **🌟 Enhanced RAG Embedding Support**: Ollama, and OpenAI models can now be used for RAG embedding model.
- **🔄 Seamless Integration**: Copy 'ollama run <model name>' directly from Ollama page to easily select and pull models.
- **🏷️ Tagging Feature**: Add tags to chats directly via the sidebar chat menu.
- **📱 Mobile Accessibility**: Swipe left and right on mobile to effortlessly open and close the sidebar.
- **🔍 Improved Navigation**: Admin panel now supports pagination for user list.
- **🌍 Additional Language Support**: Added Polish language support.

### Fixed

- **🌍 Language Enhancements**: Vietnamese and Spanish translations have been improved.
- **🔧 Helm Fixes**: Resolved issues with Helm trailing slash and manifest.json.

### Changed

- **🐳 Docker Optimization**: Updated docker image build process to utilize 'uv' for significantly faster builds compared to 'pip3'.

## [0.1.118] - 2024-04-10

### Added

- **🦙 Ollama and CUDA Images**: Added support for ':ollama' and ':cuda' tagged images.
- **👍 Enhanced Response Rating**: Now you can annotate your ratings for better feedback.
- **👤 User Initials Profile Photo**: User initials are now the default profile photo.
- **🔍 Update RAG Embedding Model**: Customize RAG embedding model directly in document settings.
- **🌍 Additional Language Support**: Added Turkish language support.

### Fixed

- **🔒 Share Chat Permission**: Resolved issue with chat sharing permissions.
- **🛠 Modal Close**: Modals can now be closed using the Esc key.

### Changed

- **🎨 Admin Panel Styling**: Refreshed styling for the admin panel.
- **🐳 Docker Image Build**: Updated docker image build process for improved efficiency.

## [0.1.117] - 2024-04-03

### Added

- 🗨️ **Local Chat Sharing**: Share chat links seamlessly between users.
- 🔑 **API Key Generation Support**: Generate secret keys to leverage Open WebUI with OpenAI libraries.
- 📄 **Chat Download as PDF**: Easily download chats in PDF format.
- 📝 **Improved Logging**: Enhancements to logging functionality.
- 📧 **Trusted Email Authentication**: Authenticate using a trusted email header.

### Fixed

- 🌷 **Enhanced Dutch Translation**: Improved translation for Dutch users.
- ⚪ **White Theme Styling**: Resolved styling issue with the white theme.
- 📜 **LaTeX Chat Screen Overflow**: Fixed screen overflow issue with LaTeX rendering.
- 🔒 **Security Patches**: Applied necessary security patches.

## [0.1.116] - 2024-03-31

### Added

- **🔄 Enhanced UI**: Model selector now conveniently located in the navbar, enabling seamless switching between multiple models during conversations.
- **🔍 Improved Model Selector**: Directly pull a model from the selector/Models now display detailed information for better understanding.
- **💬 Webhook Support**: Now compatible with Google Chat and Microsoft Teams.
- **🌐 Localization**: Korean translation (I18n) now available.
- **🌑 Dark Theme**: OLED dark theme introduced for reduced strain during prolonged usage.
- **🏷️ Tag Autocomplete**: Dropdown feature added for effortless chat tagging.

### Fixed

- **🔽 Auto-Scrolling**: Addressed OpenAI auto-scrolling issue.
- **🏷️ Tag Validation**: Implemented tag validation to prevent empty string tags.
- **🚫 Model Whitelisting**: Resolved LiteLLM model whitelisting issue.
- **✅ Spelling**: Corrected various spelling issues for improved readability.

## [0.1.115] - 2024-03-24

### Added

- **🔍 Custom Model Selector**: Easily find and select custom models with the new search filter feature.
- **🛑 Cancel Model Download**: Added the ability to cancel model downloads.
- **🎨 Image Generation ComfyUI**: Image generation now supports ComfyUI.
- **🌟 Updated Light Theme**: Updated the light theme for a fresh look.
- **🌍 Additional Language Support**: Now supporting Bulgarian, Italian, Portuguese, Japanese, and Dutch.

### Fixed

- **🔧 Fixed Broken Experimental GGUF Upload**: Resolved issues with experimental GGUF upload functionality.

### Changed

- **🔄 Vector Storage Reset Button**: Moved the reset vector storage button to document settings.

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
