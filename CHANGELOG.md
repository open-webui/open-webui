# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.18] - 2025-07-19

### Fixed

- 🚑 **Users Not Loading in Groups**: Resolved an issue where user list was not displaying within user groups, restoring full visibility and management of group memberships for teams and admins.

## [0.6.17] - 2025-07-19

### Added

- 📂 **Dedicated Folder View with Chat List**: Clicking a folder now reveals a brand-new landing page showcasing a list of all chats within that folder, making navigation simpler and giving teams immediate visibility into project-specific conversations.
- 🆕 **Streamlined Folder Creation Modal**: Creating a new folder is now a seamless, unified experience with a dedicated modal that visually and functionally matches the edit folder flow, making workspace organization more intuitive and error-free for all users.
- 🗃️ **Direct File Uploads to Folder Knowledge**: You can now upload files straight to a folder’s knowledge—empowering you to enrich project spaces by adding resources and documents directly, without the need to pre-create knowledge bases beforehand.
- 🔎 **Chat Preview in Search**: When searching chats, instantly preview results in context without having to open them—making discovery, auditing, and recall dramatically quicker, especially in large, active teams.
- 🖼️ **Image Upload and Inline Insertion in Notes**: Notes now support inserting images directly among your text, letting you create rich, visually structured documentation, brainstorms, or reports in a more natural and engaging way—no more images just as attachments.
- 📱 **Enhanced Note Selection Editing and Q&A**: Select any portion of your notes to either edit just the highlighted part or ask focused questions about that content—streamlining workflows, boosting productivity, and making reviews or AI-powered enhancements more targeted.
- 📝 **Copy Notes as Rich Text**: Copy entire notes—including all formatting, images, and structure—directly as rich text for seamless pasting into emails, reports, or other tools, maintaining clarity and consistency outside the WebUI.
- ⚡ **Fade-In Streaming Text Experience**: Live-generated responses now elegantly fade in as the AI streams them, creating a more natural and visually engaging reading experience; easily toggled off in Interface settings if you prefer static displays.
- 🔄 **Settings for Follow-Up Prompts**: Fine-tune your follow-up prompt experience—with new controls, you can choose to keep them visible or have them inserted directly into the message input instead of auto-submitting, giving you more flexibility and control over your workflow.
- 🔗 **Prompt Variable Documentation Quick Link**: Access documentation for prompt variables in one click from the prompt editor modal—shortening the learning curve and making advanced prompt-building more accessible.
- 📈 **Active and Total User Metrics for Telemetry**: Gain valuable insights into usage patterns and platform engagement with new metrics tracking active and total users—enhancing auditability and planning for large organizations.
- 🏷️ **Traceability with Log Trace and Span IDs**: Each log entry now carries detailed trace and span IDs, making it much easier for admins to pinpoint and resolve issues across distributed systems or in complex troubleshooting.
- 👥 **User Group Add/Remove Endpoints**: Effortlessly add or remove users from groups with new, improved endpoints—giving admins and team leads faster, clearer control over collaboration and permissions.
- ⚙️ **Note Settings and Controls Streamlined**: The main “Settings” for notes are now simply called “Controls”, and note files now reside in a dedicated controls section, decluttering navigation and making it easier to find and configure note-related options.
- 🚀 **Faster Admin User Page Loads**: The user list endpoint for admins has been optimized to exclude heavy profile images, speeding up load times for large teams and reducing waiting during administrative tasks.
- 📡 **Chat ID Header Forwarding**: Ollama and OpenAI router requests now include the chat ID in request headers, enabling better request correlation and debugging capabilities across AI model integrations.
- 🧠 **Enhanced Reasoning Tag Processing**: Improved and expanded reasoning tag parsing to handle various tag formats more robustly, including standard XML-style tags and custom delimiters, ensuring better AI reasoning transparency and debugging capabilities.
- 🔐 **OAuth Token Endpoint Authentication Method**: Added configurable OAuth token endpoint authentication method support, providing enhanced flexibility and security options for enterprise OAuth integrations and identity provider compatibility.
- 🛡️ **Redis Sentinel High Availability Support**: Comprehensive Redis Sentinel failover implementation with automatic master discovery, intelligent retry logic for connection failures, and seamless operation during master node outages—eliminating single points of failure and ensuring continuous service availability in production deployments.
- 🌐 **Localization & Internationalization Improvements**: Refined and expanded translations for Simplified Chinese, Traditional Chinese, French, German, Korean, and Polish, ensuring a more fluent and native experience for global users across all supported languages.

### Fixed

- 🏷️ **Hybrid Search Functionality Restored**: Hybrid search now works seamlessly again—enabling more accurate, relevant, and comprehensive knowledge discovery across all RAG-powered workflows.
- 🚦 **Note Chat - Edit Button Disabled During AI Generation**: The edit button when chatting with a note is now disabled while the AI is responding—preventing accidental edits and ensuring workflow clarity during chat sessions.
- 🧹 **Cleaner Database Credentials**: Database connection no longer duplicates ‘@’ in credentials, preventing potential connection issues and ensuring smoother, more reliable integrations.
- 🧑‍💻 **File Deletion Now Removes Related Vector Data**: When files are deleted from storage, they are now purged from the vector database as well, ensuring clean data management and preventing clutter or stale search results.
- 📁 **Files Modal Translation Issues Fixed**: All modal dialog strings—including “Using Entire Document” and “Using Focused Retrieval”—are now fully translated for a more consistent and localized UI experience.
- 🚫 **Drag-and-Drop File Upload Disabled for Unsupported Models**: File upload by drag-and-drop is disabled when using models that do not support attachments—removing confusion and preventing workflow interruptions.
- 🔑 **Ollama Tool Calls Now Reliable**: Fixed issues with Ollama-based tool calls, ensuring uninterrupted AI augmentation and tool use for every chat.
- 📄 **MIME Type Help String Correction**: Cleaned up mimetype help text by removing extraneous characters, providing clearer guidance for file upload configurations.
- 📝 **Note Editor Permission Fix**: Removed unnecessary admin-only restriction from note chat functionality, allowing all authorized users to access note editing features as intended.
- 📋 **Chat Sources Handling Improved**: Fixed sources handling logic to prevent duplicate source assignments in chat messages, ensuring cleaner and more accurate source attribution during conversations.
- 😀 **Emoji Generation Error Handling**: Improved error handling in audio router and fixed metadata structure for emoji generation tasks, preventing crashes and ensuring more reliable emoji generation functionality.
- 🔒 **Folder System Prompt Permission Enforcement**: System prompt fields in folder edit modal are now properly hidden for users without system prompt permissions, ensuring consistent security policy enforcement across all folder management interfaces.
- 🌐 **WebSocket Redis Lock Timeout Type Conversion**: Fixed proper integer type conversion for WebSocket Redis lock timeout configuration with robust error handling, preventing potential configuration errors and ensuring stable WebSocket connections.
- 📦 **PostHog Dependency Added**: Added PostHog 5.4.0 library to resolve ChromaDB compatibility issues, ensuring stable vector database operations and preventing library version conflicts during deployment.

### Changed

- 👀 **Tiptap Editor Upgraded to v3**: The underlying rich text editor has been updated for future-proofing, though some supporting libraries remain on v2 for compatibility. For now, please install dependencies using 'npm install --force' to avoid installation errors.
- 🚫 **Removed Redundant or Unused Strings and Elements**: Miscellaneous unused, duplicate, or obsolete code and translations have been cleaned up to maintain a streamlined and high-performance experience.

## [0.6.16] - 2025-07-14

### Added

- 🗂️ **Folders as Projects**: Organize your workflow with folder-based projects—set folder-level system prompts and associate custom knowledge, bringing seamless, context-rich management to teams and users handling multiple initiatives or clients.
- 📁 **Instant Folder-Based Chat Creation**: Start a new chat directly from any folder; just click and your new conversation is automatically embedded in the right project context—no more manual dragging or setup, saving time and eliminating mistakes.
- 🧩 **Prompt Variables with Automatic Input Modal**: Prompts containing variables now display a clean, auto-generated input modal that **autofocuses on the first field** for instant value entry—just select the prompt and fill in exactly what’s needed, reducing friction and guesswork.
- 🔡 **Variable Input Typing in Prompts**: Define input types for prompt variables (e.g., text, textarea, number, select, color, date, map and more), giving everyone a clearer and more precise prompt-building experience for advanced automation or workflows.
- 🚀 **Base Model List Caching**: Cache your base model list to speed up model selection and reduce repeated API calls; toggle this in Admin Settings > Connections for responsive model management even in large or multi-provider setups.
- ⏱️ **Configurable Model List Cache TTL**: Take control over model list caching with the new MODEL_LIST_CACHE_TTL environment variable. Set a custom cache duration in seconds to balance performance and freshness, reducing API requests in stable environments or ensuring rapid updates when models change frequently.
- 🔖 **Reference Notes as Knowledge or in Chats**: Use any note as knowledge for a model or folder, or reference it directly from chat—integrate living documentation into your Retrieval Augmented Generation workflows or discussions, bridging knowledge and action.
- 📝 **Chat Directly with Notes (Experimental)**: Ask questions about any note, and directly edit or update notes from within a chat—unlock direct AI-powered brainstorming, summarization, and cleanup, like having your own collaborative AI canvas.
- 🤝 **Collaborative Notes with Multi-User Editing**: Share notes with others and collaborate live—multiple users can edit a note in real-time, boosting cooperative knowledge building and workflow documentation.
- 🛡️ **Collaborative Note Permissions**: Control who can view or edit each note with robust sharing permissions, ensuring privacy or collaboration per your organizational needs.
- 🔗 **Copy Link to Notes**: Quickly copy and share direct links to notes for easier knowledge transfer within your team or external collaborators.
- 📋 **Task List Support in Notes**: Add, organize, and manage checklists or tasks inside your notes—plan projects, track to-dos, and keep everything actionable in a single space.
- 🧠 **AI-Generated Note Titles**: Instantly generate relevant and concise titles for your notes using AI—keep your knowledge library organized without tedious manual editing.
- 🔄 **Full Undo/Redo Support in Notes**: Effortlessly undo or redo your latest note changes—never fear mistakes or accidental edits while collaborating or writing.
- 📝 **Enhanced Note Word/Character Counter**: Always know the size of your notes with built-in counters, making it easier to adhere to length guidelines for shared or published content.
- 🖊️ **Floating & Bubble Formatting Menus in Note Editor**: Access text formatting tools through both a floating menu and an intuitive bubble menu directly in the note editor—making rich text editing faster, more discoverable, and easier than ever.
- ✍️ **Rich Text Prompt Insertion**: A new setting allows prompts to be inserted directly into the chat box as fully-formatted rich text, preserving Markdown elements like headings, lists, and bold text for a more intuitive and visually consistent editing experience.
- 🌐 **Configurable Database URL**: WebUI now supports more flexible database configuration via new environment variables—making deployment and scaling simpler across various infrastructure setups.
- 🎛️ **Completely Frontend-Handled File Upload in Temporary Chats**: When using temporary chats, file extraction now occurs fully in your browser with zero files sent to the backend, further strengthening privacy and giving you instant feedback.
- 🔄 **Enhanced Banner and Chat Command Visibility**: Banner handling and command feedback in chat are now clearer and more contextually visible, making alerts, suggestions, and automation easier to spot and interact with for all users.
- 📱 **Mobile Experience Polished**: The "new chat" button is back in mobile, plus core navigation and input controls have been smoothed out for better usability on phones and tablets.
- 📄 **OpenDocument Text (.odt) Support**: Seamlessly upload and process .odt files from open-source office suites like LibreOffice and OpenOffice, expanding your ability to build knowledge from a wider range of document formats.
- 📑 **Enhanced Markdown Document Splitting**: Improve knowledge retrieval from Markdown files with a new header-aware splitting strategy. This method intelligently chunks documents based on their header structure, preserving the original context and hierarchy for more accurate and relevant RAG results.
- 📚 **Full Context Mode for Knowledge Bases**: When adding a knowledge base to a folder or custom model, you can now toggle full context mode for the entire knowledge base. This bypasses the usual chunking and retrieval process, making it perfect for leaner knowledge bases.
- 🕰️ **Configurable OAuth Timeout**: Enhance login reliability by setting a custom timeout (OAUTH_TIMEOUT) for all OAuth providers (Google, Microsoft, GitHub, OIDC), preventing authentication failures on slow or restricted networks.
- 🎨 **Accessibility & High-Contrast Theme Enhancements**: Major accessibility overhaul with significant updates to the high-contrast theme. Improved focus visibility, ARIA labels, and semantic HTML ensure core components like the chat interface and model selector are fully compliant and readable for visually impaired users.
- ↕️ **Resizable System Prompt Fields**: Conveniently resize system prompt input fields to comfortably view and edit lengthy or complex instructions, improving the user experience for advanced model configuration.
- 🔧 **Granular Update Check Control**: Gain finer control over outbound connections with the new ENABLE_VERSION_UPDATE_CHECK flag. This allows administrators to disable version update checks independently of the full OFFLINE_MODE, perfect for environments with restricted internet access that still need to download embedding models.
- 🗃️ **Configurable Qdrant Collection Prefix**: Enhance scalability by setting a custom QDRANT_COLLECTION_PREFIX. This allows multiple Open WebUI instances to share a single Qdrant cluster safely, ensuring complete data isolation between separate deployments without conflicts.
- ⚙️ **Improved Default Database Performance**: Enhanced out-of-the-box performance by setting smarter database connection pooling defaults, reducing API response times for users on non-SQLite databases without requiring manual configuration.
- 🔧 **Configurable Redis Key Prefix**: Added support for the REDIS_KEY_PREFIX environment variable, allowing multiple Open WebUI instances to share a Redis cluster with isolated key namespaces for improved multi-tenancy.
- ➡️ **Forward User Context to Reranker**: For advanced RAG integrations, user information (ID, name, email, role) can now be forwarded as HTTP headers to external reranking services, enabling personalized results or per-user access control.
- ⚙️ **PGVector Connection Pooling**: Enhance performance and stability for PGVector-based RAG by enabling and configuring the database connection pool. New environment variables allow fine-tuning of pool size, timeout, and overflow settings to handle high-concurrency workloads efficiently.
- ⚙️ **General Backend Refactoring**: Extensive refactoring delivers a faster, more reliable, and robust backend experience—improving chat speed, model management, and day-to-day reliability.
- 🌍 **Expanded & Improved Translations**: Enjoy a more accessible and intuitive experience thanks to comprehensive updates and enhancements for Chinese (Simplified and Traditional), German, French, Catalan, Irish, and Spanish translations throughout the interface.

### Fixed

- 🛠️ **Rich Text Input Stability and Performance**: Multiple improvements ensure faster, cleaner text editing and rendering with reduced glitches—especially supporting links, color picking, checkbox controls, and code blocks in notes and chats.
- 📷 **Seamless iPhone Image Uploads**: Effortlessly upload photos from iPhones and other devices using HEIC format—images are now correctly recognized and processed, eliminating compatibility issues.
- 🔄 **Audio MIME Type Registration**: Issues with audio file content types have been resolved, guaranteeing smoother, error-free uploads and playback for transcription or note attachments.
- 🖍️ **Input Commands Now Always Visible**: Input commands (like prompts or knowledge) dynamically adjust their height on small screens, ensuring nothing is cut off and every tool remains easily accessible.
- 🛑 **Tool Result Rendering**: Fixed display problems with tool results, providing fast, clear feedback when using external or internal tools.
- 🗂️ **Table Alignment in Markdown**: Markdown tables are now rendered and aligned as expected, keeping reports and documentation readable.
- 🖼️ **Thread Image Handling**: Fixed an issue where messages containing only images in threads weren’t displayed correctly.
- 🗝️ **Note Access Control Security**: Tightened access control logic for notes to guarantee that shared or collaborative notes respect all user permissions and privacy safeguards.
- 🧾 **Ollama API Compatibility**: Fixed model parameter naming in the API to ensure uninterrupted compatibility for all Ollama endpoints.
- 🛠️ **Detection for 'text/html' Files**: Files loaded with docling/tika are now reliably detected as the correct type, improving knowledge ingestion and document parsing.
- 🔐 **OAuth Login Stability**: Resolved a critical OAuth bug that caused login failures on subsequent attempts after logging out. The user session is now completely cleared on logout, ensuring reliable and secure authentication across all supported providers (Google, Microsoft, GitHub, OIDC).
- 🚪 **OAuth Logout and Redirect Reliability**: The OAuth logout process has been made more robust. Logout requests now correctly use proxy environment variables, ensuring they succeed in corporate networks. Additionally, the custom WEBUI_AUTH_SIGNOUT_REDIRECT_URL is now properly respected for all OAuth/OIDC configurations, ensuring a seamless sign-out experience.
- 📜 **Banner Newline Rendering**: Banners now correctly render newline characters, ensuring that multi-line announcements and messages are displayed with their intended formatting.
- ℹ️ **Consistent Model Description Rendering**: Model descriptions now render Markdown correctly in the main chat interface, matching the formatting seen in the model selection dropdown for a consistent user experience.
- 🔄 **Offline Mode Update Check Display**: Corrected a UI bug where the "Checking for Updates..." message would display indefinitely when the application was set to offline mode.
- 🛠️ **Tool Result Encoding**: Fixed a bug where tool calls returning non-ASCII characters would fail, ensuring robust handling of international text and special characters in tool outputs.

## [0.6.15] - 2025-06-16

### Added

- 🖼️ **Global Image Compression Option**: Effortlessly set image compression globally so all image uploads and outputs are optimized, speeding up load times and saving bandwidth—perfect for teams dealing with large files or limited network resources.
- 🎤 **Custom Speech-to-Text Content-Type for Transcription**: Define custom content types for audio transcription, ensuring compatibility with diverse audio sources and unlocking smoother, more accurate transcriptions in advanced setups.
- 🗂️ **LDAP Group Synchronization (Experimental)**: Automatically sync user groups from your LDAP directory directly into Open WebUI for seamless enterprise access management—simplifies identity integration and governance across your organization.
- 📈 **OpenTelemetry Metrics via OTLP Exporter (Experimental)**: Gain enterprise-grade analytics and monitor your AI usage in real time with experimental OpenTelemetry Metrics support—connect to any OTLP-compatible backend for instant insights into performance, load, and user interactions.
- 🕰️ **See User Message Timestamps on Hover (Chat Bubble UI)**: Effortlessly check when any user message was sent by hovering over it in Chat Bubble mode—no more switching screens or digging through logs for context.
- 🗂️ **Leaderboard Sorting Options**: Sort the leaderboard directly in the UI for a clearer, more actionable view of top performers, models, or tools—making analysis and recognition quick and easy for teams.
- 🏆 **Evaluation Details Modal in Feedbacks and Leaderboard**: Dive deeper with new modals that display detailed evaluation information when reviewing feedbacks and leaderboard rankings—accelerates learning, progress tracking, and quality improvement.
- 🔄 **Support for Multiple Pages in External Document Loaders**: Effortlessly extract and work with content spanning multiple pages in external documents, giving you complete flexibility for in-depth research and document workflows.
- 🌐 **New Accessibility Enhancements Across the Interface**: Benefit from significant accessibility improvements—tab navigation, ARIA roles/labels, better high-contrast text/modes, accessible modals, and more—making Open WebUI more usable and equitable for everyone, including those using assistive technologies.
- ⚡ **Performance & Stability Upgrades Across Frontend and Backend**: Enjoy a smoother, more reliable experience with numerous behind-the-scenes optimizations and refactoring on both frontend and backend—resulting in faster load times, fewer errors, and even greater stability throughout your workflows.
- 🌏 **Updated and Expanded Localizations**: Enjoy improved, up-to-date translations for Finnish, German (now with model pinning features), Korean, Russian, Simplified Chinese, Spanish, and more—making every interaction smoother, clearer, and more intuitive for international users.

### Fixed

- 🦾 **Ollama Error Messages More Descriptive**: Receive clearer, more actionable error messages when something goes wrong with Ollama models—making troubleshooting and user support faster and more effective.
- 🌐 **Bypass Webloader Now Works as Expected**: Resolved an issue where the "bypass webloader" feature failed to function correctly, ensuring web search bypasses operate smoothly and reliably for lighter, faster query results.
- 🔍 **Prevent Redundant Documents in Citation List**: The expanded citation list no longer shows duplicate documents, offering a cleaner, easier-to-digest reference experience when reviewing sources in knowledge and research workflows.
- 🛡️ **Trusted Header Email Matching is Now Case-Insensitive**: Fixed a critical authentication issue where email case sensitivity could cause secure headers to mismatch, ensuring robust, seamless login and session management in all environments.
- ⚙️ **Direct Tool Server Input Accepts Empty Strings**: You can now submit direct tool server commands without unexpected errors when passing empty-string values, improving integration and automation efficiency.
- 📄 **Citation Page Number for Page 1 is Now Displayed**: Corrected an oversight where references for page 1 documents were missing the page number; citations are now always accurate and fully visible.
- 📒 **Notes Access Restored**: Fixed an issue where some users could not access their notes—everyone can now view and manage their notes reliably, ensuring seamless documentation and workflow continuity.
- 🛑 **OAuth Callback Double-Slash Issue Resolved**: Fixed rare cases where an extra slash in OAuth callbacks caused failed logins or redirects, making third-party login integrations more reliable.

### Changed

- 🔑 **Dedicated Permission for System Prompts**: System prompt access is now controlled by its own specific permission instead of being grouped with general chat controls, empowering admins with finer-grained management over who can view or modify system prompts for enhanced security and workflow customization.
- 🛠️ **YouTube Transcript API and python-pptx Updated**: Enjoy better performance, reliability, and broader compatibility thanks to underlying library upgrades—less friction with media-rich and presentation workflows.

### Removed

- 🗑️ **Console Logging Disabled in Production**: All 'console.log' and 'console.debug' statements are now disabled in production, guaranteeing improved security and cleaner browser logs for end users by removing extraneous technical output.

## [0.6.14] - 2025-06-10

### Added

- 🤖 **Automatic "Follow Up" Suggestions**: Open WebUI now intelligently generates actionable "Follow Up" suggestions automatically with each message you send, helping you stay productive and inspired without interrupting your flow; you can always disable this in Settings if you prefer a distraction-free experience.
- 🧩 **OpenAI-Compatible Embeddings Endpoint**: Introducing a fully OpenAI-style '/api/embeddings' endpoint—now you can plug in OpenAI-style embeddings workflows with zero hassle, making integrations with external tools and platforms seamless and familiar.
- ↗️ **Model Pinning for Quick Access**: Pin your favorite or most-used models to the sidebar for instant selection—no more scrolling through long model lists; your go-to models are always visible and ready for fast access.
- 📌 **Selector Model Item Menu**: Each model in the selector now features a menu where you can easily pin/unpin to the sidebar and copy a direct link—simplifying collaboration and staying organized in even the busiest environments.
- 🛑 **Reliable Stop for Ongoing Chats in Multi-Replica Setups**: Stopping or cancelling an in-progress chat now works reliably even in clustered deployments—ensuring every user can interrupt AI output at any time, no matter your scale.
- 🧠 **'Think' Parameter for Ollama Models**: Leverage new 'think' parameter support for Ollama—giving you advanced control over AI reasoning process and further tuning model behavior for your unique use cases.
- 💬 **Picture Description Modes for Docling**: Customize how images are described/extracted by Docling Loader for smarter, more detailed, and workflow-tailored image understanding in your document pipelines.
- 🛠 **Settings Modal Deep Linking**: Every tab in Settings now has its own route—making direct navigation and sharing of precise settings faster and more intuitive.
- 🎤 **Audio HTML Component Token**: Easily embed and play audio directly in your chats, improving voice-based workflows and making audio content instantly accessible and manageable from any conversation.
- 🔑 **Support for Secret Key File**: Now you can specify 'WEBUI_SECRET_KEY_FILE' for more secure and flexible key management—ideal for advanced deployments and tighter security standards.
- 💡 **Clarity When Cloning Prompts**: Cloned workspace prompts are clearly labelled with "(Clone)" and IDs have "-clone", keeping your prompt library organized and preventing accidental overwrites.
- 📝 **Dedicated User Role Edit Modal**: Updating user roles now reliably opens a dedicated edit user modal instead of cycling through roles—making it safer and more clear to manage team permissions.
- 🏞️ **Better Handling & Storage of Interpreter-Generated Images**: Code interpreter-generated images are now centrally stored and reliably loaded from the database or cloud storage, ensuring your artifacts are always available.
- 🚀 **Pinecone & Vector Search Optimizations**: Applied latest best practices from Pinecone for smarter timeouts, intelligent retry control, improved connection pooling, faster DNS, and concurrent batch handling—giving you more reliable, faster document search and RAG performance without manual tweaks.
- ⚙️ **Ollama Advanced Parameters Unified**: 'keep_alive' and 'format' options are now integrated into the advanced params section—edit everything from the model editor for flexible model control.
- 🛠️ **CUDA 12.6 Docker Image Support**: Deploy to NVIDIA GPUs with capability 7.0 and below (e.g., V100, GTX1080) via new cuda126 image—broadening your hardware options for scalable AI workloads.
- 🔒 **Experimental Table-Level PGVector Data Encryption**: Activate pgcrypto encryption support for pgvector to secure your vector search table contents, giving organizations enhanced compliance and data protection—perfect for enterprise or regulated environments.
- 👁 **Accessibility Upgrades Across Interface**: Chat buttons and close controls are now labelled and structured for optimal accessibility support, ensuring smoother operation with assistive technologies.
- 🎨 **High-Contrast Mode Expansions**: High-contrast accessibility mode now also applies to menu items, tabs, and search input fields, offering a more readable experience for all users.
- 🛠️ **Tooltip & Translation Clarity**: Improved translation and tooltip clarity, especially over radio buttons, making the UI more understandable for all users.
- 🔠 **Global Localization & Translation Improvements**: Hefty upgrades to Traditional Chinese, Simplified Chinese, Hebrew, Russian, Irish, German, and Danish translation packs—making the platform feel native and intuitive for even more users worldwide.
- ⚡ **General Backend Stability & Security Enhancements**: Refined numerous backend routines to minimize memory use, improve performance, and streamline integration with external APIs—making the entire platform more robust and secure for daily work.

### Fixed

- 🏷 **Feedback Score Display Improved**: Addressed overflow and visibility issues with feedback scores for more readable and accessible evaluations.
- 🗂 **Admin Settings Model Edits Apply Immediately**: Changes made in the Model Editor within Admin Settings now take effect instantly, eliminating confusion during model management.
- 🔄 **Assigned Tools Update Instantly on New Chats**: Models assigned with specific tools now consistently update and are available in every new chat—making tool workflows more predictable and robust.
- 🛠 **Document Settings Saved Only on User Action**: Document settings now save only when you press the Save button, reducing accidental changes and ensuring greater control.
- 🔊 **Voice Recording on Older iOS Devices Restored**: Voice input is now fully functional on older iOS devices, keeping voice workflows accessible to all users.
- 🔒 **Trusted Email Header Session Security**: User sessions now strictly verify the trusted email header matches the logged-in user's email, ensuring secure authentication and preventing accidental session switching.
- 🔒 **Consistent User Signout on Email Mismatch**: When the trusted email in the header changes, you will now be properly signed out and redirected, safeguarding your session's integrity.
- 🛠 **General Error & Content Validation Improvements**: Smarter error handling means clearer messages and fewer unnecessary retries—making batch uploads, document handling, and knowledge indexing more resilient.
- 🕵️ **Better Feedback on Chat Title Edits**: Error messages now show clearly if problems occur while editing chat titles.

## [0.6.13] - 2025-05-30

### Added

- 🟦 **Azure OpenAI Embedding Support**: You can now select Azure OpenAI endpoints for text embeddings, unlocking seamless integration with enterprise-scale Azure AI for powerful RAG and knowledge workflows—no more workarounds, connect and scale effortlessly.
- 🧩 **Smarter Custom Parameter Handling**: Instantly enjoy more flexible model setup—any JSON pasted into custom parameter fields is now parsed automatically, so you can define rich, nested parameters without tedious manual adjustment. This streamlines advanced configuration for all models and accelerates experimentation.
- ⚙️ **General Backend Refactoring**: Significant backend improvements deliver a cleaner codebase for better maintainability, faster performance, and even greater platform reliability—making all your workflows run more smoothly.
- 🌏 **Localization Upgrades**: Experience highly improved user interface translations and clarity in Simplified, Traditional Chinese, Korean, and Finnish, offering a more natural, accurate, and accessible experience for global users.

### Fixed

- 🛡️ **Robust Message Handling on Chat Load**: Fixed an issue where chat pages could fail to load if a referenced message was missing or undefined; now, chats always load smoothly and missing IDs no longer disrupt your workflow.
- 📝 **Correct Prompt Access Control**: Ensured that the prompt access controls register properly, restoring reliable permissioning and safeguarding your prompt workflows.
- 🛠 **Open WebUI-Specific Params No Longer Sent to Models**: Fixed a bug that sent internal WebUI parameters to APIs, ensuring only intended model options are transmitted—restoring predictable, error-free model operation.
- 🧠 **Refined Memory Error Handling**: Enhanced stability during memory-related operations, so even uncommon memory errors are gracefully managed without disrupting your session—resulting in a more reliable, worry-free experience.

## [0.6.12] - 2025-05-29

### Added

- 🧩 **Custom Advanced Model Parameters**: You can now add your own tailor-made advanced parameters to any model, empowering you to fine-tune behavior and unlock greater flexibility beyond just the built-in options—accelerate your experimentation.
- 🪧 **Datalab Marker API Content Extraction Support**: Seamlessly extract content from files and documents using the Datalab Marker API directly in your workflows, enabling more robust structured data extraction for RAG and document processing with just a simple engine switch in the UI.
- ⚡ **Parallelized Base Model Fetching**: Experience noticeably faster startup and model refresh times—base model data now loads in parallel, drastically shortening delays in busy or large-scale deployments.
- 🧠 **Efficient Function Loading and Caching**: Functions are now only reloaded if their content changes, preventing unnecessary duplicate loads, saving bandwidth, and boosting performance.
- 🌍 **Localization & Translation Enhancements**: Improved and expanded Simplified, Traditional Chinese, and Russian translations, providing smoother, more accurate, and context-aware experiences for global users.

### Fixed

- 💬 **Stable Message Input Box**: Fixed an issue where the message input box would shift unexpectedly (especially on mobile or with screen reader support), ensuring a smooth and reliable typing experience for every user.
- 🔊 **Reliable Read Aloud (Text-to-Speech)**: Read aloud now works seamlessly across messages, so users depending on TTS for accessibility or multitasking will experience uninterrupted and clear voice playback.
- 🖼 **Image Preview and Download Restored**: Fixed problems with image preview and downloads, ensuring frictionless creation, previewing, and downloading of images in your chats—no more interruptions in creative or documentation workflows.
- 📱 **Improved Mobile Styling for Workspace Capabilities**: Capabilities management is now readable and easy-to-use even on mobile devices, empowering admins and users to manage access quickly on the go.
- 🔁 **/api/v1/retrieval/query/collection Endpoint Reliability**: Queries to retrieval collections now return the expected results, bolstering the reliability of your knowledge workflows and citation-ready responses.

### Removed

- 🧹 **Duplicate CSS Elements**: Streamlined the UI by removing redundant CSS, reducing clutter and improving load times for a smoother visual experience.

## [0.6.11] - 2025-05-27

### Added

- 🟢 **Ollama Model Status Indicator in Model Selector**: Instantly see which Ollama models are currently loaded with a clear indicator in the model selector, helping you stay organized and optimize local model usage.
- 🗑️ **Unload Ollama Model Directly from Model Selector**: Easily release memory and resources by unloading any loaded Ollama model right in the model selector—streamline hardware management without switching pages.
- 🗣️ **User-Configurable Speech-to-Text Language Setting**: Improve transcription accuracy by letting individual users explicitly set their preferred STT language in their settings—ideal for multilingual teams and clear audio capture.
- ⚡ **Granular Audio Playback Speed Control**: Instead of just presets, you can now choose granular audio speed using a numeric input, giving you complete control over playback pace in transcriptions and media reviews.
- 📦 **GZip, Brotli, ZStd Compression Middleware**: Enjoy significantly faster page loads and reduced bandwidth usage with new server-side compression—giving users a snappier, more efficient experience.
- 🏷️ **Configurable Weight for BM25 in Hybrid Search**: Fine-tune search relevance by adjusting the weight for BM25 inside hybrid search from the UI, letting you tailor knowledge search results to your workflow.
- 🧪 **Bypass File Creation with CTRL + SHIFT + V**: When “Paste Large Text as File” is enabled, use CTRL + SHIFT + V to skip the file creation dialog and instantly upload text as a file—perfect for rapid document prep.
- 🌐 **Bypass Web Loader in Web Search**: Choose to bypass web content loading and use snippets directly in web search for faster, more reliable results when page loads are slow or blocked.
- 🚀 **Environment Variable: WEBUI_AUTH_TRUSTED_GROUPS_HEADER**: Now sync and manage user groups directly via trusted HTTP header, unlocking smoother single sign-on and identity integrations for organizations.
- 🏢 **Workspace Models Visibility Controls**: You can now hide workspace-level models from both the model selector and shared environments—keep your team focused and reduce clutter from rarely-used endpoints.
- 🛡️ **Copy Model Link**: You can now copy a direct link to any model—including those hidden from the selector—making sharing and onboarding others more seamless.
- 🔗 **Load Function Directly from URL**: Simplify custom function management—just paste any GitHub function URL into Open WebUI and import new functions in seconds.
- ⚙️ **Custom Name/Description for External Tool Servers**: Personalize and clarify external tool servers by assigning custom names and descriptions, making it easier to manage integrations in large-scale workspaces.
- 🌍 **Custom OpenAPI JSON URL Support for Tool Servers**: Supports specifying any custom OpenAPI JSON URL, unlocking more flexible integration with any backend for tool calls.
- 📊 **Source Field Now Displays in Non-Streaming Responses with Attachments**: When files or knowledge are attached, the "source" field now appears for all responses, even in non-streaming mode—enabling improved citation workflow.
- 🎛 **Pinned Chats**: Reduced payload size on pinned chat requests—leading to faster load times and less data usage, especially on busy warehouses.
- 🛠 **Import/Export Default Prompt Suggestions**: Enjoy one-click import/export of prompt suggestions, making it much easier to share, reuse, and manage best practices across teams or deployments.
- 🍰 **Banners Now Sortable from Admin Settings**: Quickly re-order or prioritize banners, letting you highlight the most critical info for your team.
- 🛠 **Advanced Chat Parameters—Clearer Ollama Support Labels**: Parameters and advanced settings now explicitly indicate if they are Ollama-specific, reducing confusion and improving setup accuracy.
- 🤏 **Scroll Bar Thumb Improved for Better Visibility**: Enhanced scrollbar styling makes navigation more accessible and visually intuitive.
- 🗄️ **Modal Redesign for Archived and User Chat Listings**: Clean, modern modal interface for browsing archived and user-specific chats makes locating conversations faster and more pleasant.
- 📝 **Add/Edit Memory Modal UX**: Memory modals are now larger and have resizable input fields, supporting easier editing of long or complex memory content.
- 🏆 **Translation & Localization Enhancements**: Major upgrades to Chinese (Simplified & Traditional), Korean, Russian, German, Danish, Finnish—not just fixing typos, but consistency, tone, and terminology for a more natural native-language experience.
- ⚡ **General Backend Stability & Security Enhancements**: Various backend refinements ensure a more resilient, reliable, and secure platform for smoother operation and peace of mind.

### Fixed

- 🖼️ **Image Generation with Allowed File Extensions Now Works Reliably**: Ensure seamless image generation even when strict file extension rules are set—no more blocked creative workflows due to technical hiccups.
- 🗂 **Remove Leading Dot for File Extension Check**: Fixed an issue where file validation failed because of a leading dot, making file uploads and knowledge management more robust.
- 🏷️ **Correct Local/External Model Classification**: The platform now accurately distinguishes between local and external models—preventing local models from showing up as external (and vice versa)—ensuring seamless setup, clarity, and management of your AI model endpoints.
- 📄 **External Document Loader Now Functions as Intended**: External document loaders are reliably invoked, ensuring smoother knowledge ingestion from external sources—expanding your RAG and knowledge workflows.
- 🎯 **Correct Handling of Toggle Filters**: Toggle filters are now robustly managed, preventing accidental auto-activation and ensuring user preferences are always respected.
- 🗃 **S3 Tagging Character Restrictions Fixed**: Tags for files in S3 now automatically meet Amazon’s allowed character set, avoiding upload errors and ensuring cross-cloud compatibility.
- 🛡️ **Authentication Now Uses Password Hash When Duplicate Emails Exist**: Ensures account security and prevents access issues if duplicate emails are present in your system.

### Changed

- 🧩 **Admin Settings: OAuth Redirects Now Use WEBUI_URL**: The OAuth redirect URL is now based on the explicitly set WEBUI_URL, ensuring single sign-on and identity provider integrations always send users to the correct frontend.

### Removed

- 💡 **Duplicate/Typo Component Removals**: Obsolete components have been cleaned up, reducing confusion and improving overall code quality for the team.
- 🚫 **Streaming Upsert in Pinecone Removed**: Removed streaming upsert references for better compatibility and future-proofing with latest Pinecone SDK updates.

## [0.6.10] - 2025-05-19

### Added

- 🧩 **Experimental Azure OpenAI Support**: Instantly connect to Azure OpenAI endpoints by simply pasting your Azure OpenAI URL into the model connections—bringing flexible, enterprise-grade AI integration directly to your workflow.
- 💧 **Watermark AI Responses**: Easily add a visible watermark to AI-generated responses for clear content provenance and compliance with EU AI regulations—perfect for regulated environments and transparent communication.
- 🔍 **Enhanced Search Experience with Dedicated Modal**: Enjoy a modern, powerful search UI in a dedicated modal (open with Ctrl/Cmd + K) accessible from anywhere—quickly find chats, models, or content and boost your productivity.
- 🔲 **"Toggle" Filter Type for Chat Input**: Add interactive toggle filters (e.g. Web Search, Image, Code Interpreter) right into the chat input—giving you one-click control to activate features and simplifying the chat configuration process.
- 🧰 **Granular Model Capabilities Editor**: Define detailed capabilities and feature access for each AI model directly from the model editor—enabling tailored behavior, modular control, and a more customized AI environment for every team or use case.
- 🌐 **Flexible Local and External Connection Support**: Now you can designate any AI connection—whether OpenAI, Ollama, or others—as local or external, enabling seamless setup for on-premise, self-hosted, or cloud configurations and giving you maximum control and flexibility.
- 🗂️ **Allowed File Extensions for RAG**: Gain full control over your Retrieval-Augmented Generation (RAG) workflows by specifying exactly which file extensions are permitted for upload, improving security and relevance of indexed documents.
- 🔊 **Enhanced Audio Transcription Logic**: Experience smoother, more reliable audio transcription—very long audio files are now automatically split and processed in segments, preventing errors and ensuring even challenging files are transcribed seamlessly, all part of a broader stability upgrade for robust media workflows.
- 🦾 **External Document Loader Support**: Enhance knowledge base building by integrating documents using external loaders from a wide range of data sources, expanding what your AI can read and process.
- 📝 **Preview Button for Code Artifacts**: Instantly jump from an HTML code block to its associated artifacts page with the click of a new preview button—speeding up review and streamlining analysis.
- 🦻 **Screen Reader Support for Response Messages**: All chat responses are now fully compatible with screen readers, making the platform more inclusive and accessible for everyone.
- 🧑‍💼 **Customizable Pending User Overlay**: You can now tailor the overlay title and content shown to pending users, ensuring onboarding messaging is perfectly aligned with your organization’s tone and requirements.
- 🔐 **Option to Disable LDAP Certificate Validation**: You can now disable LDAP certificate validation for maximum flexibility in diverse IT environments—making integrations and troubleshooting much easier.
- 🎯 **Workspace Search by Username or Email**: Easily search across workspace pages using any username or email address, streamlining user and resource management.
- 🎨 **High Contrast & Dark Mode Enhancements**: Further improved placeholder, input, suggestion, toast, and model selector contrasts—including a dedicated placeholder dark mode—for more comfortable viewing in all lighting conditions.
- 🛡️ **Refined Security for Pipelines & Model Uploads**: Strengthened safeguards against path traversal vulnerabilities during uploads—ensuring your platform’s document and model management remains secure.
- 🌏 **Major Localization Upgrades**: Comprehensive translation updates and improvements across Korean, Bulgarian, Catalan, Japanese, Italian, Traditional Chinese, and Spanish—including more accurate AI terminology for clarity; your experience is now more natural, inclusive, and professional everywhere.
- 🦾 **General Backend Stability & Security**: Multiple backend improvements (including file upload, command navigation, and logging refactorings) deliver increased resilience, better error handling, and a more robust platform for all users.

### Fixed

- ✅ **Evaluation Feedback Endpoint Reliability**: Addressed issues with feedback submission endpoints to ensure seamless user feedback collection on model responses.
- 🫰 **Model List State Fixes**: Resolved issues where model status toggles in the workspace page might inadvertently switch or confuse state, making the management of active/inactive models more dependable.
- ✍️ **Admin Signup Logic**: Admin self-signup experience and validation flow is smoother and more robust.
- 🔁 **Signout Redirect Flow Improved**: Logging out now redirects more reliably, reducing confusion and making session management seamless.

## [0.6.9] - 2025-05-10

### Added

- 📝 **Edit Attached Images/Files in Messages**: You can now easily edit your sent messages by removing attached files—streamlining document management, correcting mistakes on the fly, and keeping your chats clutter-free.
- 🚨 **Clear Alerts for Private Task Models**: When interacting with private task models, the UI now clearly alerts you—making it easier to understand resource availability and access, reducing confusion during workflow setup.

### Fixed

- 🛡️ **Confirm Dialog Focus Trap Reliability**: The focus now stays correctly within confirmation dialogs, ensuring keyboard navigation and accessibility is seamless and preventing accidental operations—especially helpful during critical or rapid workflows.
- 💬 **Temporary Chat Admin Controls & Session Cleanliness**: Admins are now able to properly enable temporary chat mode without errors, and previous session prompts or tool selections no longer carry over—delivering a fresh, predictable, and consistent temporary chat experience every time.
- 🤖 **External Reranker Integration Functionality Restored**: External reranker integrations now work correctly, allowing you to fully leverage advanced ranking services for sharper, more relevant search results in your RAG and knowledge base workflows.

## [0.6.8] - 2025-05-10

### Added

- 🏆 **External Reranker Support for Knowledge Base Search**: Supercharge your Retrieval-Augmented Generation (RAG) workflows with the new External Reranker integration; easily plug in advanced reranking services via the UI to deliver sharper and more relevant search results, accelerating research and insight discovery.
- 📤 **Unstylized PDF Export Option (Reduced File Size)**: When exporting chat transcripts or documents, you can now choose an unstylized PDF export for snappier downloads, minimal file size, and clean data archiving—perfect for large-scale storage or sharing.
- 📝 **Vazirmatn Font for Persian & Arabic**: Arabic and Persian users will now see their text beautifully rendered with the specialized Vazirmatn font for an improved localized reading experience.
- 🏷️ **SharePoint Tenant ID Support for OneDrive**: You can now specify a SharePoint tenant ID in OneDrive settings for seamless authentication and granular enterprise integration.
- 👤 **Refresh OAuth Profile Picture**: Your OAuth profile picture now updates in real-time, ensuring your presence and avatar always match your latest identity across integrated platforms.
- 🔧 **Milvus Configuration Improvements**: Configure index and metric types for Milvus directly within settings; take full control of your vector database for more accurate and robust AI search experiences.
- 🛡️ **S3 Tagging Toggle for Compatibility**: Optional S3 tagging via an environment toggle grants full compatibility with all storage backends—including those that don’t support tagging like Cloudflare R2—ensuring error-free attachment and document management.
- 👨‍🦯 **Icon Button Accessibility Improvements**: Key interactive icon-buttons now include aria-labels and ARIA descriptions, so screen readers provide precise guidance about what action each button performs for improved accessibility.
- ♿ **Enhanced Accessibility with Modal Focus Trap**: Modal dialogs and pop-ups now feature a focus trap and improved ARIA roles, ensuring seamless navigation and screen reader support—making the interface friendlier for everyone, including keyboard and assistive tech users.
- 🏃 **Improved Admin User List Loading Indicator**: The user list loading experience is now clearer and more responsive in the admin panel.
- 🧑‍🤝‍🧑 **Larger Admin User List Page Size**: Admins can now manage up to 30 users per page in the admin interface, drastically reducing pagination and making large user teams easier and faster to manage.
- 🌠 **Default Code Interpreter Prompt Clarified**: The built-in code interpreter prompt is now more explicit, preventing AI from wrapping code in Markdown blocks when not needed—ensuring properly formatted code runs as intended every time.
- 🧾 **Improved Default Title Generation Prompt Template**: Title generation now uses a robust template for reliable JSON output, improving chat organization and searchability.
- 🔗 **Support Jupyter Notebooks with Non-Root Base URLs**: Notebook-based code execution now supports non-root deployed Jupyter servers, granting full flexibility for hybrid or multi-user setups.
- 📰 **UI Scrollbar Always Visible for Overflow Tools**: When available tools overflow the display, the scrollbar is now always visible and there’s a handy "show all" toggle, making navigation of large toolsets snappier and more intuitive.
- 🛠️ **General Backend Refactoring for Stability**: Multiple under-the-hood improvements have been made across backend components, ensuring smoother performance, fewer errors, and a more reliable overall experience for all users.
- 🚀 **Optimized Web Search for Faster Results**: Web search speed and performance have been significantly enhanced, delivering answers and sources in record time to accelerate your research-heavy workflows.
- 💡 **More Supported Languages**: Expanded language support ensures an even wider range of users can enjoy an intuitive and natural interface in their native tongue.

### Fixed

- 🏃‍♂️ **Exhausting Workers in Nginx Reverse Proxy Due to Websocket Fix**: Websocket sessions are now fully compatible behind Nginx, eliminating worker exhaustion and restoring 24/7 reliability for real-time chats even in complex deployments.
- 🎤 **Audio Transcription Issue with OpenAI Resolved**: OpenAI-based audio transcription now handles WebM and newer formats without error, ensuring seamless voice-to-text workflows every time.
- 👉 **Message Input RTL Issue Fixed**: The chat message input now displays correctly for right-to-left languages, creating a flawless typing and reading experience for Arabic, Hebrew, and more.
- 🀄 **Katex: Proper Rendering of Chinese Characters Next to Math**: Math formulas now render perfectly even when directly adjacent to Chinese (CJK) characters, improving visual clarity for multilingual teams and cross-language documents.
- 🔂 **Duplicate Web Search URLs Eliminated**: Search results now reliably filter out URL duplicates, so your knowledge and search citations are always clean, trimmed, and easy to review.
- 📄 **Markdown Rendering Fixed in Knowledge Bases**: Markdown is now displayed correctly within knowledge bases, enabling better formatting and clarity of information-rich files.
- 🗂️ **LDAP Import/Loading Issue Resolved**: LDAP user imports process correctly, ensuring smooth onboarding and access without interruption.
- 🌎 **Pinecone Batch Operations and Async Safety**: All Pinecone operations (batch insert, upsert, delete) now run efficiently and safely in an async environment, boosting performance and preventing slowdowns in large-scale RAG jobs.

## [0.6.7] - 2025-05-07

### Added

- 🌐 **Custom Azure TTS API URL Support Added**: You can now define a custom Azure Text-to-Speech endpoint—enabling flexibility for enterprise deployments and regional compliance.
- ⚙️ **TOOL_SERVER_CONNECTIONS Environment Variable Suppor**: Easily configure and deploy tool servers via environment variables, streamlining setup and enabling faster enterprise provisioning.
- 👥 **Enhanced OAuth Group Handling as String or List**: OAuth group data can now be passed as either a list or a comma-separated string, improving compatibility with varied identity provider formats and reducing onboarding friction.

### Fixed

- 🧠 **Embedding with Ollama Proxy Endpoints Restored**: Fixed an issue where missing API config broke embedding for proxied Ollama models—ensuring consistent performance and compatibility.
- 🔐 **OIDC OAuth Login Issue Resolved**: Users can once again sign in seamlessly using OpenID Connect-based OAuth, eliminating login interruptions and improving reliability.
- 📝 **Notes Feature Access Fixed for Non-Admins**: Fixed an issue preventing non-admin users from accessing the Notes feature, restoring full cross-role collaboration capabilities.
- 🖼️ **Tika Loader Image Extraction Problem Resolved**: Ensured TikaLoader now processes 'extract_images' parameter correctly, restoring complete file extraction functionality in document workflows.
- 🎨 **Automatic1111 Image Model Setting Applied Properly**: Fixed an issue where switching to a specific image model via the UI wasn’t reflected in generation, re-enabling full visual creativity control.
- 🏷️ **Multiple XML Tags in Messages Now Parsed Correctly**: Fixed parsing issues when messages included multiple XML-style tags, ensuring clean and unbroken rendering of rich content in chats.
- 🖌️ **OpenAI Image Generation Issues Resolved**: Resolved broken image output when using OpenAI’s image generation, ensuring fully functional visual creation workflows.
- 🔎 **Tool Server Settings UI Privacy Restored**: Prevented restricted users from accessing tool server settings via search—restoring tight permissions control and safeguarding sensitive configurations.
- 🎧 **WebM Audio Transcription Now Supported**: Fixed an issue where WebM files failed during audio transcription—these formats are now fully supported, ensuring smoother voice note workflows and broader file compatibility.

## [0.6.6] - 2025-05-05

### Added

- 📝 **AI-Enhanced Notes (With Audio Transcription)**: Effortlessly create notes, attach meeting or voice audio, and let the AI instantly enhance, summarize, or refine your notes using audio transcriptions—making your documentation smarter, cleaner, and more insightful with minimal effort.
- 🔊 **Meeting Audio Recording & Import**: Seamlessly record audio from your meetings or capture screen audio and attach it to your notes—making it easier to revisit, annotate, and extract insights from important discussions.
- 📁 **Import Markdown Notes Effortlessly**: Bring your existing knowledge library into Open WebUI by importing your Markdown notes, so you can leverage all advanced note management and AI features right away.
- 👥 **Notes Permissions by User Group**: Fine-tune access and editing rights for notes based on user roles or groups, so you can delegate writing or restrict sensitive information as needed.
- ☁️ **OneDrive & SharePoint Integration**: Keep your content in sync by connecting notes and files directly with OneDrive or SharePoint—unlocking fast enterprise import/export and seamless collaboration with your existing workflows.
- 🗂️ **Paginated User List in Admin Panel**: Effortlessly manage and search through large teams via the new paginated user list—saving time and streamlining user administration in big organizations.
- 🕹️ **Granular Chat Share & Export Permissions**: Enjoy enhanced control over who can share or export chats, enabling tighter governance and privacy in team and enterprise settings.
- 🛑 **User Role Change Confirmation Dialog**: Reduce accidental privilege changes with a required confirmation step before updating user roles—improving security and preventing costly mistakes in team management.
- 🚨 **Audit Log for Failed Login Attempts**: Quickly detect unauthorized access attempts or troubleshoot user login problems with detailed logs of failed authentication right in the audit trail.
- 💡 **Dedicated 'Generate Title' Button for Chats**: Swiftly organize every conversation—tap the new button to let AI create relevant, clear titles for all your chats, saving time and reducing clutter.
- 💬 **Notification Sound Always-On Option**: Take control of your notifications by setting sound alerts to always play—helping you stay on top of important updates in busy environments.
- 🆔 **S3 File Tagging Support**: Uploaded files to S3 now include tags for better organization, searching, and integration with your file management policies.
- 🛡️ **OAuth Blocked Groups Support**: Gain more control over group-based access by explicitly blocking specified OAuth groups—ideal for complex identity or security requirements.
- 🚀 **Optimized Faster Web Search & Multi-Threaded Queries**: Enjoy dramatically faster web search and RAG (retrieval augmented generation) with revamped multi-threaded search—get richer, more accurate results in less time.
- 🔍 **All-Knowledge Parallel Search**: Searches across your entire knowledge base now happen in parallel even in non-hybrid mode, speeding up responses and improving knowledge accuracy for every question.
- 🌐 **New Firecrawl & Yacy Web Search Integrations**: Expand your world of information with two new advanced search engines—Firecrawl for deeper web insight and Yacy for decentralized, privacy-friendly search capabilities.
- 🧠 **Configurable Docling OCR Engine & Language**: Use environment variables to fine-tune Docling OCR engine and supported languages for smarter, more tailored document extraction and RAG workflows.
- 🗝️ **Enhanced Sentence Transformers Configuration**: Added new environment variables for easier set up and advanced customization of Sentence Transformers—ensuring best fit for your embedding needs.
- 🌲 **Pinecone Vector Database Integration**: Index, search, and manage knowledge at enterprise scale with full native support for Pinecone as your vector database—effortlessly handle even the biggest document sets.
- 🔄 **Automatic Requirements Installation for Tools & Functions**: Never worry about lost dependencies on restart—external function and tool requirements are now auto-installed at boot, ensuring tools always “just work.”
- 🔒 **Automatic Sign-Out on Token Expiry**: Security is smarter—users are now automatically logged out if their authentication token expires, protecting sensitive content and ensuring compliance without disruption.
- 🎬 **Automatic YouTube Embed Detection**: Paste YouTube links and see instant in-chat video embeds—no more manual embedding, making knowledge sharing and media consumption even easier for every team.
- 🔄 **Expanded Language & Locale Support**: Translations for Danish, French, Russian, Traditional Chinese, Simplified Chinese, Thai, Catalan, German, and Korean have been upgraded, offering smoother, more natural user experiences across the platform.

### Fixed

- 🔒 **Tighter HTML Token Security**: HTML rendering is now restricted to admin-uploaded tokens only, reducing any risk of XSS and keeping your data safe.
- 🔐 **Refined HTML Security and Token Handling**: Further hardened how HTML tokens and content are handled, guaranteeing even stronger resistance to security vulnerabilities and attacks.
- 🔏 **Correct Model Usage with Ollama Proxy Prefixes**: Enhanced model reference handling so proxied models in Ollama always download and run correctly—even when using custom prefixes.
- 📥 **Video File Upload Handling**: Prevented video files from being misclassified as text, fixing bugs with uploads and ensuring media files work as expected.
- 🔄 **No More Dependent WebSocket Sequential Delays**: Streamlined WebSocket operation to prevent delays and maintain snappy real-time collaboration, especially in multi-user environments.
- 🛠️ **More Robust Action Module Execution**: Multiple actions in a module now trigger as designed, increasing automation and scripting flexibility.
- 📧 **Notification Webhooks**: Ensured that notification webhooks are always sent for user events, even when the user isn’t currently active.
- 🗂️ **Smarter Knowledge Base Reindexing**: Knowledge reindexing continues even when corrupt or missing collections are encountered, keeping your search features running reliably.
- 🏷️ **User Import with Profile Images**: When importing users, their profile images now come along—making onboarding and collaboration visually clearer from day one.
- 💬 **OpenAI o-Series Universal Support**: All OpenAI o-series models are now seamlessly recognized and supported, unlocking more advanced capabilities and model choices for every workflow.

### Changed

- 📜 **Custom License Update & Contributor Agreement**: Open WebUI now operates under a custom license with Contributor License Agreement required by default—see https://docs.openwebui.com/license/ for details, ensuring sustainable open innovation for the community.
- 🔨 **CUDA Docker Images Updated to 12.8**: Upgraded CUDA image support for faster, more compatible model inference and futureproof GPU performance in your AI infrastructure.
- 🧱 **General Backend Refactoring for Reliability**: Continuous stability improvements streamline backend logic, reduce errors, and lay a stronger foundation for the next wave of feature releases—all under the hood for a more dependable WebUI.

## [0.6.5] - 2025-04-14

### Added

- 🛂 **Granular Voice Feature Permissions Per User Group**: Admins can now separately manage access to Speech-to-Text (record voice), Text-to-Speech (read aloud), and Tool Calls for each user group—giving teams tighter control over voice features and enhanced governance across roles.
- 🗣️ **Toggle Voice Activity Detection (VAD) for Whisper STT**: New environment variable lets you enable/disable VAD filtering with built-in Whisper speech-to-text, giving you flexibility to optimize for different audio quality and response accuracy levels.
- 📋 **Copy Formatted Response Mode**: You can now enable “Copy Formatted” in Settings > Interface to copy AI responses exactly as styled (with rich formatting, links, and structure preserved), making it faster and cleaner to paste into documents, emails, or reports.
- ⚙️ **Backend Stability and Performance Enhancements**: General backend refactoring improves system resilience, consistency, and overall reliability—offering smoother performance across workflows whether chatting, generating media, or using external tools.
- 🌎 **Translation Refinements Across Multiple Languages**: Updated translations deliver smoother language localization, clearer labels, and improved international usability throughout the UI—ensuring a better experience for non-English speakers.

### Fixed

- 🛠️ **LDAP Login Reliability Restored**: Resolved a critical issue where some LDAP setups failed due to attribute parsing—ensuring consistent, secure, and seamless user authentication across enterprise deployments.
- 🖼️ **Image Generation in Temporary Chats Now Works Properly**: Fixed a bug where image outputs weren’t generated during temporary chats—visual content can now be used reliably in all chat modes without interruptions.

## [0.6.4] - 2025-04-12

### Fixed

- 🛠️ **RAG_TEMPLATE Display Issue Resolved**: Fixed a formatting problem where the custom RAG_TEMPLATE wasn't correctly rendered in the interface—ensuring that custom retrieval prompts now appear exactly as intended for more reliable prompt engineering.

## [0.6.3] - 2025-04-12

### Added

- 🧪 **Auto-Artifact Detection Toggle**: Automatically detects artifacts in results—but now you can disable this behavior under advanced settings for full control.
- 🖼️ **Widescreen Mode for Shared Chats**: Shared link conversations now support widescreen layouts—perfect for presentations or easier review across wider displays.
- 🔁 **Reindex Knowledge Files on Demand**: Admins can now trigger reindexing of all knowledge files after changing embeddings—ensuring immediate alignment with new models for optimal RAG performance.
- 📄 **OpenAPI YAML Format Support**: External tools can now use YAML-format OpenAPI specs—making integration simpler for developers familiar with YAML-based configurations.
- 💬 **Message Content Copy Behavior**: Copy action now excludes 'details' tags—streamlining clipboard content when sharing or pasting summaries elsewhere.
- 🧭 **Sougou Web Search Integration**: New search engine option added—enhancing global relevance and diversity of search sources for multilingual users.
- 🧰 **Frontend Web Loader Engine Configuration**: Admins can now set preferred web loader engine for RAG workflows directly from the frontend—offering more control across setups.
- 👥 **Multi-Model Chat Permission Control**: Admins can manage access to multi-model chats per user group—allowing tighter governance in team environments.
- 🧱 **Persistent Configuration Can Be Disabled**: New environment variable lets advanced users and hosts turn off persistent configs—ideal for volatile or stateless deployments.
- 🧠 **Elixir Code Highlighting Support**: Elixir syntax is now beautifully rendered in code blocks—perfect for developers using this language in AI or automation projects.
- 🌐 **PWA External Manifest URL Support**: You can now define an external manifest.json—integrate Open WebUI seamlessly in managed or proxy-based PWA environments like Cloudflare Zero Trust.
- 🧪 **Azure AI Speech-to-Text Provider Integration**: Easily transcribe large audio files (up to 200MB) with high accuracy using Microsoft's Azure STT—fully configurable in Audio Settings.
- 🔏 **PKCE (Code Challenge Method) Support for OIDC**: Enhance your OIDC login security with Proof Key for Code Exchange—ideal for zero-trust and native client apps.
- ✨ **General UI/UX Enhancements**: Numerous refinements across layout, styling, and tool interactions—reducing visual noise and improving overall usability across key workflows.
- 🌍 **Translation Updates Across Multiple Languages**: Refined Catalan, Russian, Chinese (Simplified & Traditional), Hungarian, and Spanish translations for clearer navigation and instructions globally.

### Fixed

- 💥 **Chat Completion Error with Missing Models Resolved**: Fixed internal server error when referencing a model that doesn’t exist—ensuring graceful fallback and clear error guidance.
- 🔧 **Correct Knowledge Base Citations Restored**: Citations generated by RAG workflows now show accurate references—ensuring verifiability in outputs from sourced content.
- 🎙️ **Broken OGG/WebM Audio Upload Handling for OpenAI Fixed**: Uploading OGG or WebM files now converts properly to WAV before transcription—restoring accurate AI speech recognition workflows.
- 🔐 **Tool Server 'Session' Authentication Restored**: Previously broken session auth on external tool servers is now fully functional—ensuring secure and seamless access to connected tools.
- 🌐 **Folder-Based Chat Rename Now Updates Correctly**: Renaming chats in folders now reflects instantly everywhere—improving chat organization and clarity.
- 📜 **KaTeX Overflow Displays Fixed**: Math expressions now stay neatly within message bounds—preserving layout consistency even with long formulas.
- 🚫 **Stopping Ongoing Chat Fixed**: You can now return to an active (ongoing) chat and stop generation at any time—ensuring full control over sessions.
- 🔧 **TOOL_SERVERS / TOOL_SERVER_CONNECTIONS Indexing Issue Fixed**: Fixed a mismatch between tool lists and their access paths—restoring full function and preventing confusion in tool management.
- 🔐 **LDAP Login Handles Multiple Emails**: When LDAP returns multiple email attributes, the first valid one is now used—ensuring login success and account consistency.
- 🧩 **Model Visibility Toggle Fix**: Toggling model visibility now works even for untouched models—letting admins smoothly manage user access across base models.
- ⚙️ **Cross-Origin manifest.json Now Loads Properly**: Compatibility issues with Cloudflare Zero Trust (and others) resolved, allowing manifest.json to load behind authenticated proxies.

### Changed

- 🔒 **Default Access Scopes Set to Private for All Resources**: Models, tools, and knowledge are now private by default when created—ensuring better baseline security and visibility controls.
- 🧱 **General Backend Refactoring for Stability**: Numerous invisible improvements enhance backend scalability, security, and maintainability—powering upcoming features with a stronger foundation.
- 🧩 **Stable Dependency Upgrades**: Updated key platform libraries—Chromadb (0.6.3), pgvector (0.4.0), Azure Identity (1.21.0), and Youtube Transcript API (1.0.3)—for improved compatibility, functionality, and security.

## [0.6.2] - 2025-04-06

### Added

- 🌍 **Improved Global Language Support**: Expanded and refined translations across multiple languages to enhance clarity and consistency for international users.

### Fixed

- 🛠️ **Accurate Tool Descriptions from OpenAPI Servers**: External tools now use full endpoint descriptions instead of summaries when generating tool specifications—helping AI models understand tool purpose more precisely and choose the right tool more accurately in tool workflows.
- 🔧 **Precise Web Results Source Attribution**: Fixed a key issue where all web search results showed the same source ID—now each result gets its correct and distinct source, ensuring accurate citations and traceability.
- 🔍 **Clean Web Search Retrieval**: Web search now retains only results from URLs where real content was successfully fetched—improving accuracy and removing empty or broken links from citations.
- 🎵 **Audio File Upload Response Restored**: Resolved an issue where uploading audio files did not return valid responses, restoring smooth file handling for transcription and audio-based workflows.

### Changed

- 🧰 **General Backend Refactoring**: Multiple behind-the-scenes improvements streamline backend performance, reduce complexity, and ensure a more stable, maintainable system overall—making everything smoother without changing your workflow.

## [0.6.1] - 2025-04-05

### Added

- 🛠️ **Global Tool Servers Configuration**: Admins can now centrally configure global external tool servers from Admin Settings > Tools, allowing seamless sharing of tool integrations across all users without manual setup per user.
- 🔐 **Direct Tool Usage Permission for Users**: Introduced a new user-level permission toggle that grants non-admin users access to direct external tools, empowering broader team collaboration while maintaining control.
- 🧠 **Mistral OCR Content Extraction Support**: Added native support for Mistral OCR as a high-accuracy document loader, drastically improving text extraction from scanned documents in RAG workflows.
- 🖼️ **Tools Indicator UI Redesign**: Enhanced message input now smartly displays both built-in and external tools via a unified dropdown, making it simpler and more intuitive to activate tools during conversations.
- 📄 **RAG Prompt Improved and More Coherent**: Default RAG system prompt has been revised to be more clear and citation-focused—admins can leave the template field empty to use this new gold-standard prompt.
- 🧰 **Performance & Developer Improvements**: Major internal restructuring of several tool-related components, simplifying styling and merging external/internal handling logic, resulting in better maintainability and performance.
- 🌍 **Improved Translations**: Updated translations for Tibetan, Polish, Chinese (Simplified & Traditional), Arabic, Russian, Ukrainian, Dutch, Finnish, and French to improve clarity and consistency across the interface.

### Fixed

- 🔑 **External Tool Server API Key Bug Resolved**: Fixed a critical issue where authentication headers were not being sent when calling tools from external OpenAPI tool servers, ensuring full security and smooth tool operations.
- 🚫 **Conditional Export Button Visibility**: UI now gracefully hides export buttons when there's nothing to export in models, prompts, tools, or functions, improving visual clarity and reducing confusion.
- 🧪 **Hybrid Search Failure Recovery**: Resolved edge case in parallel hybrid search where empty or unindexed collections caused backend crashes—these are now cleanly skipped to ensure system stability.
- 📂 **Admin Folder Deletion Fix**: Addressed an issue where folders created in the admin workspace couldn't be deleted, restoring full organizational flexibility for admins.
- 🔐 **Improved Generic Error Feedback on Login**: Authentication errors now show simplified, non-revealing messages for privacy and improved UX, especially with federated logins.
- 📝 **Tool Message with Images Improved**: Enhanced how tool-generated messages with image outputs are shown in chat, making them more readable and consistent with the overall UI design.
- ⚙️ **Auto-Exclusion for Broken RAG Collections**: Auto-skips document collections that fail to fetch data or return "None", preventing silent errors and streamlining retrieval workflows.
- 📝 **Docling Text File Handling Fix**: Fixed file parsing inconsistency that broke docling-based RAG functionality for certain plain text files, ensuring wider file compatibility.

## [0.6.0] - 2025-03-31

### Added

- 🧩 **External Tool Server Support via OpenAPI**: Connect Open WebUI to any OpenAPI-compatible REST server instantly—offering immediate integration with thousands of developer tools, SDKs, and SaaS systems for powerful extensibility. Learn more: https://github.com/open-webui/openapi-servers
- 🛠️ **MCP Server Support via MCPO**: You can now convert and expose your internal MCP tools as interoperable OpenAPI HTTP servers within Open WebUI for seamless, plug-n-play AI toolchain creation. Learn more: https://github.com/open-webui/mcpo
- 📨 **/messages Chat API Endpoint Support**: For power users building external AI systems, new endpoints allow precise control of messages asynchronously—feed long-running external responses into Open WebUI chats without coupling with the frontend.
- 📝 **Client-Side PDF Generation**: PDF exports are now generated fully client-side for drastically improved output quality—perfect for saving conversations or documents.
- 💼 **Enforced Temporary Chats Mode**: Admins can now enforce temporary chat sessions by default to align with stringent data retention and compliance requirements.
- 🌍 **Public Resource Sharing Permission Controls**: Fine-grained user group permissions now allow enabling/disabling public sharing for models, knowledge, prompts, and tools—ideal for privacy, team control, and internal deployments.
- 📦 **Custom pip Options for Tools/Functions**: You can now specify custom pip installation options with "PIP_OPTIONS", "PIP_PACKAGE_INDEX_OPTIONS" environment variables—improving compatibility, support for private indexes, and better control over Python environments.
- 🔢 **Editable Message Counter**: You can now double-click the message count number and jump straight to editing the index—quickly navigate complex chats or regenerate specific messages precisely.
- 🧠 **Embedding Prefix Support Added**: Add custom prefixes to your embeddings for instruct-style tokens, enabling stronger model alignment and more consistent RAG performance.
- 🙈 **Ability to Hide Base Models**: Optionally hide base models from the UI, helping users streamline model visibility and limit access to only usable endpoints..
- 📚 **Docling Content Extraction Support**: Open WebUI now supports Docling as a content extraction engine, enabling smarter and more accurate parsing of complex file formats—ideal for advanced document understanding and Retrieval-Augmented Generation (RAG) workflows.
- 🗃️ **Redis Sentinel Support Added**: Enhance deployment redundancy with support for Redis Sentinel for highly available, failover-safe Redis-based caching or pub/sub.
- 📚 **JSON Schema Format for Ollama**: Added support for defining the format using JSON schema in Ollama-compatible models, improving flexibility and validation of model outputs.
- 🔍 **Chat Sidebar Search "Clear” Button**: Quickly clear search filters in chat sidebar using the new ✖️ button—streamline your chat navigation with one click.
- 🗂️ **Auto-Focus + Enter Submit for Folder Name**: When creating a new folder, the system automatically enters rename mode with name preselected—simplifying your org workflow.
- 🧱 **Markdown Alerts Rendering**: Blockquotes with syntax hinting (e.g. ⚠️, ℹ️, ✅) now render styled Markdown alert banners, making messages and documentation more visually structured.
- 🔁 **Hybrid Search Runs in Parallel Now**: Hybrid (BM25 + embedding) search components now run in parallel—dramatically reducing response times and speeding up document retrieval.
- 📋 **Cleaner UI for Tool Call Display**: Optimized the visual layout of called tools inside chat messages for better clarity and reduced visual clutter.
- 🧪 **Playwright Timeout Now Configurable**: Default timeout for Playwright processes is now shorter and adjustable via environment variables—making web scraping more robust and tunable to environments.
- 📈 **OpenTelemetry Support for Observability**: Open WebUI now integrates with OpenTelemetry, allowing you to connect with tools like Grafana, Jaeger, or Prometheus for detailed performance insights and real-time visibility—entirely opt-in and fully self-hosted. Even if enabled, no data is ever sent to us, ensuring your privacy and ownership over all telemetry data.
- 🛠 **General UI Enhancements & UX Polish**: Numerous refinements across sidebar, code blocks, modal interactions, button alignment, scrollbar visibility, and folder behavior improve overall fluidity and usability of the interface.
- 🧱 **General Backend Refactoring**: Numerous backend components have been refactored to improve stability, maintainability, and performance—ensuring a more consistent and reliable system across all features.
- 🌍 **Internationalization Language Support Updates**: Added Estonian and Galician languages, improved Spanish (fully revised), Traditional Chinese, Simplified Chinese, Turkish, Catalan, Ukrainian, and German for a more localized and inclusive interface.

### Fixed

- 🧑‍💻 **Firefox Input Height Bug**: Text input in Firefox now maintains proper height, ensuring message boxes look consistent and behave predictably.
- 🧾 **Tika Blank Line Bug**: PDFs processed with Apache Tika 3.1.0.0 no longer introduce excessive blank lines—improving RAG output quality and visual cleanliness.
- 🧪 **CSV Loader Encoding Issues**: CSV files with unknown encodings now automatically detect character sets, resolving import errors in non-UTF-8 datasets.
- ✅ **LDAP Auth Config Fix**: Path to certificate file is now optional for LDAP setups, fixing authentication trouble for users without preconfigured cert paths.
- 📥 **File Deletion in Bypass Mode**: Resolved issue where files couldn’t be deleted from knowledge when “bypass embedding” mode was enabled.
- 🧩 **Hybrid Search Result Sorting & Deduplication Fixed**: Fixed citation and sorting issues in RAG hybrid and reranker modes, ensuring retrieved documents are shown in correct order per score.
- 🧷 **Model Export/Import Broken for a Single Model**: Fixed bug where individual models couldn’t be exported or re-imported, restoring full portability.
- 📫 **Auth Redirect Fix**: Logged-in users are now routed properly without unnecessary login prompts when already authenticated.

### Changed

- 🧠 **Prompt Autocompletion Disabled By Default**: Autocomplete suggestions while typing are now disabled unless explicitly re-enabled in user preferences—reduces distractions while composing prompts for advanced users.
- 🧾 **Normalize Citation Numbering**: Source citations now properly begin from "1" instead of "0"—improving consistency and professional presentation in AI outputs.
- 📚 **Improved Error Handling from Pipelines**: Pipelines now show the actual returned error message from failed tasks rather than generic "Connection closed"—making debugging far more user-friendly.

### Removed

- 🧾 **ENABLE_AUDIT_LOGS Setting Removed**: Deprecated setting “ENABLE_AUDIT_LOGS” has been fully removed—now controlled via “AUDIT_LOG_LEVEL” instead.

## [0.5.20] - 2025-03-05

### Added

- **⚡ Toggle Code Execution On/Off**: You can now enable or disable code execution, providing more control over security, ensuring a safer and more customizable experience.

### Fixed

- **📜 Pinyin Keyboard Enter Key Now Works Properly**: Resolved an issue where the Enter key for Pinyin keyboards was not functioning as expected, ensuring seamless input for Chinese users.
- **🖼️ Web Manifest Loading Issue Fixed**: Addressed inconsistencies with 'site.webmanifest', guaranteeing proper loading and representation of the app across different browsers and devices.
- **📦 Non-Root Container Issue Resolved**: Fixed a critical issue where the UI failed to load correctly in non-root containers, ensuring reliable deployment in various environments.

## [0.5.19] - 2025-03-04

### Added

- **📊 Logit Bias Parameter Support**: Fine-tune conversation dynamics by adjusting the Logit Bias parameter directly in chat settings, giving you more control over model responses.
- **⌨️ Customizable Enter Behavior**: You can now configure Enter to send messages only when combined with Ctrl (Ctrl+Enter) via Settings > Interface, preventing accidental message sends.
- **📝 Collapsible Code Blocks**: Easily collapse long code blocks to declutter your chat, making it easier to focus on important details.
- **🏷️ Tag Selector in Model Selector**: Quickly find and categorize models with the new tag filtering system in the Model Selector, streamlining model discovery.
- **📈 Experimental Elasticsearch Vector DB Support**: Now supports Elasticsearch as a vector database, offering more flexibility for data retrieval in Retrieval-Augmented Generation (RAG) workflows.
- **⚙️ General Reliability Enhancements**: Various stability improvements across the WebUI, ensuring a smoother, more consistent experience.
- **🌍 Updated Translations**: Refined multilingual support for better localization and accuracy across various languages.

### Fixed

- **🔄 "Stream" Hook Activation**: Fixed an issue where the "Stream" hook only worked when globally enabled, ensuring reliable real-time filtering.
- **📧 LDAP Email Case Sensitivity**: Resolved an issue where LDAP login failed due to email case sensitivity mismatches, improving authentication reliability.
- **💬 WebSocket Chat Event Registration**: Fixed a bug preventing chat event listeners from being registered upon sign-in, ensuring real-time updates work properly.

## [0.5.18] - 2025-02-27

### Fixed

- **🌐 Open WebUI Now Works Over LAN in Insecure Context**: Resolved an issue preventing Open WebUI from functioning when accessed over a local network in an insecure context, ensuring seamless connectivity.
- **🔄 UI Now Reflects Deleted Connections Instantly**: Fixed an issue where deleting a connection did not update the UI in real time, ensuring accurate system state visibility.
- **🛠️ Models Now Display Correctly with ENABLE_FORWARD_USER_INFO_HEADERS**: Addressed a bug where models were not visible when ENABLE_FORWARD_USER_INFO_HEADERS was set, restoring proper model listing.

## [0.5.17] - 2025-02-27

### Added

- **🚀 Instant Document Upload with Bypass Embedding & Retrieval**: Admins can now enable "Bypass Embedding & Retrieval" in Admin Settings > Documents, significantly speeding up document uploads and ensuring full document context is retained without chunking.
- **🔎 "Stream" Hook for Real-Time Filtering**: The new "stream" hook allows dynamic real-time message filtering. Learn more in our documentation (https://docs.openwebui.com/features/plugin/functions/filter).
- **☁️ OneDrive Integration**: Early support for OneDrive storage integration has been introduced, expanding file import options.
- **📈 Enhanced Logging with Loguru**: Backend logging has been improved with Loguru, making debugging and issue tracking far more efficient.
- **⚙️ General Stability Enhancements**: Backend and frontend refactoring improves performance, ensuring a smoother and more reliable user experience.
- **🌍 Updated Translations**: Refined multilingual support for better localization and accuracy across various languages.

### Fixed

- **🔄 Reliable Model Imports from the Community Platform**: Resolved import failures, allowing seamless integration of community-shared models without errors.
- **📊 OpenAI Usage Statistics Restored**: Fixed an issue where OpenAI usage metrics were not displaying correctly, ensuring accurate tracking of usage data.
- **🗂️ Deduplication for Retrieved Documents**: Documents retrieved during searches are now intelligently deduplicated, meaning no more redundant results—helping to keep information concise and relevant.

### Changed

- **📝 "Full Context Mode" Renamed for Clarity**: The "Full Context Mode" toggle in Web Search settings is now labeled "Bypass Embedding & Retrieval" for consistency across the UI.

## [0.5.16] - 2025-02-20

### Fixed

- **🔍 Web Search Retrieval Restored**: Resolved a critical issue that broke web search retrieval by reverting deduplication changes, ensuring complete and accurate search results once again.

## [0.5.15] - 2025-02-20

### Added

- **📄 Full Context Mode for Local Document Search (RAG)**: Toggle full context mode from Admin Settings > Documents to inject entire document content into context, improving accuracy for models with large context windows—ideal for deep context understanding.
- **🌍 Smarter Web Search with Agentic Workflows**: Web searches now intelligently gather and refine multiple relevant terms, similar to RAG handling, delivering significantly better search results for more accurate information retrieval.
- **🔎 Experimental Playwright Support for Web Loader**: Web content retrieval is taken to the next level with Playwright-powered scraping for enhanced accuracy in extracted web data.
- **☁️ Experimental Azure Storage Provider**: Early-stage support for Azure Storage allows more cloud storage flexibility directly within Open WebUI.
- **📊 Improved Jupyter Code Execution with Plots**: Interactive coding now properly displays inline plots, making data visualization more seamless inside chat interactions.
- **⏳ Adjustable Execution Timeout for Jupyter Interpreter**: Customize execution timeout (default: 60s) for Jupyter-based code execution, allowing longer or more constrained execution based on your needs.
- **▶️ "Running..." Indicator for Jupyter Code Execution**: A visual indicator now appears while code execution is in progress, providing real-time status updates on ongoing computations.
- **⚙️ General Backend & Frontend Stability Enhancements**: Extensive refactoring improves reliability, performance, and overall user experience for a more seamless Open WebUI.
- **🌍 Translation Updates**: Various international translation refinements ensure better localization and a more natural user interface experience.

### Fixed

- **📱 Mobile Hover Issue Resolved**: Users can now edit responses smoothly on mobile without interference, fixing a longstanding hover issue.
- **🔄 Temporary Chat Message Duplication Fixed**: Eliminated buggy behavior where messages were being unnecessarily repeated in temporary chat mode, ensuring a smooth and consistent conversation flow.

## [0.5.14] - 2025-02-17

### Fixed

- **🔧 Critical Import Error Resolved**: Fixed a circular import issue preventing 'override_static' from being correctly imported in 'open_webui.config', ensuring smooth system initialization and stability.

## [0.5.13] - 2025-02-17

### Added

- **🌐 Full Context Mode for Web Search**: Enable highly accurate web searches by utilizing full context mode—ideal for models with large context windows, ensuring more precise and insightful results.
- **⚡ Optimized Asynchronous Web Search**: Web searches now load significantly faster with optimized async support, providing users with quicker, more efficient information retrieval.
- **🔄 Auto Text Direction for RTL Languages**: Automatic text alignment based on language input, ensuring seamless conversation flow for Arabic, Hebrew, and other right-to-left scripts.
- **🚀 Jupyter Notebook Support for Code Execution**: The "Run" button in code blocks can now use Jupyter for execution, offering a powerful, dynamic coding experience directly in the chat.
- **🗑️ Message Delete Confirmation Dialog**: Prevent accidental deletions with a new confirmation prompt before removing messages, adding an additional layer of security to your chat history.
- **📥 Download Button for SVG Diagrams**: SVG diagrams generated within chat can now be downloaded instantly, making it easier to save and share complex visual data.
- **✨ General UI/UX Improvements and Backend Stability**: A refined interface with smoother interactions, improved layouts, and backend stability enhancements for a more reliable, polished experience.

### Fixed

- **🛠️ Temporary Chat Message Continue Button Fixed**: The "Continue Response" button for temporary chats now works as expected, ensuring an uninterrupted conversation flow.

### Changed

- **📝 Prompt Variable Update**: Deprecated square bracket '[]' indicators for prompt variables; now requires double curly brackets '{{}}' for consistency and clarity.
- **🔧 Stability Enhancements**: Error handling improved in chat history, ensuring smoother operations when reviewing previous messages.

## [0.5.12] - 2025-02-13

### Added

- **🛠️ Multiple Tool Calls Support for Native Function Mode**: Functions now can call multiple tools within a single response, unlocking better automation and workflow flexibility when using native function calling.

### Fixed

- **📝 Playground Text Completion Restored**: Addressed an issue where text completion in the Playground was not functioning.
- **🔗 Direct Connections Now Work for Regular Users**: Fixed a bug where users with the 'user' role couldn't establish direct API connections, enabling seamless model usage for all user tiers.
- **⚡ Landing Page Input No Longer Lags with Long Text**: Improved input responsiveness on the landing page, ensuring fast and smooth typing experiences even when entering long messages.
- **🔧 Parameter in Functions Fixed**: Fixed an issue where the reserved parameters wasn’t recognized within functions, restoring full functionality for advanced task-based automation.

## [0.5.11] - 2025-02-13

### Added

- **🎤 Kokoro-JS TTS Support**: A new on-device, high-quality text-to-speech engine has been integrated, vastly improving voice generation quality—everything runs directly in your browser.
- **🐍 Jupyter Notebook Support in Code Interpreter**: Now, you can configure Code Interpreter to run Python code not only via Pyodide but also through Jupyter, offering a more robust coding environment for AI-driven computations and analysis.
- **🔗 Direct API Connections for Private & Local Inference**: You can now connect Open WebUI to your private or localhost API inference endpoints. CORS must be enabled, but this unlocks direct, on-device AI infrastructure support.
- **🔍 Advanced Domain Filtering for Web Search**: You can now specify which domains should be included or excluded from web searches, refining results for more relevant information retrieval.
- **🚀 Improved Image Generation Metadata Handling**: Generated images now retain metadata for better organization and future retrieval.
- **📂 S3 Key Prefix Support**: Fine-grained control over S3 storage file structuring with configurable key prefixes.
- **📸 Support for Image-Only Messages**: Send messages containing only images, facilitating more visual-centric interactions.
- **🌍 Updated Translations**: German, Spanish, Traditional Chinese, and Catalan translations updated for better multilingual support.

### Fixed

- **🔧 OAuth Debug Logs & Username Claim Fixes**: Debug logs have been added for OAuth role and group management, with fixes ensuring proper OAuth username retrieval and claim handling.
- **📌 Citations Formatting & Toggle Fixes**: Inline citation toggles now function correctly, and citations with more than three sources are now fully visible when expanded.
- **📸 ComfyUI Maximum Seed Value Constraint Fixed**: The maximum allowed seed value for ComfyUI has been corrected, preventing unintended behavior.
- **🔑 Connection Settings Stability**: Addressed connection settings issues that were causing instability when saving configurations.
- **📂 GGUF Model Upload Stability**: Fixed upload inconsistencies for GGUF models, ensuring reliable local model handling.
- **🔧 Web Search Configuration Bug**: Fixed issues where web search filters and settings weren't correctly applied.
- **💾 User Settings Persistence Fix**: Ensured user-specific settings are correctly saved and applied across sessions.
- **🔄 OpenID Username Retrieval Enhancement**: Usernames are now correctly picked up and assigned for OpenID Connect (OIDC) logins.

## [0.5.10] - 2025-02-05

### Fixed

- **⚙️ System Prompts Now Properly Templated via API**: Resolved an issue where system prompts were not being correctly processed when used through the API, ensuring template variables now function as expected.
- **📝 '<thinking>' Tag Display Issue Fixed**: Fixed a bug where the 'thinking' tag was disrupting content rendering, ensuring clean and accurate text display.
- **💻 Code Interpreter Stability with Custom Functions**: Addressed failures when using the Code Interpreter with certain custom functions like Anthropic, ensuring smoother execution and better compatibility.

## [0.5.9] - 2025-02-05

### Fixed

- **💡 "Think" Tag Display Issue**: Resolved a bug where the "Think" tag was not functioning correctly, ensuring proper visualization of the model's reasoning process before delivering responses.

## [0.5.8] - 2025-02-05

### Added

- **🖥️ Code Interpreter**: Models can now execute code in real time to refine their answers dynamically, running securely within a sandboxed browser environment using Pyodide. Perfect for calculations, data analysis, and AI-assisted coding tasks!
- **💬 Redesigned Chat Input UI**: Enjoy a sleeker and more intuitive message input with improved feature selection, making it easier than ever to toggle tools, enable search, and interact with AI seamlessly.
- **🛠️ Native Tool Calling Support (Experimental)**: Supported models can now call tools natively, reducing query latency and improving contextual responses. More enhancements coming soon!
- **🔗 Exa Search Engine Integration**: A new search provider has been added, allowing users to retrieve up-to-date and relevant information without leaving the chat interface.
- **🌍 Localized Dates & Times**: Date and time formats now match your system locale, ensuring a more natural, region-specific experience.
- **📎 User Headers for External Embedding APIs**: API calls to external embedding services now include user-related headers.
- **🌍 "Always On" Web Search Toggle**: A new option under Settings > Interface allows users to enable Web Search by default—transform Open WebUI into your go-to search engine, ensuring AI-powered results with every query.
- **🚀 General Performance & Stability**: Significant improvements across the platform for a faster, more reliable experience.
- **🖼️ UI/UX Enhancements**: Numerous design refinements improving readability, responsiveness, and accessibility.
- **🌍 Improved Translations**: Chinese, Korean, French, Ukrainian and Serbian translations have been updated with refined terminologies for better clarity.

### Fixed

- **🔄 OAuth Name Field Fallback**: Resolves OAuth login failures by using the email field as a fallback when a name is missing.
- **🔑 Google Drive Credentials Restriction**: Ensures only authenticated users can access Google Drive credentials for enhanced security.
- **🌐 DuckDuckGo Search Rate Limit Handling**: Fixes issues where users would encounter 202 errors due to rate limits when using DuckDuckGo for web search.
- **📁 File Upload Permission Indicator**: Users are now notified when they lack permission to upload files, improving clarity on system restrictions.
- **🔧 Max Tokens Issue**: Fixes cases where 'max_tokens' were not applied correctly, ensuring proper model behavior.
- **🔍 Validation for RAG Web Search URLs**: Filters out invalid or unsupported URLs when using web-based retrieval augmentation.
- **🖋️ Title Generation Bug**: Fixes inconsistencies in title generation, ensuring proper chat organization.

### Removed

- **⚡ Deprecated Non-Web Worker Pyodide Execution**: Moves entirely to browser sandboxing for better performance and security.

## [0.5.7] - 2025-01-23

### Added

- **🌍 Enhanced Internationalization (i18n)**: Refined and expanded translations for greater global accessibility and a smoother experience for international users.

### Fixed

- **🔗 Connection Model ID Resolution**: Resolved an issue preventing model IDs from registering in connections.
- **💡 Prefix ID for Ollama Connections**: Fixed a bug where prefix IDs in Ollama connections were non-functional.
- **🔧 Ollama Model Enable/Disable Functionality**: Addressed the issue of enable/disable toggles not working for Ollama base models.
- **🔒 RBAC Permissions for Tools and Models**: Corrected incorrect Role-Based Access Control (RBAC) permissions for tools and models, ensuring that users now only access features according to their assigned privileges, enhancing security and role clarity.

## [0.5.6] - 2025-01-22

### Added

- **🧠 Effortful Reasoning Control for OpenAI Models**: Introduced the reasoning_effort parameter in chat controls for supported OpenAI models, enabling users to fine-tune how much cognitive effort a model dedicates to its responses, offering greater customization for complex queries and reasoning tasks.

### Fixed

- **🔄 Chat Controls Loading UI Bug**: Resolved an issue where collapsible chat controls appeared as "loading," ensuring a smoother and more intuitive user experience for managing chat settings.

### Changed

- **🔧 Updated Ollama Model Creation**: Revamped the Ollama model creation method to align with their new JSON payload format, ensuring seamless compatibility and more efficient model setup workflows.

## [0.5.5] - 2025-01-22

### Added

- **🤔 Native 'Think' Tag Support**: Introduced the new 'think' tag support that visually displays how long the model is thinking, omitting the reasoning content itself until the next turn. Ideal for creating a more streamlined and focused interaction experience.
- **🖼️ Toggle Image Generation On/Off**: In the chat input menu, you can now easily toggle image generation before initiating chats, providing greater control and flexibility to suit your needs.
- **🔒 Chat Controls Permissions**: Admins can now disable chat controls access for users, offering tighter management and customization over user interactions.
- **🔍 Web Search & Image Generation Permissions**: Easily disable web search and image generation for specific users, improving workflow governance and security for certain environments.
- **🗂️ S3 and GCS Storage Provider Support**: Scaled deployments now benefit from expanded storage options with Amazon S3 and Google Cloud Storage seamlessly integrated as providers.
- **🎨 Enhanced Model Management**: Reintroduced the ability to download and delete models directly in the admin models settings page to minimize user confusion and aid efficient model management.
- **🔗 Improved Connection Handling**: Enhanced backend to smoothly handle multiple identical base URLs, allowing more flexible multi-instance configurations with fewer hiccups.
- **✨ General UI/UX Refinements**: Numerous tweaks across the WebUI make navigation and usability even more user-friendly and intuitive.
- **🌍 Translation Enhancements**: Various translation updates ensure smoother and more polished interactions for international users.

### Fixed

- **⚡ MPS Functionality for Mac Users**: Fixed MPS support, ensuring smooth performance and compatibility for Mac users leveraging MPS.
- **📡 Ollama Connection Management**: Resolved the issue where deleting all Ollama connections prevented adding new ones.

### Changed

- **⚙️ General Stability Refac**: Backend refactoring delivers a more stable, robust platform.
- **🖥️ Desktop App Preparations**: Ongoing work to support the upcoming Open WebUI desktop app. Follow our progress and updates here: https://github.com/open-webui/desktop

## [0.5.4] - 2025-01-05

### Added

- **🔄 Clone Shared Chats**: Effortlessly clone shared chats to save time and streamline collaboration, perfect for reusing insightful discussions or custom setups.
- **📣 Native Notifications for Channel Messages**: Stay informed with integrated desktop notifications for channel messages, ensuring you never miss important updates while multitasking.
- **🔥 Torch MPS Support**: MPS support for Mac users when Open WebUI is installed directly, offering better performance and compatibility for AI workloads.
- **🌍 Enhanced Translations**: Small improvements to various translations, ensuring a smoother global user experience.

### Fixed

- **🖼️ Image-Only Messages in Channels**: You can now send images without accompanying text or content in channels.
- **❌ Proper Exception Handling**: Enhanced error feedback by ensuring exceptions are raised clearly, reducing confusion and promoting smoother debugging.
- **🔍 RAG Query Generation Restored**: Fixed query generation issues for Retrieval-Augmented Generation, improving retrieval accuracy and ensuring seamless functionality.
- **📩 MOA Response Functionality Fixed**: Addressed an error with the MOA response generation feature.
- **💬 Channel Thread Loading with 50+ Messages**: Resolved an issue where channel threads stalled when exceeding 50 messages, ensuring smooth navigation in active discussions.
- **🔑 API Endpoint Restrictions Resolution**: Fixed a critical bug where the 'API_KEY_ALLOWED_ENDPOINTS' setting was not functioning as intended, ensuring API access is limited to specified endpoints for enhanced security.
- **🛠️ Action Functions Restored**: Corrected an issue preventing action functions from working, restoring their utility for customized automations and workflows.
- **📂 Temporary Chat JSON Export Fix**: Resolved a bug blocking temporary chats from being exported in JSON format, ensuring seamless data portability.

### Changed

- **🎛️ Sidebar UI Tweaks**: Chat folders, including pinned folders, now display below the Chats section for better organization; the "New Folder" button has been relocated to the Chats section for a more intuitive workflow.
- **🏗️ Real-Time Save Disabled by Default**: The 'ENABLE_REALTIME_CHAT_SAVE' setting is now off by default, boosting response speed for users who prioritize performance in high-paced workflows or less critical scenarios.
- **🎤 Audio Input Echo Cancellation**: Audio input now features echo cancellation enabled by default, reducing audio feedback for improved clarity during conversations or voice-based interactions.
- **🔧 General Reliability Improvements**: Numerous under-the-hood enhancements have been made to improve platform stability, boost overall performance, and ensure a more seamless, dependable experience across workflows.

## [0.5.3] - 2024-12-31

### Added

- **💬 Channel Reactions with Built-In Emoji Picker**: Easily express yourself in channel threads and messages with reactions, featuring an intuitive built-in emoji picker for seamless selection.
- **🧵 Threads for Channels**: Organize discussions within channels by creating threads, improving clarity and fostering focused conversations.
- **🔄 Reset Button for SVG Pan/Zoom**: Added a handy reset button to SVG Pan/Zoom, allowing users to quickly return diagrams or visuals to their default state without hassle.
- **⚡ Realtime Chat Save Environment Variable**: Introduced the ENABLE_REALTIME_CHAT_SAVE environment variable. Choose between faster responses by disabling realtime chat saving or ensuring chunk-by-chunk data persistency for critical operations.
- **🌍 Translation Enhancements**: Updated and refined translations across multiple languages, providing a smoother experience for international users.
- **📚 Improved Documentation**: Expanded documentation on functions, including clearer guidance on function plugins and detailed instructions for migrating to v0.5. This ensures users can adapt and harness new updates more effectively. (https://docs.openwebui.com/features/plugin/)

### Fixed

- **🛠️ Ollama Parameters Respected**: Resolved an issue where input parameters for Ollama were being ignored, ensuring precise and consistent model behavior.
- **🔧 Function Plugin Outlet Hook Reliability**: Fixed a bug causing issues with 'event_emitter' and outlet hooks in filter function plugins, guaranteeing smoother operation within custom extensions.
- **🖋️ Weird Custom Status Descriptions**: Adjusted the formatting and functionality for custom user statuses, ensuring they display correctly and intuitively.
- **🔗 Restored API Functionality**: Fixed a critical issue where APIs were not operational for certain configurations, ensuring uninterrupted access.
- **⏳ Custom Pipe Function Completion**: Resolved an issue where chats using specific custom pipe function plugins weren’t finishing properly, restoring consistent chat workflows.
- **✅ General Stability Enhancements**: Implemented various under-the-hood improvements to boost overall reliability, ensuring smoother and more consistent performance across the WebUI.

## [0.5.2] - 2024-12-26

### Added

- **🖊️ Typing Indicators in Channels**: Know exactly who’s typing in real-time within your channels, enhancing collaboration and keeping everyone engaged.
- **👤 User Status Indicators**: Quickly view a user’s status by clicking their profile image in channels for better coordination and availability insights.
- **🔒 Configurable API Key Authentication Restrictions**: Flexibly configure endpoint restrictions for API key authentication, now off by default for a smoother setup in trusted environments.

### Fixed

- **🔧 Playground Functionality Restored**: Resolved a critical issue where the playground wasn’t working, ensuring seamless experimentation and troubleshooting workflows.
- **📊 Corrected Ollama Usage Statistics**: Fixed a calculation error in Ollama’s usage statistics, providing more accurate tracking and insights for better resource management.
- **🔗 Pipelines Outlet Hook Registration**: Addressed an issue where outlet hooks for pipelines weren’t registered, restoring functionality and consistency in pipeline workflows.
- **🎨 Image Generation Error**: Resolved a persistent issue causing errors with 'get_automatic1111_api_auth()' to ensure smooth image generation workflows.
- **🎙️ Text-to-Speech Error**: Fixed the missing argument in Eleven Labs’ 'get_available_voices()', restoring full text-to-speech capabilities for uninterrupted voice interactions.
- **🖋️ Title Generation Issue**: Fixed a bug where title generation was not working in certain cases, ensuring consistent and reliable chat organization.

## [0.5.1] - 2024-12-25

### Added

- **🔕 Notification Sound Toggle**: Added a new setting under Settings > Interface to disable notification sounds, giving you greater control over your workspace environment and focus.

### Fixed

- **🔄 Non-Streaming Response Visibility**: Resolved an issue where non-streaming responses were not displayed, ensuring all responses are now reliably shown in your conversations.
- **🖋️ Title Generation with OpenAI APIs**: Fixed a bug preventing title generation when using OpenAI APIs, restoring the ability to automatically generate chat titles for smoother organization.
- **👥 Admin Panel User List**: Addressed the issue where only 50 users were visible in the admin panel. You can now manage and view all users without restrictions.
- **🖼️ Image Generation Error**: Fixed the issue causing 'get_automatic1111_api_auth()' errors in image generation, ensuring seamless creative workflows.
- **⚙️ Pipeline Settings Loading Issue**: Resolved a problem where pipeline settings were stuck at the loading screen, restoring full configurability in the admin panel.

## [0.5.0] - 2024-12-25

### Added

- **💬 True Asynchronous Chat Support**: Create chats, navigate away, and return anytime with responses ready. Ideal for reasoning models and multi-agent workflows, enhancing multitasking like never before.
- **🔔 Chat Completion Notifications**: Never miss a completed response. Receive instant in-UI notifications when a chat finishes in a non-active tab, keeping you updated while you work elsewhere.
- **🌐 Notification Webhook Integration**: Get alerts via webhooks even when your tab is closed! Configure your webhook URL in Settings > Account and receive timely updates for long-running chats or external integration needs.
- **📚 Channels (Beta)**: Explore Discord/Slack-style chat rooms designed for real-time collaboration between users and AIs. Build bots for channels and unlock asynchronous communication for proactive multi-agent workflows. Opt-in via Admin Settings > General. A Comprehensive Bot SDK tutorial (https://github.com/open-webui/bot) is incoming, so stay tuned!
- **🖼️ Client-Side Image Compression**: Now compress images before upload (Settings > Interface), saving bandwidth and improving performance seamlessly.
- **🛠️ OAuth Management for User Groups**: Enable group-level management via OAuth integration for enhanced control and scalability in collaborative environments.
- **✅ Structured Output for Ollama**: Pass structured data output directly to Ollama, unlocking new possibilities for streamlined automation and precise data handling.
- **📜 Offline Swagger Documentation**: Developer-friendly Swagger API docs are now available offline, ensuring full accessibility wherever you are.
- **📸 Quick Screen Capture Button**: Effortlessly capture your screen with a single click from the message input menu.
- **🌍 i18n Updates**: Improved and refined translations across several languages, including Ukrainian, German, Brazilian Portuguese, Catalan, and more, ensuring a seamless global user experience.

### Fixed

- **📋 Table Export to CSV**: Resolved issues with CSV export where headers were missing or errors occurred due to values with commas, ensuring smooth and reliable data handling.
- **🔓 BYPASS_MODEL_ACCESS_CONTROL**: Fixed an issue where users could see models but couldn’t use them with 'BYPASS_MODEL_ACCESS_CONTROL=True', restoring proper functionality for environments leveraging this setting.

### Changed

- **💡 API Key Authentication Restriction**: Narrowed API key auth permissions to '/api/models' and '/api/chat/completions' for enhanced security and better API governance.
- **⚙️ Backend Overhaul for Performance**: Major backend restructuring; a heads-up that some "Functions" using internal variables may face compatibility issues. Moving forward, websocket support is mandatory to ensure Open WebUI operates seamlessly.

### Removed

- **⚠️ Legacy Functionality Clean-Up**: Deprecated outdated backend systems that were non-essential or overlapped with newer implementations, allowing for a leaner, more efficient platform.

## [0.4.8] - 2024-12-07

### Added

- **🔓 Bypass Model Access Control**: Introduced the 'BYPASS_MODEL_ACCESS_CONTROL' environment variable. Easily bypass model access controls for user roles when access control isn't required, simplifying workflows for trusted environments.
- **📝 Markdown in Banners**: Now supports markdown for banners, enabling richer, more visually engaging announcements.
- **🌐 Internationalization Updates**: Enhanced translations across multiple languages, further improving accessibility and global user experience.
- **🎨 Styling Enhancements**: General UI style refinements for a cleaner and more polished interface.
- **📋 Rich Text Reliability**: Improved the reliability and stability of rich text input across chats for smoother interactions.

### Fixed

- **💡 Tailwind Build Issue**: Resolved a breaking bug caused by Tailwind, ensuring smoother builds and overall system reliability.
- **📚 Knowledge Collection Query Fix**: Addressed API endpoint issues with querying knowledge collections, ensuring accurate and reliable information retrieval.

## [0.4.7] - 2024-12-01

### Added

- **✨ Prompt Input Auto-Completion**: Type a prompt and let AI intelligently suggest and complete your inputs. Simply press 'Tab' or swipe right on mobile to confirm. Available only with Rich Text Input (default setting). Disable via Admin Settings for full control.
- **🌍 Improved Translations**: Enhanced localization for multiple languages, ensuring a more polished and accessible experience for international users.

### Fixed

- **🛠️ Tools Export Issue**: Resolved a critical issue where exporting tools wasn’t functioning, restoring seamless export capabilities.
- **🔗 Model ID Registration**: Fixed an issue where model IDs weren’t registering correctly in the model editor, ensuring reliable model setup and tracking.
- **🖋️ Textarea Auto-Expansion**: Corrected a bug where textareas didn’t expand automatically on certain browsers, improving usability for multi-line inputs.
- **🔧 Ollama Embed Endpoint**: Addressed the /ollama/embed endpoint malfunction, ensuring consistent performance and functionality.

### Changed

- **🎨 Knowledge Base Styling**: Refined knowledge base visuals for a cleaner, more modern look, laying the groundwork for further enhancements in upcoming releases.

## [0.4.6] - 2024-11-26

### Added

- **🌍 Enhanced Translations**: Various language translations improved to make the WebUI more accessible and user-friendly worldwide.

### Fixed

- **✏️ Textarea Shifting Bug**: Resolved the issue where the textarea shifted unexpectedly, ensuring a smoother typing experience.
- **⚙️ Model Configuration Modal**: Fixed the issue where the models configuration modal introduced in 0.4.5 wasn’t working for some users.
- **🔍 Legacy Query Support**: Restored functionality for custom query generation in RAG when using legacy prompts, ensuring both default and custom templates now work seamlessly.
- **⚡ Improved General Reliability**: Various minor fixes improve platform stability and ensure a smoother overall experience across workflows.

## [0.4.5] - 2024-11-26

### Added

- **🎨 Model Order/Defaults Reintroduced**: Brought back the ability to set model order and default models, now configurable via Admin Settings > Models > Configure (Gear Icon).

### Fixed

- **🔍 Query Generation Issue**: Resolved an error in web search query generation, enhancing search accuracy and ensuring smoother search workflows.
- **📏 Textarea Auto Height Bug**: Fixed a layout issue where textarea input height was shifting unpredictably, particularly when editing system prompts.
- **🔑 Ollama Authentication**: Corrected an issue with Ollama’s authorization headers, guaranteeing reliable authentication across all endpoints.
- **⚙️ Missing Min_P Save**: Resolved an issue where the 'min_p' parameter was not being saved in configurations.
- **🛠️ Tools Description**: Fixed a key issue that omitted tool descriptions in tools payload.

## [0.4.4] - 2024-11-22

### Added

- **🌐 Translation Updates**: Refreshed Catalan, Brazilian Portuguese, German, and Ukrainian translations, further enhancing the platform's accessibility and improving the experience for international users.

### Fixed

- **📱 Mobile Controls Visibility**: Resolved an issue where the controls button was not displaying on the new chats page for mobile users, ensuring smoother navigation and functionality on smaller screens.
- **📷 LDAP Profile Image Issue**: Fixed an LDAP integration bug related to profile images, ensuring seamless authentication and a reliable login experience for users.
- **⏳ RAG Query Generation Issue**: Addressed a significant problem where RAG query generation occurred unnecessarily without attached files, drastically improving speed and reducing delays during chat completions.

### Changed

- **⚙️ Legacy Event Emitter Support**: Reintroduced compatibility with legacy "citation" types for event emitters in tools and functions, providing smoother workflows and broader tool support for users.

## [0.4.3] - 2024-11-21

### Added

- **📚 Inline Citations for RAG Results**: Get seamless inline citations for Retrieval-Augmented Generation (RAG) responses using the default RAG prompt. Note: This feature only supports newly uploaded files, improving traceability and providing source clarity.
- **🎨 Better Rich Text Input Support**: Enjoy smoother and more reliable rich text formatting for chats, enhancing communication quality.
- **⚡ Faster Model Retrieval**: Implemented caching optimizations for faster model loading, providing a noticeable speed boost across workflows. Further improvements are on the way!

### Fixed

- **🔗 Pipelines Feature Restored**: Resolved a critical issue that previously prevented Pipelines from functioning, ensuring seamless workflows.
- **✏️ Missing Suffix Field in Ollama Form**: Added the missing "suffix" field to the Ollama generate form, enhancing customization options.

### Changed

- **🗂️ Renamed "Citations" to "Sources"**: Improved clarity and consistency by renaming the "citations" field to "sources" in messages.

## [0.4.2] - 2024-11-20

### Fixed

- **📁 Knowledge Files Visibility Issue**: Resolved the bug preventing individual files in knowledge collections from displaying when referenced with '#'.
- **🔗 OpenAI Endpoint Prefix**: Fixed the issue where certain OpenAI connections that deviate from the official API spec weren’t working correctly with prefixes.
- **⚔️ Arena Model Access Control**: Corrected an issue where arena model access control settings were not being saved.
- **🔧 Usage Capability Selector**: Fixed the broken usage capabilities selector in the model editor.

## [0.4.1] - 2024-11-19

### Added

- **📊 Enhanced Feedback System**: Introduced a detailed 1-10 rating scale for feedback alongside thumbs up/down, preparing for more precise model fine-tuning and improving feedback quality.
- **ℹ️ Tool Descriptions on Hover**: Easily access tool descriptions by hovering over the message input, providing a smoother workflow with more context when utilizing tools.

### Fixed

- **🗑️ Graceful Handling of Deleted Users**: Resolved an issue where deleted users caused workspace items (models, knowledge, prompts, tools) to fail, ensuring reliable workspace loading.
- **🔑 API Key Creation**: Fixed an issue preventing users from creating new API keys, restoring secure and seamless API management.
- **🔗 HTTPS Proxy Fix**: Corrected HTTPS proxy issues affecting the '/api/v1/models/' endpoint, ensuring smoother, uninterrupted model management.

## [0.4.0] - 2024-11-19

### Added

- **👥 User Groups**: You can now create and manage user groups, making user organization seamless.
- **🔐 Group-Based Access Control**: Set granular access to models, knowledge, prompts, and tools based on user groups, allowing for more controlled and secure environments.
- **🛠️ Group-Based User Permissions**: Easily manage workspace permissions. Grant users the ability to upload files, delete, edit, or create temporary chats, as well as define their ability to create models, knowledge, prompts, and tools.
- **🔑 LDAP Support**: Newly introduced LDAP authentication adds robust security and scalability to user management.
- **🌐 Enhanced OpenAI-Compatible Connections**: Added prefix ID support to avoid model ID clashes, with explicit model ID support for APIs lacking '/models' endpoint support, ensuring smooth operation with custom setups.
- **🔐 Ollama API Key Support**: Now manage credentials for Ollama when set behind proxies, including the option to utilize prefix ID for proper distinction across multiple Ollama instances.
- **🔄 Connection Enable/Disable Toggle**: Easily enable or disable individual OpenAI and Ollama connections as needed.
- **🎨 Redesigned Model Workspace**: Freshly redesigned to improve usability for managing models across users and groups.
- **🎨 Redesigned Prompt Workspace**: A fresh UI to conveniently organize and manage prompts.
- **🧩 Sorted Functions Workspace**: Functions are now automatically categorized by type (Action, Filter, Pipe), streamlining management.
- **💻 Redesigned Collaborative Workspace**: Enhanced support for multiple users contributing to models, knowledge, prompts, or tools, improving collaboration.
- **🔧 Auto-Selected Tools in Model Editor**: Tools enabled through the model editor are now automatically selected, whereas previously it only gave users the option to enable the tool, reducing manual steps and enhancing efficiency.
- **🔔 Web Search & Tools Indicator**: A clear indication now shows when web search or tools are active, reducing confusion.
- **🔑 Toggle API Key Auth**: Tighten security by easily enabling or disabling API key authentication option for Open WebUI.
- **🗂️ Agentic Retrieval**: Improve RAG accuracy via smart pre-processing of chat history to determine the best queries before retrieval.
- **📁 Large Text as File Option**: Optionally convert large pasted text into a file upload, keeping the chat interface cleaner.
- **🗂️ Toggle Citations for Models**: Ability to disable citations has been introduced in the model editor.
- **🔍 User Settings Search**: Quickly search for settings fields, improving ease of use and navigation.
- **🗣️ Experimental SpeechT5 TTS**: Local SpeechT5 support added for improved text-to-speech capabilities.
- **🔄 Unified Reset for Models**: A one-click option has been introduced to reset and remove all models from the Admin Settings.
- **🛠️ Initial Setup Wizard**: The setup process now explicitly informs users that they are creating an admin account during the first-time setup, ensuring clarity. Previously, users encountered the login page right away without this distinction.
- **🌐 Enhanced Translations**: Several language translations, including Ukrainian, Norwegian, and Brazilian Portuguese, were refined for better localization.

### Fixed

- **🎥 YouTube Video Attachments**: Fixed issues preventing proper loading and attachment of YouTube videos as files.
- **🔄 Shared Chat Update**: Corrected issues where shared chats were not updating, improving collaboration consistency.
- **🔍 DuckDuckGo Rate Limit Fix**: Addressed issues with DuckDuckGo search integration, enhancing search stability and performance when operating within rate limits.
- **🧾 Citations Relevance Fix**: Adjusted the relevance percentage calculation for citations, so that Open WebUI properly reflect the accuracy of a retrieved document in RAG, ensuring users get clearer insights into sources.
- **🔑 Jina Search API Key Requirement**: Added the option to input an API key for Jina Search, ensuring smooth functionality as keys are now mandatory.

### Changed

- **🛠️ Functions Moved to Admin Panel**: As Functions operate as advanced plugins, they are now accessible from the Admin Panel instead of the workspace.
- **🛠️ Manage Ollama Connections**: The "Models" section in Admin Settings has been relocated to Admin Settings > "Connections" > Ollama Connections. You can now manage Ollama instances via a dedicated "Manage Ollama" modal from "Connections", streamlining the setup and configuration of Ollama models.
- **📊 Base Models in Admin Settings**: Admins can now find all base models, both connections or functions, in the "Models" Admin setting. Global model accessibility can be enabled or disabled here. Models are private by default, requiring explicit permission assignment for user access.
- **📌 Sticky Model Selection for New Chats**: The model chosen from a previous chat now persists when creating a new chat. If you click "New Chat" again from the new chat page, it will revert to your default model.
- **🎨 Design Refactoring**: Overall design refinements across the platform have been made, providing a more cohesive and polished user experience.

### Removed

- **📂 Model List Reordering**: Temporarily removed and will be reintroduced in upcoming user group settings improvements.
- **⚙️ Default Model Setting**: Removed the ability to set a default model for users, will be reintroduced with user group settings in the future.

## [0.3.35] - 2024-10-26

### Added

- **🌐 Translation Update**: Added translation labels in the SearchInput and CreateCollection components and updated Brazilian Portuguese translation (pt-BR)
- **📁 Robust File Handling**: Enhanced file input handling for chat. If the content extraction fails or is empty, users will now receive a clear warning, preventing silent failures and ensuring you always know what's happening with your uploads.
- **🌍 New Language Support**: Introduced Hungarian translations and updated French translations, expanding the platform's language accessibility for a more global user base.

### Fixed

- **📚 Knowledge Base Loading Issue**: Resolved a critical bug where the Knowledge Base was not loading, ensuring smooth access to your stored documents and improving information retrieval in RAG-enhanced workflows.
- **🛠️ Tool Parameters Issue**: Fixed an error where tools were not functioning correctly when required parameters were missing, ensuring reliable tool performance and more efficient task completions.
- **🔗 Merged Response Loss in Multi-Model Chats**: Addressed an issue where responses in multi-model chat workflows were being deleted after follow-up queries, improving consistency and ensuring smoother interactions across models.

## [0.3.34] - 2024-10-26

### Added

- **🔧 Feedback Export Enhancements**: Feedback history data can now be exported to JSON, allowing for seamless integration in RLHF processing and further analysis.
- **🗂️ Embedding Model Lazy Loading**: Search functionality for leaderboard reranking is now more efficient, as embedding models are lazy-loaded only when needed, optimizing performance.
- **🎨 Rich Text Input Toggle**: Users can now switch back to legacy textarea input for chat if they prefer simpler text input, though rich text is still the default until deprecation.
- **🛠️ Improved Tool Calling Mechanism**: Enhanced method for parsing and calling tools, improving the reliability and robustness of tool function calls.
- **🌐 Globalization Enhancements**: Updates to internationalization (i18n) support, further refining multi-language compatibility and accuracy.

### Fixed

- **🖥️ Folder Rename Fix for Firefox**: Addressed a persistent issue where users could not rename folders by pressing enter in Firefox, now ensuring seamless folder management across browsers.
- **🔠 Tiktoken Model Text Splitter Issue**: Resolved an issue where the tiktoken text splitter wasn’t working in Docker installations, restoring full functionality for tokenized text editing.
- **💼 S3 File Upload Issue**: Fixed a problem affecting S3 file uploads, ensuring smooth operations for those who store files on cloud storage.
- **🔒 Strict-Transport-Security Crash**: Resolved a crash when setting the Strict-Transport-Security (HSTS) header, improving stability and security enhancements.
- **🚫 OIDC Boolean Access Fix**: Addressed an issue with boolean values not being accessed correctly during OIDC logins, ensuring login reliability.
- **⚙️ Rich Text Paste Behavior**: Refined paste behavior in rich text input to make it smoother and more intuitive when pasting various content types.
- **🔨 Model Exclusion for Arena Fix**: Corrected the filter function that was not properly excluding models from the arena, improving model management.
- **🏷️ "Tags Generation Prompt" Fix**: Addressed an issue preventing custom "tags generation prompts" from registering properly, ensuring custom prompt work seamlessly.

## [0.3.33] - 2024-10-24

### Added

- **🏆 Evaluation Leaderboard**: Easily track your performance through a new leaderboard system where your ratings contribute to a real-time ranking based on the Elo system. Sibling responses (regenerations, many model chats) are required for your ratings to count in the leaderboard. Additionally, you can opt-in to share your feedback history and be part of the community-wide leaderboard. Expect further improvements as we refine the algorithm—help us build the best community leaderboard!
- **⚔️ Arena Model Evaluation**: Enable blind A/B testing of models directly from Admin Settings > Evaluation for a true side-by-side comparison. Ideal for pinpointing the best model for your needs.
- **🎯 Topic-Based Leaderboard**: Discover more accurate rankings with experimental topic-based reranking, which adjusts leaderboard standings based on tag similarity in feedback. Get more relevant insights based on specific topics!
- **📁 Folders Support for Chats**: Organize your chats better by grouping them into folders. Drag and drop chats between folders and export them seamlessly for easy sharing or analysis.
- **📤 Easy Chat Import via Drag & Drop**: Save time by simply dragging and dropping chat exports (JSON) directly onto the sidebar to import them into your workspace—streamlined, efficient, and intuitive!
- **📚 Enhanced Knowledge Collection**: Now, you can reference individual files from a knowledge collection—ideal for more precise Retrieval-Augmented Generations (RAG) queries and document analysis.
- **🏷️ Enhanced Tagging System**: Tags now take up less space! Utilize the new 'tag:' query system to manage, search, and organize your conversations more effectively without cluttering the interface.
- **🧠 Auto-Tagging for Chats**: Your conversations are now automatically tagged for improved organization, mirroring the efficiency of auto-generated titles.
- **🔍 Backend Chat Query System**: Chat filtering has become more efficient, now handled through the backend\*\* instead of your browser, improving search performance and accuracy.
- **🎮 Revamped Playground**: Experience a refreshed and optimized Playground for smoother testing, tweaks, and experimentation of your models and tools.
- **🧩 Token-Based Text Splitter**: Introducing token-based text splitting (tiktoken), giving you more precise control over how text is processed. Previously, only character-based splitting was available.
- **🔢 Ollama Batch Embeddings**: Leverage new batch embedding support for improved efficiency and performance with Ollama embedding models.
- **🔍 Enhanced Add Text Content Modal**: Enjoy a cleaner, more intuitive workflow for adding and curating knowledge content with an upgraded input modal from our Knowledge workspace.
- **🖋️ Rich Text Input for Chats**: Make your chat inputs more dynamic with support for rich text formatting. Your conversations just got a lot more polished and professional.
- **⚡ Faster Whisper Model Configurability**: Customize your local faster whisper model directly from the WebUI.
- **☁️ Experimental S3 Support**: Enable stateless WebUI instances with S3 support, greatly enhancing scalability and balancing heavy workloads.
- **🔕 Disable Update Toast**: Now you can streamline your workspace even further—choose to disable update notifications for a more focused experience.
- **🌟 RAG Citation Relevance Percentage**: Easily assess citation accuracy with the addition of relevance percentages in RAG results.
- **⚙️ Mermaid Copy Button**: Mermaid diagrams now come with a handy copy button, simplifying the extraction and use of diagram contents directly in your workflow.
- **🎨 UI Redesign**: Major interface redesign that will make navigation smoother, keep your focus where it matters, and ensure a modern look.

### Fixed

- **🎙️ Voice Note Mic Stopping Issue**: Fixed the issue where the microphone stayed active after ending a voice note recording, ensuring your audio workflow runs smoothly.

### Removed

- **👋 Goodbye Sidebar Tags**: Sidebar tag clutter is gone. We’ve shifted tag buttons to more effective query-based tag filtering for a sleeker, more agile interface.

## [0.3.32] - 2024-10-06

### Added

- **🔢 Workspace Enhancements**: Added a display count for models, prompts, tools, and functions in the workspace, providing a clear overview and easier management.

### Fixed

- **🖥️ Web and YouTube Attachment Fix**: Resolved an issue where attaching web links and YouTube videos was malfunctioning, ensuring seamless integration and display within chats.
- **📞 Call Mode Activation on Landing Page**: Fixed a bug where call mode was not operational from the landing page.

### Changed

- **🔄 URL Parameter Refinement**: Updated the 'tool_ids' URL parameter to 'tools' or 'tool-ids' for more intuitive and consistent user experience.
- **🎨 Floating Buttons Styling Update**: Refactored the styling of floating buttons to intelligently adjust to the left side when there isn't enough room on the right, improving interface usability and aesthetic.
- **🔧 Enhanced Accessibility for Floating Buttons**: Implemented the ability to close floating buttons with the 'Esc' key, making workflow smoother and more efficient for users navigating via keyboard.
- **🖇️ Updated Information URL**: Information URLs now direct users to a general release page rather than a version-specific URL, ensuring access to the latest and relevant details all in one place.
- **📦 Library Dependencies Update**: Upgraded dependencies to ensure compatibility and performance optimization for pip installs.

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
