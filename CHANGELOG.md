# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.33] - 2025-10-08

### Added

- 🎨 Workspace interface received a comprehensive redesign across Models, Knowledge, Prompts, and Tools sections, featuring reorganized controls, view filters for created vs shared items, tag selectors, improved visual hierarchy, and streamlined import/export functionality. [Commit](https://github.com/open-webui/open-webui/commit/2c59a288603d8c5f004f223ee00fef37cc763a8e), [Commit](https://github.com/open-webui/open-webui/commit/6050c86ab6ef6b8c96dd3f99c62a6867011b67a4), [Commit](https://github.com/open-webui/open-webui/commit/96ecb47bc71c072aa34ef2be10781b042bef4e8c), [Commit](https://github.com/open-webui/open-webui/commit/2250d102b28075a9611696e911536547abb8b38a), [Commit](https://github.com/open-webui/open-webui/commit/23c8f6d507bfee75ab0015a3e2972d5c26f7e9bf), [Commit](https://github.com/open-webui/open-webui/commit/a743b16728c6ae24b8befbc2d7f24eb9e20c4ad5)
- 🛠️ Functions admin interface received a comprehensive redesign with creator attribution display, ownership filters for created vs shared items, improved organization, and refined styling. [Commit](https://github.com/open-webui/open-webui/commit/f5e1a42f51acc0b9d5b63a33c1ca2e42470239c1)
- ⚡ Page initialization performance is significantly improved through parallel data loading and optimized folder API calls, reducing initial page load time. [#17559](https://github.com/open-webui/open-webui/pull/17559), [#17889](https://github.com/open-webui/open-webui/pull/17889)
- ⚡ Chat overview component is now dynamically loaded on demand, reducing initial page bundle size by approximately 470KB and improving first-screen loading speed. [#17595](https://github.com/open-webui/open-webui/pull/17595)
- 📁 Folders can now be attached to chats using the "#" command, automatically expanding to include all files within the folder for streamlined knowledge base integration. [Commit](https://github.com/open-webui/open-webui/commit/d2cb78179d66dc85188172a08622d4c97a2ea1ee)
- 📱 Progressive Web App now supports Android share target functionality, allowing users to share web pages, YouTube videos, and text directly to Open WebUI from the system share menu. [#17633](https://github.com/open-webui/open-webui/pull/17633), [#17125](https://github.com/open-webui/open-webui/issues/17125)
- 🗄️ Redis session storage is now available as an experimental option for OAuth authentication flows via the ENABLE_STAR_SESSIONS_MIDDLEWARE environment variable, providing shared session state across multi-replica deployments to address CSRF errors, though currently only basic Redis setups are supported. [#17223](https://github.com/open-webui/open-webui/pull/17223), [#15373](https://github.com/open-webui/open-webui/issues/15373), [Docs:Commit](https://github.com/open-webui/docs/commit/14052347f165d1b597615370373d7289ce44c7f9)
- 📊 Vega and Vega-Lite chart visualization renderers are now supported in code blocks, enabling inline rendering of data visualizations with automatic compilation of Vega-Lite specifications. [#18033](https://github.com/open-webui/open-webui/pull/18033), [#18040](https://github.com/open-webui/open-webui/pull/18040), [#18022](https://github.com/open-webui/open-webui/issues/18022)
- 🔗 OpenAI connections now support custom HTTP headers, enabling users to configure authentication and routing headers for specific deployment requirements. [#18021](https://github.com/open-webui/open-webui/pull/18021), [#9732](https://github.com/open-webui/open-webui/discussions/9732)
- 🔐 OpenID Connect authentication now supports OIDC providers without email scope via the ENABLE_OAUTH_WITHOUT_EMAIL environment variable, enabling compatibility with identity providers that don't expose email addresses. [#18047](https://github.com/open-webui/open-webui/pull/18047), [#18045](https://github.com/open-webui/open-webui/issues/18045)
- 🤖 Ollama model management modal now features individual model update cancellation, comprehensive tooltips for all buttons, and streamlined notification behavior to reduce toast spam. [#16863](https://github.com/open-webui/open-webui/pull/16863)
- ☁️ OneDrive file picker now includes search functionality and "My Organization" pivot for business accounts, enabling easier file discovery across organizational content. [#17930](https://github.com/open-webui/open-webui/pull/17930), [#17929](https://github.com/open-webui/open-webui/issues/17929)
- 📊 Chat overview flow diagram now supports toggling between vertical and horizontal layout orientations for improved visualization flexibility. [#17941](https://github.com/open-webui/open-webui/pull/17941)
- 🔊 OpenAI Text-to-Speech engine now supports additional parameters, allowing users to customize TTS behavior with provider-specific options via JSON configuration. [#17985](https://github.com/open-webui/open-webui/issues/17985), [#17188](https://github.com/open-webui/open-webui/pull/17188)
- 🛠️ Tool server list now displays server name, URL, and type (OpenAPI or MCP) for easier identification and management. [#18062](https://github.com/open-webui/open-webui/issues/18062)
- 📁 Folders now remember the last selected model, automatically applying it when starting new chats within that folder. [#17836](https://github.com/open-webui/open-webui/issues/17836)
- 🔢 Ollama embedding endpoint now supports the optional dimensions parameter for controlling embedding output size, compatible with Ollama v0.11.11 and later. [#17942](https://github.com/open-webui/open-webui/pull/17942)
- ⚡ Workspace knowledge page load time is improved by removing redundant API calls, enhancing overall responsiveness. [#18057](https://github.com/open-webui/open-webui/pull/18057)
- ⚡ File metadata query performance is enhanced by selecting only relevant columns instead of retrieving entire records, reducing database overhead. [#18013](https://github.com/open-webui/open-webui/pull/18013)
- 📄 Note PDF exports now include titles and properly render in dark mode with appropriate background colors. [Commit](https://github.com/open-webui/open-webui/commit/216fb5c3db1a223ffe6e72d97aa9551fe0e2d028)
- 📄 Docling document extraction now supports additional parameters for VLM pipeline configuration, enabling customized vision model settings. [#17363](https://github.com/open-webui/open-webui/pull/17363)
- ⚙️ Server startup script now supports passing arbitrary arguments to uvicorn, enabling custom server configuration options. [#17919](https://github.com/open-webui/open-webui/pull/17919), [#17918](https://github.com/open-webui/open-webui/issues/17918)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for German, Danish, Spanish, Korean, Portuguese (Brazil), Simplified Chinese, and Traditional Chinese were enhanced and expanded.

### Fixed

- 💬 System prompts are no longer duplicated in chat requests, eliminating confusion and excessive token usage caused by repeated instructions being sent to models. [#17198](https://github.com/open-webui/open-webui/issues/17198), [#16855](https://github.com/open-webui/open-webui/issues/16855)
- 🔐 MCP OAuth 2.1 authentication now complies with the standard by implementing PKCE with S256 code challenge method and explicitly passing client credentials during token authorization, resolving "code_challenge: Field required" and "client_id: Field required" errors when connecting to OAuth-secured MCP servers. [Commit](https://github.com/open-webui/open-webui/commit/911a114ad459f5deebd97543c13c2b90196efb54), [#18010](https://github.com/open-webui/open-webui/issues/18010), [#18087](https://github.com/open-webui/open-webui/pull/18087)
- 🔐 OAuth signup flow now handles password hashing correctly by migrating from passlib to native bcrypt, preventing failures when passwords exceed 72 bytes. [#17917](https://github.com/open-webui/open-webui/issues/17917)
- 🔐 OAuth token refresh errors are resolved by properly registering and storing OAuth clients, fixing "Constructor parameter should be str" exceptions for Google, Microsoft, and OIDC providers. [#17829](https://github.com/open-webui/open-webui/issues/17829)
- 🔐 OAuth server metadata URL is now correctly accessed via the proper attribute, fixing automatic token refresh and logout functionality for Microsoft OAuth provider when OPENID_PROVIDER_URL is not set. [#18065](https://github.com/open-webui/open-webui/pull/18065)
- 🔐 OAuth credential decryption failures now allow the application to start gracefully with clear error messages instead of crashing, preventing complete service outages when WEBUI_SECRET_KEY mismatches occur during database migrations or environment changes. [#18094](https://github.com/open-webui/open-webui/pull/18094), [#18092](https://github.com/open-webui/open-webui/issues/18092)
- 🔐 OAuth 2.1 server discovery now correctly attempts all configured discovery URLs in sequence instead of only trying the first URL. [#17906](https://github.com/open-webui/open-webui/pull/17906), [#17904](https://github.com/open-webui/open-webui/issues/17904), [#18026](https://github.com/open-webui/open-webui/pull/18026)
- 🔐 Login redirect now correctly honors the redirect query parameter after authentication, ensuring users are returned to their intended destination with query parameters intact instead of defaulting to the homepage. [#18071](https://github.com/open-webui/open-webui/issues/18071)
- ☁️ OneDrive Business integration authentication regression is resolved, ensuring the popup now properly triggers when connecting to OneDrive accounts. [#17902](https://github.com/open-webui/open-webui/pull/17902), [#17825](https://github.com/open-webui/open-webui/discussions/17825), [#17816](https://github.com/open-webui/open-webui/issues/17816)
- 👥 Default group settings now persist correctly after page navigation, ensuring configuration changes are properly saved and retained. [#17899](https://github.com/open-webui/open-webui/issues/17899), [#18003](https://github.com/open-webui/open-webui/issues/18003)
- 📁 Folder data integrity is now verified on retrieval, automatically fixing orphaned folders with invalid parent references and ensuring proper cascading deletion of nested folder structures. [Commit](https://github.com/open-webui/open-webui/commit/5448618dd5ea181b9635b77040cef60926a902ff)
- 🗄️ Redis Sentinel and Redis Cluster configurations with the experimental ENABLE_STAR_SESSIONS_MIDDLEWARE feature are now properly isolated by making the feature opt-in only, preventing ReadOnlyError failures when connecting to read replicas in multi-node Redis deployments. [#18073](https://github.com/open-webui/open-webui/issues/18073)
- 📊 Mermaid and Vega diagram rendering now displays error toast notifications when syntax errors are detected, helping users identify and fix diagram issues instead of silently failing. [#18068](https://github.com/open-webui/open-webui/pull/18068)
- 🤖 Reasoning models that return reasoning_content instead of content no longer cause NoneType errors during chat title generation, follow-up suggestions, and tag generation. [#18080](https://github.com/open-webui/open-webui/pull/18080)
- 📚 Citation rendering now correctly handles multiple source references in a single bracket, parsing formats like [1,2] and [1, 2] into separate clickable citation links. [#18120](https://github.com/open-webui/open-webui/pull/18120)
- 🔍 Web search now handles individual source failures gracefully, continuing to process remaining sources instead of failing entirely when a single URL is unreachable or returns an error. [Commit](https://github.com/open-webui/open-webui/commit/e000494e488090c5f66989a2b3f89d3eaeb7946b), [Commit](https://github.com/open-webui/open-webui/commit/53e98620bff38ab9280aee5165af0a704bdd99b9)
- 🔍 Hybrid search with reranking now handles empty result sets gracefully instead of crashing with ValueError when all results are filtered out due to relevance thresholds. [#18096](https://github.com/open-webui/open-webui/issues/18096)
- 🔍 Reranking models without defined padding tokens now work correctly by automatically falling back to eos_token_id as pad_token_id, fixing "Cannot handle batch sizes > 1" errors for models like Qwen3-Reranker. [#18108](https://github.com/open-webui/open-webui/pull/18108), [#16027](https://github.com/open-webui/open-webui/discussions/16027)
- 🔍 Model selector search now correctly returns results for non-admin users by dynamically updating the search index when the model list changes, fixing a race condition that caused empty search results. [#17996](https://github.com/open-webui/open-webui/pull/17996), [#17960](https://github.com/open-webui/open-webui/pull/17960)
- ⚡ Task model function calling performance is improved by excluding base64 image data from payloads, significantly reducing token count and memory usage when images are present in conversations. [#17897](https://github.com/open-webui/open-webui/pull/17897)
- 🤖 Text selection "Ask" action now correctly recognizes and uses local models configured via direct connections instead of only showing external provider models. [#17896](https://github.com/open-webui/open-webui/issues/17896)
- 🛑 Task cancellation API now returns accurate response status, correctly reporting successful cancellations instead of incorrectly indicating failures. [#17920](https://github.com/open-webui/open-webui/issues/17920)
- 💬 Follow-up query suggestions are now generated and displayed in temporary chats, matching the behavior of saved chats. [#14987](https://github.com/open-webui/open-webui/issues/14987)
- 🔊 Azure Text-to-Speech now properly escapes special characters like ampersands in SSML, preventing HTTP 400 errors and ensuring audio generation succeeds for all text content. [#17962](https://github.com/open-webui/open-webui/issues/17962)
- 🛠️ OpenAPI tool server calls with optional parameters now execute successfully even when no arguments are provided, removing the incorrect requirement for a request body. [#18036](https://github.com/open-webui/open-webui/issues/18036)
- 🛠️ MCP mode tool server connections no longer incorrectly validate the OpenAPI path field, allowing seamless switching between OpenAPI and MCP connection types. [#17989](https://github.com/open-webui/open-webui/pull/17989), [#17988](https://github.com/open-webui/open-webui/issues/17988)
- 🛠️ Third-party tool responses containing non-UTF8 or invalid byte sequences are now handled gracefully without causing request failures. [#17882](https://github.com/open-webui/open-webui/pull/17882)
- 🎨 Workspace filter dropdown now correctly renders model tags as strings instead of displaying individual characters, fixing broken filtering interface when models have multiple tags. [#18034](https://github.com/open-webui/open-webui/issues/18034)
- ⌨️ Ctrl+Enter keyboard shortcut now correctly sends messages in mobile and narrow browser views on Chrome instead of inserting newlines. [#17975](https://github.com/open-webui/open-webui/issues/17975)
- ⌨️ Tab characters are now preserved when pasting code or formatted text into the chat input box in plain text mode. [#17958](https://github.com/open-webui/open-webui/issues/17958)
- 📋 Text selection copying from the chat input box now correctly copies only the selected text instead of the entire textbox content. [#17911](https://github.com/open-webui/open-webui/issues/17911)
- 🔍 Web search query logging now uses debug level instead of info level, preventing user search queries from appearing in production logs. [#17888](https://github.com/open-webui/open-webui/pull/17888)
- 📝 Debug print statements in middleware were removed to prevent excessive log pollution and respect configured logging levels. [#17943](https://github.com/open-webui/open-webui/issues/17943)

### Changed

- 🗄️ Milvus vector database dependency is updated from pymilvus 2.5.0 to 2.6.2, ensuring compatibility with newer Milvus versions but requiring users on older Milvus instances to either upgrade their database or manually downgrade the pymilvus package. [#18066](https://github.com/open-webui/open-webui/pull/18066)

## [0.6.32] - 2025-09-29

### Added

- ⚡ JSON model import moved to backend processing for significant performance improvements when importing large model files. [#17871](https://github.com/open-webui/open-webui/pull/17871)
- ⚠️ Visual warnings for group permissions that display when a permission is disabled in a group but remains enabled in the default user role, clarifying inheritance behavior for administrators. [#17848](https://github.com/open-webui/open-webui/pull/17848)
- 🗄️ Milvus multi-tenancy mode using shared collections with resource ID filtering for improved scalability, mirroring the existing Qdrant implementation and configurable via ENABLE_MILVUS_MULTITENANCY_MODE environment variable. [#17837](https://github.com/open-webui/open-webui/pull/17837)
- 🛠️ Enhanced tool result processing with improved error handling, better MCP tool result handling, and performance improvements for embedded UI components. [Commit](https://github.com/open-webui/open-webui/commit/4f06f29348b2c9d71c87d1bbe5b748a368f5101f)
- 👥 New user groups now automatically inherit default group permissions, streamlining the admin setup process by eliminating manual permission configuration. [#17843](https://github.com/open-webui/open-webui/pull/17843)
- 🗂️ Bulk unarchive functionality for all chats, providing a single backend endpoint to efficiently restore all archived chats at once. [#17857](https://github.com/open-webui/open-webui/pull/17857)
- 🏷️ Browser tab title toggle setting allows users to control whether chat titles appear in the browser tab or display only "Open WebUI". [#17851](https://github.com/open-webui/open-webui/pull/17851)
- 💬 Reply-to-message functionality in channels, allowing users to reply directly to specific messages with visual threading and context display. [Commit](https://github.com/open-webui/open-webui/commit/1a18928c94903ad1f1f0391b8ade042c3e60205b)
- 🔧 Tool server import and export functionality, allowing direct upload of openapi.json and openapi.yaml files as an alternative to URL-based configuration. [#14446](https://github.com/open-webui/open-webui/issues/14446)
- 🔧 User valve configuration for Functions is now available in the integration menu, providing consistent management alongside Tools. [#17784](https://github.com/open-webui/open-webui/issues/17784)
- 🔐 Admin permission toggle for controlling public sharing of notes, configurable via USER_PERMISSIONS_NOTES_ALLOW_PUBLIC_SHARING environment variable. [#17801](https://github.com/open-webui/open-webui/pull/17801), [Docs:#715](https://github.com/open-webui/docs/pull/715)
- 🗄️ DISKANN index type support for Milvus vector database with configurable maximum degree and search list size parameters. [#17770](https://github.com/open-webui/open-webui/pull/17770), [Docs:Commit](https://github.com/open-webui/docs/commit/cec50ab4d4b659558ca1ccd4b5e6fc024f05fb83)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for Chinese (Simplified & Traditional) and Bosnian (Latin) were enhanced and expanded.

### Fixed

- 🛠️ MCP tool calls are now correctly routed to the appropriate server when multiple streamable-http MCP servers are enabled, preventing "Tool not found" errors. [#17817](https://github.com/open-webui/open-webui/issues/17817)
- 🛠️ External tool servers (OpenAPI/MCP) now properly process and return tool results to the model, restoring functionality that was broken in v0.6.31. [#17764](https://github.com/open-webui/open-webui/issues/17764)
- 🔧 User valve detection now correctly identifies valves in imported tool code, ensuring gear icons appear in the integrations menu for all tools with user valves. [#17765](https://github.com/open-webui/open-webui/issues/17765)
- 🔐 MCP OAuth discovery now correctly handles multi-tenant configurations by including subpaths in metadata URL discovery. [#17768](https://github.com/open-webui/open-webui/issues/17768)
- 🗄️ Milvus query operations now correctly use -1 instead of None for unlimited queries, preventing TypeError exceptions. [#17769](https://github.com/open-webui/open-webui/pull/17769), [#17088](https://github.com/open-webui/open-webui/issues/17088)
- 📁 File upload error messages are now displayed when files are modified during upload, preventing user confusion on Android and Windows devices. [#17777](https://github.com/open-webui/open-webui/pull/17777)
- 🎨 MessageInput Integrations button hover effect now displays correctly with proper visual feedback. [#17767](https://github.com/open-webui/open-webui/pull/17767)
- 🎯 "Set as default" label positioning is fixed to ensure it remains clickable in all scenarios, including multi-model configurations. [#17779](https://github.com/open-webui/open-webui/pull/17779)
- 🎛️ Floating buttons now correctly retrieve message context by using the proper messageId parameter in createMessagesList calls. [#17823](https://github.com/open-webui/open-webui/pull/17823)
- 📌 Pinned chats are now properly cleared from the sidebar after archiving all chats, ensuring UI consistency without requiring a page refresh. [#17832](https://github.com/open-webui/open-webui/pull/17832)
- 🗑️ Delete confirmation modals now properly truncate long names for Notes, Prompts, Tools, and Functions to prevent modal overflow. [#17812](https://github.com/open-webui/open-webui/pull/17812)
- 🌐 Internationalization function calls now use proper Svelte store subscription syntax, preventing "i18n.t is not a function" errors on the model creation page. [#17819](https://github.com/open-webui/open-webui/pull/17819)
- 🎨 Playground chat interface button layout is corrected to prevent vertical text rendering for Assistant/User role buttons. [#17819](https://github.com/open-webui/open-webui/pull/17819)
- 🏷️ UI text truncation is improved across multiple components including usernames in admin panels, arena model names, model tags, and filter tags to prevent layout overflow issues. [#17805](https://github.com/open-webui/open-webui/pull/17805), [#17803](https://github.com/open-webui/open-webui/pull/17803), [#17791](https://github.com/open-webui/open-webui/pull/17791), [#17796](https://github.com/open-webui/open-webui/pull/17796)

## [0.6.31] - 2025-09-25

### Added

- 🔌 MCP (streamable HTTP) server support was added alongside existing OpenAPI server integration, allowing users to connect both server types through an improved server configuration interface. [#15932](https://github.com/open-webui/open-webui/issues/15932) [#16651](https://github.com/open-webui/open-webui/pull/16651), [Commit](https://github.com/open-webui/open-webui/commit/fd7385c3921eb59af76a26f4c475aedb38ce2406), [Commit](https://github.com/open-webui/open-webui/commit/777e81f7a8aca957a359d51df8388e5af4721a68), [Commit](https://github.com/open-webui/open-webui/commit/de7f7b3d855641450f8e5aac34fbae0665e0b80e), [Commit](https://github.com/open-webui/open-webui/commit/f1bbf3a91e4713039364b790e886e59b401572d0), [Commit](https://github.com/open-webui/open-webui/commit/c55afc42559c32a6f0c8beb0f1bb18e9360ab8af), [Commit](https://github.com/open-webui/open-webui/commit/61f20acf61f4fe30c0e5b0180949f6e1a8cf6524)
- 🔐 To enable MCP server authentication, OAuth 2.1 dynamic client registration was implemented with secure automatic client registration, encrypted session management, and seamless authentication flows. [Commit](https://github.com/open-webui/open-webui/commit/972be4eda5a394c111e849075f94099c9c0dd9aa), [Commit](https://github.com/open-webui/open-webui/commit/77e971dd9fbeee806e2864e686df5ec75e82104b), [Commit](https://github.com/open-webui/open-webui/commit/879abd7feea3692a2f157da4a458d30f27217508), [Commit](https://github.com/open-webui/open-webui/commit/422d38fd114b1ebd8a7dbb114d64e14791e67d7a), [Docs:#709](https://github.com/open-webui/docs/pull/709)
- 🛠️ External & Built-In Tools can now support rich UI element embedding ([Docs](https://docs.openwebui.com/features/plugin/tools/development)), allowing tools to return HTML content and interactive iframes that display directly within chat conversations with configurable security settings. [Commit](https://github.com/open-webui/open-webui/commit/07c5b25bc8b63173f406feb3ba183d375fedee6a), [Commit](https://github.com/open-webui/open-webui/commit/a5d8882bba7933a2c2c31c0a1405aba507c370bb), [Commit](https://github.com/open-webui/open-webui/commit/7be5b7f50f498de97359003609fc5993a172f084), [Commit](https://github.com/open-webui/open-webui/commit/a89ffccd7e96705a4a40e845289f4fcf9c4ae596)
- 📝 Note editor now supports drag-and-drop reordering of list items with visual drag handles, making list organization more intuitive and efficient. [Commit](https://github.com/open-webui/open-webui/commit/e4e97e727e9b4971f1c363b1280ca3a101599d88), [Commit](https://github.com/open-webui/open-webui/commit/aeb5288a3c7a6e9e0a47b807cc52f870c1b7dbe6)
- 🔍 Search modal was enhanced with quick action buttons for starting new conversations and creating notes, with intelligent content pre-population from search queries. [Commit](https://github.com/open-webui/open-webui/commit/aa6f63a335e172fec1dc94b2056541f52c1167a6), [Commit](https://github.com/open-webui/open-webui/commit/612a52d7bb7dbe9fa0bbbc8ac0a552d2b9801146), [Commit](https://github.com/open-webui/open-webui/commit/b03529b006f3148e895b1094584e1ab129ecac5b)
- 🛠️ Tool user valve configuration interface was added to the integrations menu, displaying clickable gear icon buttons with tooltips for tools that support user-specific settings, making personal tool configurations easily accessible. [Commit](https://github.com/open-webui/open-webui/commit/27d61307cdce97ed11a05ec13fc300249d6022cd)
- 👥 Channel access control was enhanced to require write permissions for posting, editing, and deleting messages, while read-only users can view content but cannot contribute. [#17543](https://github.com/open-webui/open-webui/pull/17543)
- 💬 Channel models now support image processing, allowing AI assistants to view and analyze images shared in conversation threads. [Commit](https://github.com/open-webui/open-webui/commit/9f0010e234a6f40782a66021435d3c02b9c23639)
- 🌐 Attach Webpage button was added to the message input menu, providing a user-friendly modal interface for attaching web content and YouTube videos as an alternative to the existing URL syntax. [#17534](https://github.com/open-webui/open-webui/pull/17534)
- 🔐 Redis session storage support was added for OAuth redirects, providing better state handling in multi-pod Kubernetes deployments and resolving CSRF mismatch errors. [#17223](https://github.com/open-webui/open-webui/pull/17223), [#15373](https://github.com/open-webui/open-webui/issues/15373)
- 🔍 Ollama Cloud web search integration was added as a new search engine option, providing access to web search functionality through Ollama's cloud infrastructure. [Commit](https://github.com/open-webui/open-webui/commit/e06489d92baca095b8f376fbef223298c7772579), [Commit](https://github.com/open-webui/open-webui/commit/4b6d34438bcfc45463dc7a9cb984794b32c1f0a1), [Commit](https://github.com/open-webui/open-webui/commit/05c46008da85357dc6890b846789dfaa59f4a520), [Commit](https://github.com/open-webui/open-webui/commit/fe65fe0b97ec5a8fff71592ff04a25c8e123d108), [Docs:#708](https://github.com/open-webui/docs/pull/708)
- 🔍 Perplexity Websearch API integration was added as a new search engine option, providing access to the new websearch functionality provided by Perplexity. [#17756](https://github.com/open-webui/open-webui/issues/17756), [Commit](https://github.com/open-webui/open-webui/pull/17747/commits/7f411dd5cc1c29733216f79e99eeeed0406a2afe)
- ☁️ OneDrive integration was improved to support separate client IDs for personal and business authentication, enabling both integrations to work simultaneously. [#17619](https://github.com/open-webui/open-webui/pull/17619), [Docs](https://docs.openwebui.com/tutorials/integrations/onedrive-sharepoint), [Docs](https://docs.openwebui.com/getting-started/env-configuration/#onedrive)
- 📝 Pending user overlay content now supports markdown formatting, enabling rich text display for custom messages similar to banner functionality. [#17681](https://github.com/open-webui/open-webui/pull/17681)
- 🎨 Image generation model selection was centralized to enable dynamic model override in function calls, allowing pipes and tools to specify different models than the global default while maintaining backward compatibility. [#17689](https://github.com/open-webui/open-webui/pull/17689)
- 🎨 Interface design was modernized with updated visual styling, improved spacing, and refined component layouts across modals, sidebar, settings, and navigation elements. [Commit](https://github.com/open-webui/open-webui/commit/27a91cc80a24bda0a3a188bc3120a8ab57b00881), [Commit](https://github.com/open-webui/open-webui/commit/4ad743098615f9c58daa9df392f31109aeceeb16), [Commit](https://github.com/open-webui/open-webui/commit/fd7385c3921eb59af76a26f4c475aedb38ce2406)
- 📊 Notes query performance was optimized through database-level filtering and separated access control logic, reducing memory usage and eliminating N+1 query problems for better scalability. [#17607](https://github.com/open-webui/open-webui/pull/17607) [Commit](https://github.com/open-webui/open-webui/pull/17747/commits/da661756fa7eec754270e6dd8c67cbf74a28a17f)
- ⚡ Page loading performance was optimized by deferring API requests until components are actually opened, including ChangelogModal, ModelSelector, RecursiveFolder, ArchivedChatsModal, and SearchModal. [#17542](https://github.com/open-webui/open-webui/pull/17542), [#17555](https://github.com/open-webui/open-webui/pull/17555), [#17557](https://github.com/open-webui/open-webui/pull/17557), [#17541](https://github.com/open-webui/open-webui/pull/17541), [#17640](https://github.com/open-webui/open-webui/pull/17640)
- ⚡ Bundle size was reduced by 1.58MB through optimized highlight.js language support, improving page loading speed and reducing bandwidth usage. [#17645](https://github.com/open-webui/open-webui/pull/17645)
- ⚡ Editor collaboration functionality was refactored to reduce package size by 390KB and minimize compilation errors, improving build performance and reliability. [#17593](https://github.com/open-webui/open-webui/pull/17593)
- ♿ Enhanced user interface accessibility through the addition of unique element IDs, improving targeting for testing, styling, and assistive technologies while providing better semantic markup for screen readers and accessibility tools. [#17746](https://github.com/open-webui/open-webui/pull/17746)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for Portuguese (Brazil), Chinese (Simplified and Traditional), Korean, Irish, Spanish, Finnish, French, Kabyle, Russian, and Catalan were enhanced and improved.

### Fixed

- 🛡️ SVG content security was enhanced by implementing DOMPurify sanitization to prevent XSS attacks through malicious SVG elements, ensuring safe rendering of user-generated SVG content. [Commit](https://github.com/open-webui/open-webui/pull/17747/commits/750a659a9fee7687e667d9d755e17b8a0c77d557)
- ☁️ OneDrive attachment menu rendering issues were resolved by restructuring the submenu interface from dropdown to tabbed navigation, preventing menu items from being hidden or clipped due to overflow constraints. [#17554](https://github.com/open-webui/open-webui/issues/17554), [Commit](https://github.com/open-webui/open-webui/pull/17747/commits/90e4b49b881b644465831cc3028bb44f0f7a2196)
- 💬 Attached conversation references now persist throughout the entire chat session, ensuring models can continue querying referenced conversations after multiple conversation turns. [#17750](https://github.com/open-webui/open-webui/issues/17750)
- 🔍 Search modal text box focus issues after pinning or unpinning chats were resolved, allowing users to properly exit the search interface by clicking outside the text box. [#17743](https://github.com/open-webui/open-webui/issues/17743)
- 🔍 Search function chat list is now properly updated in real-time when chats are created or deleted, eliminating stale search results and preview loading failures. [#17741](https://github.com/open-webui/open-webui/issues/17741)
- 💬 Chat jitter and delayed code block expansion in multi-model sessions were resolved by reverting dynamic CodeEditor loading, restoring stable rendering behavior. [#17715](https://github.com/open-webui/open-webui/pull/17715), [#17684](https://github.com/open-webui/open-webui/issues/17684)
- 📎 File upload handling was improved to properly recognize uploaded files even when no accompanying text message is provided, resolving issues where attachments were ignored in custom prompts. [#17492](https://github.com/open-webui/open-webui/issues/17492)
- 💬 Chat conversation referencing within projects was restored by including foldered chats in the reference menu, allowing users to properly quote conversations from within their project scope. [#17530](https://github.com/open-webui/open-webui/issues/17530)
- 🔍 RAG query generation is now skipped when all attached files are set to full context mode, preventing unnecessary retrieval operations and improving system efficiency. [#17744](https://github.com/open-webui/open-webui/pull/17744)
- 💾 Memory leaks in file handling and HTTP connections are prevented through proper resource cleanup, ensuring stable memory usage during large file downloads and processing operations. [#17608](https://github.com/open-webui/open-webui/pull/17608)
- 🔐 OAuth access token refresh errors are resolved by properly implementing async/await patterns, preventing "coroutine object has no attribute get" failures during token expiry. [#17585](https://github.com/open-webui/open-webui/issues/17585), [#17678](https://github.com/open-webui/open-webui/issues/17678)
- ⚙️ Valve behavior was improved to properly handle default values and array types, ensuring only explicitly set values are persisted while maintaining consistent distinction between custom and default valve states. [#17664](https://github.com/open-webui/open-webui/pull/17664)
- 🔍 Hybrid search functionality was enhanced to handle inconsistent parameter types and prevent failures when collection results are None, empty, or in unexpected formats. [#17617](https://github.com/open-webui/open-webui/pull/17617)
- 📁 Empty folder deletion is now allowed regardless of chat deletion permission restrictions, resolving cases where users couldn't remove folders after deleting all contained chats. [#17683](https://github.com/open-webui/open-webui/pull/17683)
- 📝 Rich text editor console errors were resolved by adding proper error handling when the TipTap editor view is not available or not yet mounted. [#17697](https://github.com/open-webui/open-webui/issues/17697)
- 🗒️ Hidden models are now properly excluded from the notes section dropdown and default model selection, preventing users from accessing models they shouldn't see. [#17722](https://github.com/open-webui/open-webui/pull/17722)
- 🖼️ AI-generated image download filenames now use a clean, translatable "Generated Image" format instead of potentially problematic response text, improving file management and compatibility. [#17721](https://github.com/open-webui/open-webui/pull/17721)
- 🎨 Toggle switch display issues in the Integrations interface are fixed, preventing background highlighting and obscuring on hover. [#17564](https://github.com/open-webui/open-webui/issues/17564)

### Changed

- 👥 Channel permissions now require write access for message posting, editing, and deletion, with existing user groups defaulting to read-only access requiring manual admin migration to write permissions for full participation.
- ☁️ OneDrive environment variable configuration was updated to use separate ONEDRIVE_CLIENT_ID_PERSONAL and ONEDRIVE_CLIENT_ID_BUSINESS variables for better client ID separation, while maintaining backward compatibility with the legacy ONEDRIVE_CLIENT_ID variable. [Docs](https://docs.openwebui.com/tutorials/integrations/onedrive-sharepoint), [Docs](https://docs.openwebui.com/getting-started/env-configuration/#onedrive)

## [0.6.30] - 2025-09-17

### Added

- 🔑 Microsoft Entra ID authentication type support was added for Azure OpenAI connections, enabling enhanced security and streamlined authentication workflows.

### Fixed

- ☁️ OneDrive integration was fixed after recent breakage, restoring reliable account connectivity and file access.

## [0.6.29] - 2025-09-17

### Added

- 🎨 The chat input menu has been completely overhauled with a revolutionary new design, consolidating attachments under a unified '+' button, organizing integrations into a streamlined options menu, and introducing powerful, interactive selectors for attaching chats, notes, and knowledge base items. [Commit](https://github.com/open-webui/open-webui/commit/a68342d5a887e36695e21f8c2aec593b159654ff), [Commit](https://github.com/open-webui/open-webui/commit/96b8aaf83ff341fef432649366bc5155bac6cf20), [Commit](https://github.com/open-webui/open-webui/commit/4977e6d50f7b931372c96dd5979ca635d58aeb78), [Commit](https://github.com/open-webui/open-webui/commit/d973db829f7ec98b8f8fe7d3b2822d588e79f94e), [Commit](https://github.com/open-webui/open-webui/commit/d4c628de09654df76653ad9bce9cb3263e2f27c8), [Commit](https://github.com/open-webui/open-webui/commit/cd740f436db4ea308dbede14ef7ff56e8126f51b), [Commit](https://github.com/open-webui/open-webui/commit/5c2db102d06b5c18beb248d795682ff422e9b6d1), [Commit](https://github.com/open-webui/open-webui/commit/031cf38655a1a2973194d2eaa0fbbd17aca8ee92), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/3ed0a6d11fea1a054e0bc8aa8dfbe417c7c53e51), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/eadec9e86e01bc8f9fb90dfe7a7ae4fc3bfa6420), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/c03ca7270e64e3a002d321237160c0ddaf2bb129), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/b53ddfbd19aa94e9cbf7210acb31c3cfafafa5fe), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/c923461882fcde30ae297a95e91176c95b9b72e1)
- 🤖 AI models can now be mentioned in channels to automatically generate responses, enabling multi-model conversations where mentioned models participate directly in threaded discussions with full context awareness. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/4fe97d8794ee18e087790caab9e5d82886006145)
- 💬 The Channels feature now utilizes the modern rich text editor, including support for '/', '@', and '#' command suggestions. [Commit](https://github.com/open-webui/open-webui/commit/06c1426e14ac0dfaf723485dbbc9723a4d89aba9), [Commit](https://github.com/open-webui/open-webui/commit/02f7c3258b62970ce79716f75d15467a96565054)
- 📎 Channel message input now supports direct paste functionality for images and files from the clipboard, streamlining content sharing workflows. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/6549fc839f86c40c26c2ef4dedcaf763a9304418)
- ⚙️ Models can now be configured with default features (Web Search, Image Generation) and filters that automatically activate when a user selects the model. [Commit](https://github.com/open-webui/open-webui/commit/9a555478273355a5177bfc7f7211c64778e4c8de), [Commit](https://github.com/open-webui/open-webui/commit/384a53b339820068e92f7eaea0d9f3e0536c19c2), [Commit](https://github.com/open-webui/open-webui/commit/d7f43bfc1a30c065def8c50d77c2579c1a3c5c67), [Commit](https://github.com/open-webui/open-webui/commit/6a67a2217cc5946ad771e479e3a37ac213210748)
- 💬 The ability to reference other chats as context within a conversation was added via the attachment menu. [Commit](https://github.com/open-webui/open-webui/commit/e097bbdf11ae4975c622e086df00d054291cdeb3), [Commit](https://github.com/open-webui/open-webui/commit/f3cd2ffb18e7dedbe88430f9ae7caa6b3cfd79d0), [Commit](https://github.com/open-webui/open-webui/commit/74263c872c5d574a9bb0944d7984f748dc772dba), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/aa8ab349ed2fcb46d1cf994b9c0de2ec2ea35d0d), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/025eef754f0d46789981defd473d001e3b1d0ca2)
- 🎨 The command suggestion UI for prompts ('/'), models ('@'), and knowledge ('#') was completely overhauled with a more responsive and keyboard-navigable interface. [Commit](https://github.com/open-webui/open-webui/commit/6b69c4da0fb9329ccf7024483960e070cf52ccab), [Commit](https://github.com/open-webui/open-webui/commit/06a6855f844456eceaa4d410c93379460e208202), [Commit](https://github.com/open-webui/open-webui/commit/c55f5578280b936cf581a743df3703e3db1afd54), [Commit](https://github.com/open-webui/open-webui/commit/f68d1ba394d4423d369f827894cde99d760b2402)
- 👥 User and channel suggestions were added to the mention system, enabling '@' mentions for users and models, and '#' mentions for channels with searchable user lookup and clickable navigation. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/bbd1d2b58c89b35daea234f1fc9208f2af840899), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/aef1e06f0bb72065a25579c982dd49157e320268), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/779db74d7e9b7b00d099b7d65cfbc8a831e74690)
- 📁 Folder functionality was enhanced with custom background image support, improved drag-and-drop capabilities for moving folders to root level, and better menu interactions. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/2a234829f5dfdfde27fdfd30591caa908340efb4), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/2b1ee8b0dc5f7c0caaafdd218f20705059fa72e2), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/b1e5bc8e490745f701909c19b6a444b67c04660e), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/3e584132686372dfeef187596a7c557aa5f48308)
- ☁️ OneDrive integration configuration now supports selecting between personal and work/school account types via ENABLE_ONEDRIVE_PERSONAL and ENABLE_ONEDRIVE_BUSINESS environment variables. [#17354](https://github.com/open-webui/open-webui/pull/17354), [Commit](https://github.com/open-webui/open-webui/commit/e1e3009a30f9808ce06582d81a60e391f5ca09ec), [Docs:#697](https://github.com/open-webui/docs/pull/697)
- ⚡ Mermaid.js is now dynamically loaded on demand, significantly reducing first-screen loading time and improving initial page performance. [#17476](https://github.com/open-webui/open-webui/issues/17476), [#17477](https://github.com/open-webui/open-webui/pull/17477)
- ⚡ Azure MSAL browser library is now dynamically loaded on demand, reducing initial bundle size by 730KB and improving first-screen loading speed. [#17479](https://github.com/open-webui/open-webui/pull/17479)
- ⚡ CodeEditor component is now dynamically loaded on demand, reducing initial bundle size by 1MB and improving first-screen loading speed. [#17498](https://github.com/open-webui/open-webui/pull/17498)
- ⚡ Hugging Face Transformers library is now dynamically loaded on demand, reducing initial bundle size by 1.9MB and improving first-screen loading speed. [#17499](https://github.com/open-webui/open-webui/pull/17499)
- ⚡ jsPDF and html2canvas-pro libraries are now dynamically loaded on demand, reducing initial bundle size by 980KB and improving first-screen loading speed. [#17502](https://github.com/open-webui/open-webui/pull/17502)
- ⚡ Leaflet mapping library is now dynamically loaded on demand, reducing initial bundle size by 454KB and improving first-screen loading speed. [#17503](https://github.com/open-webui/open-webui/pull/17503)
- 📊 OpenTelemetry metrics collection was enhanced to properly handle HTTP 500 errors and ensure metrics are recorded even during exceptions. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/b14617a653c6bdcfd3102c12f971924fd1faf572)
- 🔒 OAuth token retrieval logic was refactored, improving the reliability and consistency of authentication handling across the backend. [Commit](https://github.com/open-webui/open-webui/commit/6c0a5fa91cdbf6ffb74667ee61ca96bebfdfbc50)
- 💻 Code block output processing was improved to handle Python execution results more reliably, along with refined visual styling and button layouts. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/0e5320c39e308ff97f2ca9e289618af12479eb6e)
- ⚡ Message input processing was optimized to skip unnecessary text variable handling when input is empty, improving performance. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/e1386fe80b77126a12dabc4ad058abe9b024b275)
- 📄 Individual chat PDF export was added to the sidebar chat menu, allowing users to export single conversations as PDF documents with both stylized and plain text options. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/d041d58bb619689cd04a391b4f8191b23941ca62)
- 🛠️ Function validation was enhanced with improved valve validation and better error handling during function loading and synchronization. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/e66e0526ed6a116323285f79f44237538b6c75e6), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/8edfd29102e0a61777b23d3575eaa30be37b59a5)
- 🔔 Notification toast interaction was enhanced with drag detection to prevent accidental clicks and added keyboard support for accessibility. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/621e7679c427b6f0efa85f95235319238bf171ad)
- 🗓️ Improved date and time formatting dynamically adapts to the selected language, ensuring consistent localization across the UI. [#17409](https://github.com/open-webui/open-webui/pull/17409), [Commit](https://github.com/open-webui/open-webui/commit/2227f24bd6d861b1fad8d2cabacf7d62ce137d0c)
- 🔒 Feishu SSO integration was added, allowing users to authenticate via Feishu. [#17284](https://github.com/open-webui/open-webui/pull/17284), [Docs:#685](https://github.com/open-webui/docs/pull/685)
- 🔠 Toggle filters in the chat input options menu are now sorted alphabetically for easier navigation. [Commit](https://github.com/open-webui/open-webui/commit/ca853ca4656180487afcd84230d214f91db52533)
- 🎨 Long chat titles in the sidebar are now truncated to prevent text overflow and maintain a clean layout. [#17356](https://github.com/open-webui/open-webui/pull/17356)
- 🎨 Temporary chat interface design was refined with improved layout and visual consistency. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/67549dcadd670285d491bd41daf3d081a70fd094), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/2ca34217e68f3b439899c75881dfb050f49c9eb2), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/fb02ec52a5df3f58b53db4ab3a995c15f83503cd)
- 🎨 Download icon consistency was improved across the entire interface by standardizing the icon component used in menus, functions, tools, and export features. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/596be451ece7e11b5cd25465d49670c27a1cb33f)
- 🎨 Settings interface was enhanced with improved iconography and reorganized the 'Chats' section into 'Data Controls' for better clarity. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/8bf0b40fdd978b5af6548a6e1fb3aabd90bcd5cd)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for Finnish, German, Kabyle, Portuguese (Brazil), Simplified Chinese, Spanish (Spain), and Traditional Chinese (Taiwan) were enhanced and expanded.

### Fixed

- 📚 Knowledge base permission logic was corrected to ensure private collection owners can access their own content when embedding bypass is enabled. [#17432](https://github.com/open-webui/open-webui/issues/17432), [Commit](https://github.com/open-webui/open-webui/commit/a51f0c30ec1472d71487eab3e15d0351a2716b12)
- ⚙️ Connection URL editing in Admin Settings now properly saves changes instead of reverting to original values, fixing issues with both Ollama and OpenAI-compatible endpoints. [#17435](https://github.com/open-webui/open-webui/issues/17435), [Commit](https://github.com/open-webui/open-webui/commit/e4c864de7eb0d577843a80688677ce3659d1f81f)
- 📊 Usage information collection from Google models was corrected to handle providers that send usage data alongside content chunks instead of separately. [#17421](https://github.com/open-webui/open-webui/pull/17421), [Commit](https://github.com/open-webui/open-webui/commit/c2f98a4cd29ed738f395fef09c42ab8e73cd46a0)
- ⚙️ Settings modal scrolling issue was resolved by moving image compression controls to a dedicated modal, preventing the main settings from becoming scrollable out of view. [#17474](https://github.com/open-webui/open-webui/issues/17474), [Commit](https://github.com/open-webui/open-webui/commit/fed5615c19b0045a55b0be426b468a57bfda4b66)
- 📁 Folder click behavior was improved to prevent accidental actions by implementing proper double-click detection and timing delays for folder expansion and selection. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/19e3214997170eea6ee92452e8c778e04a28e396)
- 🔐 Access control component reliability was improved with better null checking and error handling for group permissions and private access scenarios. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/c8780a7f934c5e49a21b438f2f30232f83cf75d2), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/32015c392dbc6b7367a6a91d9e173e675ea3402c)
- 🔗 The citation modal now correctly displays and links to external web page sources in addition to internal documents. [Commit](https://github.com/open-webui/open-webui/commit/9208a84185a7e59524f00a7576667d493c3ac7d4)
- 🔗 Web and YouTube attachment handling was fixed, ensuring their content is now reliably processed and included in the chat context for retrieval. [Commit](https://github.com/open-webui/open-webui/commit/210197fd438b52080cda5d6ce3d47b92cdc264c8)
- 📂 Large file upload failures are resolved by correcting the processing logic for scenarios where document embedding is bypassed. [Commit](https://github.com/open-webui/open-webui/commit/051b6daa8299fd332503bd584563556e2ae6adab)
- 🌐 Rich text input placeholder text now correctly updates when the interface language is switched, ensuring proper localization. [#17473](https://github.com/open-webui/open-webui/pull/17473), [Commit](https://github.com/open-webui/open-webui/commit/77358031f5077e6efe5cc08d8d4e5831c7cd1cd9)
- 📊 Llama.cpp server timing metrics are now correctly parsed and displayed by fixing a typo in the response handling. [#17350](https://github.com/open-webui/open-webui/issues/17350), [Commit](https://github.com/open-webui/open-webui/commit/cf72f5503f39834b9da44ebbb426a3674dad0caa)
- 🛠️ Filter functions with file_handler configuration now properly handle messages without file attachments, preventing runtime errors. [#17423](https://github.com/open-webui/open-webui/pull/17423)
- 🔔 Channel notification delivery was fixed to properly handle background task execution and user access checking. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/1077b2ac8b96e49c2ad2620e76eb65bbb2a3a1f3)

### Changed

- 📝 Prompt template variables are now optional by default instead of being forced as required, allowing flexible workflows with optional metadata fields. [#17447](https://github.com/open-webui/open-webui/issues/17447), [Commit](https://github.com/open-webui/open-webui/commit/d5824b1b495fcf86e57171769bcec2a0f698b070), [Docs:#696](https://github.com/open-webui/docs/pull/696)
- 🛠️ Direct external tool servers now require explicit user selection from the input interface instead of being automatically included in conversations, providing better control over tool usage. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/0f04227c34ca32746c43a9323e2df32299fcb6af), [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/99bba12de279dd55c55ded35b2e4f819af1c9ab5)
- 📺 Widescreen mode option was removed from Channels interface, with all channel layouts now using full-width display. [Commit](https://github.com/open-webui/open-webui/pull/17420/commits/d46b7b8f1b99a8054b55031fe935c8a16d5ec956)
- 🎛️ The plain textarea input option was deprecated, and the custom text editor is now the standard for all chat inputs. [Commit](https://github.com/open-webui/open-webui/commit/153afd832ccd12a1e5fd99b085008d080872c161)

## [0.6.28] - 2025-09-10

### Added

- 🔍 The "@" command for model selection now supports real-time search and filtering, improving usability and aligning its behavior with other input commands. [#17307](https://github.com/open-webui/open-webui/issues/17307), [Commit](https://github.com/open-webui/open-webui/commit/f2a09c71499489ee71599af4a179e7518aaf658b)
- 🛠️ External tool server data handling is now more robust, automatically attempting to parse specifications as JSON before falling back to YAML, regardless of the URL extension. [Commit](https://github.com/open-webui/open-webui/commit/774c0056bde88ed4831422efa81506488e3d6641)
- 🎯 The "Title" field is now automatically focused when creating a new chat folder, streamlining the folder creation process. [#17315](https://github.com/open-webui/open-webui/issues/17315), [Commit](https://github.com/open-webui/open-webui/commit/c51a651a2d5e2a27546416666812e9b92205562d)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Brazilian Portuguese and Simplified Chinese translations were expanded and refined.

### Fixed

- 🔊 A regression affecting Text-to-Speech for local providers using the OpenAI engine was fixed by reverting a URL joining change. [#17316](https://github.com/open-webui/open-webui/issues/17316), [Commit](https://github.com/open-webui/open-webui/commit/8339f59cdfc63f2d58c8e26933d1bf1438479d75)
- 🪧 A regression was fixed where the input modal for prompts with placeholders would not open, causing the raw prompt text to be pasted into the chat input field instead. [#17325](https://github.com/open-webui/open-webui/issues/17325), [Commit](https://github.com/open-webui/open-webui/commit/d5cb65527eaa4831459a4c7dbf187daa9c0525ae)
- 🔑 An issue was resolved where modified connection keys in the OpenAIConnection component did not take effect. [#17324](https://github.com/open-webui/open-webui/pull/17324)

## [0.6.27] - 2025-09-09

### Added

- 📁 Emoji folder icons were added, allowing users to personalize workspace organization with visual cues, including improved chevron display. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/1588f42fe777ad5d807e3f2fc8dbbc47a8db87c0), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/b70c0f36c0f5bbfc2a767429984d6fba1a7bb26c), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/11dea8795bfce42aa5d8d58ef316ded05173bd87), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/c0a47169fa059154d5f5a9ea6b94f9a66d82f255)
- 📁 The 'Search Collection' input field now dynamically displays the total number of files within the knowledge base. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/fbbe1117ae4c9c8fec6499d790eee275818eccc5)
- ☁️ A provider toggle in connection settings now allows users to manually specify Azure OpenAI deployments. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/5bdd334b74fbd154085f2d590f4afdba32469c8a)
- ⚡ Model list caching performance was optimized by fixing cache key generation to reduce redundant API calls. [#17158](https://github.com/open-webui/open-webui/pull/17158)
- 🎨 Azure OpenAI image generation is now supported, with configurations for IMAGES_OPENAI_API_VERSION via environment variable and admin UI. [#17147](https://github.com/open-webui/open-webui/pull/17147), [#16274](https://github.com/open-webui/open-webui/discussions/16274), [Docs:#679](https://github.com/open-webui/docs/pull/679)
- ⚡ Comprehensive N+1 query performance is optimized by reducing database queries from 1+N to 1+1 patterns across major listing endpoints. [#17165](https://github.com/open-webui/open-webui/pull/17165), [#17160](https://github.com/open-webui/open-webui/pull/17160), [#17161](https://github.com/open-webui/open-webui/pull/17161), [#17162](https://github.com/open-webui/open-webui/pull/17162), [#17159](https://github.com/open-webui/open-webui/pull/17159), [#17166](https://github.com/open-webui/open-webui/pull/17166)
- ⚡ The PDF.js library is now dynamically loaded, significantly reducing initial page load size and improving responsiveness. [#17222](https://github.com/open-webui/open-webui/pull/17222)
- ⚡ The heic2any library is now dynamically loaded across various message input components, including channels, for faster page loads. [#17225](https://github.com/open-webui/open-webui/pull/17225), [#17229](https://github.com/open-webui/open-webui/pull/17229)
- 📚 The knowledge API now supports a "delete_file" query parameter, allowing configurable file deletion behavior. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/22c4ef4fb096498066b73befe993ae3a82f7a8e7)
- 📊 Llama.cpp timing statistics are now integrated into the usage field for comprehensive model performance metrics. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/e830b4959ecd4b2795e29e53026984a58a7696a9)
- 🗄️ The PGVECTOR_CREATE_EXTENSION environment variable now allows control over automatic pgvector extension creation. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/c2b4976c82d335ed524bd80dc914b5e2f5bfbd9e), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/b45219c8b15b48d5ee3d42983e1107bbcefbab01), [Docs:#672](https://github.com/open-webui/docs/pull/672)
- 🔒 Comprehensive server-side OAuth token management was implemented, securely storing encrypted tokens in a new database table and introducing an automatic refresh mechanism, enabling seamless and secure forwarding of valid user-specific OAuth tokens to downstream services, including OpenAI-compatible endpoints and external tool servers via the new "system_oauth" authentication type, resolving long-standing issues such as large token size limitations, stale/expired tokens, and reliable token propagation, and enhancing overall security by minimizing client-side token exposure, configurable via "ENABLE_OAUTH_ID_TOKEN_COOKIE" and "OAUTH_SESSION_TOKEN_ENCRYPTION_KEY" environment variables. [Docs:#683](https://github.com/open-webui/docs/pull/683), [#17210](https://github.com/open-webui/open-webui/pull/17210), [#8957](https://github.com/open-webui/open-webui/discussions/8957), [#11029](https://github.com/open-webui/open-webui/discussions/11029), [#17178](https://github.com/open-webui/open-webui/issues/17178), [#17183](https://github.com/open-webui/open-webui/issues/17183), [Commit](https://github.com/open-webui/open-webui/commit/217f4daef09b36d3d4cc4681e11d3ebd9984a1a5), [Commit](https://github.com/open-webui/open-webui/commit/fc11e4384fe98fac659e10596f67c23483578867), [Commit](https://github.com/open-webui/open-webui/commit/f11bdc6ab5dd5682bb3e27166e77581f5b8af3e0), [Commit](https://github.com/open-webui/open-webui/commit/f71834720e623761d972d4d740e9bbd90a3a86c6), [Commit](https://github.com/open-webui/open-webui/commit/b5bb6ae177dcdc4e8274d7e5ffa50bc8099fd466), [Commit](https://github.com/open-webui/open-webui/commit/b786d1e3f3308ef4f0f95d7130ddbcaaca4fc927), [Commit](https://github.com/open-webui/open-webui/commit/8a9f8627017bd0a74cbd647891552b26e56aabb7), [Commit](https://github.com/open-webui/open-webui/commit/30d1dc2c60e303756120fe1c5538968c4e6139f4), [Commit](https://github.com/open-webui/open-webui/commit/2b2d123531eb3f42c0e940593832a64e2806240d), [Commit](https://github.com/open-webui/open-webui/commit/6f6412dd16c63c2bb4df79a96b814bf69cb3f880)
- 🔒 Conditional Permission Hardening for OpenShift Deployments: Added a build argument to enable optional permission hardening for OpenShift and container environments. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/0ebe4f8f8490451ac8e85a4846f010854d9b54e5)
- 👥 Regex pattern support is added for OAuth blocked groups, allowing more flexible group filtering rules. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/df66e21472646648d008ebb22b0e8d5424d491df)
- 💬 Web search result display was enhanced to include titles and favicons, providing a clearer overview of search sources. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/33f04a771455e3fabf8f0e8ebb994ae7f41b8ed4), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/0a85dd4bca23022729eafdbc82c8c139fa365af2), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/16090bc2721fde492afa2c4af5927e2b668527e1), [#17197](https://github.com/open-webui/open-webui/pull/17197), [#14179](https://github.com/open-webui/open-webui/issues/14179), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/1cdb7aed1ee9bf81f2fd0404be52dcfa64f8ed4f), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/f2525ebc447c008cf7269ef20ce04fa456f302c4), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/7f523de408ede4075349d8de71ae0214b7e1a62e), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/3d37e4a42d344051ae715ab59bd7b5718e46c343), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/cd5e2be27b613314aadda6107089331783987985), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/6dc0df247347aede2762fe2065cf30275fd137ae)
- 💬 A new setting was added to control whether clicking a suggested prompt automatically sends the message or only inserts the text. [#17192](https://github.com/open-webui/open-webui/issues/17192), [Commit](https://github.com/open-webui/open-webui/commit/e023a98f11fc52feb21e4065ec707cc98e50c7d3)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for Portuguese (Brazil), Simplified Chinese, Catalan, and Spanish were enhanced and expanded.

### Fixed

- 🔍 Hybrid search functionality now correctly handles lexical-semantic weight labels and avoids errors when BM25 weight is zero. [#17049](https://github.com/open-webui/open-webui/pull/17049), [#17046](https://github.com/open-webui/open-webui/issues/17046)
- 🛑 Task stopping errors are prevented by gracefully handling multiple stop requests for the same task. [#17195](https://github.com/open-webui/open-webui/pull/17195)
- 🐍 Code execution package detection precision is improved in Pyodide to prevent unnecessary package inclusions. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/bbe116795860a81a647d9567e0d9cb1950650095)
- 🛠️ Tool message format API compliance is fixed by ensuring content fields in tool call responses contain valid string values instead of null. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/37bf0087e5b8a324009c9d06b304027df351ea6b)
- 📱 Mobile app config API authentication now supports Authorization header token verification with cookie fallback for iOS and Android requests. [#17175](https://github.com/open-webui/open-webui/pull/17175)
- 💾 Knowledge file save race conditions are prevented by serializing API calls and adding an "isSaving" guard. [#17137](https://github.com/open-webui/open-webui/pull/17137), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/4ca936f0bf9813bee11ec8aea41d7e34fb6b16a9)
- 🔐 The SSO login button visibility is restored for OIDC PKCE authentication without a client secret. [#17012](https://github.com/open-webui/open-webui/pull/17012)
- 🔊 Text-to-Speech (TTS) API requests now use proper URL joining methods, ensuring reliable functionality regardless of trailing slashes in the base URL. [#17061](https://github.com/open-webui/open-webui/pull/17061)
- 🛡️ Admin account creation on Hugging Face Spaces now correctly detects the configured port, resolving issues with custom port deployments. [#17064](https://github.com/open-webui/open-webui/pull/17064)
- 📁 Unicode filename support is improved for external document loaders by properly URL-encoding filenames in HTTP headers. [#17013](https://github.com/open-webui/open-webui/pull/17013), [#17000](https://github.com/open-webui/open-webui/issues/17000)
- 🔗 Web page and YouTube attachments are now correctly processed by setting their type as "text" and using collection names for accurate content retrieval. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/487979859a6ffcfd60468f523822cdf838fbef5b)
- ✍️ Message input composition event handling is fixed to properly manage text input for multilingual users using Input Method Editors (IME). [#17085](https://github.com/open-webui/open-webui/pull/17085)
- 💬 Follow-up tooltip duplication is removed, streamlining the user interface and preventing visual clutter. [#17186](https://github.com/open-webui/open-webui/pull/17186)
- 🎨 Chat button text display is corrected by preventing clipping of descending characters and removing unnecessary capitalization. [#17191](https://github.com/open-webui/open-webui/pull/17191)
- 🧠 RAG Loop/Error with Gemma 3.1 2B Instruct is fixed by correctly unwrapping unexpected single-item list responses from models. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/1bc9711afd2b72cd07c4e539a83783868733767c), [#17213](https://github.com/open-webui/open-webui/issues/17213)
- 🖼️ HEIC conversion failures are resolved, improving robustness of image handling. [#17225](https://github.com/open-webui/open-webui/pull/17225)
- 📦 The slim Docker image size regression has been fixed by refining the build process to correctly exclude components when USE_SLIM=true. [#16997](https://github.com/open-webui/open-webui/issues/16997), [Commit](https://github.com/open-webui/open-webui/commit/be373e9fd42ac73b0302bdb487e16dbeae178b4e), [Commit](https://github.com/open-webui/open-webui/commit/0ebe4f8f8490451ac8e85a4846f010854d9b54e5)
- 📁 Knowledge base update validation errors are resolved, ensuring seamless management via UI or API. [#17244](https://github.com/open-webui/open-webui/issues/17244), [Commit](https://github.com/open-webui/open-webui/commit/9aac1489080a5c9441e89b1a56de0d3a672bc5fb)
- 🔐 Resolved a security issue where a global web search setting overrode model-specific restrictions, ensuring model-level settings are now correctly prioritized. [#17151](https://github.com/open-webui/open-webui/issues/17151), [Commit](https://github.com/open-webui/open-webui/commit/9368d0ac751ec3072d5a96712b80a9b20a642ce6)
- 🔐 OAuth redirect reliability is improved by robustly preserving the intended redirect path using session storage. [#17235](https://github.com/open-webui/open-webui/issues/17235), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/4f2b821088367da18374027919594365c7a3f459), [#15575](https://github.com/open-webui/open-webui/pull/15575), [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/d9f97c832c556fae4b116759da0177bf4fe619de)
- 🔐 Fixed a security vulnerability where knowledge base access within chat folders persisted after permissions were revoked. [#17182](https://github.com/open-webui/open-webui/issues/17182), [Commit](https://github.com/open-webui/open-webui/commit/40e40d1dddf9ca937e99af41c8ca038dbc93a7e6)
- 🔒 OIDC access denied errors are now displayed as user-friendly toast notifications instead of raw JSON. [#17208](https://github.com/open-webui/open-webui/issues/17208), [Commit](https://github.com/open-webui/open-webui/commit/3d6d050ad82d360adc42d6e9f42e8faf8d13c9f4)
- 💬 Chat exception handling is enhanced to prevent system instability during message generation and ensure graceful error recovery. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/f56889c5c7f0cf1a501c05d35dfa614e4f8b6958)
- 🔒 Static asset authentication is improved by adding crossorigin="use-credentials" attributes to all link elements, enabling proper cookie forwarding for proxy environments and authenticated requests to favicon, manifest, and stylesheet resources. [#17280](https://github.com/open-webui/open-webui/pull/17280), [Commit](https://github.com/open-webui/open-webui/commit/f17d8b5d19e1a05df7d63f53e939c99772a59c1e)

### Changed

- 🛠️ Renamed "Tools" to "External Tools" across the UI for clearer distinction between built-in and external functionalities. [Commit](https://github.com/open-webui/open-webui/pull/17070/commits/0bca4e230ef276bec468889e3be036242ad11086f)
- 🛡️ Default permission validation for message regeneration and deletion actions is enhanced to provide more restrictive access controls, improving chat security and user data protection. [#17285](https://github.com/open-webui/open-webui/pull/17285)

## [0.6.26] - 2025-08-28

### Added

- 🛂 **Granular Chat Interaction Permissions**: Added fine-grained permission controls for individual chat actions including "Continue Response", "Regenerate Response", "Rate Response", and "Delete Messages". Administrators can now configure these permissions per user group or set system defaults via environment variables, providing enhanced security and governance by preventing potential system prompt leakage through response continuation and enabling precise control over user interactions with AI responses.
- 🧠 **Custom Reasoning Tags Configuration**: Added configurable reasoning tag detection for AI model responses, allowing administrators and users to customize how the system identifies and processes reasoning content. Users can now define custom reasoning tag pairs, use default tags like "think" and "reasoning", or disable reasoning detection entirely through the Advanced Parameters interface, providing enhanced control over AI thought process visibility.
- 📱 **Pull-to-Refresh Support**: Added pull-to-refresh functionality allowing user to easily refresh the interface by pulling down on the navbar area. This resolves timeout issues that occurred when temporarily switching away from the app during long AI response generations, eliminating the need to close and relaunch the PWA.
- 📁 **Configurable File Upload Processing Mode**: Added "process_in_background" query parameter to the file upload API endpoint, allowing clients to choose between asynchronous (default) and synchronous file processing. Setting "process_in_background=false" forces the upload request to wait until extraction and embedding complete, returning immediately usable files and simplifying integration for backend API consumers that prefer blocking calls over polling workflows.
- 🔐 **Azure Document Intelligence DefaultAzureCredential Support**: Added support for authenticating with Azure Document Intelligence using DefaultAzureCredential in addition to API key authentication, enabling seamless integration with Azure Entra ID and managed identity authentication for enterprise Azure environments.
- 🔐 **Authentication Bootstrapping Enhancements**: Added "ENABLE_INITIAL_ADMIN_SIGNUP" environment variable and "?form=true" URL parameter to enable initial admin user creation and forced login form display in SSO-only deployments. This resolves bootstrap issues where administrators couldn't create the first user when login forms were disabled, allowing proper initialization of SSO-configured deployments without requiring temporary configuration changes.
- ⚡ **Query Generation Caching**: Added "ENABLE_QUERIES_CACHE" environment variable to enable request-scoped caching of generated search queries. When both web search and file retrieval are active, queries generated for web search are automatically reused for file retrieval, eliminating duplicate LLM API calls and reducing token usage and costs while maintaining search quality.
- 🔧 **Configurable Tool Call Retry Limit**: Added "CHAT_RESPONSE_MAX_TOOL_CALL_RETRIES" environment variable to control the maximum number of sequential tool calls allowed before safety stopping a chat session. This replaces the previous hardcoded limit of 10, enabling administrators to configure higher limits for complex workflows requiring extensive tool interactions.
- 📦 **Slim Docker Image Variant**: Added new slim Docker image option via "USE_SLIM" build argument that excludes embedded AI models and Ollama installation, reducing image size by approximately 1GB. This variant enables faster image pulls and deployments for environments where AI models are managed externally, particularly beneficial for auto-scaling clusters and distributed deployments.
- 🗂️ **Shift-to-Delete Functionality for Workspace Prompts**: Added keyboard shortcut support for quick prompt deletion on the Workspace Prompts page. Hold Shift and hover over any prompt to reveal a trash icon for instant deletion, bringing consistent interaction patterns across all workspace sections (Models, Tools, Functions, and now Prompts) and streamlining prompt management workflows.
- ♿ **Accessibility Enhancements**: Enhanced user interface accessibility with improved keyboard navigation, ARIA labels, and screen reader compatibility across key platform components.
- 📄 **Optimized PDF Export for Smaller File Size**: PDF exports are now significantly optimized, producing much smaller files for faster downloads and easier sharing or archiving of your chats and documents.
- 📦 **Slimmed Default Install with Optional Full Dependencies**: Installing Open WebUI via pip now defaults to a slimmer package; PostgreSQL support is no longer included by default—simply use 'pip install open-webui[all]' to include all optional dependencies for full feature compatibility.
- 🔄 **General Backend Refactoring**: Implemented various backend improvements to enhance performance, stability, and security, ensuring a more resilient and reliable platform for all users.
- 🌐 **Localization & Internationalization Improvements**: Enhanced and expanded translations for Finnish, Spanish, Japanese, Polish, Portuguese (Brazil), and Chinese, including missing translations and typo corrections, providing a more natural and professional user experience for speakers of these languages across the entire interface.

### Fixed

- ⚠️ **Chat Error Feedback Restored**: Fixed an issue where various backend errors (tool server failures, API connection issues, malformed responses) would cause chats to load indefinitely without providing user feedback. The system now properly displays error messages when failures occur during chat generation, allowing users to understand issues and retry as needed instead of waiting indefinitely.
- 🖼️ **Image Generation Steps Setting Visibility Fixed**: Fixed a UI issue where the "Set Steps" configuration option was incorrectly displayed for OpenAI and Gemini image generation engines that don't support this parameter. The setting is now only visible for compatible engines like ComfyUI and Automatic1111, eliminating user confusion about non-functional configuration options.
- 📄 **Datalab Marker API Document Loader Fixed**: Fixed broken Datalab Marker API document loader functionality by correcting URL path handling for both hosted Datalab services and self-hosted Marker servers. Removed hardcoded "/marker" paths from the loader code and restored proper default URL structure, ensuring PDF and document processing works correctly with both deployment types.
- 📋 **Citation Error Handling Improved**: Fixed an issue where malformed citation or source objects from external tools, pipes, or filters would cause JavaScript errors and make the chat interface completely unresponsive. The system now gracefully handles missing or undefined citation properties, allowing conversations to load properly even when tools generate defective citation events.
- 👥 **Group User Add API Endpoint Fixed**: Fixed an issue where the "/api/v1/groups/id/{group_id}/users/add" API endpoint would accept requests without errors but fail to actually add users to groups. The system now properly initializes and deduplicates user ID lists, ensuring users are correctly added to and removed from groups via API calls.
- 🛠️ **External Tool Server Error Handling Improved**: Fixed an issue where unreachable or misconfigured external tool servers would cause JavaScript errors and prevent the interface from loading properly. The system now gracefully handles connection failures, displays appropriate error messages, and filters out inaccessible servers while maintaining full functionality for working connections.
- 📋 **Code Block Copy Button Content Fixed**: Fixed an issue where the copy button in code blocks would copy the original AI-generated code instead of any user-edited content, ensuring the copy function always captures the currently displayed code as modified by users.
- 📄 **PDF Export Content Mismatch Fixed**: Resolved an issue where exporting a PDF of one chat while viewing another chat would incorrectly generate the PDF using the currently viewed chat's content instead of the intended chat's content. Additionally optimized the PDF generation algorithm with improved canvas slicing, better memory management, and enhanced image quality, while removing the problematic PDF export option from individual chat menus to prevent further confusion.
- 🖱️ **Windows Sidebar Cursor Icon Corrected**: Fixed confusing cursor icons on Windows systems where sidebar toggle buttons displayed resize cursors (ew-resize) instead of appropriate pointer cursors. The sidebar buttons now show standard pointer cursors on Windows, eliminating user confusion about whether the buttons expand/collapse the sidebar or resize it.
- 📝 **Safari IME Composition Bug Fixed**: Resolved an issue where pressing Enter while composing Chinese text using Input Method Editors (IMEs) on Safari would prematurely send messages instead of completing text composition. The system now properly detects composition states and ignores keydown events that occur immediately after composition ends, ensuring smooth multilingual text input across all browsers.
- 🔍 **Hybrid Search Parameter Handling Fixed**: Fixed an issue where the "hybrid" parameter in collection query requests was not being properly evaluated, causing the system to ignore user-specified hybrid search preferences and only check global configuration. Additionally resolved a division by zero error that occurred in hybrid search when BM25Retriever was called with empty document lists, ensuring robust search functionality across all collection states.
- 💬 **RTL Text Orientation in Messages Fixed**: Fixed text alignment issues in user messages and AI responses for Right-to-Left languages, ensuring proper text direction based on user language settings. Code blocks now consistently use Left-to-Right orientation regardless of the user's language preference, maintaining code readability across all supported languages.
- 📁 **File Content Preview in Modal Restored**: Fixed an issue where clicking on uploaded files would display an empty preview modal, even when the files were successfully processed and available for AI context. File content now displays correctly in the preview modal, ensuring users can verify and review their uploaded documents as intended.
- 🌐 **Playwright Timeout Configuration Corrected**: Fixed an issue where Playwright timeout values were incorrectly converted from milliseconds to seconds with an additional 1000x multiplier, causing excessively long web loading timeouts. The timeout parameter now correctly uses the configured millisecond values as intended, ensuring responsive web search and document loading operations.

### Changed

- 🔄 **Follow-Up Question Language Constraint Removed**: Follow-up question suggestions no longer strictly adhere to the chat's primary language setting, allowing for more flexible and diverse suggestion generation that may include questions in different languages based on conversation context and relevance rather than enforced language matching.

## [0.6.25] - 2025-08-22

### Fixed

- 🖼️ **Image Generation Reliability Restored**: Fixed a key issue causing image generation failures.
- 🏆 **Reranking Functionality Restored**: Resolved errors with rerank feature.

## [0.6.24] - 2025-08-21

### Added

- ♿ **High Contrast Mode in Chat Messages**: Implemented enhanced High Contrast Mode support for chat messages, making text and important details easier to read and improving accessibility for users with visual preferences or requirements.
- 🌎 **Localization & Internationalization Improvements**: Enhanced and expanded translations for a more natural and professional user experience for speakers of these languages across the entire interface.

### Fixed

- 🖼️ **ComfyUI Image Generation Restored**: Fixed a critical bug where ComfyUI-based image generation was not functioning, ensuring users can once again effortlessly create and interact with AI-generated visuals in their workflows.
- 🛠️ **Tool Server Loading and Visibility Restored**: Resolved an issue where connected tool servers were not loading or visible, restoring seamless integration and uninterrupted access to all external and custom tools directly within the platform.
- 🛡️ **Redis User Session Reliability**: Fixed a problem affecting the saving of user sessions in Redis, ensuring reliable login sessions, stable authentication, and secure multi-user environments.

## [0.6.23] - 2025-08-21

### Added

- ⚡ **Asynchronous Chat Payload Processing**: Refactored the chat completion pipeline to return a response immediately for streaming requests involving web search or tool calls. This enables users to stop ongoing generations promptly and preventing network timeouts during lengthy preprocessing phases, thus significantly improving user experience and responsiveness.
- 📁 **Asynchronous File Upload with Polling**: Implemented an asynchronous file upload process with frontend polling to resolve gateway timeouts and improve reliability when uploading large files. This ensures that even lengthy file processing, such as embedding or transcription, does not block the user interface or lead to connection timeouts, providing a smoother experience for all file operations.
- 📈 **Database Performance Indexes and Migration Script**: Introduced new database indexes on the "chat", "tag", and "function" tables to significantly enhance query performance for SQLite and PostgreSQL installations. For existing deployments, a new Alembic migration script is included to seamlessly apply these indexes, ensuring faster filtering and sorting operations across the platform.
- ✨ **Enhanced Database Performance Options**: Introduced new configurable options to significantly improve database performance, especially for SQLite. This includes "DATABASE_ENABLE_SQLITE_WAL" to enable SQLite WAL (Write-Ahead Logging) mode for concurrent operations, and "DATABASE_DEDUPLICATE_INTERVAL" which, in conjunction with a new deduplication mechanism, reduces redundant updates to "user.last_active_at", minimizing write conflicts across all database types.
- 💾 **Save Temporary Chats Button**: Introduced a new 'Save Chat' button for conversations initiated in temporary mode. This allows users to permanently save valuable temporary conversations to their chat history, providing greater flexibility and ensuring important discussions are not lost.
- 📂 **Chat Movement Options in Menu**: Added the ability to move chats directly to folders from the chat menu. This enhances chat organization and allows users to manage their conversations more efficiently by relocating them between folders with ease.
- 💬 **Language-Aware Follow-Up Suggestions**: Enhanced the AI's follow-up question generation to dynamically adapt to the primary language of the current chat. Follow-up prompts will now be suggested in the same language the user and AI are conversing in, ensuring more natural and contextually relevant interactions.
- 👤 **Expanded User Profile Details**: Introduced new user profile fields including username, bio, gender, and date of birth, allowing for more comprehensive user customization and information management. This enhancement includes corresponding updates to the database schema, API, and user interface for seamless integration.
- 👥 **Direct Navigation to User Groups from User Edit**: Enhanced the user edit modal to include a direct link to the associated user group. This allows administrators to quickly navigate from a user's profile to their group settings, streamlining user and group management workflows.
- 🔧 **Enhanced External Tool Server Compatibility**: Improved handling of responses from external tool servers, allowing both the backend and frontend to process plain text content in addition to JSON, ensuring greater flexibility and integration with diverse tool outputs.
- 🗣️ **Enhanced Audio Transcription Language Fallback and Deepgram Support**: Implemented a robust language fallback mechanism for both OpenAI and Deepgram Speech-to-Text (STT) API calls. If a specified language parameter is not supported by the model or provider, the system will now intelligently retry the transcription without the language parameter or with a default, ensuring greater reliability and preventing failed API calls. This also specifically adds and refines support for the audio language parameter in Deepgram API integrations.
- ⚡ **Optimized Hybrid Search Performance for BM25 Weight Configuration**: Enhanced hybrid search to significantly improve performance when the BM25 weight is set to 0 or less. This optimization intelligently disables unnecessary collection retrieval and BM25 ranking calculations, leading to faster search results without impacting accuracy for configurations that do not utilize lexical search contributions.
- 🔒 **Configurable Code Interpreter Module Blacklist**: Introduced the "CODE_INTERPRETER_BLACKLISTED_MODULES" environment variable, allowing administrators to specify Python modules that are forbidden from being imported or executed within the code interpreter. This significantly enhances the security posture by mitigating risks associated with arbitrary code execution, such as unauthorized data access, system manipulation, or outbound connections.
- 🔐 **Enhanced OAuth Role Claim Handling**: Improved compatibility with diverse OAuth providers by allowing role claims to be supplied as single strings or integers, in addition to arrays. The system now automatically normalizes these single-value claims into arrays for consistent processing, streamlining integration with identity providers that format role data differently.
- ⚙️ **Configurable Tool Call Timeout**: Introduced the "AIOHTTP_CLIENT_TIMEOUT" environment variable, allowing administrators to specify custom timeout durations for external tool calls, which is crucial for integrations with tools that have varying or extended response times.
- 🛠️ **Improved Tool Callable Generation for Google genai SDK**: Enhanced the creation of tool callables to directly support native function calling within the Google 'genai' SDK. This refactoring ensures proper signature inference and removes extraneous parameters, enabling seamless integration for advanced AI workflows using Google's generative AI models.
- ✨ **Dynamic Loading of 'kokoro-js'**: Implemented dynamic loading for the 'kokoro-js' library, preventing failures and improving compatibility on older iOS browsers that may not support direct imports or certain modern JavaScript APIs like 'DecompressionStream'.
- 🖥️ **Improved Command List Visibility on Small Screens**: Resolved an issue where the top items in command lists (e.g., Knowledge Base, Models, Prompts) were hidden or overlapped by the header on smaller screen sizes or specific browser zoom levels. The command option lists now dynamically adjust their height, ensuring all items are fully visible and accessible with proper scrolling.
- 📦 **Improved Docker Image Compatibility for Arbitrary UIDs**: Fixed issues preventing the Open WebUI container from running in environments with arbitrary User IDs (UIDs), such as OpenShift's restricted Security Context Constraints (SCC). The Dockerfile has been updated to correctly set file system permissions for "/app" and "/root" directories, ensuring they are writable by processes running with a supplemental GID 0, thus resolving permission errors for Python libraries and application caches.
- ♿ **Accessibility Enhancements**: Significantly improved the semantic structure of chat messages by using "section", "h2", "ul", and "li" HTML tags, and enhanced screen reader compatibility by explicitly hiding decorative images with "aria-hidden" attributes. This refactoring provides clearer structural context and improves overall accessibility and web standards compliance for the conversation flow.
- 🌐 **Localization & Internationalization Improvements**: Significantly expanded internationalization support throughout the user interface, translating numerous user-facing strings in toast messages, placeholders, and other UI elements. This, alongside continuous refinement and expansion of translations for languages including Brazilian Portuguese, Kabyle (Taqbaylit), Czech, Finnish, Chinese (Simplified), Chinese (Traditional), and German, and general fixes for several other translation files, further enhances linguistic coverage and user experience.

### Fixed

- 🛡️ **Resolved Critical OIDC SSO Login Failure**: Fixed a critical issue where OIDC Single Sign-On (SSO) logins failed due to an error in setting the authentication token as a cookie during the redirect process. This ensures reliable and seamless authentication for users utilizing OIDC providers, restoring full login functionality that was impacted by previous security hardening.
- ⚡ **Prevented UI Blocking by Unreachable Webhooks**: Resolved a critical performance and user experience issue where synchronous webhook calls to unreachable or slow endpoints would block the entire user interface for all users. Webhook requests are now processed asynchronously using "aiohttp", ensuring that the UI remains responsive and functional even if webhook delivery encounters delays or failures.
- 🔒 **Password Change Option Hidden for Externally Authenticated Users**: Resolved an issue where the password change dialog was visible to users authenticated via external methods (e.g., LDAP, OIDC, Trusted Header). The option to change a password in user settings is now correctly hidden for these users, as their passwords are managed externally, streamlining the user interface and preventing confusion.
- 💬 **Resolved Temporary Chat and Permission Enforcement Issues**: Fixed a bug where temporary chats (identified by "chat_id = local") incorrectly triggered database checks, leading to 404 errors. This also resolves the issue where the 'USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED' setting was not functioning as intended, ensuring temporary chat mode now works correctly for user roles.
- 🔐 **Admin Model Visibility for Administrators**: Private models remained visible and usable for administrators in the chat model selector, even when the intended privacy setting ("ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS" - now renamed to "BYPASS_ADMIN_ACCESS_CONTROL") was disabled. This ensures consistent enforcement of model access controls and adherence to the principle of least privilege.
- 🔍 **Clarified Web Search Engine Label for DDGS**: Addressed user confusion and inaccurate labeling by renaming "duckduckgo" to "DDGS" (Dux Distributed Global Search) in the web search engine selector. This clarifies that the system utilizes DDGS, a metasearch library that aggregates results from various search providers, accurately reflecting its underlying functionality rather than implying exclusive use of DuckDuckGo's search engine.
- 🛠️ **Improved Settings UI Reactivity and Visibility**: Resolved an issue where settings tabs for 'Connections' and 'Tools' did not dynamically update their visibility based on global administrative feature flags (e.g., 'enable_direct_connections'). The UI now reactively shows or hides these sections, ensuring a consistent and clear experience when administrators control feature availability.
- 🎚️ **Restored Model and Banner Reordering Functionality**: Fixed a bug that prevented administrators from reordering models in the Admin Panel's 'Models' settings and banners in the 'Interface' settings via drag-and-drop. The sortable functionality has been restored, allowing for proper customization of display order.
- 📝 **Restored Custom Pending User Overlay Visibility**: Fixed an issue where the custom title and description configured for pending users were not visible. The application now correctly exposes these UI configuration settings to pending users, ensuring that the custom onboarding messages are displayed as intended.
- 📥 **Fixed Community Function Import Compatibility**: Resolved an issue that prevented the successful import of function files downloaded from openwebui.com due to schema differences. The system now correctly processes these files, allowing for seamless integration of community-contributed functions.
- 📦 **Fixed Stale Ollama Version in Docker Images**: Resolved an issue where the Ollama installation within Docker images could become stale due to caching during the build process. The Dockerfile now includes a mechanism to invalidate the build cache for the Ollama installation step, ensuring that the latest version of Ollama is always installed.
- 🗄️ **Improved Milvus Query Handling for Large Datasets**: Fixed a "MilvusException" that occurred when attempting to query more than 16384 entries from a Milvus collection. The query logic has been refactored to use "query_iterator()", enabling efficient fetching of larger result sets in batches and resolving the previous limitation on the number of entries that could be retrieved.
- 🐛 **Restored Message Toolbar Icons for Empty Messages with Files**: Fixed an issue where the edit, copy, and delete icons were not displayed on user messages that contained an attached file but no text content. This ensures full interaction capabilities for all message types, allowing users to manage their messages consistently.
- 💬 **Resolved Streaming Interruption for Kimi-Dev Models**: Fixed an issue where streaming responses from Kimi-Dev models would halt prematurely upon encountering specific 'thinking' tokens (◁think▷, ◁/think▷). The system now correctly processes these tokens, ensuring uninterrupted streaming and proper handling of hidden or collapsible thinking sections.
- 🔍 **Enhanced Knowledge Base Search Functionality**: Improved the search capability within the 'Knowledge' section of the Workspace. Previously, searching for knowledge bases required exact term matches or starting with the first letter. Now, the search algorithm has been refined to allow broader, less exact matches, making it easier and more intuitive to find relevant knowledge bases.
- 📝 **Resolved Chinese Input 'Enter' Key Issue (macOS & iOS Safari)**: Fixed a bug where pressing the 'Enter' key during text composition with Input Method Editors (IMEs) on macOS and iOS Safari browsers would prematurely send the message. The system now robustly handles the composition state by addressing a 'compositionend' event bug specific to Safari, ensuring a smooth and expected typing experience for users of various languages, including Chinese and Korean.
- 🔐 **Resolved OAUTH_GROUPS_CLAIM Configuration Issue**: Fixed a bug where the "OAUTH_GROUPS_CLAIM" environment variable was not correctly parsed due to a typo in the configuration file. This ensures that OAuth group management features, including automatic group creation, now correctly utilize the specified claim from the identity provider, allowing for seamless integration with external user directories like Keycloak.
- 🗄️ **Resolved Azure PostgreSQL pgvector Extension Permissions**: Fixed an issue preventing the creation of "pgvector" and "pgcrypto" extensions on Azure PostgreSQL Flexible Servers due to permission limitations (e.g., 'Only members of "azure_pg_admin" are allowed to use "CREATE EXTENSION"'). The extension creation process now includes a conditional check, ensuring seamless deployment and compatibility with Azure PostgreSQL environments even with restricted database user permissions.
- 🛠️ **Improved Backend Path Resolution and Alembic Stability**: Fixed issues causing Alembic database migrations to fail due to incorrect path resolution within the application. By implementing canonical path resolution for core directories and refining Alembic configuration, the robustness and correctness of internal pathing have been significantly enhanced, ensuring reliable database operations.
- 📊 **Resolved Arena Model Identification in Feedback History**: Fixed an issue where the model used for feedback in arena settings was incorrectly reported as 'arena-model' in the evaluation history. The system now correctly logs and displays the actual model ID that received the feedback, restoring clarity and enabling proper analysis of model performance in arena environments.
- 🎨 **Resolved Icon Overlap in 'Her' Theme**: Fixed a visual glitch in the 'Her' theme where icons would overlap on the loading screen and certain icons appeared incongruous. The display has been corrected to ensure proper visual presentation and theme consistency.
- 🛠️ **Resolved Model Sorting TypeError with Null Names**: Fixed a "TypeError" that occurred in the "/api/models" endpoint when sorting models with null or missing names. The model sorting logic has been improved to gracefully handle such edge cases by ensuring that model IDs and names are treated as empty strings if their values are null or undefined, preventing comparison errors and improving API stability.
- 💬 **Resolved Silently Dropped Streaming Response Chunks**: Fixed an issue where the final partial chunks of streaming chat responses could be silently dropped, leading to incomplete message delivery. The system now reliably flush any pending delta data upon stream termination, early breaks (e.g., code interpreter tags), or connection closure, ensuring complete and accurate response delivery.
- 📱 **Disabled Overscroll for iOS Frontend**: Fixed an issue where overscrolling was enabled on iOS devices, causing unexpected scrolling behavior over fixed or sticky elements within the PWA. Overscroll has now been disabled, providing a more native application-like experience for iOS users.
- 📝 **Resolved Code Block Input Issue with Shift+Enter**: Fixed a bug where typing three backticks followed by a language and then pressing Shift+Enter would cause the code block prefix to disappear, preventing proper code formatting. The system now correctly preserves the code block syntax, ensuring consistent behavior for multi-line code input.
- 🛠️ **Improved OpenAI Model List Handling for Null Names**: Fixed an edge case where some OpenAI-compatible API providers might return models with a null value for their 'name' field. This could lead to issues like broken model list sorting. The system now gracefully handles these instances by removing the null 'name' key, ensuring stable model retrieval and display.
- 🔍 **Resolved DDGS Concurrent Request Configuration**: Fixed an issue where the configured number of concurrent requests was not being honored for the DDGS (Dux Distributed Global Search) metasearch engine. The system now correctly applies the specified concurrency setting, improving efficiency for web searches.
- 🛠️ **Improved Tool List Synchronization in Multi-Replica Deployments**: Resolved an issue where tool updates were not consistently reflected across all instances in multi-replica environments, leading to stale tool lists for users on other replicas. The tool list in the message input menu is now automatically refreshed each time it is accessed, ensuring all users always see the most current set of available tools.
- 🛠️ **Resolved Duplicate Tool Name Collision**: Fixed an issue where tools with identical names from different external servers were silently removed, preventing their simultaneous use. The system now correctly handles tool name collisions by internally prefixing tools with their server identifier, allowing multiple instances of similarly named tools from different servers to be active and usable by LLMs.
- 🖼️ **Resolved Image Generation API Size Parameter Issue**: Fixed a bug where the "/api/v1/images/generations" API endpoint did not correctly apply the 'size' parameter specified in the request payload for image generation. The system now properly honors the requested image dimensions (e.g., '1980x1080'), ensuring that generated images match the user's explicit size preference rather than defaulting to settings.
- 🗄️ **Resolved S3 Vector Upload Limitations**: Fixed an issue that prevented uploading more than 500 vectors to S3 Vector buckets due to API limitations, which resulted in a "ValidationException". S3 vector uploads are now batched in groups of 500, ensuring successful processing of larger datasets.
- 🛠️ **Fixed Tool Installation Error During Startup**: Resolved a "NoneType" error that occurred during tool installation at startup when 'tool.user' was unexpectedly null. The system now includes a check to ensure 'tool.user' exists before attempting to access its properties, preventing crashes and ensuring robust tool initialization.
- 🛠️ **Improved Azure OpenAI GPT-5 Parameter Handling**: Fixed an issue with Azure OpenAI SDK parameter handling to correctly support GPT-5 models. The 'max_tokens' parameter is now appropriately converted to 'max_completion_tokens' for GPT-5 models, ensuring consistent behavior and proper function execution similar to existing o-series models.
- 🐛 **Resolved Exception with Missing Group Permissions**: Fixed an exception that occurred in the access control logic when group permission objects were missing or null. The system now correctly handles cases where groups may not have explicit permission definitions, ensuring that 'None' checks prevent errors and maintain application stability when processing user permissions.
- 🛠️ **Improved OpenAI API Base URL Handling**: Fixed an issue where a trailing slash in the 'OPENAI_API_BASE_URL' configuration could lead to models not being detected or the endpoint failing. The system now automatically removes trailing slashes from the configured URL, ensuring robust and consistent connections to OpenAI-compatible APIs.
- 🖼️ **Resolved S3-Compatible Storage Upload Failures**: Fixed an issue where uploads to S3-compatible storage providers would fail with an "XAmzContentSHA256Mismatch" error. The system now correctly handles checksum calculations, ensuring reliable file and image uploads to S3-compatible services.
- 🌐 **Corrected 'Releases' Link**: Fixed an issue where the 'Releases' button in the user menu directed to an incorrect URL, now correctly linking to the Open WebUI GitHub releases page.
- 🛠️ **Resolved Model Sorting Errors with Null or Undefined Names**: Fixed multiple "TypeError" instances that occurred when attempting to sort model lists where model names were null or undefined. The sorting logic across various UI components (including Ollama model selection, leaderboard, and admin model settings) has been made more robust by gracefully handling absent model names, preventing crashes and ensuring consistent alphabetical sorting based on available name or ID.
- 🎨 **Resolved Banner Dismissal Issue with Iteration IDs**: Fixed a bug where dismissing banners could lead to unintended multiple banner dismissals or other incorrect behavior, especially when banners lacked unique iteration IDs. Unique IDs are now assigned during banner iteration, ensuring proper individual dismissal and consistent display behavior.

### Changed

- 🛂 **Environment Variable for Admin Access Control**: The environment variable "ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS" has been renamed to "BYPASS_ADMIN_ACCESS_CONTROL". This new name more accurately reflects its function as a control to allow administrators to bypass model access restrictions. Users are encouraged to update their configurations to use the new variable name; existing configurations using the old name will still be honored for backward compatibility.
- 🗂️ **Core Directory Path Resolution Updated**: The internal mechanism for resolving core application directory paths ("OPEN_WEBUI_DIR", "BACKEND_DIR", "BASE_DIR") has been updated to use canonical resolution via "Path().resolve()". This change improves path reliability but may require adjustments for any external scripts or configurations that previously relied on specific non-canonical path interpretations.
- 🗃️ **Database Performance Options**: New database performance options, "DATABASE_ENABLE_SQLITE_WAL" and "DATABASE_DEDUPLICATE_INTERVAL", are now available. If "DATABASE_ENABLE_SQLITE_WAL" is enabled, SQLite will operate in WAL mode, which may alter SQLite's file locking behavior. If "DATABASE_DEDUPLICATE_INTERVAL" is set to a non-zero value, the "user.last_active_at" timestamp will be updated less frequently, leading to slightly less real-time accuracy for this specific field but significantly reducing database write conflicts and improving overall performance. Both options are disabled by default.
- 🌐 **Renamed Web Search Concurrency Setting**: The environment variable "WEB_SEARCH_CONCURRENT_REQUESTS" has been renamed to "WEB_LOADER_CONCURRENT_REQUESTS". This change clarifies its scope, explicitly applying to the concurrency of the web loader component (which fetches content from search results) rather than the initial search engine query. Users relying on the old environment variable name for configuring web search concurrency must update their configurations to use "WEB_LOADER_CONCURRENT_REQUESTS".

## [0.6.22] - 2025-08-11

### Added

- 🔗 **OpenAI API '/v1' Endpoint Compatibility**: Enhanced API compatibility by supporting requests to paths like '/v1/models', '/v1/embeddings', and '/v1/chat/completions'. This allows Open WebUI to integrate more seamlessly with tools that expect OpenAI's '/v1' API structure.
- 🪄 **Toggle for Guided Response Regeneration Menu**: Introduced a new setting in 'Interface' settings, providing the ability to enable or disable the expanded guided response regeneration menu. This offers users more control over their chat workflow and interface preferences.
- ✨ **General UI/UX Enhancements**: Implemented various user interface and experience improvements, including more rounded corners for cards in the Knowledge, Prompts, and Tools sections, and minor layout adjustments within the chat Navbar for improved visual consistency.
- 🌐 **Localization & Internationalization Improvements**: Introduced support for the Kabyle (Taqbaylit) language, refined and expanded translations for Chinese, expanding the platform's linguistic coverage.

### Fixed

- 🐞 **OpenAI Error Message Propagation**: Resolved an issue where specific OpenAI API errors (e.g., 'Organization Not Verified') were obscured by generic 'JSONResponse' iterable errors. The system now correctly propagates detailed and actionable error messages from OpenAI to the user.
- 🌲 **Pinecone Insert Issue**: Fixed a bug that prevented proper insertion of items into Pinecone vector databases.
- 📦 **S3 Vector Issue**: Resolved a bug where s3vector functionality failed due to incorrect import paths.
- 🏠 **Landing Page Option Setting Not Working**: Fixed an issue where the landing page option in settings was not functioning as intended.

## [0.6.21] - 2025-08-10

### Added

- 👥 **User Groups in Edit Modal**: Added display of user groups information in the user edit modal, allowing administrators to view and manage group memberships directly when editing a user.

### Fixed

- 🐞 **Chat Completion 'model_id' Error**: Resolved a critical issue where chat completions failed with an "undefined model_id" error after upgrading to version 0.6.20, ensuring all models now function correctly and reliably.
- 🛠️ **Audit Log User Information Logging**: Fixed an issue where user information was not being correctly logged in the audit trail due to an unreflected function prototype change, ensuring complete logging for administrative oversight.
- 🛠️ **OpenTelemetry Configuration Consistency**: Fixed an issue where OpenTelemetry metric and log exporters' 'insecure' settings did not correctly default to the general OpenTelemetry 'insecure' flag, ensuring consistent security configurations across all OpenTelemetry exports.
- 📝 **Reply Input Content Display**: Fixed an issue where replying to a message incorrectly displayed '{{INPUT_CONTENT}}' instead of the actual message content, ensuring proper content display in replies.
- 🌐 **Localization & Internationalization Improvements**: Refined and expanded translations for Catalan, Korean, Spanish and Irish, ensuring a more fluent and native experience for global users.

## [0.6.20] - 2025-08-10

### Fixed

- 🛠️ **Quick Actions "Add" Behavior**: Fixed a bug where using the "Add" button in Quick Actions would add the resulting message as the very first message in the chat, instead of appending it to the latest message.

## [0.6.19] - 2025-08-09

### Added

- ✨ **Modernized Sidebar and Major UI Refinements**: The main navigation sidebar has been completely redesigned with a modern, cleaner aesthetic, featuring a sticky header and footer to keep key controls accessible. Core sidebar logic, like the pinned models list, was also refactored into dedicated components for better performance and maintainability.
- 🪄 **Guided Response Regeneration**: The "Regenerate" button has been transformed into a powerful new menu. You can now guide the AI's next attempt by suggesting changes in a text prompt, or use one-click options like "Try Again," "Add Details," or "More Concise" to instantly refine and reshape the response to better fit your needs.
- 🛠️ **Improved Tool Call Handling for GPT-OSS Models**: Implemented robust handling for tool calls specifically for GPT-OSS models, ensuring proper function execution and integration.
- 🛑 **Stop Button for Merge Responses**: Added a dedicated stop button to immediately halt the generation of merged AI responses, providing users with more control over ongoing outputs.
- 🔄 **Experimental SCIM 2.0 Support**: Implemented SCIM 2.0 (System for Cross-domain Identity Management) protocol support, enabling enterprise-grade automated user and group provisioning from identity providers like Okta, Azure AD, and Google Workspace for seamless user lifecycle management. Configuration is managed securely via environment variables.
- 🗂️ **Amazon S3 Vector Support**: You can now use Amazon S3 Vector as a high-performance vector database for your Retrieval-Augmented Generation (RAG) workflows. This provides a scalable, cloud-native storage option for users deeply integrated into the AWS ecosystem, simplifying infrastructure and enabling enterprise-scale knowledge management.
- 🗄️ **Oracle 23ai Vector Search Support**: Added support for Oracle 23ai's new vector search capabilities as a supported vector database, providing a robust and scalable option for managing large-scale documents and integrating vector search with existing business data at the database level.
- ⚡ **Qdrant Performance and Configuration Enhancements**: The Qdrant client has been significantly improved with faster data retrieval logic for 'get' and 'query' operations. New environment variables ('QDRANT_TIMEOUT', 'QDRANT_HNSW_M') provide administrators with finer control over query timeouts and HNSW index parameters, enabling better performance tuning for large-scale deployments.
- 🔐 **Encrypted SQLite Database with SQLCipher**: You can now encrypt your entire SQLite database at rest using SQLCipher. By setting the 'DATABASE_TYPE' to 'sqlite+sqlcipher' and providing a 'DATABASE_PASSWORD', all data is transparently encrypted, providing an essential security layer for protecting sensitive information in self-hosted deployments. Note that this requires additional system libraries and the 'sqlcipher3-wheels' Python package.
- 🚀 **Efficient Redis Connection Management**: Implemented a shared connection pool cache to reuse Redis connections, dramatically reducing the number of active clients. This prevents connection exhaustion errors, improves performance, and ensures greater stability in high-concurrency deployments and those using Redis Sentinel.
- ⚡ **Batched Response Streaming for High Performance**: Dramatically improve performance and stability during high-speed response streaming by batching multiple tokens together before sending them to the client. A new 'Stream Delta Chunk Size' advanced parameter can be set per-model or in user/chat settings, significantly reducing CPU load on the server, Redis, and client, and preventing connection issues in high-concurrency environments.
- ⚙️ **Global Batched Streaming Configuration**: Administrators can now set a system-wide default for response streaming using the new 'CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE' environment variable. This allows for global performance tuning, while still letting per-model or per-chat settings override the default for more granular control.
- 🔎 **Advanced Chat Search with Status Filters**: Quickly find any conversation with powerful new search filters. You can now instantly narrow down your chats using prefixes like 'pinned:true', 'shared:true', and 'archived:true' directly in the search bar. An intelligent dropdown menu assists you by suggesting available filter options as you type, streamlining your workflow and making chat management more efficient than ever.
- 🛂 **Granular Chat Controls Permissions**: Administrators can now manage chat settings with greater detail. The main "Chat Controls" permission now acts as a master switch, while new granular toggles for "Valves", "System Prompts", and "Advanced Parameters" allow for more specific control over which sections are visible to users inside the panel.
- ✍️ **Formatting Toolbar for Chat Input**: Introduced a dedicated formatting toolbar for the rich text chat input field, providing users with more accessible options for text styling and editing, configurable via interface settings.
- 📑 **Tabbed View for Multi-Model Responses**: You can now enable a new tabbed interface to view responses from multiple models. Instead of side-scrolling cards, this compact view organizes each model's response into its own tab, making it easier to compare outputs and saving vertical space. This feature can be toggled on or off in Interface settings.
- ↕️ **Reorder Pinned Models via Drag-and-Drop**: You can now organize your pinned models in the sidebar by simply dragging and dropping them into your preferred order. This custom layout is saved automatically, giving you more flexible control over your workspace.
- 📌 **Quick Model Unpin Shortcut**: You can now quickly unpin a model by holding the Shift key and hovering over it to reveal an instant unpin button, streamlining your workspace customization.
- ⚡ **Improved Chat Input Performance**: The chat input is now significantly more responsive, especially when pasting or typing large amounts of text. This was achieved by implementing a debounce mechanism for the auto-save feature, which prevents UI lag and ensures a smooth, uninterrupted typing experience.
- ✍️ **Customizable Floating Quick Actions with Tool Support**: Take full control of your text interaction workflow with new customizable floating quick actions. In Settings, you can create, edit, or disable these actions and even integrate tools using the '{{TOOL:tool_id}}' syntax in your prompts, enabling powerful one-click automations on selected text. This is in addition to using placeholders like '{{CONTENT}}' and '{{INPUT_CONTENT}}' for custom text transformations.
- 🔒 **Admin Workspace Privacy Control**: Introduced the 'ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS' environment variable (defaults to 'True') allowing administrators to control their access privileges to workspace items (Knowledge, Models, Prompts, Tools). When disabled, administrators adhere to the same access control rules as regular users, enhancing data separation for multi-tenant deployments.
- 🗄️ **Comprehensive Model Configuration Management**: Administrators can now export the entire model configuration to a file and use a new declarative sync endpoint to manage models in bulk. This powerful feature enables seamless backups, migrations, and state replication across multiple instances.
- 📦 **Native Redis Cluster Mode Support**: Added full support for connecting to Redis in cluster mode, allowing for scalable and highly available Redis deployments beyond Sentinel-managed setups. New environment variables 'REDIS_CLUSTER' and 'WEBSOCKET_REDIS_CLUSTER' enable the use of 'redis.cluster.RedisCluster' clients.
- 📊 **Granular OpenTelemetry Metrics Configuration**: Introduced dedicated environment variables and enhanced configuration options for OpenTelemetry metrics, allowing for separate OTLP endpoints, basic authentication credentials, and protocol (HTTP/gRPC) specifically for metrics export, independent of trace settings. This provides greater flexibility for integrating with diverse observability stacks.
- 🪵 **Granular OpenTelemetry Logging Configuration**: Enhanced the OpenTelemetry logging integration by introducing dedicated environment variables for logs, allowing separate OTLP endpoints, basic authentication credentials, and protocol (HTTP/gRPC) specifically for log export, independent of general OTel settings. The application's default Python logger now leverages this configuration to automatically send logs to your OTel endpoint when enabled via 'ENABLE_OTEL_LOGS'.
- 📁 **Enhanced Folder Chat Management with Sorting and Time Blocks**: The chat list within folders now supports comprehensive sorting options by title and updated time, along with intelligent time-based grouping (e.g., "Today," "Yesterday") similar to the main chat view, making navigation and organization of project-specific conversations significantly easier.
- ⚙️ **Configurable Datalab Marker API & Advanced Processing Options**: Enhanced Datalab Marker API integration, allowing administrators to configure custom API base URLs for self-hosting and to specify comprehensive processing options via a new 'additional_config' JSON parameter. This replaces the deprecated language selection feature and provides granular control over document extraction, with streamlined API endpoint resolution for more robust self-hosted deployments.
- 🧑‍💼 **Export All Users to CSV**: Administrators can now export a complete list of all users to a CSV file directly from the Admin Panel's database settings. This provides a simple, one-click way to generate user data for auditing, reporting, or management purposes.
- 🛂 **Customizable OAuth 'sub' Claim**: Administrators can now use the 'OAUTH_SUB_CLAIM_OVERRIDE' environment variable to specify which claim from the identity provider should be used as the unique user identifier ('sub'). This provides greater flexibility and control for complex enterprise authentication setups where modifying the IDP's default claims is not possible.
- 👁️ **Password Visibility Toggle for Input Fields**: Password fields across the application (login, registration, user management, and account settings) now utilize a new 'SensitiveInput' component, providing a consistent toggle to reveal/hide passwords for improved usability and security.
- 🛂 **Optional "Confirm Password" on Sign-Up**: To help prevent password typos during account creation, administrators can now enable a "Confirm Password" field on the sign-up page. This feature is disabled by default and can be activated via an environment variable for enhanced user experience.
- 💬 **View Full Chat from User Feedback**: Administrators can now easily navigate to the full conversation associated with a user feedback entry directly from the feedback modal, streamlining the review and troubleshooting process.
- 🎚️ **Intuitive Hybrid Search BM25-Weight Slider**: The numerical input for the BM25-Weight parameter in Hybrid Search has been replaced with an interactive slider, offering a more intuitive way to adjust the balance between lexical and semantic search. A "Default/Custom" toggle and clearer labels enhance usability and understanding of this key parameter.
- ⚙️ **Enhanced Bulk Function Synchronization**: The API endpoint for synchronizing functions has been significantly improved to reliably handle bulk updates. This ensures that importing and managing large libraries of functions is more robust and error-free for administrators.
- 🖼️ **Option to Disable Image Compression in Channels**: Introduced a new setting under Interface options to allow users to force-disable image compression specifically for images posted in channels, ensuring higher resolution for critical visual content.
- 🔗 **Custom CORS Scheme Support**: Introduced a new environment variable 'CORS_ALLOW_CUSTOM_SCHEME' that allows administrators to define custom URL schemes (e.g., 'app://') for CORS origins, enabling greater flexibility for local development or desktop client integrations.
- ♿ **Translatable and Accessible Banners**: Enhanced banner elements with translatable badge text and proper ARIA attributes (aria-label, aria-hidden) for SVG icons, significantly improving accessibility and screen reader compatibility.
- ⚠️ **OAuth Configuration Warning for Missing OPENID_PROVIDER_URL**: Added a proactive startup warning that notifies administrators when OAuth providers (Google, Microsoft, or GitHub) are configured but the essential 'OPENID_PROVIDER_URL' environment variable is missing. This prevents silent OAuth logout failures and guides administrators to complete their setup correctly.
- ♿ **Major Accessibility Enhancements**: Key parts of the interface have been made significantly more accessible. The user profile menu is now fully navigable via keyboard, essential controls in the Playground now include proper ARIA labels for screen readers, and decorative images have been hidden from assistive technologies to reduce audio clutter. Menu buttons also feature enhanced accessibility with 'aria-label', 'aria-hidden' for SVGs, and 'aria-pressed' for toggle buttons.
- ⚙️ **General Backend Refactoring**: Implemented various backend improvements to enhance performance, stability, and security, ensuring a more resilient and reliable platform for all users, including refining logging output to be cleaner and more efficient by conditionally including 'extra_json' fields and improving consistent metadata handling in vector database operations, and laying preliminary scaffolding for future analytics features.
- 🌐 **Localization & Internationalization Improvements**: Refined and expanded translations for Catalan, Danish, Korean, Persian, Polish, Simplified Chinese, and Spanish, ensuring a more fluent and native experience for global users across all supported languages.

### Fixed

- 🛡️ **Hardened Channel Message Security**: Fixed a key permission flaw that allowed users with channel access to edit or delete messages belonging to others. The system now correctly enforces that users can only modify their own messages, protecting data integrity in shared channels.
- 🛡️ **Hardened OAuth Security by Removing JWT from URL**: Fixed a critical security vulnerability where the authentication token was exposed in the URL after a successful OAuth login. The token is now transferred via a browser cookie, preventing potential leaks through browser history or server logs and protecting user sessions.
- 🛡️ **Hardened Chat Completion API Security**: The chat completion API endpoint now includes an explicit ownership check, ensuring non-admin users cannot access chats that do not belong to them and preventing potential unauthorized access.
- 🛠️ **Resilient Model Loading**: Fixed an issue where a failure in loading the model list (e.g., from a misconfigured provider) would prevent the entire user interface, including the admin panel, from loading. The application now gracefully handles these errors, ensuring the UI remains accessible.
- 🔒 **Resolved FIPS Self-Test Failure**: Fixed a critical issue that prevented Open WebUI from running on FIPS-compliant systems, specifically resolving the "FATAL FIPS SELFTEST FAILURE" error related to OpenSSL and SentenceTransformers, restoring compatibility with secure environments.
- 📦 **Redis Cluster Connection Restored**: Fixed an issue where the backend was unable to connect to Redis in cluster mode, now ensuring seamless integration with scalable Redis cluster deployments.
- 📦 **PGVector Connection Stability**: Fixed an issue where read-only operations could leave database transactions idle, preventing potential connection errors and improving overall database stability and resource management.
- 🛠️ **OpenAPI Tool Integration for Array Parameters Fixed**: Resolved a critical bug where external tools using array parameters (e.g., for tags) would fail when used with OpenAI models. The system now correctly generates the required 'items' property in the function schema, restoring functionality and preventing '400 Bad Request' errors.
- 🛠️ **Tool Creation for Users Restored**: Fixed a bug in the code editor where status messages were incorrectly prepended to tool scripts, causing a syntax error upon saving. All authorized users can now reliably create and save new tools.
- 📁 **Folder Knowledge Processing Restored**: Fixed a bug where files uploaded to folder and model knowledge bases were not being extracted or analyzed for Retrieval-Augmented Generation (RAG) when the 'Max Upload Count' setting was empty, ensuring seamless document processing and knowledge augmentation.
- 🧠 **Custom Model Knowledge Base Updates Recognized**: Fixed a bug where custom models linked to to knowledge bases did not automatically recognize newly added files to those knowledge bases. Models now correctly incorporate the latest information from updated knowledge collections.
- 📦 **Comprehensive Redis Key Prefixing**: Corrected hardcoded prefixes to ensure the REDIS_KEY_PREFIX is now respected across all WebSocket and task management keys. This prevents data collisions in multi-instance deployments and improves compatibility with Redis cluster mode.
- ✨ **More Descriptive OpenAI Router Errors**: The OpenAI-compatible API router now propagates detailed upstream error messages instead of returning a generic 'Bad Request'. This provides clear, actionable feedback for developers and API users, making it significantly easier to debug and resolve issues with model requests.
- 🔐 **Hardened OIDC Signout Flow**: The OpenID Connect signout process now verifies that the 'OPENID_PROVIDER_URL' is configured before attempting to communicate with it, preventing potential errors and ensuring a more reliable logout experience.
- 🍓 **Raspberry Pi Compatibility Restored**: Pinned the pyarrow library to version 20.0.0, resolving an "Illegal Instruction" crash on ARM-based devices like the Raspberry Pi and ensuring stable operation on this hardware.
- 📁 **Folder System Prompt Variables Restored**: Fixed a bug where prompt variables (e.g., '{{CURRENT_DATETIME}}') were not being rendered in Folder-level System Prompts. This restores an important capability for creating dynamic, context-aware instructions for all chats within a project folder.
- 📝 **Note Access in Knowledge Retrieval Fixed**: Corrected a permission oversight in knowledge retrieval, ensuring users can always use their own notes as a source for RAG without needing explicit sharing permissions.
- 🤖 **Title Generation Compatibility for GPT-5 Models**: Added support for 'gpt-5' models in the payload handler, which correctly converts the deprecated 'max_tokens' parameter to 'max_completion_tokens'. This resolves title generation failures and ensures seamless operation with the latest generation of models.
- ⚙️ **Correct API 'finish_reason' in Streaming Responses**: Fixed an issue where intermediate 'reasoning_content' chunks in streaming API responses incorrectly reported a 'finish_reason' of 'stop'. The 'finish_reason' is now correctly set to 'null' for these chunks, ensuring compatibility with third-party applications that rely on this field.
- 📈 **Evaluation Pages Stability**: Resolved a crash on the Leaderboard and Feedbacks pages when processing legacy feedback entries that were missing a 'rating' field. The system now gracefully handles this older data, ensuring both pages load reliably for all users.
- 🤝 **Reliable Collaborative Session Cleanup**: Fixed an asynchronous bug in the real-time collaboration engine that prevented document sessions from being properly cleaned up after all users had left. This ensures greater stability and resource management for features like Collaborative Notes.
- 🧠 **Enhanced Memory Stability and Security**: Refactored memory update and delete operations to strictly enforce user ownership, preventing potential data integrity issues. Additionally, improved error handling for memory queries now provides clearer feedback when no memories exists.
- 🧑‍⚖️ **Restored Admin Access to User Feedback**: Fixed a permission issue that blocked administrators from viewing or editing user feedback they didn't create, ensuring they can properly manage all evaluations across the platform.
- 🔐 **PGVector Encryption Fix for Metadata**: Corrected a SQL syntax error in the experimental 'PGVECTOR_PGCRYPTO' feature that prevented encrypted metadata from being saved. Document uploads to encrypted PGVector collections now work as intended.
- 🔍 **Serply Web Search Integration Restored**: Fixed an issue where incorrect parameters were passed to the Serply web search engine, restoring its functionality for RAG and web search workflows.
- 🔍 **Resilient Web Search Processing**: Web search retrieval now gracefully handles search results that are missing a 'snippet', preventing crashes and ensuring that RAG workflows complete successfully even with incomplete data from search engines.
- 🖼️ **Table Pasting in Rich Text Input Displayed Correctly**: Fixed an issue where pasting table text into the rich text input would incorrectly display it as code. Tables are now properly rendered as expected, improving content formatting and user experience.
- ✍️ **Rich Text Input TypeError Resolution**: Addressed a potential 'TypeError: ue.getWordAtDocPos is not a function' in 'MessageInput.svelte' by refactoring how the 'getWordAtDocPos' function is accessed and referenced from 'RichTextInput.svelte', ensuring stable rich text input behavior, especially after production restarts.
- ✏️ **Manual Code Block Creation in Chat Restored**: Fixed an issue where typing three backticks and then pressing Shift+Enter would incorrectly remove the backticks when "Enter to Send" mode was active. This ensures users can reliably create multi-line code blocks manually.
- 🎨 **Consistent Dark Mode Background**: Fixed an issue where the application background could incorrectly flash or remain white during page loads and refreshes in dark mode, ensuring a seamless and consistent visual experience.
- 🎨 **'Her' Theme Rendering Fixed**: Corrected a bug that caused the "Her" theme to incorrectly render as a dark theme in some situations. The theme now reliably applies its intended light appearance across all sessions.
- 📜 **Corrected Markdown Table Line Break Rendering**: Fixed an issue where line breaks ('<br>') within Markdown tables were displayed as raw HTML instead of being rendered correctly. This ensures that tables with multi-line cell content are now displayed as intended.
- 🚦 **Corrected App Configuration for Pending Users**: Fixed an issue where users awaiting approval could incorrectly load the full application interface, leading to a confusing or broken UI. This ensures that only fully approved users receive the standard app 'config', resulting in a smoother and more reliable onboarding experience.
- 🔄 **Chat Cloning Now Includes Tags, Folder Status, and Pinned Status**: When cloning a chat or shared chat, its associated tags, folder organization, and pinned status are now correctly replicated, ensuring consistent chat management.
- ⚙️ **Enhanced Backend Reliability**: Resolved a potential crash in knowledge base retrieval when referencing a deleted note. Additionally, chat processing was refactored to ensure model information is saved more reliably, enhancing overall system stability.
- ⚙️ **Floating 'Ask/Explain' Modal Stability**: Fixed an issue that spammed the console with errors when navigating away while a model was generating a response in the floating 'Ask' or 'Explain' modals. In-flight requests are now properly cancelled, improving application stability.
- ⚡ **Optimized User Count Checks**: Improved performance for user count and existence checks across the application by replacing resource-intensive 'COUNT' queries with more efficient 'EXISTS' queries, reducing database load.
- 🔐 **Hardened OpenTelemetry Exporter Configuration**: The OTLP HTTP exporter no longer uses a potentially insecure explicit flag, improving security by relying on the connection URL's protocol (HTTP/HTTPS) to ensure transport safety.
- 📱 **Mobile User Menu Closing Behavior Fixed**: Resolved an issue where the user menu would remain open on mobile devices after selecting an option, ensuring the menu correctly closes and returns focus to the main interface for a smoother mobile experience.
- 📱 **OnBoarding Page Display Fixed on Mobile**: Resolved an issue where buttons on the OnBoarding page were not consistently visible on certain mobile browsers, ensuring a functional and complete user experience across devices.
- ↕️ **Improved Pinned Models Drag-and-Drop Behavior**: The drag-and-drop functionality for reordering pinned models is now explicitly disabled on mobile devices, ensuring better usability and preventing potential UI conflicts or unexpected behavior.
- 📱 **PWA Rotation Behavior Corrected**: The Progressive Web App now correctly respects the device's screen orientation lock, preventing unwanted rotation and ensuring a more native mobile experience.
- ✏️ **Improved Chat Title Editing Behavior**: Changes to a chat title are now reliably saved when the user clicks away or presses Enter, replacing a less intuitive behavior that could accidentally discard edits. This makes renaming chats a smoother and more predictable experience.
- ✏️ **Underscores Allowed in Prompt Commands**: Fixed the validation for prompt commands to correctly allow the use of underscores ('\_'), aligning with documentation examples and improving flexibility in naming custom prompts.
- 💡 **Title Generation Button Behavior Fixed**: Resolved an issue where clicking the "Generate Title" button while editing a chat or note title would incorrectly save the title before generation could start. The focus is now managed correctly, ensuring a smooth and predictable user experience.
- ✏️ **Consistent Chat Input Height**: Fixed a minor visual bug where the chat input field's height would change slightly when toggling the "Rich Text Input for Chat" setting, ensuring a more stable and consistent layout.
- 🙈 **Admin UI Toggle Stability**: Fixed a visual glitch in the Admin settings where toggle switches could briefly display an incorrect state on page load, ensuring the UI always accurately reflects the saved settings.
- 🙈 **Community Sharing Button Visibility**: The "Share to Community" button on the feedback page is now correctly hidden when the Enable Community Sharing feature is disabled in the admin settings, ensuring the UI respects the configured sharing policy.
- 🙈 **"Help Us Translate" Link Visibility**: The "Help us translate" link in settings is now correctly hidden in deployments with specific license configurations, ensuring a cleaner interface for enterprise users.
- 🔗 **Robust Tool Server URL Handling**: Fixed an issue where providing a full URL for a tool server's OpenAPI specification resulted in an invalid path. The system now correctly handles both absolute URLs and relative paths, improving configuration flexibility.
- 🔧 **Improved Azure URL Detection**: The logic for identifying Azure OpenAI endpoints has been made more robust, ensuring all valid Azure URLs are now correctly detected for a smoother connection setup.
- ⚙️ **Corrected Direct Connection Save Logic**: Fixed a bug in the Admin Connections settings page by removing a redundant save action for 'Direct Connections', leading to more reliable and predictable behavior when updating settings.
- 🔗 **Corrected "Discover" Links**: The "Discover" links for models, prompts, tools, and functions now point to their specific, relevant pages on openwebui.com, improving content discovery for users.
- ⏱️ **Refined Display of AI Thought Duration**: Adjusted the display logic for AI thought (reasoning) durations to more accurately show very short thought times as "less than a second," improving clarity in AI process feedback.
- 📜 **Markdown Line Break Rendering Refinement**: Improved handling of line breaks within Markdown rendering for better visual consistency.
- 🛠️ **Corrected OpenTelemetry Docker Compose Example**: The docker-compose.otel.yaml file has been fixed and enhanced by removing duplicates, adding necessary environment variables, and hardening security settings, ensuring a more reliable out-of-box observability setup.
- 🛠️ **Development Script CORS Fix**: Corrected the CORS origin URL in the local development script (dev.sh) by removing the trailing slash, ensuring a more reliable and consistent setup for developers.
- ⬆️ **OpenTelemetry Libraries Updated**: Upgraded all OpenTelemetry-related libraries to their latest versions, ensuring better performance, stability, and compatibility for observability.

### Changed

- ❗ **Docling Integration Upgraded to v1 API (Breaking Change)**: The integration with the Docling document processing engine has been updated to its new, stable '/v1' API. This is required for compatibility with Docling version 1.0.0 and newer. As a result, older versions of Docling are no longer supported. Users who rely on Docling for document ingestion **must upgrade** their docling-serve instance to ensure continued functionality.
- 🗣️ **Admin-First Whisper Language Priority**: The global WHISPER_LANGUAGE setting now acts as a strict override for audio transcriptions. If set, it will be used for all speech-to-text tasks, ignoring any language specified by the user on a per-request basis. This gives administrators more control over transcription consistency.
- ✂️ **Datalab Marker API Language Selection Removed**: The separate language selection option for the Datalab Marker API has been removed, as its functionality is now integrated and superseded by the more comprehensive 'additional_config' parameter. Users should transition to using 'additional_config' for relevant language and processing settings.
- 📄 **Documentation and Releases Links Visibility**: The "Documentation" and "Releases" links in the user menu are now visible only to admin users, streamlining the user interface for non-admin roles.

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
