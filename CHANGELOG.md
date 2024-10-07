# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.31] - 2024-10-06

### Added

- **📚 Knowledge Feature**: Reimagined documents feature, now more performant with a better UI for enhanced organization; includes streamlined API integration for Retrieval-Augmented Generation (RAG). Detailed documentation forthcoming: https://docs.openwebui.com/
- **🌐 New Landing Page**: Freshly designed landing page; toggle between the new UI and the classic chat UI from Settings > Interface for a personalized experience.
- **📁 Full Document Retrieval Mode**: Toggle between full document retrieval or traditional snippets by clicking on the file item. This mode enhances document capabilities and supports comprehensive tasks like summarization by utilizing the entire content instead of RAG.
- **📄 Extracted File Content Display**: View extracted content directly by clicking on the file item, simplifying file analysis.
- **🎨 Artifacts Feature**: Render web content and SVGs directly in the interface, supporting quick iterations and live changes.
- **🖊️ Editable Code Blocks**: Supercharged code blocks now allow live editing directly in the LLM response, with live reloads supported by artifacts.
- **🔧 Code Block Enhancements**: Introduced a floating copy button in code blocks to facilitate easier code copying without scrolling.
- **🔍 SVG Pan/Zoom**: Enhanced interaction with SVG images, including Mermaid diagrams, via new pan and zoom capabilities.
- **🔍 Text Select Quick Actions**: New floating buttons appear when text is highlighted in LLM responses, offering deeper interactions like "Ask a Question" or "Explain".
- **🗃️ Database Pool Configuration**: Enhanced database handling to support scalable user growth.
- **🔊 Experimental Audio Compression**: Compress audio files to navigate around the 25MB limit for OpenAI's speech-to-text processing.
- **🔍 Query Embedding**: Adjusted embedding behavior to enhance system performance by not repeating query embedding.
- **💾 Lazy Load Optimizations**: Implemented lazy loading of large dependencies to minimize initial memory usage, boosting performance.
- **🍏 Apple Touch Icon Support**: Optimizes the display of icons for web bookmarks on Apple mobile devices.
- **🔽 Expandable Content Markdown Support**: Introducing 'details', 'summary' tag support for creating expandable content sections in markdown, facilitating cleaner, organized documentation and interactive content display.

### Fixed

- **🔘 Action Button Issue**: Resolved a bug where action buttons were not functioning, enhancing UI reliability.
- **🔄 Multi-Model Chat Loop**: Fixed an infinite loop issue in multi-model chat environments, ensuring smoother chat operations.
- **📄 Chat PDF/TXT Export Issue**: Resolved problems with exporting chat logs to PDF and TXT formats.
- **🔊 Call to Text-to-Speech Issues**: Rectified problems with text-to-speech functions to improve audio interactions.

### Changed

- **⚙️ Endpoint Renaming**: Renamed 'rag' endpoints to 'retrieval' for clearer function description.
- **🎨 Styling and Interface Updates**: Multiple refinements across the platform to enhance visual appeal and user interaction.

### Removed

- **🗑️ Deprecated 'DOCS_DIR'**: Removed the outdated 'docs_dir' variable in favor of more direct file management solutions, with direct file directory syncing and API uploads for a more integrated experience.

## [0.3.30] - 2024-09-26

### Fixed

- **🍞 Update Available Toast Dismissal**: Enhanced user experience by ensuring that once the update available notification is dismissed, it won't reappear for 24 hours.
- **📋 Ollama /embed Form Data**: Adjusted the integration inaccuracies in the /embed form data to ensure it perfectly matches with Ollama's specifications.
- **🔧 O1 Max Completion Tokens Issue**: Resolved compatibility issues with OpenAI's o1 models max_completion_tokens param to ensure smooth operation.
- **🔄 Pip Install Database Issue**: Fixed a critical issue where database changes during pip installations were reverting and not saving chat logs, now ensuring data persistence and reliability in chat operations.
- **🏷️ Chat Rename Tab Update**: Fixed the functionality to change the web browser's tab title simultaneously when a chat is renamed, keeping tab titles consistent.

## [0.3.29] - 2023-09-25

### Fixed

- **🔧 KaTeX Rendering Improvement**: Resolved specific corner cases in KaTeX rendering to enhance the display of complex mathematical notation.
- **📞 'Call' URL Parameter Fix**: Corrected functionality for 'call' URL search parameter ensuring reliable activation of voice calls through URL triggers.
- **🔄 Configuration Reset Fix**: Fixed the RESET_CONFIG_ON_START to ensure settings revert to default correctly upon each startup, improving reliability in configuration management.
- **🌍 Filter Outlet Hook Fix**: Addressed issues in the filter outlet hook, ensuring all filter functions operate as intended.

## [0.3.28] - 2024-09-24

### Fixed

- **🔍 Web Search Functionality**: Corrected an issue where the web search option was not functioning properly.

## [0.3.27] - 2024-09-24

### Fixed

- **🔄 Periodic Cleanup Error Resolved**: Fixed a critical RuntimeError related to the 'periodic_usage_pool_cleanup' coroutine, ensuring smooth and efficient performance post-pip install, correcting a persisting issue from version 0.3.26.
- **📊 Enhanced LaTeX Rendering**: Improved rendering for LaTeX content, enhancing clarity and visual presentation in documents and mathematical models.

## [0.3.26] - 2024-09-24

### Fixed

- **🔄 Event Loop Error Resolution**: Addressed a critical error where a missing running event loop caused 'periodic_usage_pool_cleanup' to fail with pip installs. This fix ensures smoother and more reliable updates and installations, enhancing overall system stability.

## [0.3.25] - 2024-09-24

### Fixed

- **🖼️ Image Generation Functionality**: Resolved an issue where image generation was not functioning, restoring full capability for visual content creation.
- **⚖️ Rate Response Corrections**: Addressed a problem where rate responses were not working, ensuring reliable feedback mechanisms are operational.

## [0.3.24] - 2024-09-24

### Added

- **🚀 Rendering Optimization**: Significantly improved message rendering performance, enhancing user experience and webui responsiveness.
- **💖 Favorite Response Feature in Chat Overview**: Users can now mark responses as favorite directly from the chat overview, enhancing ease of retrieval and organization of preferred responses.
- **💬 Create Message Pairs with Shortcut**: Implemented creation of new message pairs using Cmd/Ctrl+Shift+Enter, making conversation editing faster and more intuitive.
- **🌍 Expanded User Prompt Variables**: Added weekday, timezone, and language information variables to user prompts to match system prompt variables.
- **🎵 Enhanced Audio Support**: Now includes support for 'audio/x-m4a' files, broadening compatibility with audio content within the platform.
- **🔏 Model URL Search Parameter**: Added an ability to select a model directly via URL parameters, streamlining navigation and model access.
- **📄 Enhanced PDF Citations**: PDF citations now open at the associated page, streamlining reference checks and document handling.
- **🔧Use of Redis in Sockets**: Enhanced socket implementation to fully support Redis, enabling effective stateless instances suitable for scalable load balancing.
- **🌍 Stream Individual Model Responses**: Allows specific models to have individualized streaming settings, enhancing performance and customization.
- **🕒 Display Model Hash and Last Modified Timestamp for Ollama Models**: Provides critical model details directly in the Models workspace for enhanced tracking.
- **❗ Update Info Notification for Admins**: Ensures administrators receive immediate updates upon login, keeping them informed of the latest changes and system statuses.

### Fixed

- **🗑️ Temporary File Handling On Windows**: Fixed an issue causing errors when accessing a temporary file being used by another process, Tools & Functions should now work as intended.
- **🔓 Authentication Toggle Issue**: Resolved the malfunction where setting 'WEBUI_AUTH=False' did not appropriately disable authentication, ensuring that user experience and system security settings function as configured.
- **🔧 Save As Copy Issue for Many Model Chats**: Resolved an error preventing users from save messages as copies in many model chats.
- **🔒 Sidebar Closure on Mobile**: Resolved an issue where the mobile sidebar remained open after menu engagement, improving user interface responsivity and comfort.
- **🛡️ Tooltip XSS Vulnerability**: Resolved a cross-site scripting (XSS) issue within tooltips, ensuring enhanced security and data integrity during user interactions.

### Changed

- **↩️ Deprecated Interface Stream Response Settings**: Moved to advanced parameters to streamline interface settings and enhance user clarity.
- **⚙️ Renamed 'speedRate' to 'playbackRate'**: Standardizes terminology, improving usability and understanding in media settings.

## [0.3.23] - 2024-09-21

### Added

- **🚀 WebSocket Redis Support**: Enhanced load balancing capabilities for multiple instance setups, promoting better performance and reliability in WebUI.
- **🔧 Adjustable Chat Controls**: Introduced width-adjustable chat controls, enabling a personalized and more comfortable user interface.
- **🌎 i18n Updates**: Improved and updated the Chinese translations.

### Fixed

- **🌐 Task Model Unloading Issue**: Modified task handling to use the Ollama /api/chat endpoint instead of OpenAI compatible endpoint, ensuring models stay loaded and ready with custom parameters, thus minimizing delays in task execution.
- **📝 Title Generation Fix for OpenAI Compatible APIs**: Resolved an issue preventing the generation of titles, enhancing consistency and reliability when using multiple API providers.
- **🗃️ RAG Duplicate Collection Issue**: Fixed a bug causing repeated processing of the same uploaded file. Now utilizes indexed files to prevent unnecessary duplications, optimizing resource usage.
- **🖼️ Image Generation Enhancement**: Refactored OpenAI image generation endpoint to be asynchronous, preventing the WebUI from becoming unresponsive during processing, thus enhancing user experience.
- **🔓 Downgrade Authlib**: Reverted Authlib to version 1.3.1 to address and resolve issues concerning OAuth functionality.

### Changed

- **🔍 Improved Message Interaction**: Enhanced the message node interface to allow for easier focus redirection with a simple click, streamlining user interaction.
- **✨ Styling Refactor**: Updated WebUI styling for a cleaner, more modern look, enhancing user experience across the platform.

## [0.3.22] - 2024-09-19

### Added

- **⭐ Chat Overview**: Introducing a node-based interactive messages diagram for improved visualization of conversation flows.
- **🔗 Multiple Vector DB Support**: Now supports multiple vector databases, including the newly added Milvus support. Community contributions for additional database support are highly encouraged!
- **📡 Experimental Non-Stream Chat Completion**: Experimental feature allowing the use of OpenAI o1 models, which do not support streaming, ensuring more versatile model deployment.
- **🔍 Experimental Colbert-AI Reranker Integration**: Added support for "jinaai/jina-colbert-v2" as a reranker, enhancing search relevance and accuracy. Note: it may not function at all on low-spec computers.
- **🕸️ ENABLE_WEBSOCKET_SUPPORT**: Added environment variable for instances to ignore websocket upgrades, stabilizing connections on platforms with websocket issues.
- **🔊 Azure Speech Service Integration**: Added support for Azure Speech services for Text-to-Speech (TTS).
- **🎚️ Customizable Playback Speed**: Playback speed control is now available in Call mode settings, allowing users to adjust audio playback speed to their preferences.
- **🧠 Enhanced Error Messaging**: System now displays helpful error messages directly to users during chat completion issues.
- **📂 Save Model as Transparent PNG**: Model profile images are now saved as PNGs, supporting transparency and improving visual integration.
- **📱 iPhone Compatibility Adjustments**: Added padding to accommodate the iPhone navigation bar, improving UI display on these devices.
- **🔗 Secure Response Headers**: Implemented security response headers, bolstering web application security.
- **🔧 Enhanced AUTOMATIC1111 Settings**: Users can now configure 'CFG Scale', 'Sampler', and 'Scheduler' parameters directly in the admin settings, enhancing workflow flexibility without source code modifications.
- **🌍 i18n Updates**: Enhanced translations for Chinese, Ukrainian, Russian, and French, fostering a better localized experience.

### Fixed

- **🛠️ Chat Message Deletion**: Resolved issues with chat message deletion, ensuring a smoother user interaction and system stability.
- **🔢 Ordered List Numbering**: Fixed the incorrect ordering in lists.

### Changed

- **🎨 Transparent Icon Handling**: Allowed model icons to be displayed on transparent backgrounds, improving UI aesthetics.
- **📝 Improved RAG Template**: Enhanced Retrieval-Augmented Generation template, optimizing context handling and error checking for more precise operation.

## [0.3.21] - 2024-09-08

### Added

- **📊 Document Count Display**: Now displays the total number of documents directly within the dashboard.
- **🚀 Ollama Embed API Endpoint**: Enabled /api/embed endpoint proxy support.

### Fixed

- **🐳 Docker Launch Issue**: Resolved the problem preventing Open-WebUI from launching correctly when using Docker.

### Changed

- **🔍 Enhanced Search Prompts**: Improved the search query generation prompts for better accuracy and user interaction, enhancing the overall search experience.

## [0.3.20] - 2024-09-07

### Added

- **🌐 Translation Update**: Updated Catalan translations to improve user experience for Catalan speakers.

### Fixed

- **📄 PDF Download**: Resolved a configuration issue with fonts directory, ensuring PDFs are now downloaded with the correct formatting.
- **🛠️ Installation of Tools & Functions Requirements**: Fixed a bug where necessary requirements for tools and functions were not properly installing.
- **🔗 Inline Image Link Rendering**: Enabled rendering of images directly from links in chat.
- **📞 Post-Call User Interface Cleanup**: Adjusted UI behavior to automatically close chat controls after a voice call ends, reducing screen clutter.
- **🎙️ Microphone Deactivation Post-Call**: Addressed an issue where the microphone remained active after calls.
- **✍️ Markdown Spacing Correction**: Corrected spacing in Markdown rendering, ensuring text appears neatly and as expected.
- **🔄 Message Re-rendering**: Fixed an issue causing all response messages to re-render with each new message, now improving chat performance.

### Changed

- **🌐 Refined Web Search Integration**: Deprecated the Search Query Generation Prompt threshold; introduced a toggle button for "Enable Web Search Query Generation" allowing users to opt-in to using web search more judiciously.
- **📝 Default Prompt Templates Update**: Emptied environment variable templates for search and title generation now default to the Open WebUI default prompt templates, simplifying configuration efforts.

## [0.3.19] - 2024-09-05

### Added

- **🌐 Translation Update**: Improved Chinese translations.

### Fixed

- **📂 DATA_DIR Overriding**: Fixed an issue to avoid overriding DATA_DIR, preventing errors when directories are set identically, ensuring smoother operation and data management.
- **🛠️ Frontmatter Extraction**: Fixed the extraction process for frontmatter in tools and functions.

### Changed

- **🎨 UI Styling**: Refined the user interface styling for enhanced visual coherence and user experience.

## [0.3.18] - 2024-09-04

### Added

- **🛠️ Direct Database Execution for Tools & Functions**: Enhanced the execution of Python files for tools and functions, now directly loading from the database for a more streamlined backend process.

### Fixed

- **🔄 Automatic Rewrite of Import Statements in Tools & Functions**: Tool and function scripts that import 'utils', 'apps', 'main', 'config' will now automatically rename these with 'open_webui.', ensuring compatibility and consistency across different modules.
- **🎨 Styling Adjustments**: Minor fixes in the visual styling to improve user experience and interface consistency.

## [0.3.17] - 2024-09-04

### Added

- **🔄 Import/Export Configuration**: Users can now import and export webui configurations from admin settings > Database, simplifying setup replication across systems.
- **🌍 Web Search via URL Parameter**: Added support for activating web search directly through URL by setting 'web-search=true'.
- **🌐 SearchApi Integration**: Added support for SearchApi as an alternative web search provider, enhancing search capabilities within the platform.
- **🔍 Literal Type Support in Tools**: Tools now support the Literal type.
- **🌍 Updated Translations**: Improved translations for Chinese, Ukrainian, and Catalan.

### Fixed

- **🔧 Pip Install Issue**: Resolved the issue where pip install failed due to missing 'alembic.ini', ensuring smoother installation processes.
- **🌃 Automatic Theme Update**: Fixed an issue where the color theme did not update dynamically with system changes.
- **🛠️ User Agent in ComfyUI**: Added default headers in ComfyUI to fix access issues, improving reliability in network communications.
- **🔄 Missing Chat Completion Response Headers**: Ensured proper return of proxied response headers during chat completion, improving API reliability.
- **🔗 Websocket Connection Prioritization**: Modified socket.io configuration to prefer websockets and more reliably fallback to polling, enhancing connection stability.
- **🎭 Accessibility Enhancements**: Added missing ARIA labels for buttons, improving accessibility for visually impaired users.
- **⚖️ Advanced Parameter**: Fixed an issue ensuring that advanced parameters are correctly applied in all scenarios, ensuring consistent behavior of user-defined settings.

### Changed

- **🔁 Namespace Reorganization**: Reorganized all Python files under the 'open_webui' namespace to streamline the project structure and improve maintainability. Tools and functions importing from 'utils' should now use 'open_webui.utils'.
- **🚧 Dependency Updates**: Updated several backend dependencies like 'aiohttp', 'authlib', 'duckduckgo-search', 'flask-cors', and 'langchain' to their latest versions, enhancing performance and security.

## [0.3.16] - 2024-08-27

### Added

- **🚀 Config DB Migration**: Migrated configuration handling from config.json to the database, enabling high-availability setups and load balancing across multiple Open WebUI instances.
- **🔗 Call Mode Activation via URL**: Added a 'call=true' URL search parameter enabling direct shortcuts to activate call mode, enhancing user interaction on mobile devices.
- **✨ TTS Content Control**: Added functionality to control how message content is segmented for Text-to-Speech (TTS) generation requests, allowing for more flexible speech output options.
- **😄 Show Knowledge Search Status**: Enhanced model usage transparency by displaying status when working with knowledge-augmented models, helping users understand the system's state during queries.
- **👆 Click-to-Copy for Codespan**: Enhanced interactive experience in the WebUI by allowing users to click to copy content from code spans directly.
- **🚫 API User Blocking via Model Filter**: Introduced the ability to block API users based on customized model filters, enhancing security and control over API access.
- **🎬 Call Overlay Styling**: Adjusted call overlay styling on large screens to not cover the entire interface, but only the chat control area, for a more unobtrusive interaction experience.

### Fixed

- **🔧 LaTeX Rendering Issue**: Addressed an issue that affected the correct rendering of LaTeX.
- **📁 File Leak Prevention**: Resolved the issue of uploaded files mistakenly being accessible across user chats.
- **🔧 Pipe Functions with '**files**' Param**: Fixed issues with '**files**' parameter not functioning correctly in pipe functions.
- **📝 Markdown Processing for RAG**: Fixed issues with processing Markdown in files.
- **🚫 Duplicate System Prompts**: Fixed bugs causing system prompts to duplicate.

### Changed

- **🔋 Wakelock Permission**: Optimized the activation of wakelock to only engage during call mode, conserving device resources and improving battery performance during idle periods.
- **🔍 Content-Type for Ollama Chats**: Added 'application/x-ndjson' content-type to '/api/chat' endpoint responses to match raw Ollama responses.
- **✋ Disable Signups Conditionally**: Implemented conditional logic to disable sign-ups when 'ENABLE_LOGIN_FORM' is set to false.

## [0.3.15] - 2024-08-21

### Added

- **🔗 Temporary Chat Activation**: Integrated a new URL parameter 'temporary-chat=true' to enable temporary chat sessions directly through the URL.
- **🌄 ComfyUI Seed Node Support**: Introduced seed node support in ComfyUI for image generation, allowing users to specify node IDs for randomized seed assignment.

### Fixed

- **🛠️ Tools and Functions**: Resolved a critical issue where Tools and Functions were not properly functioning, restoring full capability and reliability to these essential features.
- **🔘 Chat Action Button in Many Model Chat**: Fixed the malfunctioning of chat action buttons in many model chat environments, ensuring a smoother and more responsive user interaction.
- **⏪ Many Model Chat Compatibility**: Restored backward compatibility for many model chats.

## [0.3.14] - 2024-08-21

### Added

- **🛠️ Custom ComfyUI Workflow**: Deprecating several older environment variables, this enhancement introduces a new, customizable workflow for a more tailored user experience.
- **🔀 Merge Responses in Many Model Chat**: Enhances the dialogue by merging responses from multiple models into a single, coherent reply, improving the interaction quality in many model chats.
- **✅ Multiple Instances of Same Model in Chats**: Enhanced many model chat to support adding multiple instances of the same model.
- **🔧 Quick Actions in Model Workspace**: Enhanced Shift key quick actions for hiding/unhiding and deleting models, facilitating a smoother workflow.
- **🗨️ Markdown Rendering in User Messages**: User messages are now rendered in Markdown, enhancing readability and interaction.
- **💬 Temporary Chat Feature**: Introduced a temporary chat feature, deprecating the old chat history setting to enhance user interaction flexibility.
- **🖋️ User Message Editing**: Enhanced the user chat editing feature to allow saving changes without sending, providing more flexibility in message management.
- **🛡️ Security Enhancements**: Various security improvements implemented across the platform to ensure safer user experiences.
- **🌍 Updated Translations**: Enhanced translations for Chinese, Ukrainian, and Bahasa Malaysia, improving localization and user comprehension.

### Fixed

- **📑 Mermaid Rendering Issue**: Addressed issues with Mermaid chart rendering to ensure clean and clear visual data representation.
- **🎭 PWA Icon Maskability**: Fixed the Progressive Web App icon to be maskable, ensuring proper display on various device home screens.
- **🔀 Cloned Model Chat Freezing Issue**: Fixed a bug where cloning many model chats would cause freezing, enhancing stability and responsiveness.
- **🔍 Generic Error Handling and Refinements**: Various minor fixes and refinements to address previously untracked issues, ensuring smoother operations.

### Changed

- **🖼️ Image Generation Refactor**: Overhauled image generation processes for improved efficiency and quality.
- **🔨 Refactor Tool and Function Calling**: Refactored tool and function calling mechanisms for improved clarity and maintainability.
- **🌐 Backend Library Updates**: Updated critical backend libraries including SQLAlchemy, uvicorn[standard], faster-whisper, bcrypt, and boto3 for enhanced performance and security.

### Removed

- **🚫 Deprecated ComfyUI Environment Variables**: Removed several outdated environment variables related to ComfyUI settings, simplifying configuration management.

## [0.3.13] - 2024-08-14

### Added

- **🎨 Enhanced Markdown Rendering**: Significant improvements in rendering markdown, ensuring smooth and reliable display of LaTeX and Mermaid charts, enhancing user experience with more robust visual content.
- **🔄 Auto-Install Tools & Functions Python Dependencies**: For 'Tools' and 'Functions', Open WebUI now automatically install extra python requirements specified in the frontmatter, streamlining setup processes and customization.
- **🌀 OAuth Email Claim Customization**: Introduced an 'OAUTH_EMAIL_CLAIM' variable to allow customization of the default "email" claim within OAuth configurations, providing greater flexibility in authentication processes.
- **📶 Websocket Reconnection**: Enhanced reliability with the capability to automatically reconnect when a websocket is closed, ensuring consistent and stable communication.
- **🤳 Haptic Feedback on Support Devices**: Android devices now support haptic feedback for an immersive tactile experience during certain interactions.

### Fixed

- **🛠️ ComfyUI Performance Improvement**: Addressed an issue causing FastAPI to stall when ComfyUI image generation was active; now runs in a separate thread to prevent UI unresponsiveness.
- **🔀 Session Handling**: Fixed an issue mandating session_id on client-side to ensure smoother session management and transitions.
- **🖋️ Minor Bug Fixes and Format Corrections**: Various minor fixes including typo corrections, backend formatting improvements, and test amendments enhancing overall system stability and performance.

### Changed

- **🚀 Migration to SvelteKit 2**: Upgraded the underlying framework to SvelteKit version 2, offering enhanced speed, better code structure, and improved deployment capabilities.
- **🧹 General Cleanup and Refactoring**: Performed broad cleanup and refactoring across the platform, improving code efficiency and maintaining high standards of code health.
- **🚧 Integration Testing Improvements**: Modified how Cypress integration tests detect chat messages and updated sharing tests for better reliability and accuracy.
- **📁 Standardized '.safetensors' File Extension**: Renamed the '.sft' file extension to '.safetensors' for ComfyUI workflows, standardizing file formats across the platform.

### Removed

- **🗑️ Deprecated Frontend Functions**: Removed frontend functions that were migrated to backend to declutter the codebase and reduce redundancy.

## [0.3.12] - 2024-08-07

### Added

- **🔄 Sidebar Infinite Scroll**: Added an infinite scroll feature in the sidebar for more efficient chat navigation, reducing load times and enhancing user experience.
- **🚀 Enhanced Markdown Rendering**: Support for rendering all code blocks and making images clickable for preview; codespan styling is also enhanced to improve readability and user interaction.
- **🔒 Admin Shared Chat Visibility**: Admins no longer have default visibility over shared chats when ENABLE_ADMIN_CHAT_ACCESS is set to false, tightening security and privacy settings for users.
- **🌍 Language Updates**: Added Malay (Bahasa Malaysia) translation and updated Catalan and Traditional Chinese translations to improve accessibility for more users.

### Fixed

- **📊 Markdown Rendering Issues**: Resolved issues with markdown rendering to ensure consistent and correct display across components.
- **🛠️ Styling Issues**: Multiple fixes applied to styling throughout the application, improving the overall visual experience and interface consistency.
- **🗃️ Modal Handling**: Fixed an issue where modals were not closing correctly in various model chat scenarios, enhancing usability and interface reliability.
- **📄 Missing OpenAI Usage Information**: Resolved issues where usage statistics for OpenAI services were not being correctly displayed, ensuring users have access to crucial data for managing and monitoring their API consumption.
- **🔧 Non-Streaming Support for Functions Plugin**: Fixed a functionality issue with the Functions plugin where non-streaming operations were not functioning as intended, restoring full capabilities for async and sync integration within the platform.
- **🔄 Environment Variable Type Correction (COMFYUI_FLUX_FP8_CLIP)**: Corrected the data type of the 'COMFYUI_FLUX_FP8_CLIP' environment variable from string to boolean, ensuring environment settings apply correctly and enhance configuration management.

### Changed

- **🔧 Backend Dependency Updates**: Updated several backend dependencies such as boto3, pypdf, python-pptx, validators, and black, ensuring up-to-date security and performance optimizations.

## [0.3.11] - 2024-08-02

### Added

- **📊 Model Information Display**: Added visuals for model selection, including images next to model names for more intuitive navigation.
- **🗣 ElevenLabs Voice Adaptations**: Voice enhancements including support for ElevenLabs voice ID by name for personalized vocal interactions.
- **⌨️ Arrow Keys Model Selection**: Users can now use arrow keys for quicker model selection, enhancing accessibility.
- **🔍 Fuzzy Search in Model Selector**: Enhanced model selector with fuzzy search to locate models swiftly, including descriptions.
- **🕹️ ComfyUI Flux Image Generation**: Added support for the new Flux image gen model; introduces environment controls like weight precision and CLIP model options in Settings.
- **💾 Display File Size for Uploads**: Enhanced file interface now displays file size, preparing for upcoming upload restrictions.
- **🎚️ Advanced Params "Min P"**: Added 'Min P' parameter in the advanced settings for customized model precision control.
- **🔒 Enhanced OAuth**: Introduced custom redirect URI support for OAuth behind reverse proxies, enabling safer authentication processes.
- **🖥 Enhanced Latex Rendering**: Adjustments made to latex rendering processes, now accurately detecting and presenting latex inputs from text.
- **🌐 Internationalization**: Enhanced with new Romanian and updated Vietnamese and Ukrainian translations, helping broaden accessibility for international users.

### Fixed

- **🔧 Tags Handling in Document Upload**: Tags are now properly sent to the upload document handler, resolving issues with missing metadata.
- **🖥️ Sensitive Input Fields**: Corrected browser misinterpretation of secure input fields, preventing misclassification as password fields.
- **📂 Static Path Resolution in PDF Generation**: Fixed static paths that adjust dynamically to prevent issues across various environments.

### Changed

- **🎨 UI/UX Styling Enhancements**: Multiple minor styling updates for a cleaner and more intuitive user interface.
- **🚧 Refactoring Various Components**: Numerous refactoring changes across styling, file handling, and function simplifications for clarity and performance.
- **🎛️ User Valves Management**: Moved user valves from settings to direct chat controls for more user-friendly access during interactions.

### Removed

- **⚙️ Health Check Logging**: Removed verbose logging from the health checking processes to declutter logs and improve backend performance.

## [0.3.10] - 2024-07-17

### Fixed

- **🔄 Improved File Upload**: Addressed the issue where file uploads lacked animation.
- **💬 Chat Continuity**: Fixed a problem where existing chats were not functioning properly in some instances.
- **🗂️ Chat File Reset**: Resolved the issue of chat files not resetting for new conversations, now ensuring a clean slate for each chat session.
- **📁 Document Workspace Uploads**: Corrected the handling of document uploads in the workspace using the Files API.

## [0.3.9] - 2024-07-17

### Added

- **📁 Files Chat Controls**: We've reverted to the old file handling behavior where uploaded files are always included. You can now manage files directly within the chat controls section, giving you the ability to remove files as needed.
- **🔧 "Action" Function Support**: Introducing a new "Action" function to write custom buttons to the message toolbar. This feature enables more interactive messaging, with documentation coming soon.
- **📜 Citations Handling**: For newly uploaded files in documents workspace, citations will now display the actual filename. Additionally, you can click on these filenames to open the file in a new tab for easier access.
- **🛠️ Event Emitter and Call Updates**: Enhanced 'event_emitter' to allow message replacement and 'event_call' to support text input for Tools and Functions. Detailed documentation will be provided shortly.
- **🎨 Styling Refactor**: Various styling updates for a cleaner and more cohesive user interface.
- **🌐 Enhanced Translations**: Improved translations for Catalan, Ukrainian, and Brazilian Portuguese.

### Fixed

- **🔧 Chat Controls Priority**: Resolved an issue where Chat Controls values were being overridden by model information parameters. The priority is now Chat Controls, followed by Global Settings, then Model Settings.
- **🪲 Debug Logs**: Fixed an issue where debug logs were not being logged properly.
- **🔑 Automatic1111 Auth Key**: The auth key for Automatic1111 is no longer required.
- **📝 Title Generation**: Ensured that the title generation runs only once, even when multiple models are in a chat.
- **✅ Boolean Values in Params**: Added support for boolean values in parameters.
- **🖼️ Files Overlay Styling**: Fixed the styling issue with the files overlay.

### Changed

- **⬆️ Dependency Updates**
  - Upgraded 'pydantic' from version 2.7.1 to 2.8.2.
  - Upgraded 'sqlalchemy' from version 2.0.30 to 2.0.31.
  - Upgraded 'unstructured' from version 0.14.9 to 0.14.10.
  - Upgraded 'chromadb' from version 0.5.3 to 0.5.4.

## [0.3.8] - 2024-07-09

### Added

- **💬 Chat Controls**: Easily adjust parameters for each chat session, offering more precise control over your interactions.
- **📌 Pinned Chats**: Support for pinned chats, allowing you to keep important conversations easily accessible.
- **📄 Apache Tika Integration**: Added support for using Apache Tika as a document loader, enhancing document processing capabilities.
- **🛠️ Custom Environment for OpenID Claims**: Allows setting custom claims for OpenID, providing more flexibility in user authentication.
- **🔧 Enhanced Tools & Functions API**: Introduced 'event_emitter' and 'event_call', now you can also add citations for better documentation and tracking. Detailed documentation will be provided on our documentation website.
- **↔️ Sideways Scrolling in Settings**: Settings tabs container now supports horizontal scrolling for easier navigation.
- **🌑 Darker OLED Theme**: Includes a new, darker OLED theme and improved styling for the light theme, enhancing visual appeal.
- **🌐 Language Updates**: Updated translations for Indonesian, German, French, and Catalan languages, expanding accessibility.

### Fixed

- **⏰ OpenAI Streaming Timeout**: Resolved issues with OpenAI streaming response using the 'AIOHTTP_CLIENT_TIMEOUT' setting, ensuring reliable performance.
- **💡 User Valves**: Fixed malfunctioning user valves, ensuring proper functionality.
- **🔄 Collapsible Components**: Addressed issues with collapsible components not working, restoring expected behavior.

### Changed

- **🗃️ Database Backend**: Switched from Peewee to SQLAlchemy for improved concurrency support, enhancing database performance.
- **⬆️ ChromaDB Update**: Upgraded to version 0.5.3. Ensure your remote ChromaDB instance matches this version.
- **🔤 Primary Font Styling**: Updated primary font to Archivo for better visual consistency.
- **🔄 Font Change for Windows**: Replaced Arimo with Inter font for Windows users, improving readability.
- **🚀 Lazy Loading**: Implemented lazy loading for 'faster_whisper' and 'sentence_transformers' to reduce startup memory usage.
- **📋 Task Generation Payload**: Task generations now include only the "task" field in the body instead of "title".

## [0.3.7] - 2024-06-29

### Added

- **🌐 Enhanced Internationalization (i18n)**: Newly introduced Indonesian translation, and updated translations for Turkish, Chinese, and Catalan languages to improve user accessibility.

### Fixed

- **🕵️‍♂️ Browser Language Detection**: Corrected the issue where the application was not properly detecting and adapting to the browser's language settings.
- **🔐 OIDC Admin Role Assignment**: Fixed a bug where the admin role was not being assigned to the first user who signed up via OpenID Connect (OIDC).
- **💬 Chat/Completions Endpoint**: Resolved an issue where the chat/completions endpoint was non-functional when the stream option was set to False.
- **🚫 'WEBUI_AUTH' Configuration**: Addressed the problem where setting 'WEBUI_AUTH' to False was not being applied correctly.

### Changed

- **📦 Dependency Update**: Upgraded 'authlib' from version 1.3.0 to 1.3.1 to ensure better security and performance enhancements.

## [0.3.6] - 2024-06-27

### Added

- **✨ "Functions" Feature**: You can now utilize "Functions" like filters (middleware) and pipe (model) functions directly within the WebUI. While largely compatible with Pipelines, these native functions can be executed easily within Open WebUI. Example use cases for filter functions include usage monitoring, real-time translation, moderation, and automemory. For pipe functions, the scope ranges from Cohere and Anthropic integration directly within Open WebUI, enabling "Valves" for per-user OpenAI API key usage, and much more. If you encounter issues, SAFE_MODE has been introduced.
- **📁 Files API**: Compatible with OpenAI, this feature allows for custom Retrieval-Augmented Generation (RAG) in conjunction with the Filter Function. More examples will be shared on our community platform and official documentation website.
- **🛠️ Tool Enhancements**: Tools now support citations and "Valves". Documentation will be available shortly.
- **🔗 Iframe Support via Files API**: Enables rendering HTML directly into your chat interface using functions and tools. Use cases include playing games like DOOM and Snake, displaying a weather applet, and implementing Anthropic "artifacts"-like features. Stay tuned for updates on our community platform and documentation.
- **🔒 Experimental OAuth Support**: New experimental OAuth support. Check our documentation for more details.
- **🖼️ Custom Background Support**: Set a custom background from Settings > Interface to personalize your experience.
- **🔑 AUTOMATIC1111_API_AUTH Support**: Enhanced security for the AUTOMATIC1111 API.
- **🎨 Code Highlight Optimization**: Improved code highlighting features.
- **🎙️ Voice Interruption Feature**: Reintroduced and now toggleable from Settings > Interface.
- **💤 Wakelock API**: Now in use to prevent screen dimming during important tasks.
- **🔐 API Key Privacy**: All API keys are now hidden by default for better security.
- **🔍 New Web Search Provider**: Added jina_search as a new option.
- **🌐 Enhanced Internationalization (i18n)**: Improved Korean translation and updated Chinese and Ukrainian translations.

### Fixed

- **🔧 Conversation Mode Issue**: Fixed the issue where Conversation Mode remained active after being removed from settings.
- **📏 Scroll Button Obstruction**: Resolved the issue where the scrollToBottom button container obstructed clicks on buttons beneath it.

### Changed

- **⏲️ AIOHTTP_CLIENT_TIMEOUT**: Now set to 'None' by default for improved configuration flexibility.
- **📞 Voice Call Enhancements**: Improved by skipping code blocks and expressions during calls.
- **🚫 Error Message Handling**: Disabled the continuation of operations with error messages.
- **🗂️ Playground Relocation**: Moved the Playground from the workspace to the user menu for better user experience.

## [0.3.5] - 2024-06-16

### Added

- **📞 Enhanced Voice Call**: Text-to-speech (TTS) callback now operates in real-time for each sentence, reducing latency by not waiting for full completion.
- **👆 Tap to Interrupt**: During a call, you can now stop the assistant from speaking by simply tapping, instead of using voice. This resolves the issue of the speaker's voice being mistakenly registered as input.
- **😊 Emoji Call**: Toggle this feature on from the Settings > Interface, allowing LLMs to express emotions using emojis during voice calls for a more dynamic interaction.
- **🖱️ Quick Archive/Delete**: Use the Shift key + mouseover on the chat list to swiftly archive or delete items.
- **📝 Markdown Support in Model Descriptions**: You can now format model descriptions with markdown, enabling bold text, links, etc.
- **🧠 Editable Memories**: Adds the capability to modify memories.
- **📋 Admin Panel Sorting**: Introduces the ability to sort users/chats within the admin panel.
- **🌑 Dark Mode for Quick Selectors**: Dark mode now available for chat quick selectors (prompts, models, documents).
- **🔧 Advanced Parameters**: Adds 'num_keep' and 'num_batch' to advanced parameters for customization.
- **📅 Dynamic System Prompts**: New variables '{{CURRENT_DATETIME}}', '{{CURRENT_TIME}}', '{{USER_LOCATION}}' added for system prompts. Ensure '{{USER_LOCATION}}' is toggled on from Settings > Interface.
- **🌐 Tavily Web Search**: Includes Tavily as a web search provider option.
- **🖊️ Federated Auth Usernames**: Ability to set user names for federated authentication.
- **🔗 Auto Clean URLs**: When adding connection URLs, trailing slashes are now automatically removed.
- **🌐 Enhanced Translations**: Improved Chinese and Swedish translations.

### Fixed

- **⏳ AIOHTTP_CLIENT_TIMEOUT**: Introduced a new environment variable 'AIOHTTP_CLIENT_TIMEOUT' for requests to Ollama lasting longer than 5 minutes. Default is 300 seconds; set to blank ('') for no timeout.
- **❌ Message Delete Freeze**: Resolved an issue where message deletion would sometimes cause the web UI to freeze.

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
