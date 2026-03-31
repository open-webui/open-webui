# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.12] - 2026-03-26

### Added

- 🌐 **Translation updates.** Translations for Simplified Chinese, Catalan, Portuguese (Brazil), Finnish, and Lithuanian were enhanced and expanded.

### Fixed

- 🔒 **Terminal server connection security.** Terminal server verification and policy saving now proxy through the backend, preventing API key exposure and CORS errors when connecting to in-cluster services. [Commit](https://github.com/open-webui/open-webui/commit/a6413257079a52fa4487eda36543f3955d0fbd53), [Commit](https://github.com/open-webui/open-webui/commit/4567cdc0d9cb7b42b6eba7b676c0ced3f4850d31)
- 🛠️ **Terminal tools exception handling.** Exceptions in middleware.py due to invalid return values from get_terminal_tools() have been resolved. [Commit](https://github.com/open-webui/open-webui/commit/52a06bd48aff34fb2211aac2879f0cd028129267)
- 📦 **Missing beautifulsoup4 dependency.** Users can now start Open WebUI using uvx without encountering the "bs4 module missing" error. [Commit](https://github.com/open-webui/open-webui/commit/1994d65306bbcc7406584e1bfef82f5d353fc91c)
- 🔌 **API files list error.** The /api/v1/files/ endpoint no longer returns a 500 error, fixing a regression that prevented file listing via the API. [Commit](https://github.com/open-webui/open-webui/commit/11f52921dc21c2dc61c03f12bcdf6f19140a350c)
- 📜 **License data loading.** License data now loads correctly, displaying the expected color and logo in the interface. [Commit](https://github.com/open-webui/open-webui/commit/16335f866ea4cedf00c4971963622fcc1fe02d82)
- 👑 **Admin model visibility.** Administrators can now see models even when no access control is configured yet, allowing them to manage all available models. [Commit](https://github.com/open-webui/open-webui/commit/f3f8f9874f55282603c2650b91801640cb3f69cb)
- 📊 **Tool call embed visibility.** Rich UI embeds from tool calls (like visualizations) are now rendered outside collapsed groups and remain visible without requiring manual expansion. [Commit](https://github.com/open-webui/open-webui/commit/4c872a8d128757d4a6f311fb86bc382af2ba5d0d), [Commit](https://github.com/open-webui/open-webui/commit/308fa924a5b2b7e08cd1e8f15b9c8c96e1de8f02)

## [0.8.11] - 2026-03-25

### Added

- 🔀 **Responses API streaming improvements.** The OpenAI proxy now properly handles tool call streaming and re-invocations in the Responses API, preventing duplicate tool calls and preserving output during model re-invocations. [Commit](https://github.com/open-webui/open-webui/commit/93415a48e8893139db13d02d0a6d24e8604a2ac5), [Commit](https://github.com/open-webui/open-webui/commit/f8b3a32caf00dad76687fd8fe698b86f304f3997), [Commit](https://github.com/open-webui/open-webui/commit/2ae47cf20057e92a83fd618b938f3ee9bb124e5b), [Commit](https://github.com/open-webui/open-webui/commit/adcbba34f8bbfbab3e4041269a084f2b71c076d9)
- 🔀 **Responses API stateful sessions.** Administrators can now enable experimental stateful session support via the ENABLE_RESPONSES_API_STATEFUL environment variable, allowing compatible backends to store responses server-side with previous_response_id anchoring for improved multi-turn conversations. [Commit](https://github.com/open-webui/open-webui/commit/dfc2dc2c0bd298cb4bfcf212ef11223586aa54f1)
- 📄 **File viewing pagination.** The view_file and view_knowledge_file tools now support pagination with offset and max_chars parameters, allowing models to read large files in chunks. [Commit](https://github.com/open-webui/open-webui/commit/5d7766e1b6f7ca7749c5a5a780d7b1bb2da28a2f)
- 🗺️ **Knowledge search scoping.** The search_knowledge_files tool now respects model-attached knowledge, searching only within attached knowledge bases and files when available. [Commit](https://github.com/open-webui/open-webui/commit/0f0ba7dadd043460d205477fd3b57556aa970847)
- 🛠️ **Tool HTML embed context.** Tools can now return custom context alongside HTML embeds by using a tuple format, providing the LLM with actionable information instead of a generic message. [#22691](https://github.com/open-webui/open-webui/pull/22691)
- 🔒 **Trusted role header configuration.** Administrators can now configure the WEBUI_AUTH_TRUSTED_ROLE_HEADER environment variable to set user roles (admin, user, or pending) via a trusted header from their identity provider or reverse proxy. [#22523](https://github.com/open-webui/open-webui/pull/22523)
- 🔑 **OIDC authorization parameter injection.** Administrators can now inject extra parameters into the OIDC authorization redirect URL via the OAUTH_AUTHORIZE_PARAMS environment variable, enabling IdP pre-selection for brokers like CILogon and Keycloak. [#22863](https://github.com/open-webui/open-webui/issues/22863), [Commit](https://github.com/open-webui/open-webui/commit/69171a4c8bb7f995461b4a2feef194f112b32004)
- 🔑 **Google OAuth session persistence.** Administrators can now configure Google OAuth to issue refresh tokens via the GOOGLE_OAUTH_AUTHORIZE_PARAMS environment variable, preventing OAuth sessions from expiring after one hour and ensuring tools and integrations that rely on OAuth tokens remain functional. [#22652](https://github.com/open-webui/open-webui/pull/22652)
- 🔌 **Embed prompt confirmation.** Interactive tool embeds can now submit prompts to the chat without requiring same-origin access, showing a confirmation dialog for cross-origin requests to prevent abuse. [#22908](https://github.com/open-webui/open-webui/pull/22908)
- 🏮 **Tool binary response handling.** Tool servers can now return binary data such as images, which are properly processed and displayed in chat for both multimodal and non-multimodal models. [Commit](https://github.com/open-webui/open-webui/commit/1c25b06dca83ad491b4dc3d373b1c215a7a8fd3e), [Commit](https://github.com/open-webui/open-webui/commit/108a019cb8e63a533250abe84f2b6f2b7c2131c4)
- ⚡ **Svelte upgrade performance.** Page and markdown rendering are now approximately 25% faster across the board, with significantly less memory usage for smoother UI interactions. [#22611](https://github.com/open-webui/open-webui/issues/22611)
- 🧩 **Model and filter lookup optimization.** Model and filter membership lookups are now faster thanks to optimized data structure operations during model list loading. [Commit](https://github.com/open-webui/open-webui/commit/7eae377c01f8d2de94a694b72279f769c82658cd)
- 💨 **Chat render throttling.** Chat message rendering now uses requestAnimationFrame batching to stay smooth during rapid model responses, preventing dropped frames when fast models send many events per second. [#22947](https://github.com/open-webui/open-webui/pull/22947)
- 🚀 **Function list API optimization.** The functions list API now returns only essential metadata without function source code, reducing payload sizes by over 99% and making the Functions admin page load significantly faster. [#22788](https://github.com/open-webui/open-webui/pull/22788)
- ✨ **Smoother loading animation.** The loading shimmer animation now looks smoother and more natural, with softer highlight colors. [#22516](https://github.com/open-webui/open-webui/pull/22516)
- 🧪 **Terminal connection verification.** Users can now verify their terminal server connection is working before saving the configuration, making setup more reliable. [#22567](https://github.com/open-webui/open-webui/pull/22567)
- 📁 **Chat folder emoji reset.** Users can now reset chat folder emojis back to the default icon using a "Reset to Default" button in the emoji picker, making it easier to revert custom icons. [#22554](https://github.com/open-webui/open-webui/pull/22554)
- 📊 **Metrics export interval configuration.** Administrators can now control OpenTelemetry metrics export frequency via the OTEL_METRICS_EXPORT_INTERVAL_MILLIS environment variable, enabling cost optimization for metrics services like Grafana Cloud. [#22529](https://github.com/open-webui/open-webui/pull/22529)
- 🏥 **Readiness probe endpoint.** A new /ready endpoint is now available for Kubernetes deployments, returning 200 only after startup completes and database/Redis are reachable, enabling more reliable container orchestration. [#22507](https://github.com/open-webui/open-webui/pull/22507)
- 🔩 **Tool server timeout configuration.** Administrators can now configure a separate HTTP timeout for tool server requests via the AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER environment variable, enabling fine-tuned control over how long tool calls are allowed to take. [Commit](https://github.com/open-webui/open-webui/commit/a3238aa79f344765f5b62cb64eba71ffd001abaf)
- 📌 **Knowledge file previews.** Knowledge base files can now be opened in a new tab directly from the file list, making it easier to view content without downloading. [#22629](https://github.com/open-webui/open-webui/pull/22629)
- 🎯 **Knowledge tool hybrid search support.** The built-in query_knowledge_files tool now respects hybrid search and reranking settings, matching the behavior of the middleware RAG pipeline. [Commit](https://github.com/open-webui/open-webui/commit/9a2c60d5954ecbc172d09e9955d52a07d135dcbc)
- 🗣️ **Temporary chat folder support.** Temporary chats can now use folder-level system prompts and knowledge files, making them more powerful for quick explorations. [Commit](https://github.com/open-webui/open-webui/commit/adcc50d3370301afd5561e0f58ff6f3ab3750818)
- 📡 **Terminal port previews.** Detected ports in the File Navigator can now be previewed inline with a browser-style view, navigation controls, and an address bar, instead of only opening in a new tab. [Commit](https://github.com/open-webui/open-webui/commit/689061822173e561a153290b2bb816f4cb6f4959), [Commit](https://github.com/open-webui/open-webui/commit/1dc647f43b1929f5c4d1af393a90a47f56cb745e)
- ✏️ **File renaming.** Files and folders in the File Navigator can now be renamed by double-clicking or using the context menu, with Enter to confirm and Escape to cancel. [Commit](https://github.com/open-webui/open-webui/commit/637cd136c2271baf4787815bc8bc25241626a943)
- 🧭 **File Navigator navigation history.** The File Navigator toolbar now includes Back and Forward buttons for navigating through folder and file history, similar to a web browser. [Commit](https://github.com/open-webui/open-webui/commit/3a4b862e818c69fff6f3a3c67b50c51aa00c03e9)
- 🗑️ **Delete connection confirmations.** Users are now prompted with a confirmation dialog before deleting connections, preventing accidental deletions. [Commit](https://github.com/open-webui/open-webui/commit/157ff57c40bc40c53bc608828dac3779e95c2ffa)
- 📦 **Document loader fallbacks.** Excel and PowerPoint files can now be processed even when the unstructured package is not installed, using pandas and python-pptx as fallback loaders. [Commit](https://github.com/open-webui/open-webui/commit/6862d618ee17f95d3cae78819ed993e7fbc7e632)
- 🧠 **Memory management search and sort.** Users can now search and sort their personal memories in the Memory management modal, making it easier to find specific memories. [Commit](https://github.com/open-webui/open-webui/commit/47ab4c71d50fd631b04c95f2febb085dd0a13083)
- 📦 **SBOM generation script.** A new script for generating CycloneDX Software Bill of Materials is now available in the scripts directory. [Commit](https://github.com/open-webui/open-webui/commit/39100eca4915e4fe86a6912aa97dde86ed72e015)
- ⚙️ **Ruff linter and formatter.** Added Ruff as the Python linter and formatter, replacing the black-based workflow for better code quality with near-instant execution. [#22576](https://github.com/open-webui/open-webui/pull/22576), [#22462](https://github.com/open-webui/open-webui/discussions/22462)
- 🖥️ **Offline code formatting support.** The black formatter for Python code editing is now bundled locally in the Docker image, enabling code formatting to work in air-gapped deployments where client browsers cannot reach PyPI. Formatting failures no longer block saves, allowing code to be preserved even when offline. [#22509](https://github.com/open-webui/open-webui/issues/22509), [Commit](https://github.com/open-webui/open-webui/commit/8507e5eb0d18896f1bbf990a00a4361aec171a30)
- ✏️ **Markdown file editing.** Users can now edit and save Markdown files directly in the file navigator, with empty files automatically switching to editor mode for immediate editing. [Commit](https://github.com/open-webui/open-webui/commit/47e47e42af682e7f75c8359999f7cdf969bf903e)
- 🍔 **Model bulk actions menu.** Users can now quickly enable, disable, show, or hide multiple models at once using a new hamburger menu on the workspace Models page filter bar, with actions respecting the current search and filter settings. [#22484](https://github.com/open-webui/open-webui/pull/22484)
- 📂 **Files list pagination.** The files list API now supports pagination, returning paginated results with a total count for easier navigation through large file collections. [Commit](https://github.com/open-webui/open-webui/commit/f9756de693a93e918c037d757afddb7defc847e4)
- 🖇 **Web fetch content length config.** Administrators can now configure the maximum characters to return from fetched URLs via WEB_FETCH_MAX_CONTENT_LENGTH environment variable or the admin settings page, instead of the previous hardcoded 50K limit. [Commit](https://github.com/open-webui/open-webui/commit/b171b0216b916745420c7caf513093a315ed9560), [#22774](https://github.com/open-webui/open-webui/issues/22774)
- 🤖 **Ollama Anthropic endpoint support.** The Ollama proxy now supports the Anthropic-compatible /v1/messages endpoint, allowing clients using the Anthropic API format to work through Open WebUI with proper authentication and model access controls. [Commit](https://github.com/open-webui/open-webui/commit/f23296b22d3304e5bfcd19151e5802eec55bd98f), [#22861](https://github.com/open-webui/open-webui/issues/22861)
- 📝 **Writing block rendering.** Responses from OpenAI models that include :::writing blocks are now rendered as formatted content in a styled container with a copy button, instead of displaying raw marker text. [#22672](https://github.com/open-webui/open-webui/issues/22672), [Commit](https://github.com/open-webui/open-webui/commit/53b8a1f71bd0cb0a0122175ad5210da492018728)
- 💡 **Memory deletion confirmation.** Users are now asked to confirm before deleting individual memory entries, with the memory content displayed for review. [#22888](https://github.com/open-webui/open-webui/pull/22888)
- 📓 **Multi-artifact HTML rendering.** Code blocks with multiple HTML sections now render as separate artifacts instead of merging into one, allowing models to display distinct interactive components. [Commit](https://github.com/open-webui/open-webui/commit/9a6bf78e14a13864e72db87426da4f5996abe716)
- 🚩 **Drag chats as references.** Users can now drag chats from the sidebar and drop them into the message input to add them as Reference Chats. [Commit](https://github.com/open-webui/open-webui/commit/ebb7ce2092efc8d78da4974623647dbd18b6e372)
- ⌨️ **Terminal system prompts.** Terminal servers can now provide custom system prompts that are automatically included when their tools are used. [Commit](https://github.com/open-webui/open-webui/commit/6a9d67b5bb4c93fd343b334bee3e37703dff59f6)
- 💾 **Terminal state persistence.** The selected terminal server and its enabled state now persist across page loads, making terminal usage more seamless. [Commit](https://github.com/open-webui/open-webui/commit/d577ff1e4af750dda09e558dac7edb8dd2470850)
- 💾 **Terminal folder downloads.** Users can now download folders as ZIP archives and bulk-download multiple selected files as a single ZIP directly from the File Navigator toolbar, making file exports faster and more convenient. [Commit](https://github.com/open-webui/open-webui/commit/3841e85abb3ea3e8d8b364dff0102f0124844d22), [Commit](https://github.com/open-webui/open-webui/commit/cf60b1882f1929200649b59f867289dea54e4210)
- 🔐 **MCP OAuth 2.1 static credentials.** MCP servers that require static client_id and client_secret can now be connected using a new OAuth 2.1 Static auth type, enabling integration with MCP servers that don't support dynamic client registration. [#22266](https://github.com/open-webui/open-webui/pull/22266), [Commit](https://github.com/open-webui/open-webui/commit/601bb783587a3e965cf88c148e4856b988655b13)
- 🎪 **Collapsible tool and thinking groups.** Consecutive tool calls and reasoning blocks are now grouped into a single collapsible summary (e.g., "Explored tool1, tool2"), keeping chat responses clean and readable while preserving full detail on expand. [#21604](https://github.com/open-webui/open-webui/issues/21604), [Commit](https://github.com/open-webui/open-webui/commit/261aec8c864646eb7215be0d5c14a79cad3cb93f)
- 🔄 **General improvements.** Various improvements were implemented across the application to enhance performance, stability, and security.
- 🌐 Translations for Finnish, Portuguese (Portugal), Catalan, Turkish, Japanese, Simplified Chinese, Traditional Chinese, Estonian, Spanish, Azerbaijani, and German were enhanced and expanded.

### Fixed

- 🔒 **Model access control bypass.** Fixed a security vulnerability where external clients could bypass model access controls by setting a URL parameter, preventing unauthorized access to restricted models. [Commit](https://github.com/open-webui/open-webui/commit/c0385f60ba049da48d2d5452068586d375303c37)
- 🛡️ **Terminal proxy path sanitization.** The terminal server proxy now properly sanitizes paths to prevent directory traversal and SSRF attacks, protecting against security vulnerabilities. [Commit](https://github.com/open-webui/open-webui/commit/f9d38a073fae32032ed44073cf2817cba20210bb)
- 🛡️ **Tool configuration access control.** Tool configuration endpoints now properly verify user permissions, preventing unauthorized access to tool settings. [Commit](https://github.com/open-webui/open-webui/commit/bc5b3ec6b8ec0fef894eb8046c636ee33688b8c4)
- 🗝️ **Tool valves access control.** The tool user valves endpoints now properly verify ownership and access grants before returning or updating configuration, with appropriate 404 responses for missing tools and 401 for unauthorized access. [Commit](https://github.com/open-webui/open-webui/commit/f949d17db1e62e0b79aecbbcbcabe3d57d8d4af6)
- 🔐 **Collaborative document authorization.** Fixed a security vulnerability in collaborative documents where authorization could be bypassed using alternative document ID formats, preventing unauthorized access to notes. [Commit](https://github.com/open-webui/open-webui/commit/3107a5363d13c899a995c930cbb1121a80f754f9)
- 🔏 **OAuth session persistence.** Users logging in via OAuth or OIDC providers now stay logged in for the configured JWT expiry duration instead of being logged out when closing the browser. [#22809](https://github.com/open-webui/open-webui/pull/22809)
- 🚪 **OAuth sub claim configuration crash.** Using the OAUTH_SUB_CLAIM environment variable no longer causes crashes during token exchange requests, fixing a missing configuration registration. [#22865](https://github.com/open-webui/open-webui/pull/22865)
- 🔍 **OAuth discovery header parsing.** The OAuth protected resource discovery now correctly handles both quoted and unquoted values in the WWW-Authenticate header, fixing compatibility with MCP servers that return unquoted metadata. [#22646](https://github.com/open-webui/open-webui/discussions/22646), [Commit](https://github.com/open-webui/open-webui/commit/fe7e002fea7283abcf901e22de5c8a7d86e336ea)
- 👤 **Admin OAuth group sync.** Admin user group memberships from OAuth and LDAP providers are now properly synced to Open WebUI, fixing a limitation where admin role excluded users from group updates. [#22537](https://github.com/open-webui/open-webui/pull/22537), [Commit](https://github.com/open-webui/open-webui/commit/a1aceb5f879abd130ef83085d98a0d51316a8fc3)
- 🎫 **Password change complexity validation.** Password complexity rules are now properly enforced when users change their password, closing a security gap where new passwords could bypass configured complexity requirements. [Commit](https://github.com/open-webui/open-webui/commit/bd8aa3b6a0b6a2320f41b20a51b9842f39aadb7f)
- 🔏 **OAuth role enforcement.** OAuth role management now properly denies access when a user's roles don't match any configured OAUTH_ALLOWED_ROLES or OAUTH_ADMIN_ROLES, instead of silently bypassing the restriction. [#13676](https://github.com/open-webui/open-webui/issues/13676), [#15551](https://github.com/open-webui/open-webui/issues/15551), [Commit](https://github.com/open-webui/open-webui/commit/6d7744c21903ec5a9ad951770dea76e9ba19cbcc)
- 🔑 **Microsoft Entra ID role claim preservation.** Role claims from Microsoft Entra ID tokens are now preserved during OAuth login, fixing ENABLE_OAUTH_ROLE_MANAGEMENT for Microsoft OAuth which was previously ignored because the userinfo endpoint stripped the roles claim. [#20518](https://github.com/open-webui/open-webui/issues/20518), [Commit](https://github.com/open-webui/open-webui/commit/aa2f7fbe5229c3985ce427602069cdeababda481)
- 🔍 **SCIM group filtering.** The SCIM endpoint now properly handles displayName and externalId filters when provisioning groups from identity providers like Microsoft Entra ID, preventing all groups from being returned instead of the filtered subset. [#21543](https://github.com/open-webui/open-webui/pull/21543)
- 🔐 **Forwarded allow IPs configuration.** The FORWARDED_ALLOW_IPS environment variable is now properly respected by the startup scripts instead of being hardcoded to '\*', allowing administrators to restrict which proxies are trusted for request forwarding. [#22539](https://github.com/open-webui/open-webui/issues/22539), [Commit](https://github.com/open-webui/open-webui/commit/0aebdd5f83cd1d811009edcbb2bec432a34e7c81)
- 🍪 **Model list auth cookie forwarding.** Model list requests to backends that require cookie-based authentication now properly forward auth headers and cookies, preventing "Unauthorized" errors when loading models. [Commit](https://github.com/open-webui/open-webui/commit/76ece4049e96bd6890593f17a946a9af6b082fab)
- 🔱 **Model lookup race condition.** Fixed a race condition in Redis model storage that caused intermittent "model not found" errors in multi-replica deployments under heavy load, by eliminating the window between hash deletion and updates. [Commit](https://github.com/open-webui/open-webui/commit/ee901fcd2ca82d7a7dad48170c64df782d3e040a)
- 🎚️ **Bulk model action reliability.** Bulk enable, disable, show, and hide operations in the admin Models settings now properly refresh the model list after completion, ensuring changes are reflected immediately and correct toast notifications are shown. [#22962](https://github.com/open-webui/open-webui/pull/22962), [Commit](https://github.com/open-webui/open-webui/commit/75932be880f3b86f78f00b4352b9f1350b8f53fa), [Commit](https://github.com/open-webui/open-webui/commit/15ae3f588b1aa4ddb686ae68afebd6064036a201)
- 🔄 **Paginated list duplicates.** Fixed duplicate items appearing in paginated lists when loading more items in chats, knowledge, notes, and search across the UI. [Commit](https://github.com/open-webui/open-webui/commit/58e78e8946fb3644107489fe8e01b17709302b2f)
- 🧽 **Duplicate chat list refresh.** Sending messages no longer triggers duplicate sidebar chat list refreshes, eliminating an unnecessary database query that was already handled by the save and completion handlers. [#22982](https://github.com/open-webui/open-webui/pull/22982)
- 🧹 **Chat history save optimization.** The chat list is no longer refreshed on every chat history save, branch navigation, or edit — only on meaningful state changes like new chat creation, title generation, and response completion. [#22983](https://github.com/open-webui/open-webui/pull/22983)
- 💬 **Message queue responsiveness.** The message queue no longer waits for background tasks like title generation and follow-up suggestions to complete, allowing users to send new messages immediately after a response finishes without unnecessary delays. [Commit](https://github.com/open-webui/open-webui/commit/486c004cbb43f15d5c3e31561f51f22effff1f6c), [#22565](https://github.com/open-webui/open-webui/issues/22565)
- 🗄️ **Migration reliability.** Database migrations no longer fail when chat data has unexpected format, making upgrades more reliable. [#22588](https://github.com/open-webui/open-webui/pull/22588), [#22568](https://github.com/open-webui/open-webui/issues/22568)
- 🫧 **Memory modal event bubbling.** Fixed an issue where clicking the Delete button in the Memory management modal would also open the Edit Memory modal due to event bubbling. [#22783](https://github.com/open-webui/open-webui/issues/22783)
- 🧩 **Memory tool registration.** Models with capabilities.memory: true now correctly have memory tools available for execution, fixing a retry loop where add_memory appeared in the tool schema but was not registered for backend execution. [#22666](https://github.com/open-webui/open-webui/issues/22666), [#22675](https://github.com/open-webui/open-webui/pull/22675), [Commit](https://github.com/open-webui/open-webui/commit/d9339919046c3e977f313f603782d220aab4257f)
- 📝 **Input variables modal crash.** Fixed a crash that occurred when selecting custom prompts with prompt variables, causing the Input Variables modal to display an infinite loading spinner instead of the variable input fields. [#22748](https://github.com/open-webui/open-webui/issues/22748), [Commit](https://github.com/open-webui/open-webui/commit/0dcd6ac983bede06b8477179192154467f5b24a2)
- 🪛 **Function list API crash fix.** Fixed a 500 error on the functions list API endpoint that was introduced by the recent optimization, by adding proper model configuration for SQLAlchemy ORM objects. [#22924](https://github.com/open-webui/open-webui/pull/22924)
- 🗂️ **Sidebar chat menu closure.** Sidebar chat dropdown menus now close properly after clicking "Clone", "Share", "Download", "Rename", "Pin", "Move", "Archive", or "Delete", instead of remaining visible. [#22884](https://github.com/open-webui/open-webui/pull/22884), [#22784](https://github.com/open-webui/open-webui/issues/22784)
- 🧭 **Chat deletion and archive redirection.** Users are now redirected to the chat list when deleting or archiving the currently active chat, instead of being left on a stale chat page. [#22755](https://github.com/open-webui/open-webui/pull/22755)
- 🚩 **User menu navigation fix.** Clicking Playground or Admin Panel from the user menu now uses client-side routing instead of causing full page reloads, restoring smooth SPA navigation. [Commit](https://github.com/open-webui/open-webui/commit/7ffcd3908ee90f88a4c4684d6cd6e75efd117461)
- 🔧 **Tool server connection persistence.** Fixed a bug where tool server connection updates were not being saved to persistent storage, ensuring OAuth client information is now properly preserved. [Commit](https://github.com/open-webui/open-webui/commit/b8ea267f8ec3931de55db7801156b9c07d3ad5f6)
- 🔩 **Tool server index bounds checking.** Tool servers with invalid indices no longer crash the application with IndexError after upgrades, preventing tool server configuration loss. [#22490](https://github.com/open-webui/open-webui/issues/22490), [Commit](https://github.com/open-webui/open-webui/commit/8da29566a1f81c38e80009bdea3ce4d9be860605)
- 🔌 **Tool server frontend timeout.** Fetch requests to external tool servers now time out after 10 seconds, preventing the UI from hanging indefinitely when a configured tool server is unreachable. [#22543](https://github.com/open-webui/open-webui/issues/22543), [Commit](https://github.com/open-webui/open-webui/commit/adf7af34ff934319a35470c572237d2d08f1de0b)
- 🔌 **MCP OAuth tool auto-selection.** MCP tools requiring OAuth authentication are now automatically re-selected after completing the auth flow, instead of leaving users to manually re-enable the tool on return to the chat. [#22994](https://github.com/open-webui/open-webui/issues/22994), [#22995](https://github.com/open-webui/open-webui/pull/22995), [Commit](https://github.com/open-webui/open-webui/commit/4d50001c4192c609b1010626ebb6496692823873)
- 🏷️ **Channel @mentions.** Direct connection models no longer appear in channel @mention suggestions, preventing confusion since they don't work in channels. [#22553](https://github.com/open-webui/open-webui/issues/22553), [Commit](https://github.com/open-webui/open-webui/commit/0a87c1ecd078320a08c4cc62d41fe8727fb3b5f7)
- 📎 **Channel message attachments.** Users can now press Enter to send messages with only file or image attachments in channels, direct messages, and threads, aligning with the behavior of the Send button. [#22752](https://github.com/open-webui/open-webui/pull/22752)
- 🗣️ **Image-only message handling.** Models like Gemini and Claude no longer fail when receiving messages with only file or image attachments and no text, by stripping empty text content blocks before sending to the API. [Commit](https://github.com/open-webui/open-webui/commit/ea515fa26e11faac146c48a5e3a2a284e1792bb3), [#22880](https://github.com/open-webui/open-webui/issues/22880)
- 🧹 **Channel thread sidebar cleanup.** The thread sidebar in channels and direct messages now automatically closes when the parent message is deleted, preventing orphaned threads. [#22890](https://github.com/open-webui/open-webui/pull/22890)
- 💡 **Chat input suggestion modal.** The suggestion modal for tags, mentions, and commands now correctly reappears when backspacing into a trigger character after it was dismissed. [#22899](https://github.com/open-webui/open-webui/pull/22899)
- ⏱️ **Chat action button timing.** Action buttons under assistant messages no longer appear prematurely when switching chats while a response is still streaming. [Commit](https://github.com/open-webui/open-webui/commit/ecba37070d6eb3cb033195a070b6c4ab5f396415), [#22891](https://github.com/open-webui/open-webui/issues/22891)
- 💬 **Skill and model mention persistence.** Skills selected via $ and models selected via @ in the chat input are now properly restored after a page refresh, instead of reverting to plain text while losing their interactive state. [#22913](https://github.com/open-webui/open-webui/issues/22913), [Commit](https://github.com/open-webui/open-webui/commit/be21db706993c0db95ac09509dfdb023de64daff)
- 🧹 **Webhook profile image errors.** Fixed 404 errors appearing in the browser console when scrolling through channel messages sent by webhooks, by skipping the user profile preview for webhook senders. [#22893](https://github.com/open-webui/open-webui/pull/22893)
- 🧮 **Logit bias parameter handling.** Using logit_bias parameters no longer causes errors when the input is already in dictionary format. [#22597](https://github.com/open-webui/open-webui/issues/22597), [Commit](https://github.com/open-webui/open-webui/commit/e34ed72e1e958505e940b74bf1c6a4808640bd17)
- 🪛 **Temp chat tool calling.** Temporary chats now properly preserve tool call information, fixing native tool calling with JSON schema that was previously broken. [#22475](https://github.com/open-webui/open-webui/pull/22475), [Commit](https://github.com/open-webui/open-webui/commit/bcd313c363ca50d71aa80bcb2f29c81fad3dff37)
- 🔗 **Multi-system message merging.** Models with strict chat templates like Qwen no longer fail when multiple pipeline stages inject separate system messages, as all system messages are now merged into one at the start. [#22505](https://github.com/open-webui/open-webui/issues/22505), [Commit](https://github.com/open-webui/open-webui/commit/631bd20c3537ce85bbaec02f9e0049c88fa8fdd4)
- 📜 **Public note access.** Opening public notes via direct share link no longer returns a 500 error caused by a missing function import. [#22680](https://github.com/open-webui/open-webui/issues/22680), [Commit](https://github.com/open-webui/open-webui/commit/566e25569e5e7d9c1e42db840ba4ba578887d208)
- 👤 **Terminal access user visibility.** The terminal connection access dialog now shows the currently logged-in user when searching for users to grant access, fixing an issue where users with identical display names were filtered incorrectly. [#22491](https://github.com/open-webui/open-webui/issues/22491), [Commit](https://github.com/open-webui/open-webui/commit/4a8f995c3fd4602ec2aaccc07efc4e8504dda84d)
- 👥 **User groups display.** User groups in the admin panel profile preview now wrap properly instead of overflowing horizontally, with a scrollbar when the list is long. [#22547](https://github.com/open-webui/open-webui/pull/22547)
- 🔧 **Model list drag-and-drop.** Fixed drag-and-drop reordering of models in admin settings, preventing UI glitches and state synchronization issues. [Commit](https://github.com/open-webui/open-webui/commit/753589e51ccbbe5c4f78a7d13e19c67e6c0000d7)
- 🖼️ **Model profile image fallbacks.** Model profile images now display a fallback icon when they fail to load, and model icons no longer disappear on paginated Models pages in admin and workspace settings. [#22485](https://github.com/open-webui/open-webui/pull/22485)
- 🖼️ **Profile image fallbacks.** Added fallback handlers for model and user profile images throughout the chat interface, preventing broken image icons when avatars fail to load. [#22486](https://github.com/open-webui/open-webui/pull/22486)
- 🧲 **RAG thinking model support.** Knowledge base queries now correctly parse JSON responses from thinking models like GLM-5 and DeepSeek-R1 by stripping their reasoning blocks before JSON extraction. [#22400](https://github.com/open-webui/open-webui/pull/22400)
- 🔍 **RAG query generation robustness.** The RAG query generation, web search, and image generation handlers now correctly extract JSON from model responses containing thinking tags by finding the last JSON block instead of the first, preventing "No sources found" errors with thinking models. [#21888](https://github.com/open-webui/open-webui/issues/21888), [Commit](https://github.com/open-webui/open-webui/commit/c0fcbc5b4cb29012e2913983c632edc5d24b9aea)
- 🔍 **Ollama embedding robustness.** Ollama embedding requests now include the truncate parameter to handle inputs exceeding the context window, preventing 500 errors when processing long documents. Error messages from failed embedding requests are also now properly surfaced instead of being silently swallowed. [#22671](https://github.com/open-webui/open-webui/issues/22671), [Commit](https://github.com/open-webui/open-webui/commit/d738044f47c70c755bec9bf244aa11878fe98d9c)
- 🔄 **Ollama embedding retry logic.** Embedding requests to Ollama now retry with exponential backoff when encountering 503 errors (such as when the model reloads mid-processing), preventing files from being silently dropped from knowledge bases. [#22571](https://github.com/open-webui/open-webui/issues/22571), [Commit](https://github.com/open-webui/open-webui/commit/8b6fa1f4ab6099a305de08706621075c205f65c4)
- 🗄️ **Oracle 23AI hybrid search.** Fixed an UnboundLocalError that occurred when using hybrid search with Oracle 23AI as the vector store, preventing knowledge base queries from failing. [Commit](https://github.com/open-webui/open-webui/commit/fcf720835285a4cea10fc1ebed0b454971463b20), [#22616](https://github.com/open-webui/open-webui/issues/22616)
- 🌐 **Dynamic HTML language attribute.** The HTML lang attribute now dynamically updates when users change their interface language, preventing browsers from triggering unwanted translation popups. [Commit](https://github.com/open-webui/open-webui/commit/de5e0fbc00e7abcd84e1272c301b0707f8ea5ac6)
- 📐 **File upload deduplication.** Attaching files that are already in the chat no longer triggers duplicate uploads. [Commit](https://github.com/open-webui/open-webui/commit/10f06a64fed474e9958b96295a953e0eebf9e4be)
- 🕵️ **Serper.dev search results.** Fixed web search results not displaying properly when using the Serper.dev provider by using the correct API response field. [#22869](https://github.com/open-webui/open-webui/pull/22869)
- 🔲 **Markdown task list checkbox styling.** Fixed task list checkboxes in markdown rendering to display consistently without shrinking in narrow layouts. [#22886](https://github.com/open-webui/open-webui/pull/22886)
- 🎨 **Artifacts sidebar tab background fix.** The Artifacts sidebar now correctly updates and displays when switching back to a browser tab that was in the background, ensuring artifacts are visible without requiring a manual refresh. [#22889](https://github.com/open-webui/open-webui/issues/22889)
- 🔃 **Chat input URL indexing fix.** Fixed an issue where URLs could be indexed twice when using multiple triggers followed by backspace and re-entering a URL. [#22749](https://github.com/open-webui/open-webui/issues/22749)
- 🔎 **Search modal chat preview avatars.** Fixed assistant profile images not displaying in the chat preview pane of the Search Modal. [#22782](https://github.com/open-webui/open-webui/pull/22782)
- 📋 **Prompts search pagination fix.** Fixed a bug where searching prompts from a paginated page would incorrectly use the current page number, resulting in "No prompts found" even when matching results existed. [#22912](https://github.com/open-webui/open-webui/pull/22912)
- 🗂️ **Reasoning block copy cleanup.** Copied chat responses no longer include reasoning block content or excess whitespace, ensuring only the intended message text is captured. [#22786](https://github.com/open-webui/open-webui/issues/22786), [Commit](https://github.com/open-webui/open-webui/commit/4f0e57420154800946394bc986b2c691462b2782)
- 🔤 **Emoji removal for text normalization.** Fixed the emoji removal function used in search and title generation to correctly handle all emoji types, including those with variation selectors (❤️, ☀️, ✅), keycap sequences (1️⃣), and ZWJ family sequences (👨‍👩‍👧‍👦). [#22915](https://github.com/open-webui/open-webui/pull/22915)
- ⏹️ **Task cancellation status tracking.** Cancelled tasks now correctly mark only the affected messages as done instead of clearing all task statuses for the chat, ensuring proper status tracking when multiple messages have pending tasks. [#22743](https://github.com/open-webui/open-webui/pull/22743)
- 🎨 **Filter icon display fix.** Fixed filter icons showing the wrong icon after removing one of multiple active filters below the chat input. [#22862](https://github.com/open-webui/open-webui/pull/22862)
- 📊 **Channel message data loading.** Fixed redundant 404 API calls that occurred when rendering channel messages, preventing unnecessary requests and console errors. [#22894](https://github.com/open-webui/open-webui/pull/22894)
- 👻 **Response message skeleton display.** Fixed an issue where the skeleton loader would incorrectly show or hide based on complex status history conditions, by extracting the visibility logic into a cleaner reactive variable. [Commit](https://github.com/open-webui/open-webui/commit/5df4277216fbb9de603fdf4289f8366292568234)
- 🐛 **Shared chat viewing crash.** Shared chats can now be viewed by unauthenticated users without crashing, with proper fallback handling for missing user profile information. [#22751](https://github.com/open-webui/open-webui/pull/22751), [#22742](https://github.com/open-webui/open-webui/issues/22742)
- 🛠️ **Plugin ID sanitization.** Creating Functions or Tools with emojis or special characters in their names now generates valid IDs that pass backend validation, instead of failing with an error. [#22695](https://github.com/open-webui/open-webui/pull/22695)
- 📋 **Chat title preservation.** Regenerating responses or using branches no longer overwrites user-specified chat titles when auto-naming is disabled, by checking the full chat message count instead of just the current branch. [#22754](https://github.com/open-webui/open-webui/pull/22754)
- 🎧 **Read Aloud in chat preview.** The Read Aloud button in the Search Chats modal preview no longer causes crashes, and TTS functionality is now properly hidden in read-only chat contexts. [Commit](https://github.com/open-webui/open-webui/commit/d8fa0f426a88f5c27b3216b7db35e1db47bbba28)
- 📡 **Heartbeat event loop blocking.** The WebSocket heartbeat handler no longer blocks the event loop when updating user activity, improving responsiveness under heavy load with many concurrent connections. [#22980](https://github.com/open-webui/open-webui/pull/22980)
- 🗝️ **Message upsert API reliability.** The message upsert API endpoint no longer crashes when called, fixing an error where a database session was incorrectly passed to a function that doesn't accept it. [#22959](https://github.com/open-webui/open-webui/issues/22959), [Commit](https://github.com/open-webui/open-webui/commit/70285fb6cad26b50d783583b68be5227ace16055)
- 🔓 **Forward auth proxy compatibility.** Fixed error pages that could appear when using authenticating reverse-proxies by properly handling 401 responses from background API requests, allowing the browser to re-authenticate with the identity provider. [#22942](https://github.com/open-webui/open-webui/pull/22942)
- 🔃 **Tool call streaming display.** Sequential tool calls are now properly accumulated during streaming, fixing an issue where completed tool calls could disappear from the display before the next tool call finished streaming. [Commit](https://github.com/open-webui/open-webui/commit/a9c5c787b9f6b10491924d38645042064b3c941e)
- 🧠 **Reasoning spinner content preservation.** Prior assistant content and tool call blocks no longer disappear during the reasoning spinner when responding after tool execution. [#23001](https://github.com/open-webui/open-webui/pull/23001)
- 🖥️ **Pyodide file list refresh.** Files created or modified during manual code execution now appear immediately in the pyodide files list without requiring a browser tab refresh. [Commit](https://github.com/open-webui/open-webui/commit/5c4062c64841974bf193ff321d92d10f28a09746)
- 🖱️ **Dropdown submenu hover stability.** Secondary hover menus like Download and Move now remain open while navigating into them, fixing an issue where an 8px gap between the trigger and submenu would cause the menu to disappear before a selection could be made. [#22744](https://github.com/open-webui/open-webui/issues/22744), [Commit](https://github.com/open-webui/open-webui/commit/cffbc3558e911abd6c4780cd028794b2f7282cd7)
- 📊 **Model tag normalization.** Model tags from backends that return them as string arrays are now properly normalized to object format, preventing crashes when filtering models by tag in the admin and workspace models pages. [#20819](https://github.com/open-webui/open-webui/issues/20819), [Commit](https://github.com/open-webui/open-webui/commit/90ca2e9b0f15cc9be7cf298fbefacaa45074cae9)
- 🎯 **Arena model sub-model settings.** Arena models now properly use the selected sub-model's settings — including RAG knowledge bases, web access, code interpreter, and tool capabilities — instead of the arena wrapper's empty defaults. [#16950](https://github.com/open-webui/open-webui/issues/16950), [Commit](https://github.com/open-webui/open-webui/commit/857d7e6f373d26a7a8989417c3a7fe99cdc03f20)
- 🧩 **Model editor default metadata.** The Model Editor now loads admin-configured default model metadata instead of hardcoded values, preventing admin defaults from being silently overwritten when users save models without realizing they were overriding system-wide settings. [#22996](https://github.com/open-webui/open-webui/issues/22996), [Commit](https://github.com/open-webui/open-webui/commit/cdc2b3bf850044051aafcd46f22fb25a1899788c)
- ✏️ **Rich text paste sanitization.** Copying and pasting text with HTML characters (like `<` or `>`) no longer corrupts the editor content, as the paste handler now properly escapes HTML entities before processing mentions and special syntax. [Commit](https://github.com/open-webui/open-webui/commit/94f877ff328d410339308ad2c566c9afcdf43014)

### Changed

- 🪝 **User webhooks disabled by default.** User webhook notifications are now disabled by default and properly gated by the ENABLE_USER_WEBHOOKS configuration, ensuring webhooks only fire when explicitly enabled. [Commit](https://github.com/open-webui/open-webui/commit/c24a4da17dbaddf47e2e0f865c1d602d0ff36ee6)
- 🧩 **MCP integration visibility.** MCP (Streamable HTTP) integrations are now hidden from user-level settings, matching the intended behavior where only administrators can configure MCP connections through the admin panel. User-level connections now show the connection type as read-only. [#22615](https://github.com/open-webui/open-webui/issues/22615), [Commit](https://github.com/open-webui/open-webui/commit/1eef5b4f6a718c0fcf3605f1ed62669aca07b454)
- 🧲 **Web search result limit.** The configured web search result count now acts as a maximum limit, preventing models from requesting more results than administrators allow. [#22577](https://github.com/open-webui/open-webui/pull/22577)

## [0.8.10] - 2026-03-08

### Added

- 🔐 **Custom OIDC logout endpoint.** Administrators can now configure a custom OpenID Connect logout URL via OPENID_END_SESSION_ENDPOINT, enabling logout functionality for OIDC providers that require custom endpoints like AWS Cognito. [Commit](https://github.com/open-webui/open-webui/commit/3f350f865920daf2844769a758b2d2e6a7ee3efa)
- 🗄️ **MariaDB Vector community support.** Added MariaDB Vector as a new vector database backend, enabling deployments with VECTOR_DB=mariadb-vector; supports cosine and euclidean distance strategies with configurable HNSW indexing. [#21931](https://github.com/open-webui/open-webui/pull/21931)
- 📝 **Task message truncation.** Chat messages sent to task models for title and tag generation can now be truncated using a filter in the prompt template, reducing token usage and processing time for long conversations. [#21499](https://github.com/open-webui/open-webui/issues/21499)
- 🔄 **General improvements.** Various improvements were implemented across the application to enhance performance, stability, and security.
- 🌐 Translations for Portuguese (Brazil), Spanish, and Malay were enhanced and expanded.

### Fixed

- 🔗 **Pipeline filter HTTP errors.** Fixed a bug where HTTP errors in pipeline inlet/outlet filters would silently corrupt the user's chat payload; errors are now properly raised before parsing the response. [#22445](https://github.com/open-webui/open-webui/pull/22445)
- 📚 **Knowledge file embedding updates.** Fixed a bug where updating knowledge files left old embeddings in the database, causing search results to include duplicate and stale data. [#20558](https://github.com/open-webui/open-webui/issues/20558)
- 📁 **Files list stability.** Fixed the files list ordering to use created_at with id as secondary sort, ensuring consistent ordering and preventing page crashes when managing many files. [#21879](https://github.com/open-webui/open-webui/issues/21879)
- 📨 **Teams webhook crash.** Fixed a TypeError crash in the Teams webhook handler when user data is missing from the event payload. [#22444](https://github.com/open-webui/open-webui/pull/22444)
- 🛠️ **Process shutdown handling.** Fixed bare except clauses in the main process that prevented clean shutdown; replaced with proper exception handling. [#22423](https://github.com/open-webui/open-webui/pull/22423)
- 🐳 **Docker deployment startup.** Docker deployments now start correctly; the missing OpenTelemetry system metrics dependency was added. [#22447](https://github.com/open-webui/open-webui/pull/22447), [#22401](https://github.com/open-webui/open-webui/issues/22401)
- 🛠️ **Tool access for non-admin users.** Fixed a NameError that prevented non-admin users from viewing tools; the missing has_access function is now properly imported. [#22393](https://github.com/open-webui/open-webui/issues/22393)
- 🔐 **OAuth error handling.** Fixed a bug where bare except clauses silently caught SystemExit and KeyboardInterrupt, preventing clean process shutdown during OAuth authentication. [#22420](https://github.com/open-webui/open-webui/pull/22420)
- 🛠️ **Exception error messages.** Fixed three locations where incorrect exception raising caused confusing TypeError messages instead of proper error descriptions, making debugging much easier. [#22446](https://github.com/open-webui/open-webui/pull/22446)
- 📄 **YAML file processing.** Fixed an error when uploading YAML files with Docling enabled; YAML and YML files are now properly recognized as text files and processed correctly. [#22399](https://github.com/open-webui/open-webui/pull/22399), [#22263](https://github.com/open-webui/open-webui/issues/22263)
- 📅 **Time range month names.** Fixed month names in time range labels appearing in the wrong language when OS regional settings differ from browser language; month names now consistently display in English. [#22454](https://github.com/open-webui/open-webui/pull/22454)
- 🔐 **OAuth error URL encoding.** Fixed OAuth error messages with special characters causing malformed redirect URLs; error messages are now properly URL-encoded. [#22415](https://github.com/open-webui/open-webui/pull/22415)
- 🛠️ **Internal tool method filtering.** Tools no longer expose internal methods starting with underscore to the LLM, reducing clutter and improving accuracy. [#22408](https://github.com/open-webui/open-webui/pull/22408)
- 🔊 **Azure TTS locale extraction.** Fixed Azure text-to-speech using incomplete locale codes in SSML; now correctly uses full locale like "en-US" instead of just "en". [#22443](https://github.com/open-webui/open-webui/pull/22443)
- 🎤 **Azure speech transcription errors.** Improved Azure AI Speech error handling to display user-friendly messages instead of generic connection errors; empty transcripts, no language identified, and other Azure-specific errors now show clear descriptions. [#20485](https://github.com/open-webui/open-webui/issues/20485)
- 📊 **Analytics group filtering.** Fixed token usage analytics not being filtered by user group; the query now properly respects group filters like other analytics metrics. [#22167](https://github.com/open-webui/open-webui/pull/22167)
- 🔍 **Web search favicon fallback.** Fixed web search sources showing broken image icons when favicons couldn't be loaded from external sources; now falls back to the default Open WebUI favicon. [#21897](https://github.com/open-webui/open-webui/pull/21897)
- 🔄 **Custom model fallback.** Fixed custom model fallback not working when the base model is unavailable; the base model ID is now correctly retrieved from model info instead of empty params. [#22456](https://github.com/open-webui/open-webui/issues/22456)
- 🖼️ **Pending message image display.** Fixed images in queued messages appearing blank; image thumbnails are now properly displayed in the pending message queue. [#22256](https://github.com/open-webui/open-webui/issues/22256)
- 🛠️ **File metadata sanitization.** Fixed file uploads failing with JSON serialization errors when metadata contained non-serializable objects like callable functions; metadata is now sanitized before database insertion. [#20561](https://github.com/open-webui/open-webui/issues/20561)

## [0.8.9] - 2026-03-07

### Added

- ▶️ **Open Terminal notebook cell execution.** Users can now run Jupyter Notebook code cells directly in the Open Terminal file navigator, execute entire notebooks with a single click, edit and modify cells before running, and control the kernel - bringing full interactive notebook execution to the browser. [Commit](https://github.com/open-webui/open-webui/commit/4b3ed3e802d6f2ec8ee7caf358af810b7d09f789)
- 🗃️ **Open Terminal SQLite browser.** Users can now browse SQLite database files directly in the Open Terminal file navigator, viewing tables and running queries without downloading them first. [Commit](https://github.com/open-webui/open-webui/commit/a181b4a731a9ec7856be08d0b045a454d1341cf4)
- 📉 **Open Terminal Mermaid diagram rendering.** Markdown files with Mermaid code blocks are now rendered as diagrams directly in the Open Terminal file navigator, making it easier to visualize flowcharts and other diagrams. [Commit](https://github.com/open-webui/open-webui/commit/aaa49bdd6d6e5c10e8be554039d3cac673008fc2)
- 📓 **Open Terminal Jupyter Notebook previews.** Users can now preview Jupyter Notebook files directly in the Open Terminal file navigator, making it easier to view notebook content without downloading them first. [Commit](https://github.com/open-webui/open-webui/commit/b081e33c0a37585a1ee60b6e0e1ea03457f1e5f4)
- 🔃 **Open Terminal auto-refresh.** The Open Terminal file navigator now automatically refreshes when the model writes or modifies files, keeping the view in sync without manual refresh. [Commit](https://github.com/open-webui/open-webui/commit/828656b35f04bf486609183799cf8aa2e9850a76)
- 📎 **Open Terminal file copy button.** Users can now copy file contents directly to clipboard in the Open Terminal file navigator with a single click, making it easier to quickly grab file content without downloading. [Commit](https://github.com/open-webui/open-webui/commit/f5ea1ce250cb02fbc583c6cb3f52a923912d0178)
- 💻 **Code syntax highlighting and XLSX improvements in Open Terminal.** Code files now display with syntax highlighting in the Open Terminal file navigator, and XLSX spreadsheets now show column headers and row numbers for easier navigation. [Commit](https://github.com/open-webui/open-webui/commit/f962bae98306ea9264967b78b803397f4821f9b0)
- 🌳 **Open Terminal JSON tree view.** JSON, JSONC, JSONL, and JSON5 files now display as interactive collapsible tree views in the Open Terminal file navigator, and SVG files render as preview images with syntax highlighting support. [Commit](https://github.com/open-webui/open-webui/commit/f4c38e6001dd9d4853ed923e0bc5e790c4fd9941)
- 🛜 **Open Terminal port viewing.** Users can now view listening ports in the Open Terminal file navigator and open proxy connections to them directly from the UI. [Commit](https://github.com/open-webui/open-webui/commit/e08341dab3bb10e26a64eb44cbebd2d507087b03)
- 🎬 **Open Terminal video previews.** Users can now preview video and audio files directly in the Open Terminal file navigator, making it easier to view media without downloading them first. [Commit](https://github.com/open-webui/open-webui/commit/c40f26946f2eaeb1587a1f8b0c643b4a5121fc06)
- ✏️ **Open Terminal HTML editing.** Users can now edit HTML source files in Open Terminal with CodeMirror editor, and the save button is properly hidden in preview mode. [Commit](https://github.com/open-webui/open-webui/commit/7806cd5aef9fb0505b2c642ef70599a403cf14ba)
- 📄 **Open Terminal DOCX preview.** Word documents generated or modified by the AI can now be viewed directly in the file navigator with formatted text, tables, and images rendered inline — no need to download and open in a separate application. [Commit](https://github.com/open-webui/open-webui/commit/890949abe6b01d201355a86c50317e20da07dd34)
- 📊 **Open Terminal XLSX preview.** Excel spreadsheets in the file navigator now render as interactive tables with column headers and row numbers, making it easy to verify data the AI has generated or processed. [Commit](https://github.com/open-webui/open-webui/commit/890949abe6b01d201355a86c50317e20da07dd34)
- 📽️ **Open Terminal PPTX preview.** PowerPoint presentations created by the AI can now be viewed slide-by-slide directly in the file navigator, enabling quick review and iteration without leaving the browser. [Commit](https://github.com/open-webui/open-webui/commit/890949abe6b01d201355a86c50317e20da07dd34)
- 📁 **Pyodide file system support.** Users can now upload files for Python code execution in the code interpreter. Uploaded files are available in the `/mnt/uploads/` directory, and code can write output files there for download. The file system persists across code executions within the same session. The code interpreter now also informs models that pip install is not available in the Pyodide environment, guiding them to use alternative approaches with available modules. [#3583](https://github.com/open-webui/open-webui/issues/3583), [Commit](https://github.com/open-webui/open-webui/commit/ce0ca894fea8a2904bc6f832ff186d5fe53dd0b9), [Commit](https://github.com/open-webui/open-webui/commit/989938856fdb4b4afa584ae2d18c88d5be614ae2)
- 🧰 **Tool files access.** Tools can now access the files from the current chat context via the files property in their metadata, enabling more powerful tool integrations. [Commit](https://github.com/open-webui/open-webui/commit/35bc8310772c222fd8a466f7d00113a84e0402d0)
- ⚡ **Chat performance.** Chat messages now load and display significantly faster thanks to optimized markdown rendering, eliminating delays when viewing messages with mathematical expressions. [#22196](https://github.com/open-webui/open-webui/pull/22196), [#20878](https://github.com/open-webui/open-webui/discussions/20878)
- 📜 **Message list performance.** Improved message list rendering performance by optimizing array operations, reducing complexity from O(n²) to O(n). [#22280](https://github.com/open-webui/open-webui/pull/22280)
- 🧵 **Streaming markdown performance.** Improved chat responsiveness during streaming by skipping unnecessary markdown re-parsing when the content hasn't changed, eliminating wasted processing during model pauses. [#22183](https://github.com/open-webui/open-webui/pull/22183)
- 🏃 **Chat streaming performance.** Chat streaming is now faster for users not using the voice call feature by skipping unnecessary text parsing that was running on every token. [#22195](https://github.com/open-webui/open-webui/pull/22195)
- 🔖 **Source list performance.** Source lists in chat now render faster thanks to optimized computation that avoids unnecessary recalculations, including moving sourceIds computation to a reactive variable. [#22279](https://github.com/open-webui/open-webui/pull/22279), [Commit](https://github.com/open-webui/open-webui/commit/88af78c), [Commit](https://github.com/open-webui/open-webui/commit/339ed1d72e100c89d8eb26de761dfefe842ef90c)
- 💨 **Chat message tree operations.** Chat message tree operations are now significantly faster, improving overall chat responsiveness. [#22194](https://github.com/open-webui/open-webui/pull/22194)
- 🚀 **Initial page load speed.** Page load is now significantly faster thanks to deferred loading of the syntax highlighting library, reducing the initial JavaScript bundle by several megabytes. [#22304](https://github.com/open-webui/open-webui/pull/22304)
- 🗓️ **Action priority query optimization.** Improved performance of action priority resolution by fixing an N+1 query pattern, reducing database round-trips when loading model actions. [#22301](https://github.com/open-webui/open-webui/pull/22301)
- 🔑 **API key middleware optimization.** The API key restriction middleware was converted to a pure ASGI middleware for improved streaming performance, removing per-chunk call overhead. [#22188](https://github.com/open-webui/open-webui/pull/22188)
- 🏎️ **Model list loading performance.** Model lists now load significantly faster thanks to optimized custom model matching that uses dictionary lookups instead of nested loops. [#22299](https://github.com/open-webui/open-webui/pull/22299), [Commit](https://github.com/open-webui/open-webui/commit/29160741a3defa8768a43100cb6e63c56400279c), [Commit](https://github.com/open-webui/open-webui/commit/03c6caac1fc8625f85cf1164f5a977be8005c1bc)
- ⏱️ **Event call timeout configuration.** Administrators can now configure the WebSocket event call timeout via the WEBSOCKET_EVENT_CALLER_TIMEOUT environment variable, giving users more time to respond to event_call forms instead of timing out after 60 seconds. [#22222](https://github.com/open-webui/open-webui/pull/22222), [#22220](https://github.com/open-webui/open-webui/issues/22220)
- 🔁 **File refresh button visibility.** The refresh button in the chat file navigator now appears when viewing files as well as directories, allowing users to refresh the file view at any time. [Commit](https://github.com/open-webui/open-webui/commit/49a2e5bf573415dae6d4c7e5bd635e499c8de77a)
- 📂 **Nested folders support.** Users can now create subfolders within parent folders, improving organization of chats. A new "Create Subfolder" option is available in the folder context menu. [#22073](https://github.com/open-webui/open-webui/pull/22073), [Commit](https://github.com/open-webui/open-webui/commit/8913f37c3d8fde7dea6d54a550357f1d495b3941)
- 🔔 **Banner loading on navigation.** Admin-configured banners now load when navigating to the homepage, not just on page refresh, ensuring users see new banners immediately. [#22340](https://github.com/open-webui/open-webui/pull/22340), [#22180](https://github.com/open-webui/open-webui/issues/22180)
- 📡 **System metrics via OpenTelemetry.** Administrators can now monitor Python runtime and system metrics including CPU, memory, garbage collection, and thread counts through the existing OpenTelemetry pipeline. [#22265](https://github.com/open-webui/open-webui/pull/22265)
- 🔄 **General improvements.** Various improvements were implemented across the application to enhance performance, stability, and security.
- 🌐 Translations for French, Finnish, Turkish, German, Simplified Chinese, and Traditional Chinese were enhanced and expanded.
- 🔍 **Web search tool guidance.** The web search tool description was updated to encourage direct usage without first checking knowledge bases, making it clearer for users who want to search the web immediately. [#22264](https://github.com/open-webui/open-webui/pull/22264)

### Fixed

- 🗄️ **Migration memory usage.** Database migration on large deployments now processes messages in batches instead of loading everything into memory, preventing out-of-memory errors during upgrades. [#21542](https://github.com/open-webui/open-webui/pull/21542), [#21539](https://github.com/open-webui/open-webui/discussions/21539)
- 🔒 **SQLCipher connection stability.** Fixed a crash that occurred when using database encryption with SQLCipher by changing the default connection pool behavior, ensuring stable operation during multi-threaded operations like user signup. [#22273](https://github.com/open-webui/open-webui/pull/22273), [#22258](https://github.com/open-webui/open-webui/issues/22258)
- 🛑 **Stop sequence error.** Fixed a bug where setting stop sequences on a model caused the chat to fail with a split error, preventing any responses from being returned. The fix handles both string and array formats for stop tokens. [#22251](https://github.com/open-webui/open-webui/issues/22251), [Commit](https://github.com/open-webui/open-webui/commit/c7d1d1e390a79c6c86d4bfe439fd7de6f5fb060f)
- 🔐 **Microsoft OAuth refresh token fix.** Fixed a bug where Microsoft OAuth refresh token requests failed with error AADSTS90009 by adding support for the required scope parameter. Users can now stay logged in reliably with Microsoft OAuth. [#22359](https://github.com/open-webui/open-webui/pull/22359)
- 🛠️ **Parameterless tool calls.** Fixed parameterless tool calls failing during streaming by correcting the default arguments initialization, eliminating unnecessary model retries. [#22189](https://github.com/open-webui/open-webui/pull/22189)
- 🔧 **Tool call streaming fixes.** Fixed two bugs where streaming tool calls failed silently for models like GPT-5: function names were incorrectly duplicated when sent in multiple delta chunks, and arguments containing multiple JSON objects were not properly split. Tools now execute correctly instead of failing without explanation. [#22177](https://github.com/open-webui/open-webui/issues/22177), [Commit](https://github.com/open-webui/open-webui/commit/d7efdcce2b1cdbe1637a469294bf9d52dbacab53), [Commit](https://github.com/open-webui/open-webui/commit/459a60a24240eab33441ed50f4f68cc27e65a037)
- 🔗 **Tool server URL trailing slash.** Fixed tool server connection failures when URLs have trailing slashes by stripping them before path concatenation. Previously, URLs like "http://host:8080/v1/" + "/openapi.json" produced double-slash URLs that some servers rejected. [#22116](https://github.com/open-webui/open-webui/pull/22116), [#21917](https://github.com/open-webui/open-webui/issues/21917)
- 🛡️ **Citation parser error handling.** Fixed crashes when tools return error strings instead of expected data structures by adding type guards to the citation parser. The system now returns an empty source list instead of crashing with AttributeError. [#22118](https://github.com/open-webui/open-webui/pull/22118)
- 🧠 **Artifacts memory leak.** Fixed a memory leak where Svelte store subscriptions in the Artifacts component were not properly cleaned up when the component unmounted, causing memory to accumulate over time. [#22303](https://github.com/open-webui/open-webui/pull/22303)
- ♾️ **Artifacts reactive loop fix.** Fixed an infinite reactive loop in chat when artifacts are present by moving the animation frame logic outside the reactive block, preventing continuous re-rendering and CPU usage. [#22238](https://github.com/open-webui/open-webui/pull/22238), [Commit](https://github.com/open-webui/open-webui/commit/626fcff417afba642f4f71e0498267a21435c524)
- 🔀 **Artifact navigation.** Artifact navigation via arrow buttons now works correctly; the selected artifact is no longer reset when content updates. [#22239](https://github.com/open-webui/open-webui/pull/22239)
- 🧩 **Artifact thinking block fix.** Fixed a bug where HTML preview rendered code blocks inside thinking blocks for certain models like Mistral and Z.ai, causing stray code with ">" symbols to appear before the actual artifact. The fix strips thinking blocks before extracting code for artifact rendering. [#22267](https://github.com/open-webui/open-webui/issues/22267), [Commit](https://github.com/open-webui/open-webui/commit/35bc8310772c222fd8a466f7d00113a84e0402d0)
- 💬 **Floating Quick Actions availability.** Fixed an issue where the "Ask" and "Explain" Floating Quick Actions were missing when selecting text in chats that used a model that is no longer available. [#22149](https://github.com/open-webui/open-webui/pull/22149), [#22139](https://github.com/open-webui/open-webui/issues/22139)
- 💡 **Follow-up suggestions.** Fixed follow-up suggestions not appearing by correcting contradictory format instructions in the prompt template, ensuring the LLM returns the correct JSON object format. [#22212](https://github.com/open-webui/open-webui/pull/22212)
- 🔊 **TTS thinking content.** Fixed TTS playback reading think tags instead of skipping them by handling edge cases where code blocks inside thinking content prevented proper tag removal. [#22237](https://github.com/open-webui/open-webui/pull/22237), [#22197](https://github.com/open-webui/open-webui/issues/22197)
- 🎨 **Button spinner alignment.** Button spinners across multiple modals now align correctly and stay on the same line as the button text, fixing layout issues when loading states are displayed. [#22227](https://github.com/open-webui/open-webui/pull/22227)
- 📶 **Terminal keepalive.** Terminal connections now stay active without being closed by idle timeouts from proxies or load balancers, and spurious disconnection messages no longer appear. [Commit](https://github.com/open-webui/open-webui/commit/ca2aaf0321c219d041e92e2c0c842a4e424732ef)
- 📥 **Chat archive handler.** The archive button in the chat navbar now actually archives the chat and refreshes the chat list, instead of doing nothing. [#22229](https://github.com/open-webui/open-webui/pull/22229)
- 🐍 **BeautifulSoup4 dependency.** Added the missing BeautifulSoup4 package to backend requirements, fixing failures when using features that depend on HTML parsing. [#22231](https://github.com/open-webui/open-webui/pull/22231)
- 👥 **Group users default sort.** Group members in the admin panel now sort by last active time by default instead of creation date, making it easier to find active users. [#22211](https://github.com/open-webui/open-webui/pull/22211)
- 🔓 **Tool access permissions.** Users can now change tool and skill access permissions from private to public without errors. [#22325](https://github.com/open-webui/open-webui/pull/22325), [#22324](https://github.com/open-webui/open-webui/issues/22324)
- 🖥️ **Open Terminal permission fix.** Open Terminal is now visible without requiring "Allow Speech to Text" permission, fixing an issue where users without microphone access couldn't access the terminal feature. [#22374](https://github.com/open-webui/open-webui/issues/22374), [Commit](https://github.com/open-webui/open-webui/commit/70a31a9a57bdd0690ac270f31ebd1b46e8fdfa98)
- 📌 **Stale pinned models cleanup.** Pinned models that are deleted or hidden are now automatically unpinned, keeping your pinned models list up to date. [Commit](https://github.com/open-webui/open-webui/commit/af4500e5040c8343d339cd88dd1d2fb6138c7a72)
- 📏 **OpenTelemetry metric descriptions.** Fixed conflicting metric instrument descriptions that caused warnings in the OpenTelemetry collector, resulting in cleaner telemetry logs for administrators. [#22293](https://github.com/open-webui/open-webui/pull/22293)
- 🔢 **Non-streaming token tracking.** Token usage from non-streaming chat responses is now correctly saved to the database, fixing missing token counts in the Admin Panel analytics. Previously, non-streaming responses saved NULL usage data, causing messages to be excluded from token aggregation queries. [#22166](https://github.com/open-webui/open-webui/pull/22166)
- ⌨️ **Inline code typing.** Fixed a bug where typing inline code with backticks incorrectly deleted the character immediately before the opening backtick, so text formatted as inline code now correctly produces the full word instead of missing the last character. [#20417](https://github.com/open-webui/open-webui/issues/20417), [Commit](https://github.com/open-webui/open-webui/commit/e303c3da3b174da9e92a79b174f85ba574ca06ef)
- 📝 **Variable input newlines.** Fixed a bug where variables containing newlines were not displayed correctly in chat messages, and input values from Windows systems are now properly normalized to use standard line endings. [#21447](https://github.com/open-webui/open-webui/issues/21447), [Commit](https://github.com/open-webui/open-webui/commit/7b2f597b30c77ef300d1966e1c6a3edfdb0c465d)
- 📷 **Android photo capture.** Fixed an issue where the first photo taken in chat appeared completely black on some Android devices by using an alternative canvas export method. [#22317](https://github.com/open-webui/open-webui/pull/22317)
- 🪟 **Open Terminal Windows path fix.** Fixed a bug where navigating back to parent directories on Windows added an incorrect leading slash, causing directory loads to fail. Paths are now properly normalized for Windows drive letters. [#22352](https://github.com/open-webui/open-webui/issues/22352), [Commit](https://github.com/open-webui/open-webui/commit/044fd1bd15cae06a5c56a321ca79d8362942f66a)
- 🖼️ **Chat overview profile image sizing.** Fixed a bug where profile images in the chat overview could shrink incorrectly in tight spaces. The images now maintain their proper size with the flex-shrink-0 property. [#22261](https://github.com/open-webui/open-webui/pull/22261)
- 📨 **Queued messages display.** Fixed an issue where queued messages could be cut off or hidden. The queued messages area now scrolls properly when content exceeds the visible area, showing up to 25% of the viewport height. [#22176](https://github.com/open-webui/open-webui/pull/22176)
- 🖌️ **Image generation in temporary chats.** Generated images now display correctly in temporary chat mode when using builtin image generation tools. Previously, images were not shown because the code was overwriting the image list with a null database response. [#22330](https://github.com/open-webui/open-webui/pull/22330), [#22309](https://github.com/open-webui/open-webui/issues/22309)
- 🤖 **Ollama model unload fix.** Fixed a bug where unloading a model from Ollama via the Open WebUI proxy failed with a "Field required" error for the prompt field. The proxy now correctly allows omitting the prompt when using keep_alive: 0 to unload models. [#22260](https://github.com/open-webui/open-webui/issues/22260), [Commit](https://github.com/open-webui/open-webui/commit/95b65ff751f91131b633cb128ff2decdd87c4a85)
- 🏷️ **Banner type dropdown fix.** Fixed a bug where selecting a banner type required two clicks to register, as the first selection was being swallowed due to DOM structure changes. The dropdown now works correctly on the first click. [#22378](https://github.com/open-webui/open-webui/pull/22378)
- 📈 **Analytics URL encoding fix.** Fixed a bug where the Analytics page failed to load data for models with slashes in their ID, such as "anthropic/claude-opus-4.6". The frontend now properly URL-encodes forward slashes, allowing model analytics to load correctly. [#22380](https://github.com/open-webui/open-webui/issues/22380), [#22382](https://github.com/open-webui/open-webui/pull/22382)
- 📋 **Analytics chat list duplicate fix.** Fixed a bug where the Analytics page chat list threw an "each_key_duplicate" Svelte error when chat IDs were duplicated during pagination. The fix adds deterministic ordering to prevent duplicate entries. [#22383](https://github.com/open-webui/open-webui/pull/22383)
- 📂 **Folder knowledge base native tool call fix.** Fixed a bug where folders with attached knowledge bases were querying the knowledge base twice when using native tool call mode. The fix now correctly separates knowledge files from regular attachments, letting the builtin query_knowledge_files tool handle knowledge searches instead of duplicating RAG queries. [#22236](https://github.com/open-webui/open-webui/issues/22236), [Commit](https://github.com/open-webui/open-webui/commit/967b1137dcb7a52615f17d086ee89095bb9b60f3), [Commit](https://github.com/open-webui/open-webui/commit/80b5896b70d07ea868e2010b187430d43c9808f0)

## [0.8.8] - 2026-03-02

### Added

- 📁 **Open Terminal file moving.** Users can now move files and folders between directories in the Open Terminal file browser by dragging and dropping them. [Commit](https://github.com/open-webui/open-webui/commit/0c42cd2c012f9f49816adac897e2b46573b3cb6c), [Commit](https://github.com/open-webui/open-webui/commit/72951324dfeef64e09f4776898d675bc1c44f040), [Commit](https://github.com/open-webui/open-webui/commit/395098c6f1b7499d37ad55145a5931431d3e72e9), [Commit](https://github.com/open-webui/open-webui/commit/11487d66fc1a2dfafbdaa2b7ef939a86caaf3872)
- 📄 **Open Terminal HTML file preview.** Users can now preview HTML files directly in the Open Terminal file browser, with a rendered iframe view and source toggle, enabling iterative AI editing of HTML files. [Commit](https://github.com/open-webui/open-webui/commit/3909b62ffcf49839fa57346ed8487ae759811503), [Commit](https://github.com/open-webui/open-webui/commit/933a3bbbd3f4fc3eeb0ec52c7965e9ac1c4cea39)
- 🌐 **Open Terminal WebSocket proxy.** Added a new WebSocket proxy endpoint for interactive terminal sessions, enabling real-time bidirectional terminal communication with the terminal server. [Commit](https://github.com/open-webui/open-webui/commit/4f6cb771f1afded09aad6199cdb244dd8a6c77a6)
- ⚙️ **Open Terminal feature toggle.** Administrators can now enable or disable the Interactive Terminal feature for Open Terminal via configuration on the terminal server, controlling access to terminal routes. [Commit](https://github.com/open-webui/open-webui/commit/b5c3395f79bcc7ff5bc1d82bb86a60583bb3b5bd)
- 🔄 **General improvements.** Various improvements were implemented across the application to enhance performance, stability, and security.
- 🌐 Translations for Simplified Chinese, Traditional Chinese, Irish, and Catalan were enhanced and expanded.

### Fixed

- 🔧 **Middleware variable shadowing.** Fixed a variable shadowing issue in the middleware that could cause incorrect tool output processing during chat. [#22145](https://github.com/open-webui/open-webui/pull/22145)
- ⚡ **ChatControls reactivity fix.** Fixed a Svelte reactivity issue where the active tab state in the ChatControls panel was not properly saved when switching between chats. [#22127](https://github.com/open-webui/open-webui/pull/22127)
- 🔧 **ChatControls TypeScript fix.** Fixed a TypeScript syntax error in ChatControls.svelte where the module script block was missing lang="ts", causing esbuild to fail during vite dev. [#22131](https://github.com/open-webui/open-webui/pull/22131)
- 🔌 **Open Terminal tools for direct connections.** Fixed an issue where Open Terminal tools were not available to the model when the terminal was configured via direct connection settings, ensuring users can now interact with terminal files and operations through the AI. [#22137](https://github.com/open-webui/open-webui/issues/22137)
- 📜 **Chat history pagination.** Fixed an issue where older messages in long chats were not loaded when scrolling to the top. [Commit](https://github.com/open-webui/open-webui/commit/d7147d6cddfd314f0f1be77b15cec406a609ef36), [Commit](https://github.com/open-webui/open-webui/commit/c701ebe07bd152eecb42b0bf6de26071358a5c76)
- 🔧 **Terminal tool null parameter handling.** Fixed a bug where null parameters in terminal tool calls were sent as the string "None" instead of being omitted, causing 422 validation errors from the open-terminal server. [#22124](https://github.com/open-webui/open-webui/issues/22124), [#22144](https://github.com/open-webui/open-webui/pull/22144)

### Changed

## [0.8.7] - 2026-03-01

### Fixed

- 🔒 **Connection access control privacy.** Tool server and terminal connections without explicit access grants are now private (admin-only) by default, fixing a bug where connections configured with no access grants were visible to all users instead of being restricted. [Commit](https://github.com/open-webui/open-webui/commit/2751a0f0b)
- 🧠 **ChatControls memory leak.** The ChatControls panel no longer leaks event listeners, ResizeObserver instances, and media query handlers when navigating between chats, fixing memory accumulation that could degrade performance during extended use. [#22112](https://github.com/open-webui/open-webui/pull/22112)
- 💾 **Temporary chat params preservation.** Model parameters are now correctly saved when creating a temporary chat, ensuring custom settings like temperature and top_p persist across the session. [Commit](https://github.com/open-webui/open-webui/commit/fe837d80e)
- ⚡ **Faster artifact content updates.** Artifact content extraction during streaming is now debounced via requestAnimationFrame, reducing redundant DOM reads and improving CPU efficiency when tokens arrive faster than the browser can paint. [Commit](https://github.com/open-webui/open-webui/commit/6863ca482)

## [0.8.6] - 2026-03-01

### Added

- 🖥️ **Open Terminal integration.** Users can now connect to [Open Terminal](https://github.com/open-webui/open-terminal) instances to browse, read, and upload files directly in chat, with the terminal acting as an always-on tool. File navigation includes folder browsing, image and PDF previews, drag-and-drop uploads, directory creation, and file deletion. The current working directory is automatically injected into tool descriptions for context-aware commands. [Commit](https://github.com/open-webui/open-webui/commit/636ab99ad8e5b71b32dd37ba7c62c32368585b2a), [Commit](https://github.com/open-webui/open-webui/commit/64ff15a5365e2c4122fccab582782669f06ec58d), [Commit](https://github.com/open-webui/open-webui/commit/4737e1f11847d057859ec78892fa89e24cbcd83b)
- 📄 **Terminal file creation.** Users can now create new empty files directly in the Open Terminal file browser, in addition to the existing folder creation functionality. [Commit](https://github.com/open-webui/open-webui/commit/234306ff57c9e24314ff805a60de919632465319)
- ✏️ **Terminal file editing.** Users can now edit text files directly in the Open Terminal file browser, with the ability to save changes back to the terminal. [Commit](https://github.com/open-webui/open-webui/commit/3d535db304bfc6fa09e655f737de8a36c0482868)
- 🛠️ **Terminal file preview toolbar.** The Open Terminal file browser now displays contextual toolbar buttons based on file type, including preview/source toggle for Markdown and CSV files, reset view for images, and improved editing controls for text files. [Commit](https://github.com/open-webui/open-webui/commit/d2b38127d0572006577b85c770607b04782de4f9)
- 🔄 **Terminal file write refresh.** The file browser now automatically refreshes when files are written or modified via the write_file or replace_file_content tools, eliminating the need to manually refresh. [Commit](https://github.com/open-webui/open-webui/commit/18865a9fef1bb154603b7b8af0116a10560e03ac)
- 🛡️ **Docker image SBOM attestation.** Docker images now include a Software Bill of Materials (SBOM) for vulnerability scanning and supply chain security compliance. [#21779](https://github.com/open-webui/open-webui/issues/21779), [Commit](https://github.com/open-webui/open-webui/commit/febc66ef2bb05606b59719e737ac5ad839002977)
- 📡 **Reporting-Endpoints security header.** Administrators can now configure a Reporting-Endpoints header via the REPORTING_ENDPOINTS environment variable to receive CSP violation reports directly, aiding in security policy debugging and hardening. [#21830](https://github.com/open-webui/open-webui/issues/21830)
- 🎯 **Action button priority sorting.** Action buttons under assistant messages now appear in a consistent order based on the priority field from function Valves, allowing developers to control button placement. [#21790](https://github.com/open-webui/open-webui/pull/21790)
- 🏷️ **Public/Private model filtering.** The Admin Settings Model listing now displays Public/Private badges and includes filter options to easily view public or private models. [#21732](https://github.com/open-webui/open-webui/issues/21732), [#21797](https://github.com/open-webui/open-webui/pull/21797)
- 👁️ **Show/Hide all models bulk action.** Administrators can now show or hide all models at once from the Admin Settings Models page Actions menu, making it faster to manage model visibility. Bulk actions now display a single toast notification on success for better user feedback. [#21838](https://github.com/open-webui/open-webui/pull/21838), [#21958](https://github.com/open-webui/open-webui/pull/21958)
- 🔐 **Individual user sharing control.** Administrators can now disable individual user sharing via the USER_PERMISSIONS_ACCESS_GRANTS_ALLOW_USERS environment variable, allowing only group-based sharing when set to false. [#21793](https://github.com/open-webui/open-webui/issues/21793), [Commit](https://github.com/open-webui/open-webui/commit/3d99de67716774af2f95f2e3c8e7cc4879464c71), [Commit](https://github.com/open-webui/open-webui/commit/176f9a781619d836be003d28d53904639cad4128)
- 🔄 **OAuth profile sync on login.** Administrators can now enable automatic synchronization of user profile name and email from OAuth providers on login via the OAUTH_UPDATE_NAME_ON_LOGIN and OAUTH_UPDATE_EMAIL_ON_LOGIN environment variables. [#21787](https://github.com/open-webui/open-webui/pull/21787), [Commit](https://github.com/open-webui/open-webui/commit/9478c5e7ac8254b5f522c006da0c1c49bb282727)
- 👥 **Default group share permission.** Administrators can now configure the default sharing permission for new groups via the DEFAULT_GROUP_SHARE_PERMISSION environment variable, controlling whether anyone, no one, or only members can share to new groups. [Commit](https://github.com/open-webui/open-webui/commit/538501c88da034434bcd1969f15341dbbaf154e4)
- 💨 **Streaming performance.** Chat responses now render more efficiently during streaming, reducing CPU usage and improving responsiveness. [Commit](https://github.com/open-webui/open-webui/commit/484ba91b0777042eb848134f206ef3921f968dea)
- 🧮 **Streaming message comparison.** Chat message updates during streaming are now faster thanks to an optimization that skips expensive comparisons when content changes. [#21884](https://github.com/open-webui/open-webui/pull/21884)
- 🚀 **Streaming scroll optimization.** Chat auto-scroll during streaming is now more efficient by batching scroll operations via requestAnimationFrame, reducing unnecessary layout reflows when tokens arrive faster than the browser can paint. [#21946](https://github.com/open-webui/open-webui/pull/21946)
- 📋 **Message cloning performance.** Chat message cloning during streaming is now more efficient thanks to the use of structuredClone() instead of JSON.parse(JSON.stringify(...)). [#21948](https://github.com/open-webui/open-webui/pull/21948)
- 🎯 **Faster code block rendering.** Chat message updates during streaming are now faster. [#22101](https://github.com/open-webui/open-webui/pull/22101)
- 📊 **Faster status history display.** Chat message updates during streaming are now faster. [#22103](https://github.com/open-webui/open-webui/pull/22103)
- 🛠️ **Faster tool result handling.** Tool execution results are now handled more efficiently, improving streaming performance. [#22104](https://github.com/open-webui/open-webui/pull/22104)
- 💾 **Faster model and file operations.** Model selection, file preparation, and history saving are now faster. [#22102](https://github.com/open-webui/open-webui/pull/22102)
- 🛠️ **Tool server advanced options toggle.** Advanced OpenAPI configuration options in the tool server modal are now hidden by default behind a toggle, simplifying the interface for basic setups. The admin settings tab was also renamed from "Tools" to "Integrations" for clearer organization. [Commit](https://github.com/open-webui/open-webui/commit/f0c71e5a6d971af7322d4245313e5e04620253f0), [Commit](https://github.com/open-webui/open-webui/commit/4731ccb73c4b4bab78fd86fec7b2c231af8cca8b)
- 🔧 **Faster tool loading.** Tool access control now skips an unnecessary database query when no tools are attached to the request, slightly improving performance. [#21873](https://github.com/open-webui/open-webui/pull/21873)
- ➗ **Faster math rendering.** Mathematical notation now renders more efficiently, improving responsiveness when displaying equations in chat. [#21880](https://github.com/open-webui/open-webui/pull/21880)
- 🏎️ **Faster message list updates.** The chat message list now rebuilds at most once per animation frame during streaming, reducing CPU overhead. [#21885](https://github.com/open-webui/open-webui/pull/21885)
- 📋 **Faster message rendering.** Chat message rendering is now more efficient during streaming. [#22086](https://github.com/open-webui/open-webui/pull/22086)
- 🗄️ **Faster real-time chat updates.** Chat responses now process faster with improved handling for concurrent users. [#22087](https://github.com/open-webui/open-webui/pull/22087)
- 📝 **Faster status persistence.** Only final status updates are now saved to the database during streaming, reducing unnecessary writes. [#22085](https://github.com/open-webui/open-webui/pull/22085)
- 🔄 **Faster event matching.** Event handling in the socket handler is now more efficient. [Commit](https://github.com/open-webui/open-webui/commit/ff86283be0479ccb86b639926b2b67ccbbe78746)
- 🔀 **General improvements.** Various improvements were implemented across the application to enhance performance, stability, and security.
- 🌐 **Translation updates.** Translations for German, Portuguese (Brazil), Simplified Chinese, Traditional Chinese, Catalan, and Spanish were enhanced and expanded.

### Fixed

- 🗄️ **Database migration execution.** Database migrations now run correctly on startup, fixing a circular import issue that caused schema updates to fail silently. [#21848](https://github.com/open-webui/open-webui/pull/21848), [Commit](https://github.com/open-webui/open-webui/commit/87d33f6e18196876603eee7d1bf8e4977c7fa9c1)
- 🔔 **Notification HTML escaping.** Notification messages now properly escape HTML content, matching the behavior in chat messages and ensuring consistent rendering across the interface. [#21860](https://github.com/open-webui/open-webui/issues/21860), [Commit](https://github.com/open-webui/open-webui/commit/e83f668107723fa90ba0efa76c340c8338f45431)
- 🛠️ **Tool call JSON error handling.** Chat no longer crashes when models generate malformed JSON in tool call arguments; instead, a descriptive error message is returned to the model for retry. [#21984](https://github.com/open-webui/open-webui/pull/21984), [Commit](https://github.com/open-webui/open-webui/commit/668bd44485bdf88e9083c6f09c3c47ab97a128a4)
- 🧠 **Reasoning model KV cache preservation.** Reasoning model thinking tags are no longer stored as HTML in the database, preserving KV cache efficiency for backends like llama.cpp and ensuring faster subsequent conversation turns. [#21815](https://github.com/open-webui/open-webui/issues/21815), [Commit](https://github.com/open-webui/open-webui/commit/81781e6495dcc788c863bbf6b4aa4cf0ddd9fdcc)
- ⚡ **Duplicate model execution prevention.** Models are no longer called twice when no tools are configured, eliminating unnecessary API requests and reducing latency. [#21802](https://github.com/open-webui/open-webui/issues/21802), [Commit](https://github.com/open-webui/open-webui/commit/3c8d658160809f6d651837cf93d89dddc1d17caf)
- 🔐 **OAuth session database error.** OAuth login no longer fails with a database error when creating sessions, fixing the "'NoneType' object has no attribute 'id'" and "can't adapt type 'dict'" errors that occurred during OAuth group creation. [#21788](https://github.com/open-webui/open-webui/issues/21788)
- 👤 **User sharing permission enforcement.** The user sharing option now correctly respects the USER_PERMISSIONS_ACCESS_GRANTS_ALLOW_USERS setting, fixing an issue where sharing to individual users was incorrectly allowed even when disabled. [#21856](https://github.com/open-webui/open-webui/pull/21856), [Commit](https://github.com/open-webui/open-webui/commit/acb21470241ed6fd3eb3f659f196f697c418d9e8), [Commit](https://github.com/open-webui/open-webui/commit/ace69bba7512dc0a653695f9e6311712dfabb640)
- 🔑 **Password manager autofill.** Password manager autofill (like iCloud Passwords, 1Password, Bitwarden) now correctly captures filled-in passwords, fixing login failures where the password appeared filled but was sent as empty. [#21869](https://github.com/open-webui/open-webui/pull/21869), [Commit](https://github.com/open-webui/open-webui/commit/9dff497abf821dfba6eb8ea65e48a657ee91fd71)
- 📝 **RAG template duplication.** RAG templates are no longer duplicated in chat messages when models make multiple tool calls, preventing hallucinations and incorrect tool usage. [#21780](https://github.com/open-webui/open-webui/issues/21780), [Commit](https://github.com/open-webui/open-webui/commit/8f49725aa5f2d9b87e559e7d3f02f037335b7914)
- 📋 **Audit log stdout.** Audit logs now correctly appear on stdout when the ENABLE_AUDIT_STDOUT environment variable is set to true, aligning runtime behavior with the intended configuration. [#21777](https://github.com/open-webui/open-webui/pull/21777)
- 🎯 **Function valve priority resolution.** Function priorities defined in code are now correctly applied when no custom value has been saved in the database, ensuring consistent action button and filter ordering. [#21841](https://github.com/open-webui/open-webui/pull/21841)
- 📄 **Web content knowledge base append.** Processing web URLs with overwrite=false now correctly appends content to existing knowledge bases instead of silently doing nothing, fixing a regression where no content was being added. [#21786](https://github.com/open-webui/open-webui/pull/21786), [Commit](https://github.com/open-webui/open-webui/commit/5ee509325970f01524348b0f91081110340f2e7e)
- 🔍 **Web search domain filter config.** The WEB_SEARCH_DOMAIN_FILTER_LIST environment variable is now correctly read and applied, fixing an issue where domain filtering for web searches always used an empty default value. [#21964](https://github.com/open-webui/open-webui/pull/21964), [#20186](https://github.com/open-webui/open-webui/issues/20186)
- 🧹 **Tooltip memory leak.** Tooltip instances are now properly destroyed when elements change, fixing a memory leak that could cause performance issues over time. [#21969](https://github.com/open-webui/open-webui/pull/21969)
- ⌨️ **MessageInput memory leak.** Event listeners in the message input component are now properly cleaned up, preventing a memory leak that could cause page crashes during extended use. [#21968](https://github.com/open-webui/open-webui/pull/21968)
- 📝 **Notes memory leak.** Event listeners in the Notes component are now properly cleaned up, fixing a memory leak that could cause page crashes during extended use. [#21963](https://github.com/open-webui/open-webui/pull/21963)
- 🏗️ **Model create memory leak.** Event listeners in the model creation page are now properly cleaned up, fixing a memory leak that could cause page crashes during extended use. [#21966](https://github.com/open-webui/open-webui/pull/21966)
- 💬 **MentionList memory leak.** Event listeners in the MentionList component are now properly cleaned up, fixing a memory leak that could cause page crashes during extended use. [#21965](https://github.com/open-webui/open-webui/pull/21965)
- 📐 **Sidebar memory leak.** Event listeners in the Sidebar component are now properly cleaned up, fixing a memory leak that could cause page crashes during extended use. [#22082](https://github.com/open-webui/open-webui/pull/22082)
- 🎨 **Sidebar user menu positioning.** The sidebar user menu no longer drifts rightward when the sidebar is resized, keeping the menu properly aligned with its trigger. [#21853](https://github.com/open-webui/open-webui/pull/21853)
- 💻 **Code block UI.** Code block headers are now sticky and properly positioned, with language labels now showing tooltips for truncated text. [Commit](https://github.com/open-webui/open-webui/commit/6b462ff121d28cd2d335db7763052622d374e3a5)
- 📊 **Multi-model responses horizontal scroll.** The model list in multi-model responses tabs now has horizontal scroll support, making all models accessible on desktop screens. [#21800](https://github.com/open-webui/open-webui/issues/21800), [Commit](https://github.com/open-webui/open-webui/commit/a3de0bcc586ddd14dde6ae915067f082d628eaeb)
- 🎭 **TailwindCSS gray color theme.** Custom gray color palette is now correctly applied to the CSS root theme layer, fixing an issue where --color-gray-x variables were missing. [#21900](https://github.com/open-webui/open-webui/pull/21900), [#21899](https://github.com/open-webui/open-webui/issues/21899)
- 📎 **Broken documentation links.** Fixed broken links in the backend config and admin settings that pointed to outdated documentation locations. [#21904](https://github.com/open-webui/open-webui/pull/21904)
- 🔓 **OAuth session token decryption.** OAuth sessions are now properly detached from the database context before token decryption, preventing potential database session conflicts when reading encrypted tokens. [#21794](https://github.com/open-webui/open-webui/pull/21794)
- 🕐 **Chat timestamp i18n fix.** Chat timestamps in the sidebar now display correctly, fixing an issue where the time ago format (e.g., "5m", "2h", "3d") was not being localized properly due to incorrect variable casing in the translation function. [Commit](https://github.com/open-webui/open-webui/commit/ae28e7d24530eb9f7909b293bcd0f33048a022a9)
- 🍞 **Model toast notification fix.** Hiding or showing a single model now displays only one toast notification instead of two, removing the redundant generic "model updated" message when a specific action toast is shown. [#22079](https://github.com/open-webui/open-webui/pull/22079)
- 📡 **Offline mode embedding model fix.** Open WebUI no longer attempts to download embedding models when in offline mode, fixing error logs that occurred when trying to fetch models that weren't cached locally. [#22106](https://github.com/open-webui/open-webui/pull/22106), [#21405](https://github.com/open-webui/open-webui/issues/21405)

## [0.8.5] - 2026-02-23

### Added

- ⌨️ **Voice dictation shortcut.** Users can now toggle voice dictation using Cmd+Shift+L (or Ctrl+Shift+L on Windows/Linux), making it faster to start and stop dictation without clicking the microphone button.

### Fixed

- 🚫 **Model access KeyError fix.** The /api/models endpoint no longer crashes with a 500 error when models have incomplete info metadata missing the user_id field (e.g. models using global default metadata).
- 🔄 **Frontend initialization resilience.** The app layout now gracefully handles individual API failures during initialization (getModels, getBanners, getTools, getUserSettings, setToolServers) instead of blocking the entire page load when any single call fails.
- 🛡️ **Backend config null safety.** Language detection during app initialization no longer crashes when the backend config fetch fails, preventing a secondary cause of infinite loading.

## [0.8.4] - 2026-02-23

### Added

- 🛜 **Provider URL suggestions.** The connection form now displays a dropdown with suggested URLs for popular AI providers, making it easier to configure connections. [Commit](https://github.com/open-webui/open-webui/commit/49c36238d01aaff5466344ecd316a6dd3edd74a3)
- ☁️ **Anthropic model fetching.** The system now properly fetches available models from the Anthropic API, ensuring all Anthropic models are accessible. [Commit](https://github.com/open-webui/open-webui/commit/e9d852545cc17f0eeb8bdcfa77575a80fed8706d)
- 💡 **No models prompt.** When no models are available, a helpful prompt now guides users to manage their provider connections. [Commit](https://github.com/open-webui/open-webui/commit/a0195cd5ae9b9915295839cd0a5fbac5a1b0bfa2)
- ⚙️ **Connection enable/disable toggles.** Individual provider connections can now be enabled or disabled from both admin and user settings. [Commit](https://github.com/open-webui/open-webui/commit/990c638f6cf91507b61898f454c26f9516114c36)
- ⏸️ **Prompt enable/disable toggle.** Users can now enable or disable prompts directly from the prompts list using a toggle switch, without needing to delete and recreate them. Inactive prompts display an "Inactive" badge and are still visible in the list. [Commit](https://github.com/open-webui/open-webui/commit/094ed0b48cb86b9b6aff3c93f522072d11230761)
- 🗑️ **Memory deletion.** Agents can now delete specific memories that are no longer relevant, duplicated, or incorrect, giving better control over stored memory content. [Commit](https://github.com/open-webui/open-webui/commit/094ed0b48cb86b9b6aff3c93f522072d11230761)
- 📋 **Memory listing.** Agents can now list all stored memories, enabling them to identify which memories to manage or delete based on the complete memory inventory. [Commit](https://github.com/open-webui/open-webui/commit/094ed0b48cb86b9b6aff3c93f522072d11230761)
- 📦 **Auto pip install toggle.** Administrators can now disable automatic pip package installation from function frontmatter requirements using the ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS environment variable, providing more control over function dependency management. [Commit](https://github.com/open-webui/open-webui/commit/8bfab327ec5f635f9fe93c26efd198712ff7116d)
- 🔗 **Anthropic Messages API proxy.** A new API endpoint now supports the Anthropic Messages API format, allowing tools like Claude Code to authenticate through Open WebUI and access configured models. Tool calls are now properly supported in streaming responses with correct multi-block indexing, and error status from tools is propagated correctly. The endpoint converts requests to OpenAI format internally, routes them through the existing chat pipeline, and returns responses in Anthropic format. [#21390](https://github.com/open-webui/open-webui/discussions/21390), [Commit](https://github.com/open-webui/open-webui/commit/91a0301c9e22e93295a7c471d83592a802560795), [Commit](https://github.com/open-webui/open-webui/commit/a9312d25373d3aa161788598f87180b8db11c5b6)
- 👥 **Multi-device OAuth sessions.** Users can now stay logged in on multiple devices simultaneously with OAuth, as re-logging in no longer terminates existing sessions. The oldest sessions are automatically pruned when the session limit is exceeded. [#21647](https://github.com/open-webui/open-webui/issues/21647), [Commit](https://github.com/open-webui/open-webui/commit/ae05586fdabf318d551b53ede41575355d3b9e2b)
- 🔐 **OAuth group default share setting.** Administrators can now configure the default sharing setting for OAuth-created groups using the OAUTH_GROUP_DEFAULT_SHARE environment variable, allowing control over whether new groups default to private or shared with members. [#21679](https://github.com/open-webui/open-webui/pull/21679), [Commit](https://github.com/open-webui/open-webui/commit/4b9f821b58007d4efa4aa16a4995b23126e08a88)
- 🔧 **Knowledge base import behavior.** The web content import endpoint now supports a configurable overwrite flag, allowing users to add multiple URLs to the same knowledge base instead of replacing existing content. [#21613](https://github.com/open-webui/open-webui/pull/21613), [#21336](https://github.com/open-webui/open-webui/issues/21336), [Commit](https://github.com/open-webui/open-webui/commit/4bef69cc6344ff809090441aa6bced573a2aa838)
- 🧩 **Skill JSON import support.** Skills can now be imported from both JSON and Markdown files. [#21511](https://github.com/open-webui/open-webui/issues/21511)
- 🔍 **You.com web search provider.** A new web search provider option for You.com is now available, giving users another search engine choice for web-enabled models. The You.com provider enriches search results by including both descriptions and snippets for better context. [#21599](https://github.com/open-webui/open-webui/pull/21599)
- 🚀 **Message list performance.** Loading conversation history when sending messages is now significantly faster, improving response latency before the model starts generating. This also speeds up chat search and RAG context building. [#21588](https://github.com/open-webui/open-webui/pull/21588)
- 🎯 **Concurrent embedding request control.** Administrators can now control the maximum number of concurrent embedding API requests using the RAG_EMBEDDING_CONCURRENT_REQUESTS environment variable, helping manage API rate limits while maintaining embedding performance. [#21662](https://github.com/open-webui/open-webui/pull/21662), [Commit](https://github.com/open-webui/open-webui/commit/5d4547f934b6fbe751bb2041f9597fe11ddf8e43)
- ⚡ **Message upsert optimization.** Loading chat data during message saving is now significantly faster by eliminating a redundant database call that occurred on every message upsert, which happens many times during streaming responses. [#21592](https://github.com/open-webui/open-webui/pull/21592)
- ⚡ **Message send optimization.** Loading chat data during message sending is now significantly faster by eliminating unnecessary full conversation history loads. The system now uses targeted queries that fetch only the needed data instead of loading entire chat objects with all message history. [#21596](https://github.com/open-webui/open-webui/pull/21596)
- 🚀 **Tag filtering optimization.** Chat search with tag filtering now uses more efficient database queries, making filtered searches significantly faster. [Commit](https://github.com/open-webui/open-webui/commit/139f02a9d9fa2ffffcc96aa0de8af8ef51b6bcf2)
- ⚡ **Shared chat loading optimization.** The shared chats endpoint now loads only the needed columns instead of the full conversation history, making shared chat listings significantly faster. [#21614](https://github.com/open-webui/open-webui/pull/21614)
- 🗂️ **Archived and pinned chat loading.** Loading archived and pinned chat lists is now significantly faster by loading only the needed columns instead of full conversation data. [#21591](https://github.com/open-webui/open-webui/pull/21591)
- 💨 **Chat title query optimization.** Retrieving chat titles now queries only the title column instead of the entire conversation history, making title lookups significantly faster and reducing database load. [#21590](https://github.com/open-webui/open-webui/pull/21590)
- 🗄️ **Batch access grants for multiple resources.** Loading channels, knowledge bases, models, notes, prompts, skills, and tools now uses batch database queries for access grants instead of individual queries per item, significantly reducing database load. For 30 items, this reduces approximately 31 queries to just 3. [#21616](https://github.com/open-webui/open-webui/pull/21616)
- 📋 **Notes list payload optimization.** Notes list and search endpoints now return only a 200-character preview instead of the full note content, reducing response payload from ~167 MB to ~10 KB for 60 notes and eliminating N+1 queries for access grants. The Notes tab now loads in seconds instead of tens of seconds. [#21549](https://github.com/open-webui/open-webui/pull/21549)
- ⚡ **Tools list performance.** Loading the tools list is now significantly faster by deferring content and specs fields from database queries, and using cached tool modules instead of reloading them for each request. [Commit](https://github.com/open-webui/open-webui/commit/b48594a16680cc77921a4ed1a11ffa07df7edc60)
- 📝 **Group description display.** The admin groups list now shows each group's description, making it easier for administrators to identify groups at a glance.
- 🏷️ **Sort by dropdown.** Administrators can now sort groups using a dropdown menu with options for Name or Members, replacing the previous clickable column headers.
- 📶 **Admin groups list sorting.** The Group and Users columns in the admin groups list are now clickable for sorting, allowing administrators to sort groups alphabetically by name or numerically by member count. [#21692](https://github.com/open-webui/open-webui/pull/21692)
- 🔽 **Rich UI auto-scroll.** The view now automatically scrolls to action-generated Rich UI content once it renders, ensuring users can see the results without manually scrolling. [#21698](https://github.com/open-webui/open-webui/pull/21698), [#21482](https://github.com/open-webui/open-webui/discussions/21482)
- 📊 **Admin analytics toggle.** Administrators can now enable or disable the analytics feature using the ENABLE_ADMIN_ANALYTICS environment variable, giving more control over available admin features. [#21651](https://github.com/open-webui/open-webui/pull/21651), [Commit](https://github.com/open-webui/open-webui/commit/35598b8017557258b8c9ee3469d320adb0140751)
- 📊 **Analytics sorting enhancement.** The Analytics dashboard now supports sorting by Tokens column for both Model Usage and User Usage tables, and the Share/Percentage columns are now clickable for sorting. Administrators can more easily identify the most token-consuming models and users. [Commit](https://github.com/open-webui/open-webui/commit/053a33631f575ae1ad3123190a9e820b4057f62d)
- 📑 **Fetch URL citation sources.** When models fetch URLs during tool calling, the fetched URLs now appear as clickable citation sources in the UI with content previews, matching the existing behavior of web search and knowledge file tools. [#21669](https://github.com/open-webui/open-webui/pull/21669)
- 🔗 **Admin settings tab navigation.** The admin settings sidebar now supports native browser tab opening, allowing users to middle-click or right-click to open settings pages in new tabs. The navigation was converted from button-based to anchor-based elements. [#21721](https://github.com/open-webui/open-webui/pull/21721)
- 🏷️ **Model visibility badges.** The Admin Settings Models page now displays Public or Private badges directly on each model, making it easy to identify model access levels at a glance without opening the edit screen. [#21732](https://github.com/open-webui/open-webui/issues/21732), [Commit](https://github.com/open-webui/open-webui/commit/29217cb430bd47827ebb20782b264ae7b0f233bb)
- 🛠️ **Global model defaults.** Administrators can now configure default metadata and parameters that automatically apply to all models, reducing manual configuration for newly discovered models. Default capabilities (like vision, web search, code interpreter) and parameters (like temperature, max_tokens) can be set globally in Admin Settings, with per-model overrides still available. [#20658](https://github.com/open-webui/open-webui/issues/20658), [Commit](https://github.com/open-webui/open-webui/commit/c341f97cfe15510b7d128bd84f1e607b5289b957)
- 💬 **Plaintext tool output display.** Tool outputs that are plain strings now display naturally in a monospace block instead of quoted/escaped format, making multi-line string outputs easier to read. [#21553](https://github.com/open-webui/open-webui/issues/21553), [Commit](https://github.com/open-webui/open-webui/commit/3ad2ea6f2839e97e53f00fd797a9e083ff78d88e)
- 🔐 **Event call input masking.** Functions can now request masked password input in confirmation dialogs, allowing sensitive data entry to be hidden from view. This extends the existing masking feature from user valves to event calls. [#21540](https://github.com/open-webui/open-webui/issues/21540), [Commit](https://github.com/open-webui/open-webui/commit/4853ededcabcd76d9bd2036181486cd3a41458a1)
- 🗂️ **JSON logging support.** Administrators can now enable JSON-formatted logging by setting the LOG_FORMAT environment variable to "json", making logs suitable for log aggregators like Loki, Fluentd, CloudWatch, and Datadog. [#21747](https://github.com/open-webui/open-webui/pull/21747)
- ♿ **UI accessibility improvements.** Screen reader users can now navigate the interface more easily with improved keyboard navigation in dialogs and proper ARIA labels on all interactive elements. Added aria-labels to close, back, and action buttons across various components, and improved semantic HTML and screen reader support across auth, sidebar, chat, and notification components, addressing WCAG compliance. Added aria-labels to search inputs, select fields, and modals in admin and user settings, and improved accessibility for text inputs, rating components, citations, and web search results. Added aria-labels to workspace components including Knowledge, Models, Prompts, Skills, and Tools pages for improved screen reader support. [#21706](https://github.com/open-webui/open-webui/pull/21706), [#21705](https://github.com/open-webui/open-webui/pull/21705), [#21710](https://github.com/open-webui/open-webui/pull/21710), [#21709](https://github.com/open-webui/open-webui/pull/21709), [#21717](https://github.com/open-webui/open-webui/pull/21717), [#21715](https://github.com/open-webui/open-webui/pull/21715), [#21708](https://github.com/open-webui/open-webui/pull/21708), [#21719](https://github.com/open-webui/open-webui/pull/21719)
- 🔄 **General improvements.** Various improvements were implemented across the application to enhance performance, stability, and security.
- 🌐 Translations for Finnish, French, Portuguese (Brazil), Simplified Chinese, and Traditional Chinese were enhanced and expanded.

### Fixed

- 💥 **Admin functions page crash fix.** The admin Functions tab no longer crashes when clicked, fixing a null reference error that occurred while the functions list was loading. [#21661](https://github.com/open-webui/open-webui/pull/21661), [Commit](https://github.com/open-webui/open-webui/commit/8265422ba0660e7ba2192eb19efd70f8be652748)
- 💀 **Cyclic chat history deadlock fix.** Chat histories with circular parent-child message references no longer cause the backend to freeze when syncing usage stats. The system now detects and safely aborts when encountering cyclic message references. [#21681](https://github.com/open-webui/open-webui/pull/21681)
- 🔀 **Model fallback routing fix.** Custom model fallback now works correctly across all model types, preventing "Model not found" errors when the fallback model uses a different backend (pipe, Ollama, or OpenAI). [#21736](https://github.com/open-webui/open-webui/pull/21736)
- 🐛 **Default model selection fix.** Admin-configured default models are now properly respected when starting new chats instead of being overwritten by the first available model. [#21736](https://github.com/open-webui/open-webui/pull/21736)
- 👁️ **Scroll jumping fix.** Deleting a message pair after stopping generation no longer causes the chat to visually jump around, making message deletion smoother. [#21743](https://github.com/open-webui/open-webui/pull/21743), [Commit](https://github.com/open-webui/open-webui/commit/1f474187a77d2c8a392f00d86f48eb3cb3a18b88)
- 💬 **New chat message handling fix.** Fixed a bug where clicking "New Chat" after sending a message would silently drop subsequent messages. The system now properly clears pending message queues when starting a new conversation. [#21731](https://github.com/open-webui/open-webui/pull/21731)
- 🔍 **RAG template mutation fix.** Fixed a bug where RAG template text was recursively injected into user messages during multiple sequential tool calls, causing message content to grow exponentially and potentially confuse the model. The system now preserves the original user message before tool-calling loops and correctly accumulates citation sources. [#21663](https://github.com/open-webui/open-webui/issues/21663), [#21668](https://github.com/open-webui/open-webui/pull/21668), [Commit](https://github.com/open-webui/open-webui/commit/becac2b2b7af8aacadbfc9b7cee2024cf7ed6acc)
- 🔒 **Iframe sandbox security.** Embedded tools can no longer submit forms or access same-origin content by default, improving security for users. [#21529](https://github.com/open-webui/open-webui/pull/21529)
- 🔐 **Signup race condition fix.** Fixed a security vulnerability where multiple admin accounts could be created on fresh deployments when running multiple uvicorn workers. The signup handler now properly handles concurrent requests during first-user registration, preventing unauthorized admin privilege escalation. [#21631](https://github.com/open-webui/open-webui/pull/21631)
- 🔐 **LDAP optional fields fix.** LDAP configuration now properly accepts empty Application DN and password values, allowing LDAP authentication to work without these optional fields. Previously, empty values caused authentication failures. [Commit](https://github.com/open-webui/open-webui/commit/e1fa42d48a15c8b496a887ecfa32fc01cfd74b36)
- 🛠️ **API tools fix.** The /api/v1/chat/completions endpoint now properly respects caller-provided tools instead of overriding them with server-side tools, fixing issues where external agents like Claude Code or Cursor would receive unexpected tool advertisements. [#21557](https://github.com/open-webui/open-webui/issues/21557), [#21555](https://github.com/open-webui/open-webui/pull/21555)
- ⏱️ **Embeddings and proxy timeout fix.** The embeddings and OpenAI proxy endpoints now properly honor the AIOHTTP_CLIENT_TIMEOUT environment variable, instead of using default timeouts that could cause requests to hang. [#21558](https://github.com/open-webui/open-webui/pull/21558)
- 📄 **Text file type detection fix.** TypeScript and other text files that were mis-detected as video files based on their extension are now correctly identified and processed as text files, fixing upload rejections for .ts files. [#21454](https://github.com/open-webui/open-webui/issues/21454), [Commit](https://github.com/open-webui/open-webui/commit/f651809001ba8e40ba5f416773c1aa6f082a6c46)
- 🗄️ **File access control respect.** The files list and search endpoints now properly respect the BYPASS_ADMIN_ACCESS_CONTROL setting, ensuring admins only see their own files when the setting is disabled, consistent with other endpoints. [#21595](https://github.com/open-webui/open-webui/pull/21595), [#21589](https://github.com/open-webui/open-webui/issues/21589)
- 🗄️ **PostgreSQL workspace cloning.** Cloning workspace models now works correctly on PostgreSQL databases by generating proper unique IDs for access grants instead of using potentially duplicate or invalid IDs. [Commit](https://github.com/open-webui/open-webui/commit/3dd44c4f1931d13bfd46062291c6f23b33dde003)
- 🔓 **MCP SSL verification fix.** MCP tool connections now properly respect the AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL environment variable to disable SSL verification, instead of always verifying SSL certificates. [Commit](https://github.com/open-webui/open-webui/commit/af5661c2c807465f5600899e8c1a421f96cd7a8c), [#21481](https://github.com/open-webui/open-webui/issues/21481)
- 🔒 **Model default feature permissions.** Model default features like code interpreter, web search, and image generation now respect global configuration and user permission settings, preventing disabled features from appearing in the chat input. [#21690](https://github.com/open-webui/open-webui/pull/21690)
- 🔍 **Model selector typing fix.** The model selector list no longer disappears or becomes grayed out when typing quickly in the search field, thanks to improved virtual scroll handling. [#21659](https://github.com/open-webui/open-webui/pull/21659)
- ⛔ **Disabled model cloning prevention.** Disabled models can no longer be cloned as workspace models, preventing invalid empty configurations from being created. The Clone option is now hidden for inactive models. [#21724](https://github.com/open-webui/open-webui/pull/21724)
- 🔧 **SCIM parameter handling.** The SCIM Users and Groups endpoints now accept out-of-range startIndex and count values by clamping them to valid ranges instead of returning errors, in compliance with RFC 7644. [#21577](https://github.com/open-webui/open-webui/pull/21577)
- 🔍 **Hybrid search result fix.** Hybrid search now returns correct results after fixing a bug where query result unpacking order was mismatched, causing search results to appear empty. [#21562](https://github.com/open-webui/open-webui/pull/21562)
- 🛠️ **Imported items display.** Imported functions and tools now appear immediately in the list after import, without requiring a page reload. [#21593](https://github.com/open-webui/open-webui/issues/21593)
- 🔄 **WebSocket race condition fix.** Collaborative note saves no longer crash with errors when users disconnect before pending saves complete, preventing AttributeError exceptions and excessive logging. [#21601](https://github.com/open-webui/open-webui/issues/21601), [Commit](https://github.com/open-webui/open-webui/commit/0a700aafe46dfea2cf9721bb81725d2582b0d781)
- ✋ **Drag-and-drop overlay fix.** The "Add Files" overlay no longer remains stuck on screen when dragging files back out of the chat window in Mozilla Firefox. [#21664](https://github.com/open-webui/open-webui/pull/21664)
- 👁️ **Group search visibility fix.** Groups now appear correctly in access control search results, even when the search doesn't match any users. [#21691](https://github.com/open-webui/open-webui/pull/21691)
- 🖱️ **User menu drag and click fixes.** Fixed draggable ghost images when dragging menu items and eliminated phantom link clicks that occurred when dragging outside dropdown menus. [#21699](https://github.com/open-webui/open-webui/pull/21699)
- 🧭 **Admin and workspace nav drag fix.** Fixed ghost drag images when dragging top navigation tabs in the Admin and Workspace panels by adding proper drag constraints and text selection prevention. [#21701](https://github.com/open-webui/open-webui/pull/21701)
- 🎮 **Playground nav drag fix.** Fixed ghost drag images when dragging top navigation tabs in the Playground panel by adding proper drag constraints and text selection prevention. [#21704](https://github.com/open-webui/open-webui/pull/21704)
- ✋ **Dropdown menu drag fix.** Dropdown menu items can no longer be accidentally dragged as ghost images when highlighting text, making menu interactions smoother. [#21713](https://github.com/open-webui/open-webui/pull/21713)
- 🗂️ **Folder menu drag fix.** Folder dropdown menu items can no longer be accidentally highlighted or dragged as ghost images, making folder options behave like standard menus. [#21753](https://github.com/open-webui/open-webui/pull/21753)
- 📝 **Console log spam fix.** Requesting deleted or missing files no longer floods the backend console with Python traceback logs, thanks to proper exception handling for expected 404 errors. [#21687](https://github.com/open-webui/open-webui/pull/21687)
- 🐛 **Firefox avatar overflow fix.** Fixed a visual bug in Firefox where broken model or user avatar images would display overflowing alt text that overlapped adjacent labels on the Analytics and Leaderboard pages. Failed avatar images now properly show fallback icons instead. [#21730](https://github.com/open-webui/open-webui/pull/21730)
- 🎨 **Dark mode select background fix.** Fixed an issue where select inputs and dropdown menus had inconsistent lighter background colors in dark mode by removing conflicting dark theme overrides, ensuring a cohesive transparent look. [#21728](https://github.com/open-webui/open-webui/pull/21728)
- 💾 **Prompt import fix.** Importing prompts that were previously exported no longer fails with a "[object Object]" error toast, making prompt backup and restore work correctly. [#21594](https://github.com/open-webui/open-webui/issues/21594)
- 🔧 **Ollama reasoning effort fix.** Reasoning effort now works correctly with Ollama models that require string values ("low", "medium", "high") instead of boolean, fixing "invalid option provided" errors when using models like GPT-OSS. [#20921](https://github.com/open-webui/open-webui/issues/20921), [#20928](https://github.com/open-webui/open-webui/pull/20928), [Commit](https://github.com/open-webui/open-webui/commit/30a13b9b2fb2c6da7e1ddbf52edb93a58d09cc56)
- 🔍 **Hybrid search deduplication fix.** Hybrid search now correctly deduplicates results using content hashes, preventing duplicate chunks from appearing when using enriched text for BM25 search. [Commit](https://github.com/open-webui/open-webui/commit/d9fd2a3f30481efa24cc54193bf2f67fd0299b52)
- 📋 **SQLAlchemy warning fix.** Fixed a SQLAlchemy warning that appeared in logs when deleting shared chats, improving log clarity. [Commit](https://github.com/open-webui/open-webui/commit/0185f3340d2778f3b75a8036b0e81a0aec78037f)

### Changed

- 🎯 **Prompt suggestions relocated.** Prompt suggestions have been moved from Admin Panel - Settings - Interface to Admin Panel - Settings - Models, where they can now be configured per-model or globally via the new model defaults.
- 📢 **Banners relocated.** Banners configuration has been moved from Admin Panel - Settings - Interface to Admin Panel - Settings - General.

## [0.8.3] - 2026-02-17

### Added

- ✏️ **Model edit shortcut.** Users can now edit models directly from the model selector dropdown menu, making it faster to modify model settings without navigating to separate admin or workspace pages. [Commit](https://github.com/open-webui/open-webui/commit/519ff40cb69cdc1d215cee369e9db70ff7438153)
- 🎨 **Image edit API background support.** The image edit API now supports the background parameter for OpenAI's gpt-image-1 model, enabling background transparency control ("transparent", "opaque", "auto") when the feature is exposed in the UI. [#21459](https://github.com/open-webui/open-webui/pull/21459)
- ⚡ **Faster model filtering.** Model access control filtering no longer makes a redundant database query to re-fetch model info that is already available in memory, reducing latency when loading model lists for non-admin users. [Commit](https://github.com/open-webui/open-webui/commit/34cd3d79e8688f589e3dd2f03415f8a8f9a13115)
- 🔧 **Tool call display improvements.** Tool call results now display arguments in a cleaner key-value format instead of raw JSON, with a responsive layout that shows only the tool name on narrow screens and the full label on wider screens, preventing text wrapping to multiple lines. [Commit](https://github.com/open-webui/open-webui/commit/2ce935bdb10d2b26b230cd54cb649f5c667ed96a)
- 🔄 **General improvements.** Various improvements were implemented across the application to enhance performance, stability, and security.
- 🌐 Translations for Portuguese (Brazil), Simplified Chinese, and Traditional Chinese were enhanced and expanded.

### Fixed

- 📧 **USER_EMAIL variable fix.** The {{USER_EMAIL}} template variable now correctly returns the user's email address instead of "Unknown" in prompts. [#21479](https://github.com/open-webui/open-webui/pull/21479), [#21465](https://github.com/open-webui/open-webui/issues/21465)
- 🖼️ **Image and file attachment handling fixes.** Uploaded images are now correctly sent to vision-enabled models, and file attachments now work even when no user text is entered alongside a system prompt. This fixes two issues where the backend was not properly processing file attachments: images weren't converted to the expected format for API requests, and file context was dropped when the user sent only a file without accompanying text. [Commit](https://github.com/open-webui/open-webui/commit/f1053d94c7ef7b8b78682dd73586b65a84d202a1), [#21477](https://github.com/open-webui/open-webui/issues/21477), [#21457](https://github.com/open-webui/open-webui/issues/21457)
- 🛡️ **Missing function error handling.** Models that reference deleted functions no longer cause the entire /api/models endpoint to crash; instead, the missing functions are skipped and logged, allowing the rest of the models to load successfully. [#21476](https://github.com/open-webui/open-webui/pull/21476), [#21464](https://github.com/open-webui/open-webui/issues/21464)
- 🚀 **Startup model pre-fetch error handling.** If model pre-fetching fails during app startup, the application now logs a warning and continues instead of crashing entirely. [Commit](https://github.com/open-webui/open-webui/commit/337109e99ce390f55a9085d0a301853637923779)
- ⚙️ **Function module loading error handling.** Function modules that fail to load during startup or model processing are now caught and logged, preventing crashes when models reference functions with loading errors. [Commit](https://github.com/open-webui/open-webui/commit/15b893e651de71b033408e1b713e0b51f6829ab8)
- 🗄️ **PostgreSQL group query fix.** The '/api/v1/groups/' endpoint no longer fails with a GROUP BY error when using PostgreSQL; member counts are now calculated using correlated subqueries for better database compatibility. [#21458](https://github.com/open-webui/open-webui/pull/21458), [#21467](https://github.com/open-webui/open-webui/issues/21467)

## [0.8.2] - 2026-02-16

### Added

- 🧠 **Skill content handling.** User-selected skills now have their full content injected into the chat, while model-attached skills only display name and description in the available skills list. This allows users to override skill behavior while model-attached skills remain flexible. [Commit](https://github.com/open-webui/open-webui/commit/393c0071dc612c5ac982fb37dfc0288cb9911439)
- ⚙️ **Chat toggles now control built-in tools.** Users can now disable web search, image generation, and code execution on a per-conversation basis, even when those tools are enabled as builtin tools on the model. [#20641](https://github.com/open-webui/open-webui/issues/20641), [#21318](https://github.com/open-webui/open-webui/discussions/21318), [Commit](https://github.com/open-webui/open-webui/commit/c46ef3b63bcc1e2e9adbdd18fab82c4bbe33ff6c), [Commit](https://github.com/open-webui/open-webui/commit/f1a1e64d2e9ad953b2bc2a9543e9a308b7c669c8)
- 🖼️ **Image preview in file modal.** Images uploaded to chats can now be previewed directly in the file management modal, making it easier to identify and manage image files. [#21413](https://github.com/open-webui/open-webui/issues/21413), [Commit](https://github.com/open-webui/open-webui/commit/e1b3e7252c1896c04d498547908f0fce111434e1)
- 🏷️ **Batch tag operations.** Tag creation, deletion, and orphan cleanup for chats now use batch database queries instead of per-tag loops, significantly reducing database round trips when updating, archiving, or deleting chats with multiple tags. [Commit](https://github.com/open-webui/open-webui/commit/c748c3ede)
- 💨 **Faster group list loading.** Group lists and search results now load with a single database query that joins member counts, replacing the previous pattern of fetching groups first and then counting members in a separate batch query. [Commit](https://github.com/open-webui/open-webui/commit/33308022f)
- 🔐 **Skills sharing permissions.** Administrators can now control skills sharing and public sharing permissions per-group, matching the existing capabilities for tools, knowledge, and prompts. [Commit](https://github.com/open-webui/open-webui/commit/88401e91c)
- ⚡ **Long content truncation in preview modals.** Citation and file content modals now truncate markdown-rendered content at 10,000 characters with a "Show all" expansion button, preventing UI jank when previewing very large documents.
- 🌐 **Translation updates.** Translations for Spanish and German were enhanced and expanded.

### Fixed

- 🔐 **OAuth session error handling.** Corrupted OAuth sessions are now gracefully handled and automatically cleaned up instead of causing errors. [Commit](https://github.com/open-webui/open-webui/commit/7e224e4a536b07ec008613f06592e34050e7067c)
- 🐛 **Task model selector validation.** The task model selector in admin settings now correctly accepts models based on the new access grants system instead of rejecting all models with an incorrect error. [Commit](https://github.com/open-webui/open-webui/commit/9a2595f0706d0c9d809ae7746001cf799f98db1d)
- 🔗 **Tool call message preservation.** Models no longer hallucinate tool outputs in multi-turn conversations because tool call history is now properly preserved instead of being merged into assistant messages. [#21098](https://github.com/open-webui/open-webui/discussions/21098), [#20600](https://github.com/open-webui/open-webui/issues/20600), [Commit](https://github.com/open-webui/open-webui/commit/f2aca781c87244cffc130aa2722e700c19a81d66)
- 🔧 **Tool server startup initialization.** External tool servers configured via the "TOOL_SERVER_CONNECTIONS" environment variable now initialize automatically on startup, eliminating the need to manually visit the Admin Panel and save for tools to become available. This enables proper GitOps and containerized deployments. [#18140](https://github.com/open-webui/open-webui/issues/18140), [#20914](https://github.com/open-webui/open-webui/pull/20914), [Commit](https://github.com/open-webui/open-webui/commit/f20cc6d7e6da493eb75ca1618f5cbd068fa57684)
- ♻️ **Resource handle cleanup.** File handles are now properly closed during audio transcription and pipeline uploads, preventing resource leaks that could cause system instability over time. [#21411](https://github.com/open-webui/open-webui/issues/21411)
- ⌨️ **Strikethrough shortcut conflict fix.** Pressing Ctrl+Shift+S to toggle the sidebar no longer causes text to become struck through in the chat input, by disabling the TipTap Strike extension's default keyboard shortcut when rich text mode is off. [Commit](https://github.com/open-webui/open-webui/commit/38ae91ae2)
- 🔧 **Tool call finish_reason fix.** API responses now correctly set finish_reason to "tool_calls" instead of "stop" when tool calls are present, fixing an issue where external API clients (such as OpenCode) would halt prematurely after tool execution when routing Ollama models through the Open WebUI API. [#20896](https://github.com/open-webui/open-webui/issues/20896)

## [0.8.1] - 2026-02-14

### Added

- 🚀 **Channel user active status.** Checking user active status in channels is now faster thanks to optimized database queries. [Commit](https://github.com/open-webui/open-webui/commit/ca6b18ab5cb94153a9dae233f975d36bf6b19b76)
- 🔗 **Responses API endpoint with model routing.** The OpenAI API proxy now supports a /responses endpoint that routes requests to the correct backend based on the model field in the request, instead of always using the first configured endpoint. This enables support for backends like vLLM that provide /skills and /v1/responses endpoints. [Commit](https://github.com/open-webui/open-webui/commit/abc9b63093d65f4d74342db85b7d5df1809aa0f0), [Commit](https://github.com/open-webui/open-webui/commit/79ecbfc757f0642740d0e44fab98263d84295490)
- ⚡ **Model and prompt list optimization.** Improved performance when loading models and prompts by pre-fetching user group IDs once instead of making multiple database queries. [Commit](https://github.com/open-webui/open-webui/commit/20de5a87da0c12e4052b50887a42ddd7228c5ef5)
- 🗄️ **Batch access control queries.** Improved performance when loading models, prompts, and knowledge bases by replacing multiple individual access checks with single batch queries, significantly reducing database load for large deployments. [Commit](https://github.com/open-webui/open-webui/commit/589c4e64c1b7bb7a7a5abc20382b92fb860e28c2)
- 💨 **Faster user list loading.** User lists now load significantly faster by deferring profile image loading; images are fetched separately in parallel by the browser, improving caching and reducing database load. [Commit](https://github.com/open-webui/open-webui/commit/b7549d2f6ca2843661ec79a5a1e55da9e7553368)
- 🔍 **Web search result count.** The built-in search_web tool now respects the admin-configured "Search Result Count" setting instead of always returning 5 results when using Native Function Calling mode. [#21373](https://github.com/open-webui/open-webui/pull/21373), [#21371](https://github.com/open-webui/open-webui/issues/21371)
- 🔐 **SCIM externalId support.** SCIM-enabled deployments can now store and manage externalId for user provisioning, enabling better integration with identity providers like Microsoft Entra ID and Okta. [#21099](https://github.com/open-webui/open-webui/pull/21099), [#21280](https://github.com/open-webui/open-webui/issues/21280), [Commit](https://github.com/open-webui/open-webui/commit/d1d1efe212b16e0052359991d67fd813125077e8)
- 🌐 **Translation updates.** Portuguese (Brazil) translations were updated.

### Fixed

- 🛡️ **Public sharing security fix.** Fixed a security issue where users with write access could see the Public sharing option regardless of their actual public sharing permission, and direct API calls could bypass frontend sharing restrictions. [#21358](https://github.com/open-webui/open-webui/pull/21358), [#21356](https://github.com/open-webui/open-webui/issues/21356)
- 🔒 **Direct model access control fix.** Model access control changes now persist correctly for direct Ollama and OpenAI models that don't have database entries, and error messages display properly instead of showing "[object Object]". [Commit](https://github.com/open-webui/open-webui/commit/f027a01ab2ff3b6175af3dd13a4478c265c0544a), [#21377](https://github.com/open-webui/open-webui/issues/21377)
- 💭 **Reasoning trace rendering performance.** Reasoning traces from models now render properly without being split into many fragments, preventing browser slowdowns during streaming responses. [#21348](https://github.com/open-webui/open-webui/issues/21348), [Commit](https://github.com/open-webui/open-webui/commit/3b61562c82448cf83710d8b6ed29b797991aa83a)
- 🖥️ **ARM device compatibility fix.** Fixed an issue where upgrading to 0.8.0 would fail to start on ARM devices (like Raspberry Pi 4) due to torch 2.10.0 causing SIGILL errors; now pinned to torch<=2.9.1. [#21385](https://github.com/open-webui/open-webui/pull/21385), [#21349](https://github.com/open-webui/open-webui/issues/21349)
- 🗄️ **Skills PostgreSQL compatibility fix.** Fixed a PostgreSQL compatibility issue where creating or listing skills would fail with a TypeError, while SQLite worked correctly. [#21372](https://github.com/open-webui/open-webui/pull/21372), [Commit](https://github.com/open-webui/open-webui/commit/b4c3f54f9648c4232a0fd6557703ffa66fcf4caa), [#21365](https://github.com/open-webui/open-webui/issues/21365)
- 🗄️ **PostgreSQL analytics query fix.** Fixed an issue where retrieving chat IDs by model ID would fail on PostgreSQL due to incompatible DISTINCT ordering, while SQLite worked correctly. [#21347](https://github.com/open-webui/open-webui/issues/21347), [Commit](https://github.com/open-webui/open-webui/commit/7bda6bf767d5d5c4dc1111465096a88e10b5030e)
- 🗃️ **SQLite cascade delete fix.** Deleting chats now properly removes all associated messages in SQLite, matching PostgreSQL behavior and preventing orphaned data. [#21362](https://github.com/open-webui/open-webui/pull/21362)
- ☁️ **Ollama Cloud model naming fix.** Fixed an issue where using Ollama Cloud models would fail with "Model not found" errors because ":latest" was incorrectly appended to model names. [#21386](https://github.com/open-webui/open-webui/issues/21386)
- 🛠️ **Knowledge selector tooltip z-index.** Fixed an issue where tooltips in the "Select Knowledge" dropdown were hidden behind the menu, making it difficult to read knowledge item names and descriptions. [#21375](https://github.com/open-webui/open-webui/pull/21375)
- 🎯 **Model selector scroll position.** The model selector dropdown now correctly scrolls to and centers the currently selected model when opened, and resets scroll position when reopened. [Commit](https://github.com/open-webui/open-webui/commit/0b05b2fc7ed4c38af158707438ff404d1beb7c91)
- 🐛 **Sync modal unexpected appearance.** Fixed an issue where the Sync Modal would appear unexpectedly after enabling the "Community Sharing" feature if the user had previously visited the app with the sync parameter. [#21376](https://github.com/open-webui/open-webui/pull/21376)
- 🎨 **Knowledge collection layout fix.** Fixed a layout issue in the Knowledge integration menu where long collection names caused indentation artifacts and now properly truncate with ellipsis. [#21374](https://github.com/open-webui/open-webui/pull/21374)
- 📝 **Metadata processing crash fix.** Fixed a latent bug where processing document metadata containing certain keys (content, pages, tables, paragraphs, sections, figures) would cause a RuntimeError due to dictionary mutation during iteration. [#21105](https://github.com/open-webui/open-webui/pull/21105)
- 🔑 **Password validation regex fix.** Fixed the password validation regex by adding the raw string prefix, ensuring escape sequences like \d and \w are interpreted correctly. [#21400](https://github.com/open-webui/open-webui/pull/21400), [#21399](https://github.com/open-webui/open-webui/issues/21399)

### Changed

- ⚠️ **Database Migrations:** This release includes database schema changes; we strongly recommend backing up your database and all associated data before upgrading in production environments. If you are running a multi-worker, multi-server, or load-balanced deployment, all instances must be updated simultaneously, rolling updates are not supported and will cause application failures due to schema incompatibility.

## [0.8.0] - 2026-02-12

### Added

- 📊 **Analytics dashboard.** Administrators now have access to an Analytics dashboard showing model usage statistics, token consumption by model and user, user activity rankings, and time-series charts with hourly or daily granularity; clicking any model opens a detail view with feedback history, associated tags, and chat browser, and results can be filtered by user group. [#21106](https://github.com/open-webui/open-webui/pull/21106), [Commit](https://github.com/open-webui/open-webui/commit/68a1e87b66a7ec8831d5ed52940c4ef110e3e264), [Commit](https://github.com/open-webui/open-webui/commit/e62649f94044abfed4d7d60647a2050383a67e3d)
- 🎯 **Experimental support for Skills.** Open WebUI now supports the Skill standard — allowing users to create and manage reusable AI skills with detailed instructions, reference them in chats using the "$" command, or attach them to specific models for automatic context in conversations. [#21312](https://github.com/open-webui/open-webui/pull/21312)
- 🧪 **Experimental support for Open Responses protocol.** Connections can now be configured to use the experimental Open Responses protocol instead of Chat Completions, enabling native support for extended thinking, streaming reasoning tokens, and richer tool call handling for compatible providers. [Commit](https://github.com/open-webui/open-webui/commit/d2c695eb11ddca9fc93499bb0c3fcafcff7099b5), [Commit](https://github.com/open-webui/open-webui/commit/90a057f4005c000bda6ff8703e13e529190af73a), [Commit](https://github.com/open-webui/open-webui/commit/0dc74a8a2e7adb76fb503ef0cd3c02daddd2f4bb), [Commit](https://github.com/open-webui/open-webui/commit/ea9c58ea80646cef05e06d0beaf5e81cc2f78cb1), [Commit](https://github.com/open-webui/open-webui/commit/6ffce4bccdc13b8b61a8b286e34094c981932eda), [Commit](https://github.com/open-webui/open-webui/commit/6719558150920f570d8febe021da65903e53c976), [Commit](https://github.com/open-webui/open-webui/commit/117c091b95a1b1a76a31c31b97304bac289d6f18), [Commit](https://github.com/open-webui/open-webui/commit/aa8c2959ca8476f269786e1317fb6d2938abd3f9), [Commit](https://github.com/open-webui/open-webui/commit/e2d09ac36174de48a7d85bafc8d3291c9ffe44cd)
- 👥 **Redesigned access control UI.** The access control UI was redesigned with a more intuitive interface that makes it easier to add multiple groups at once. [#21277](https://github.com/open-webui/open-webui/pull/21277)
- 👤 **Per-user resource sharing.** Resources including knowledge bases, prompts, models, tools, channels, and base models can now be shared directly to individual users alongside the existing per-group sharing capability. [#21277](https://github.com/open-webui/open-webui/pull/21277)
- 📨 **Message queuing.** Messages can now be queued while a response is generating rather than being blocked, allowing you to continue your train of thought; queued messages are automatically combined and sent when generation completes, and can be edited, deleted, or sent immediately from the input area. [Commit](https://github.com/open-webui/open-webui/commit/62750b8980ef0a3f2da7bc64b5416706a7495686), [Commit](https://github.com/open-webui/open-webui/commit/d3f2cf74748db42311ca04a56ccd1ea15399eca0)
- 💡 **Active task sidebar indicator.** Users can now see which chats have active tasks running directly in the sidebar. [Commit](https://github.com/open-webui/open-webui/commit/48522271586a5bf24b649610f03b4ffd8afb2782)
- 📝 **Prompt version control.** Prompts now include version control with full history tracking, allowing users to commit changes with messages, view past versions, compare differences between versions, and roll back to previous versions when needed. [#20945](https://github.com/open-webui/open-webui/pull/20945)
- 🏷️ **Prompt tags.** Prompts can now be organized with tags, and users can filter the prompt workspace by tag to quickly find related prompts across large collections. [#20945](https://github.com/open-webui/open-webui/pull/20945)
- 🐍 **Native function calling code execution.** Code execution now works with Native function calling mode, allowing models to autonomously run Python code for calculations, data analysis, and visualizations without requiring Default mode. [#20592](https://github.com/open-webui/open-webui/pull/20592), [Docs:#998](https://github.com/open-webui/docs/pull/998)
- 🚀 **Async web search.** Web search operations now run asynchronously in the background, allowing users to continue interacting with the application while searches complete. [#20630](https://github.com/open-webui/open-webui/pull/20630)
- ⚡ **Search debouncing.** Search operations across the application now respond more efficiently with debouncing that reduces unnecessary server requests while typing, improving responsiveness when searching users, groups, functions, tools, prompts, knowledge bases, notes, and when using the knowledge and prompts commands in chat. [#20982](https://github.com/open-webui/open-webui/pull/20982), [Commit](https://github.com/open-webui/open-webui/commit/36766f157d46102fd76c526b42579400ca70de50), [Commit](https://github.com/open-webui/open-webui/commit/fa859de460376782bd0fa35512c8426c9cd0462c), [Commit](https://github.com/open-webui/open-webui/commit/57ec2aa088ffd5a8c3553c53d39799497ff70479)
- 🤝 **Shared chats management.** Users can now view and manage all their shared chats from Settings, with options to copy share links or unshare conversations they no longer want public. [Commit](https://github.com/open-webui/open-webui/commit/a10ac774ab5d47b505e840b029c0c0340002508b)
- 📁 **User file management.** Users can now view, search, and delete all their uploaded files from Settings, providing centralized file management in one place. [Commit](https://github.com/open-webui/open-webui/commit/93ed4ae2cda2f4311143e51f586aaa73b83a37a7), [#21047](https://github.com/open-webui/open-webui/pull/21047)
- 🗑️ **Shift-click quick delete.** Files in the File Manager can now be quickly deleted by holding Shift and clicking the delete button, bypassing the confirmation dialog for faster bulk cleanup. [#21044](https://github.com/open-webui/open-webui/pull/21044)
- ⌨️ **Model selector shortcut.** The model selector can now be opened with Ctrl+Shift+M keyboard shortcut. [#21130](https://github.com/open-webui/open-webui/pull/21130)
- 🧠 **Smarter knowledge vs web search.** Models now choose more intelligently between knowledge base search and web search rather than always trying knowledge first. [#21115](https://github.com/open-webui/open-webui/pull/21115)
- 🌍 **Community model reviews.** Users can now access community reviews for models directly from the model selector menu and are prompted to leave reviews after rating responses, with administrators able to disable this via the "Community Sharing" setting. [Commit](https://github.com/open-webui/open-webui/commit/bc90463ea60c9a66accb1fd242cf1853910ca838)
- 📄 **Prompts workspace pagination.** The prompts workspace now includes pagination for large prompt collections, loading 30 prompts at a time with search, filtering, and sorting capabilities for improved performance and navigation. [Commit](https://github.com/open-webui/open-webui/commit/36766f157d46102fd76c526b42579400ca70de50)
- 🎨 **Action function HTML rendering.** Action functions can now render rich HTML content directly in chat as embedded iframes, matching the capabilities that tools already had and eliminating the need for action authors to inject codeblocks. [#21294](https://github.com/open-webui/open-webui/pull/21294), [Commit](https://github.com/open-webui/open-webui/commit/60ada21c152ed642971429fdbe88dcbf478cf83a)
- 🔒 **Password-masked valve fields.** Tool and function developers can now mark sensitive fields as passwords, which are automatically masked in the settings UI to prevent shoulder surfing and accidental exposure. [#20852](https://github.com/open-webui/open-webui/issues/20852), [Commit](https://github.com/open-webui/open-webui/commit/8c70453b2e3a6958437d951751e84acbbaafd9aa)
- 📋 **Prompt quick copy.** Prompts in the workspace now include a quick copy button for easily copying prompt content to the clipboard. [Commit](https://github.com/open-webui/open-webui/commit/78f856e2049991441a3469230ae52799cb86954e)
- 🔔 **Dismissible notification toasts.** Notification toasts for new messages and other events now include a close button that appears on hover, allowing users to dismiss them immediately instead of waiting for auto-dismissal. [#21056](https://github.com/open-webui/open-webui/issues/21056), [Commit](https://github.com/open-webui/open-webui/commit/73bb600034c8532e30726129743a5ffe9002c5fb)
- 🔔 **Temporary chat notification privacy.** Notifications from temporary chats now only appear on the device where the chat is running, preventing privacy leaks across logged-in sessions. [#21292](https://github.com/open-webui/open-webui/pull/21292)
- 💡 **Null chat title fallback.** Notifications without chat titles now display "New Chat" instead of showing null. [#21292](https://github.com/open-webui/open-webui/pull/21292)
- 🖼️ **Concurrent image editing.** Image editing operations with multiple images now complete faster by loading all images concurrently instead of sequentially. [#20911](https://github.com/open-webui/open-webui/pull/20911)
- 📧 **USER_EMAIL template variable.** Users can now reference their email address in prompts and system messages using the "{{USER_EMAIL}}" template variable. [#20881](https://github.com/open-webui/open-webui/pull/20881)
- 🔤 **Alphabetical tool ordering.** Tools and Functions in the Chat Controls sidebar now appear in alphabetical order, making it easier to locate specific tools when working with multiple integrations. [#20871](https://github.com/open-webui/open-webui/pull/20871)
- 👁️ **Model list status filtering.** Administrators can now filter the model list by status (enabled, disabled, visible, hidden) and bulk enable or disable all filtered models at once. [#20553](https://github.com/open-webui/open-webui/issues/20553), [#20774](https://github.com/open-webui/open-webui/issues/20774), [Commit](https://github.com/open-webui/open-webui/commit/96a9696383d450dad2cbb230f3756ebfa258e029)
- ⚙️ **Per-model built-in tool toggles.** Administrators can now enable or disable individual built-in tools for each model, including time utilities, memory, chat history, notes, knowledge base, and channels. [#20641](https://github.com/open-webui/open-webui/issues/20641), [Commit](https://github.com/open-webui/open-webui/commit/c46ef3b63bcc1e2e9adbdd18fab82c4bbe33ff6c)
- 📑 **PDF loading modes.** Administrators can now choose between "page" and "single" PDF loading modes, allowing documents to be processed as individual pages or as complete documents for better chunking across page boundaries. [Commit](https://github.com/open-webui/open-webui/commit/ecbdef732bc71a07c21bbb679edb420f26eac181)
- 📑 **Model Settings pagination.** Administrators can now navigate large model lists more efficiently in Model Settings, with pagination displaying 30 models per page for smoother navigation. [Commit](https://github.com/open-webui/open-webui/commit/2f584c9f88aeb34ece07b10d05794020d1d656b8)
- 📌 **Pin read-only models.** Users can now pin read-only models from the workspace. [#21308](https://github.com/open-webui/open-webui/issues/21308), [Commit](https://github.com/open-webui/open-webui/commit/97331bf11d41ca54e47f86777fb8dbd73988c631)
- 🔍 **Yandex search provider.** Administrators can now configure Yandex as a web search provider, expanding search engine options for retrieval-augmented generation. [#20922](https://github.com/open-webui/open-webui/pull/20922)
- 🔐 **Custom password hints.** Administrators can now provide custom password requirement hints to users via the "PASSWORD_VALIDATION_HINT" environment variable, making it clearer what password criteria must be met during signup or password changes. [#20647](https://github.com/open-webui/open-webui/issues/20647), [#20650](https://github.com/open-webui/open-webui/pull/20650)
- 🔑 **OAuth token exchange.** Administrators can now enable OAuth token exchange via "ENABLE_OAUTH_TOKEN_EXCHANGE", allowing external applications to authenticate users by exchanging OAuth provider tokens for Open WebUI session tokens. [Commit](https://github.com/open-webui/open-webui/commit/655420fd25ed0ea872954baa485030079c00c10e)
- 🗄️ **Weaviate custom endpoints.** Administrators can now connect to self-hosted Weaviate deployments with separate HTTP and gRPC endpoints via new environment variables. [#20620](https://github.com/open-webui/open-webui/pull/20620)
- 🛡️ **MCP custom SSL certificates.** Administrators can now connect to MCP servers with self-signed or custom SSL certificates via the "AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL" environment variable. [#20875](https://github.com/open-webui/open-webui/issues/20875), [Commit](https://github.com/open-webui/open-webui/commit/c7f996d593e4bb48103b91316204fe7e50e25b35)
- 🗃️ **Redis Sentinel reconnection delay.** Administrators using Redis Sentinel can now configure a reconnection delay via "REDIS_RECONNECT_DELAY" to prevent retry exhaustion during failover elections. [#21021](https://github.com/open-webui/open-webui/pull/21021)
- 📡 **Custom user info headers.** Administrators can now customize the header names used when forwarding user information to external services, enabling compatibility with services like AWS Bedrock AgentCore that require specific header prefixes. [Commit](https://github.com/open-webui/open-webui/commit/6c0f886cdf4b4249dca29e9340b3b998a7262d61)
- 🔗 **Forward user info to tool servers.** User identity and chat context can now be forwarded to MCP servers and external tool servers when "ENABLE_FORWARD_USER_INFO_HEADERS" is enabled, allowing tool providers to implement per-user authorization, auditing, and rate limiting. [#21092](https://github.com/open-webui/open-webui/pull/21092), [Commit](https://github.com/open-webui/open-webui/commit/2c37daef86a058e370151ecead17f10078102307)
- 📬 **External tool event emitters.** External tools (OpenAPI/MCP) can now send tool events back to Open WebUI using the event emitter endpoint, as message ID is now forwarded alongside chat ID when "ENABLE_FORWARD_USER_INFO_HEADERS" is enabled. [#21214](https://github.com/open-webui/open-webui/pull/21214)
- 📥 **Playground chat export.** Administrators can now export playground chats as JSON or plain text files, allowing them to save their conversations for backup or sharing outside the platform. [Commit](https://github.com/open-webui/open-webui/commit/8e2b0b6fd2ac99c833a110e2bc6aa655f1682669)
- 🖼️ **Images playground.** Administrators can now test image generation and editing directly in a new Images playground, with support for uploading source images for edits and downloading results. [Commit](https://github.com/open-webui/open-webui/commit/94302de49b27bdf1df86b5c26f2cafb98f964e52)
- 🛠️ **Dynamic dropdown valve fields.** Tool and function developers can now create dropdown fields with dynamically-generated options that update based on runtime context, such as available models or user permissions. [Commit](https://github.com/open-webui/open-webui/commit/474427c67e953bb9f7d122757a756a639214e0b2)
- 🏎️ **Faster profile updates.** User profile updates and role changes are now faster by eliminating redundant database queries. [#21011](https://github.com/open-webui/open-webui/pull/21011)
- 🔑 **Faster authentication.** User authentication is now 34% faster by combining database lookups into a single query. [#21010](https://github.com/open-webui/open-webui/pull/21010)
- 🔋 **Faster chat completions.** Chat completions and embeddings now respond much faster by checking the model cache before fetching model lists, reducing Time To First Token from several seconds to subsecond for most requests. [#20886](https://github.com/open-webui/open-webui/pull/20886), [#20069](https://github.com/open-webui/open-webui/discussions/20069)
- 🏎️ **Faster Redis model list loading.** Model list loading is now significantly faster when using Redis with many models, reducing API response latency by caching configuration values locally instead of making repeated Redis lookups on every model iteration. [#21306](https://github.com/open-webui/open-webui/pull/21306)
- 💨 **Faster knowledge base file batch-add.** Batch-adding files to knowledge bases is now faster with a single database query instead of one query per file. [#21006](https://github.com/open-webui/open-webui/pull/21006)
- ⚡ **Smoother model selector dropdown.** The model selector dropdown now renders smoothly even with hundreds of models, eliminating the lag and freezing that occurred when opening the dropdown with large model lists. [Commit](https://github.com/open-webui/open-webui/commit/4331029926245b7b74fa8e254610c91400b239b0)
- 🚗 **Faster model visibility toggling.** Toggling model visibility in the admin panel is now faster with optimized database access. [#21009](https://github.com/open-webui/open-webui/pull/21009)
- 💾 **Faster model access control checks.** Model access control checks are now faster by batch-fetching model info and group memberships upfront instead of querying for each model. [#21008](https://github.com/open-webui/open-webui/pull/21008)
- ⚙️ **Faster model list and imports.** Model list loading and model imports are now faster by eliminating redundant database queries. [#21004](https://github.com/open-webui/open-webui/pull/21004)
- 🏃 **Faster SCIM group member lookups.** SCIM group member lookups are now up to 13x faster by batching user queries instead of fetching each member individually. [#21005](https://github.com/open-webui/open-webui/pull/21005)
- 💨 **Batched group member counts.** Group member counts are now fetched in a single batch query when loading group lists, eliminating redundant database lookups. [Commit](https://github.com/open-webui/open-webui/commit/96c07f44a8f5e6346b2ea6ac529ff4ec3c47e90a)
- 💨 **Faster bulk operations.** Bulk feedback deletion and group member removal are now 4-5x faster with optimized batch operations. [#21019](https://github.com/open-webui/open-webui/pull/21019)
- 🧠 **Faster memory updates.** Memory updates are now up to 39% faster by eliminating redundant database queries. [#21013](https://github.com/open-webui/open-webui/pull/21013)
- ⚙️ **Faster filter function loading.** Filter function loading is now faster by batching database queries instead of fetching each function individually. [#21018](https://github.com/open-webui/open-webui/pull/21018)
- 🖼️ **Image model regex configuration.** Administrators can now configure which image generation models support auto-sizing and URL responses via new regex environment variables, improving compatibility with LiteLLM and other proxies that use prefixed model names. [#21126](https://github.com/open-webui/open-webui/pull/21126), [Commit](https://github.com/open-webui/open-webui/commit/ecf3fa2feb28e74ff6c17ca97d94581f316da56a)
- 🎁 **Easter eggs toggle.** Administrators can now control the visibility of easter egg features via the "ENABLE_EASTER_EGGS" environment variable. [Commit](https://github.com/open-webui/open-webui/commit/907dba4517903e5646e40223a0edca26a7107bc8)
- 🔌 **Independent access control updates.** API endpoints now support independent access control updates for models, tools, knowledge bases, and notes, enabling finer-grained permission management. [Commit](https://github.com/open-webui/open-webui/commit/0044902c082f8475336cc7d5c57fe3f35ab0555d), [Commit](https://github.com/open-webui/open-webui/commit/c259c878060af1b03b702c943e8813d7b4fc3199), [Commit](https://github.com/open-webui/open-webui/commit/e3a825769063cee486650cc2eb9a032676e630c5)
- ♿ **Screen reader accessibility.** Screen reader users now hear the password field label only once on the login page, improving form navigation for assistive technology users. [Commit](https://github.com/open-webui/open-webui/commit/1441d0d735c7a1470070b33327e1dd4dc5ca1131)
- 🔄 **General improvements.** Various improvements were implemented across the application to enhance performance, stability, and security.
- 🌐 **Translation updates.** Translations for Catalan, Finnish, Irish, French, German, Japanese, Latvian, Polish, Portuguese (Brazil), Simplified Chinese, Slovak, Spanish, and Traditional Chinese were enhanced and expanded.

### Fixed

- ⚡ **Connection pool exhaustion fix.** Database connection pool exhaustion and timeout errors during concurrent usage have been resolved by releasing connections before chat completion requests and embedding operations for memory and knowledge base processing. [#20569](https://github.com/open-webui/open-webui/pull/20569), [#20570](https://github.com/open-webui/open-webui/pull/20570), [#20571](https://github.com/open-webui/open-webui/pull/20571), [#20572](https://github.com/open-webui/open-webui/pull/20572), [#20573](https://github.com/open-webui/open-webui/pull/20573), [#20574](https://github.com/open-webui/open-webui/pull/20574), [#20575](https://github.com/open-webui/open-webui/pull/20575), [#20576](https://github.com/open-webui/open-webui/pull/20576), [#20577](https://github.com/open-webui/open-webui/pull/20577), [#20578](https://github.com/open-webui/open-webui/pull/20578), [#20579](https://github.com/open-webui/open-webui/pull/20579), [#20580](https://github.com/open-webui/open-webui/pull/20580), [#20581](https://github.com/open-webui/open-webui/pull/20581), [Commit](https://github.com/open-webui/open-webui/commit/7da37b4f66b9b2e821796b06b75e03cb0237e0a9), [Commit](https://github.com/open-webui/open-webui/commit/9af40624c5f0f8f7f640a11356e167543b07b2bb)
- 🚫 **LDAP authentication hang fix.** LDAP authentication no longer freezes the entire service when logging in with non-existent accounts, preventing application hangs. [Commit](https://github.com/open-webui/open-webui/commit/a4281f6a7fbc9764b57830e4ef81bb780aa34af9), [#21300](https://github.com/open-webui/open-webui/issues/21300)
- ✅ **Trusted Header auto-registration fix.** Trusted Header Authentication now properly auto-registers new users after the first login, assigning the configured default role instead of failing for users not yet in the database. [Commit](https://github.com/open-webui/open-webui/commit/9b30e8f6894c8c8bad0a9ce4693eab810962adc9)
- 🛡️ **SSRF protection for image loading.** External image loading now validates URLs before fetching to prevent SSRF attacks against local and private network addresses. [Commit](https://github.com/open-webui/open-webui/commit/ce50d9bac4f30b054b09a2fbda52569b73ea591c)
- 🛡️ **Malformed Authorization header fix.** Malformed Authorization headers no longer cause server crashes; requests are now handled gracefully instead of returning HTTP 500 errors. [#20938](https://github.com/open-webui/open-webui/issues/20938), [Commit](https://github.com/open-webui/open-webui/commit/7e79f8d1c6b5a02f1a46e792540c6bbf7bed8edc)
- 🚪 **Channel notification access control.** Users without channel permissions can no longer access channels through notifications, properly enforcing access controls across all channel entry points. [#20883](https://github.com/open-webui/open-webui/pull/20883), [#20789](https://github.com/open-webui/open-webui/discussions/20789)
- 🐛 **Ollama model name suffix fix.** Ollama-compatible providers that do not use ":latest" in model names can now successfully chat, fixing errors where model names were incorrectly appended with ":latest" suffixes. [#21331](https://github.com/open-webui/open-webui/issues/21331), [Commit](https://github.com/open-webui/open-webui/commit/05ae44b98dc279ee12cc8eab17278ccbfec60301)
- ♻️ **Streaming connection cleanup.** Streaming responses now properly clean up network connections when interrupted, preventing "Unclosed client session" errors from accumulating over time. [#20889](https://github.com/open-webui/open-webui/pull/20889), [#17058](https://github.com/open-webui/open-webui/issues/17058)
- 💾 **Inline image context exhaustion fix.** Inline images no longer exhaust the model's context window by including their full base64 data in chat metadata, preventing premature context exhaustion with image-heavy conversations. [#20916](https://github.com/open-webui/open-webui/pull/20916)
- 🚀 **Status indicator GPU usage fix.** High GPU usage caused by the user online status indicator animation has been resolved, reducing consumption from 35-40% to near-zero in browsers with hardware acceleration. [#21062](https://github.com/open-webui/open-webui/issues/21062), [Commit](https://github.com/open-webui/open-webui/commit/938d1b0743c64f0ce513d68e57dfbb86987cb06b)
- 🔧 **Async pipeline operations.** Pipeline operations now run asynchronously instead of blocking the FastAPI event loop, allowing the server to handle other requests while waiting for external pipeline API calls. [#20910](https://github.com/open-webui/open-webui/pull/20910)
- 🔌 **MCP tools regression fix.** MCP tools now work reliably again after a regression in v0.7.2 that caused "cannot pickle '\_asyncio.Future' object" errors when attempting to use MCP servers in chat. [#20629](https://github.com/open-webui/open-webui/issues/20629), [#20500](https://github.com/open-webui/open-webui/issues/20500), [Commit](https://github.com/open-webui/open-webui/commit/886c12c5664bc2dd73313330f61c2257169da6d1)
- 🔗 **Function chat ID propagation fix.** Functions now reliably receive the chat identifier during internal task invocations like web search query generation, RAG query generation, and image prompt generation, enabling stateful functions to maintain consistent per-chat state without fragmentation. [#20563](https://github.com/open-webui/open-webui/issues/20563), [#20585](https://github.com/open-webui/open-webui/pull/20585)
- 💻 **Markdown fence code execution fix.** Code execution now works reliably when models wrap code in markdown fences, automatically stripping the backticks before execution to prevent syntax errors that affected most non-GPT models. [#20941](https://github.com/open-webui/open-webui/issues/20941), [Commit](https://github.com/open-webui/open-webui/commit/4a5516775927aaf002212f2e09c55a17c699bc46), [Commit](https://github.com/open-webui/open-webui/commit/683438b418fb3b453a8ad88c1ba1a9944eac3593)
- 💻 **ANSI code execution fix.** Code execution is now reliable when LLMs include ANSI terminal color codes in their output, preventing random failures that previously caused syntax errors. [#21091](https://github.com/open-webui/open-webui/issues/21091), [Commit](https://github.com/open-webui/open-webui/commit/b1737040a7d3bb5efcfe0f1432e89d7e82e51d2d)
- 🗨️ **Incomplete model metadata crash fix.** Starting chats with models that have incomplete metadata information no longer crashes the application. [#20565](https://github.com/open-webui/open-webui/issues/20565), [Commit](https://github.com/open-webui/open-webui/commit/14f6747dfc66fb7e942b930650286012121e5262)
- 💬 **Unavailable model crash fix.** Adding message pairs with Ctrl+Shift+Enter no longer crashes when the chat's model is unavailable, showing a helpful error message instead. [#20663](https://github.com/open-webui/open-webui/pull/20663)
- 📚 **Knowledge base file upload fix.** Uploading files to knowledge bases now works correctly, fixing database mapping errors that prevented file uploads. [#20925](https://github.com/open-webui/open-webui/issues/20925), [#20931](https://github.com/open-webui/open-webui/pull/20931)
- 🧠 **Knowledge base query type fix.** Knowledge base queries no longer fail intermittently when models send tool call parameters as strings instead of their expected types. [#20705](https://github.com/open-webui/open-webui/pull/20705)
- 📚 **Knowledge base reindex fix.** Reindexing knowledge base files now works correctly instead of failing with duplicate content errors. [#20854](https://github.com/open-webui/open-webui/issues/20854), [#20857](https://github.com/open-webui/open-webui/pull/20857)
- 🔧 **Multi-worker knowledge base timeout fix.** In multi-worker deployments, uploading very large documents to knowledge bases no longer causes workers to be killed by health check timeouts, and administrators can now configure a custom embedding timeout via "RAG_EMBEDDING_TIMEOUT". [#21158](https://github.com/open-webui/open-webui/pull/21158), [Discussion](https://github.com/open-webui/open-webui/discussions/21151), [Commit](https://github.com/open-webui/open-webui/commit/c653e4ec54d070aee5e9568d016daebb61f06632)
- 🌅 **Dark mode icon inversion fix.** Icons in chat and action menus are now displayed correctly in dark mode, fixing an issue where PNG icons with "svg" in their base64 encoding were randomly inverted. [#21272](https://github.com/open-webui/open-webui/pull/21272), [Commit](https://github.com/open-webui/open-webui/commit/0a44d80252afae73de4098ab1c3eb6cf54157fd6)
- 🛠️ **Admin model write permission fix.** Fixed the admin panel allowing models to be assigned write permissions, since users with write permission are not admins and cannot write. [Commit](https://github.com/open-webui/open-webui/commit/4aedfdc5471a1f13c1084b34b48ea3ed6311cd42)
- 🛠️ **Prompt access control save fix.** Prompt access control settings are now saved correctly when modifying resource permissions. [Commit](https://github.com/open-webui/open-webui/commit/30f72672fac2579c267a076e6ba89dfe1812137b)
- ✏️ **Knowledge base file edit fix.** Editing files within knowledge bases now saves correctly and can be used for retrieval, fixing a silent failure where the save appeared successful but the file could not be searched. [Commit](https://github.com/open-webui/open-webui/commit/f9ab66f51a52388a4eb084c8f69044e79bf5cb04)
- 🖼️ **Reasoning section artifact rendering fix.** Code blocks within model reasoning sections no longer incorrectly render as interactive artifacts, ensuring only intended output displays as previews. [#20801](https://github.com/open-webui/open-webui/issues/20801), [#20877](https://github.com/open-webui/open-webui/pull/20877), [Commit](https://github.com/open-webui/open-webui/commit/4c6f100b5fe2145a3d676b70b5f7c0e7f07cee20)
- 🔐 **Group resource sharing fix.** Sharing resources with groups now works correctly, fixing database errors and an issue where models shared with read-only access were not visible to group members. [#20666](https://github.com/open-webui/open-webui/issues/20666), [#21043](https://github.com/open-webui/open-webui/issues/21043), [Commit](https://github.com/open-webui/open-webui/commit/5a075a2c836e46b83f8710285f09aff1f6125072)
- 🔑 **Docling API key fix.** Docling API key authentication now works correctly by using the proper "X-Api-Key" header format instead of the incorrect "Bearer" authorization prefix. [#20652](https://github.com/open-webui/open-webui/pull/20652)
- 🔌 **MCP OAuth 2.1 fix.** MCP OAuth 2.1 authentication now works correctly, resolving connection verification failures and 401 errors during the authorization callback. [#20808](https://github.com/open-webui/open-webui/issues/20808), [#20828](https://github.com/open-webui/open-webui/issues/20828), [Commit](https://github.com/open-webui/open-webui/commit/8eebc2aea63b7045e61c9689a65a2dfa9c797bcb)
- 💻 **MATLAB syntax highlighting.** MATLAB code blocks now display with proper syntax highlighting in chat messages. [#20719](https://github.com/open-webui/open-webui/issues/20719), [#20773](https://github.com/open-webui/open-webui/pull/20773)
- 📊 **CSV export HTML entity decoding.** Exporting tables to CSV now properly decodes HTML entities, ensuring special characters display correctly in the exported file. [#20688](https://github.com/open-webui/open-webui/pull/20688)
- 📄 **Markdown Header Text Splitter persistence.** The "Markdown Header Text Splitter" document setting now persists correctly when disabled, preventing it from reverting to enabled after page refresh. [#20929](https://github.com/open-webui/open-webui/issues/20929), [#20930](https://github.com/open-webui/open-webui/pull/20930)
- 🔌 **Audio service timeout handling.** Audio transcription and text-to-speech requests now have proper timeouts, preventing the UI from freezing when external services don't respond. [#21055](https://github.com/open-webui/open-webui/pull/21055)
- 💬 **Reference Chats visibility fix.** The "Reference Chats" option now appears in the message input menu even when the sidebar is collapsed, fixing the issue where it was hidden on mobile devices and at first load. [#20827](https://github.com/open-webui/open-webui/issues/20827), [Commit](https://github.com/open-webui/open-webui/commit/a3600e8b219fc4c019b95258d16bd3e2827490c6)
- 🔍 **Chat search self-exclusion.** The "search_chats" builtin tool now excludes the current conversation from search results, preventing redundant matches. [#20718](https://github.com/open-webui/open-webui/issues/20718), [Commit](https://github.com/open-webui/open-webui/commit/1a4bdd2b30017d901b9cac1e2e10684ec1edd062)
- 📚 **Knowledge base pagination fix.** Paginating through knowledge base files no longer shows duplicates or skips files when multiple documents share the same update timestamp. [#20846](https://github.com/open-webui/open-webui/issues/20846), [Commit](https://github.com/open-webui/open-webui/commit/a9a0ce6beaa286cc18eff24b518a6f3d7a560e2f)
- 📋 **Batch file error reporting.** Batch file processing operations now return properly structured error information when failures occur, making it clearer what went wrong during multi-file operations. [#20795](https://github.com/open-webui/open-webui/issues/20795), [Commit](https://github.com/open-webui/open-webui/commit/68b2872ed645cffb641fa5a21a784d6e9ea0d72b)
- ⚙️ **Persistent config with Redis fix.** Configuration values now respect the "ENABLE_PERSISTENT_CONFIG" setting when Redis is used, ensuring environment variables are reloaded on restart when persistent config is disabled. [#20830](https://github.com/open-webui/open-webui/issues/20830), [Commit](https://github.com/open-webui/open-webui/commit/5d48e48e15b003874cc821d896998a01e87580a0)
- 🔧 **Engine.IO logging fix.** The "WEBSOCKET_SERVER_ENGINEIO_LOGGING" environment variable now works correctly, allowing administrators to configure Engine.IO logging independently from general websocket logging. [#20727](https://github.com/open-webui/open-webui/pull/20727), [Commit](https://github.com/open-webui/open-webui/commit/5cfb7a08cbde5d39aaf4097b849a80da87c30d66)
- 🌐 **French language default fix.** Browsers requesting French language now default to French (France) instead of French (Canada), matching standard language preference expectations. [#20603](https://github.com/open-webui/open-webui/pull/20603), [Commit](https://github.com/open-webui/open-webui/commit/4d9a7cc6c0adea54b58046c576250a0c3ae7b512)
- 🔘 **Firefox delete button fix.** Pressing Enter after clicking delete buttons no longer incorrectly retriggers confirmation modals in Firefox. [Commit](https://github.com/open-webui/open-webui/commit/57a2024c58b9c674f2ae08eeb552994ef1796888)
- 🌍 **RTL table rendering fix.** Chat markdown tables now correctly display right-to-left when containing RTL language content (Arabic, Hebrew, Farsi, etc.), matching the "Auto" direction setting behavior. [#21160](https://github.com/open-webui/open-webui/issues/21160), [Commit](https://github.com/open-webui/open-webui/commit/284b97bd84c824013ad00ea07621192ec69a5e93)
- 🔒 **Write permission enforcement for tools.** Users without write permissions are now properly prevented from editing tools, with a clear error message displayed when attempting unauthorized edits. [Commit](https://github.com/open-webui/open-webui/commit/85e92fe3b062ae669985c09495f6ff1baf8176ab), [Commit](https://github.com/open-webui/open-webui/commit/91faa9fd5a1cfc5d3ab531d2d91d28db52bcc702)
- 🛡️ **Chat Valves permission enforcement.** The "Allow Chat Valves" permission is now properly enforced in the integrations menu, preventing users from bypassing access restrictions. [#20691](https://github.com/open-webui/open-webui/pull/20691)
- 📝 **Audit log browser session fix.** Audit logs now properly capture all user activity including browser-based sessions, not just API key requests. [#20651](https://github.com/open-webui/open-webui/issues/20651), [Commit](https://github.com/open-webui/open-webui/commit/86e6b2b68b85e958188881785495030de1a30402), [Commit](https://github.com/open-webui/open-webui/commit/ee5fd1246cb3f8f16ca5cbb24feeea43b7800dcb)
- 🎨 **Long model name truncation.** Long model names and IDs in the admin panel now truncate properly to prevent visual overflow, with full names visible on hover. [#20696](https://github.com/open-webui/open-webui/pull/20696)
- 👥 **Admin user filter pagination fix.** Filtering users in the admin panel now automatically resets to page 1, preventing empty results when searching from pages beyond the first. [#20723](https://github.com/open-webui/open-webui/pull/20723), [Commit](https://github.com/open-webui/open-webui/commit/be75bc506adb048ef11b1612c0e3662511c920d0)
- 🔎 **Username search on workspace pages.** Searching for users by username now works correctly on Models, Knowledge, and Functions workspace pages, making it easier to find resources owned by specific users. [#20780](https://github.com/open-webui/open-webui/pull/20780)
- 🗑️ **File deletion orphaned embeddings fix.** Deleting files now properly removes associated knowledge base embeddings, preventing orphaned data from accumulating. [Commit](https://github.com/open-webui/open-webui/commit/93ed4ae2cda2f4311143e51f586aaa73b83a37a7)
- 🧹 **Event listener memory leak fix.** Memory leaks caused by event listeners not being cleaned up during navigation have been resolved. [#20913](https://github.com/open-webui/open-webui/pull/20913)
- 🐳 **Docker Ollama update fix.** Ollama can now be updated within Docker containers after adding a missing zstd dependency. [#20994](https://github.com/open-webui/open-webui/issues/20994), [#21052](https://github.com/open-webui/open-webui/pull/21052)
- 📝 **Workspace duplicate API request fix.** The prompts, knowledge, and models workspaces no longer make duplicate API requests when loading. [Commit](https://github.com/open-webui/open-webui/commit/ab5dfbda54664c9278b0d807ba06cad94edd798f), [Commit](https://github.com/open-webui/open-webui/commit/e5dbfc420dd3e7f6ba047a3e11584449ff0742b4)
- 📡 **OpenTelemetry Redis cluster fix.** OpenTelemetry instrumentation now works correctly with Redis cluster mode deployments. [#21129](https://github.com/open-webui/open-webui/pull/21129)
- 🐳 **Airgapped NLTK tokenizer fix.** Document extraction now works reliably in airgapped environments after container restarts by bundling NLTK tokenizer data in the Docker image. [#21165](https://github.com/open-webui/open-webui/pull/21165), [#21150](https://github.com/open-webui/open-webui/issues/21150)
- 💬 **Channel model mention crash fix.** Mentioning a model in channels no longer crashes when older thread messages have missing data. [#21112](https://github.com/open-webui/open-webui/pull/21112)
- 🔧 **OpenAPI tool import fix.** Importing OpenAPI tool specifications no longer crashes when parameters lack explicit name fields, fixing compatibility with complex request body definitions. [#21121](https://github.com/open-webui/open-webui/pull/21121), [Commit](https://github.com/open-webui/open-webui/commit/8e79b3d0bc4903f30e747b663ac818976618c83c)
- 🌐 **Webpage attachment content fix.** Attaching webpages to chats now retrieves full content instead of only metadata, fixing an unawaited coroutine in SSL certificate verification. [#21166](https://github.com/open-webui/open-webui/issues/21166), [Commit](https://github.com/open-webui/open-webui/commit/a214ec40ea00eebcba49570647ca6ab8f61765d5)
- 💾 **File upload settings persistence.** File upload settings (Max Upload Size, Max File Count, Image Compression dimensions) now persist correctly and are no longer erased when updating other RAG configuration settings. [#21057](https://github.com/open-webui/open-webui/issues/21057), [Commit](https://github.com/open-webui/open-webui/commit/258454276e1ef8ded24968515f7bf5e1833ca011)
- 📦 **Tool call expand/collapse fix.** Tool call results in chat can now be expanded and collapsed again after a recent refactor disabled this behavior. [#21205](https://github.com/open-webui/open-webui/pull/21205)
- 🪛 **Disabled API endpoint bypass fix.** Fixed Ollama/OpenAI API endpoints bypassing 'ENABLE_OLLAMA_API' and 'ENABLE_OPENAI_API' flags when the 'url_idx' parameter was provided. Endpoints now properly return a 503 error with a clear "API is disabled" message instead of attempting to connect and logging confusing connection errors.
- 🛠️ **OpenSearch 3.0 compatibility fix.** Document uploads to knowledge bases now work correctly when using OpenSearch backend with opensearch-py >= 3.0.0, fixing a TypeError that previously caused failures. [#21248](https://github.com/open-webui/open-webui/pull/21248), [#20649](https://github.com/open-webui/open-webui/issues/20649)
- 📱 **Gboard multi-line paste fix.** Multi-line text pasted from Gboard on Android now inserts correctly instead of being replaced with a single newline, fixing a bug where the keyboard's clipboard suggestion strip sent text via 'insertText' events instead of standard paste events. [#21265](https://github.com/open-webui/open-webui/pull/21265)
- 🔧 **Batch embeddings endpoint fix.** The '/api/embeddings' endpoint now correctly returns separate embeddings for each input string when processing batch requests to Ollama providers. [Commit](https://github.com/open-webui/open-webui/commit/8fd5c06e5bf7e0ccbda15d83338912ea17f66783), [#21279](https://github.com/open-webui/open-webui/issues/21279)
- 🗝️ **SSL verification for embeddings.** SSL certificate verification now respects the "AIOHTTP_CLIENT_SESSION_SSL" setting for OpenAI and Azure OpenAI embedding requests, allowing connections to self-signed certificate endpoints when disabled. [Commit](https://github.com/open-webui/open-webui/commit/cd31b8301b38bfa86872608cfbd022ff74e3ae52)
- 🔧 **Tool call HTML entity fix.** Models now receive properly formatted tool call results in multi-turn conversations, fixing an issue where HTML entities caused malformed content that was hard to parse. [#20755](https://github.com/open-webui/open-webui/pull/20755)
- 💾 **Duplicate inline image context fix.** Inline images no longer exhaust the model's context window by including their full base64 data in chat metadata, preventing premature context exhaustion with image-heavy conversations. [#20916](https://github.com/open-webui/open-webui/pull/20916)
- 🐛 **OpenAI model cache lookup fix.** The OpenAI API router model lookup was corrected to use the proper model identifier when checking the cache, ensuring consistent and correct model retrieval during chat completions. [#21327](https://github.com/open-webui/open-webui/pull/21327)
- 🐛 **Ollama latest suffix fix.** Ollama-compatible providers that don't use ":latest" in model names can now successfully chat, fixing errors where model names were incorrectly appended with ":latest" suffixes. [#21331](https://github.com/open-webui/open-webui/issues/21331), [Commit](https://github.com/open-webui/open-webui/commit/05ae44b98dc279ee12cc8eab17278ccbfec60301)
- ⛔ **OpenAI endpoint detection fix.** OpenAI API endpoint detection was corrected to use exact hostname matching instead of substring matching, preventing third-party providers with similar URL patterns from being incorrectly filtered. [Commit](https://github.com/open-webui/open-webui/commit/423d8b18170a0b92b582aba6ef7bb9ba173e876e)
- 🛠️ **RedisCluster task stopping fix.** Task stopping now works correctly in RedisCluster deployments, fixing an issue where tasks would remain active after cancellation attempts. [#20803](https://github.com/open-webui/open-webui/pull/20803), [Commit](https://github.com/open-webui/open-webui/commit/0dcbd05e2436929ae9d2c559a204844ae0239b57)
- 📎 **Citation parsing error fix.** Citation parsing no longer crashes when builtin tools return error responses, fixing AttributeError issues when tools like search_web fail. [#21071](https://github.com/open-webui/open-webui/pull/21071)

### Changed

- ‼️ **Database Migration Required** — This release includes database schema changes; multi-worker, multi-server, or load-balanced deployments must update all instances simultaneously rather than performing rolling updates, as running mixed versions will cause application failures due to schema incompatibility between old and new instances.
- ⚠️ **Chat Message Table Migration** — This release includes a new chat message table migration that can take a significant amount of time to complete in larger deployments with extensive chat histories. Administrators should plan for adequate maintenance windows and allow the migration to complete fully without interruption. Running the migration with insufficient time or resources may result in data integrity issues.
- 🔗 **Prompt ID-based URLs.** Prompts now use unique ID-based URLs instead of command-based URLs, allowing more flexible command renaming without breaking saved links or integrations. [#20945](https://github.com/open-webui/open-webui/pull/20945)

## [0.7.2] - 2026-01-10

### Fixed

- ⚡ Users no longer experience database connection timeouts under high concurrency due to connections being held during LLM calls, telemetry collection, and file status streaming. [#20545](https://github.com/open-webui/open-webui/pull/20545), [#20542](https://github.com/open-webui/open-webui/pull/20542), [#20547](https://github.com/open-webui/open-webui/pull/20547)
- 📝 Users can now create and save prompts in the workspace prompts editor without encountering errors. [Commit](https://github.com/open-webui/open-webui/commit/ab99d3b1129cffbc13cf7de5aa897692e3f8662e)
- 🎙️ Users can now use local Whisper for speech-to-text when STT_ENGINE is left empty (the default for local mode). [#20534](https://github.com/open-webui/open-webui/pull/20534)
- 📊 The Evaluations page now loads faster by eliminating duplicate API calls to the leaderboard and feedbacks endpoints. [Commit](https://github.com/open-webui/open-webui/commit/2dd09223f2aac301a4d5c17fb667d974c34f3ff1)
- 🌐 Fixed missing Settings tab i18n label keys. [#20526](https://github.com/open-webui/open-webui/pull/20526)

## [0.7.1] - 2026-01-09

### Fixed

- ⚡ **Improved reliability for low-spec and SQLite deployments.** Fixed page timeouts by disabling database session sharing by default, improving stability for resource-constrained environments. Users can re-enable via 'DATABASE_ENABLE_SESSION_SHARING=true' if needed. [#20520](https://github.com/open-webui/open-webui/issues/20520)

## [0.7.0] - 2026-01-09

### Added

- 🤖 **Native Function Calling with Built-in Tools.** Users can now ask models to perform multi-step tasks that combine web research, knowledge base queries, note-taking, and image generation in a single conversation—for example, "research the latest on X, save key findings to a note, and generate an infographic." Requires models with native function calling support and function calling mode set to "Native" in Chat Controls. [#19397](https://github.com/open-webui/open-webui/issues/19397), [Commit](https://github.com/open-webui/open-webui/commit/5c1d52231a3997a17381c48639bd7e339262cf7c)
- 🧠 Users can now ask the model to find relevant context from their notes, past chats, and channel messages—for example, "what did I discuss about project X last week?" or "find the conversation where I brainstormed ideas for Y." [Commit](https://github.com/open-webui/open-webui/commit/646835d76744ad9b2e67ede0407a61d62e969aab)
- 📚 Users can now ask the model to search their knowledge bases and retrieve documents without manually attaching files—for example, "find the section about authentication in our API docs" or "what do our internal guidelines say about X?" [Commit](https://github.com/open-webui/open-webui/commit/c8622adcb01f3091b17ca50f8c8e2f20c7b9cd2a)
- 💭 Users with models that support interleaved thinking now get more refined results from multi-step workflows, as the model can analyze each tool's output before deciding what to do next.
- 🔍 When models invoke web search, search results appear as clickable citations in real-time for full source verification. [Commit](https://github.com/open-webui/open-webui/commit/2789f6a24d8405c30cd48ae460071f6a4f2c35f9)
- 🎚️ Users can selectively disable specific built-in tools (timestamps, memory, chat history, notes, web search, knowledge bases) per model via the model editor's capabilities settings. [Commit](https://github.com/open-webui/open-webui/commit/60e916d6c0c5f7db9e6d670e12be2d1d4abc2dd6)
- 👁️ Pending tool calls are now displayed during response generation, so users know which tools are being invoked. [Commit](https://github.com/open-webui/open-webui/commit/1d08376860e775049abd1dd5f568ac0c6466c944)
- 📁 Administrators can now limit the number of files that can be uploaded to folders using the "FOLDER_MAX_FILE_COUNT" setting, preventing resource exhaustion from bulk uploads. [#19810](https://github.com/open-webui/open-webui/issues/19810), [Commit](https://github.com/open-webui/open-webui/commit/a1036e544d573e3d35e05c1c2472ba762c32431b), [Commit](https://github.com/open-webui/open-webui/commit/d3ee3fd23e762c9d83fe1da5636d03259e186e57)
- ⚡ Users experience transformative speed improvements across the entire application through completely reengineered database connection handling, delivering noticeably faster page loads, butter-smooth interactions, and rock-solid stability during intensive operations like user management and bulk data processing. [Commit](https://github.com/open-webui/open-webui/commit/2041ab483e21b3a757baa25c47dc2fa29018674f), [Commit](https://github.com/open-webui/open-webui/commit/145c7516f227ce56fd52373cee86217fadf16181), [Commit](https://github.com/open-webui/open-webui/commit/475dd91ed798f2efcdf27799d5c5cae3f0e6e847), [Commit](https://github.com/open-webui/open-webui/commit/5d1459df166cce8445eb1556cc26abbd65a3f9f4), [Commit](https://github.com/open-webui/open-webui/commit/2453b75ff0fb2dc75b929d96f417d84e332922d9), [Commit](https://github.com/open-webui/open-webui/commit/5649a668fad15393a52c27a2f188841af8b66989)
- 🚀 Users experience significantly faster initial page load times through dynamic loading of document processing libraries, reducing the initial bundle size. [#20200](https://github.com/open-webui/open-webui/pull/20200), [#20202](https://github.com/open-webui/open-webui/pull/20202), [#20203](https://github.com/open-webui/open-webui/pull/20203), [#20204](https://github.com/open-webui/open-webui/pull/20204)
- 💨 Administrators experience dramatically faster user list loading through optimized database queries that eliminate N+1 query patterns, reducing query count from 1+N to just 2 total queries regardless of user count. [#20427](https://github.com/open-webui/open-webui/pull/20427)
- 📋 Notes now load faster through optimized database queries that batch user lookups instead of fetching each note's author individually. [Commit](https://github.com/open-webui/open-webui/commit/084f0ef6a5491e186bf6b71c6386973ba18ef2fa)
- 💬 Channel messages, pinned messages, and thread replies now load faster through batched user lookups instead of individual queries per message. [#20458](https://github.com/open-webui/open-webui/pull/20458), [#20459](https://github.com/open-webui/open-webui/pull/20459), [#20460](https://github.com/open-webui/open-webui/pull/20460)
- 🔗 Users can now click citation content links to jump directly to the relevant portion of source documents with automatic text highlighting, making it easier to verify AI responses against their original sources. [#20116](https://github.com/open-webui/open-webui/pull/20116), [Commit](https://github.com/open-webui/open-webui/commit/40c45ffe1f9b45538d32c8ecba8cac62c6eca503)
- 📌 Users can now pin or hide models directly from the Workspace Models page and Admin Settings Models page, making it easier to manage which models appear in the sidebar without switching to the chat interface. [#20176](https://github.com/open-webui/open-webui/pull/20176)
- 🔎 Administrators can now quickly find settings using the new search bar in the Admin Settings sidebar, which supports fuzzy filtering by category names and related keywords like "whisper" for Audio or "rag" for Documents. [#20434](https://github.com/open-webui/open-webui/pull/20434)
- 🎛️ Users can now view read-only models in the workspace models list, with clear "Read Only" badges indicating when editing is restricted. [#20243](https://github.com/open-webui/open-webui/issues/20243), [#20369](https://github.com/open-webui/open-webui/pull/20369)
- 📝 Users can now view read-only prompts in the workspace prompts list, with clear "Read Only" badges indicating when editing is restricted. [#20368](https://github.com/open-webui/open-webui/pull/20368)
- 🔧 Users can now view read-only tools in the workspace tools list, with clear "Read Only" badges indicating when editing is restricted. [#20243](https://github.com/open-webui/open-webui/issues/20243), [#20370](https://github.com/open-webui/open-webui/pull/20370)
- 📂 Searching for files is now significantly faster, especially for users with large file collections. [Commit](https://github.com/open-webui/open-webui/commit/a9a979fb3db1743553ca0705f571c0b9c252841f)
- 🏆 The Evaluations leaderboard now calculates Elo ratings on the backend instead of in the browser, improving performance and enabling topic-based model ranking through semantic search. [#15392](https://github.com/open-webui/open-webui/pull/15392), [#20476](https://github.com/open-webui/open-webui/issues/20476), [Commit](https://github.com/open-webui/open-webui/commit/10838b3654bf6fdef02d57311f7f1c01df4cd033)
- 📊 The Evaluations leaderboard now includes a per-model activity chart displaying daily wins and losses as a diverging bar chart, with 30-day, 1-year, and all-time views using weekly aggregation for longer timeframes.
- 🎞️ Users can now upload animated GIF and WebP formats as model profile images, with animation preserved by skipping resize processing for these file types. [Commit](https://github.com/open-webui/open-webui/commit/00af37bb4ed1ea0957c7c84a6a8def3a7998b8ca)
- 📸 Users uploading profile images for users, models, and arena models now benefit from WebP compression at 80% quality instead of JPEG, resulting in significantly smaller file sizes and faster uploads while maintaining visual quality. [Commit](https://github.com/open-webui/open-webui/commit/b1d30673b69571e081abb881d34944cf33cdc67e)
- ⭐ Action Function developers can now update message favorite status using the new "chat:message:favorite" event, enabling the development of pin/unpin message actions without race conditions from frontend auto-save. [#20375](https://github.com/open-webui/open-webui/pull/20375)
- 🌐 Users with OpenAI-compatible models that have web search capabilities now see URL citations displayed as sources in the interface. [#20172](https://github.com/open-webui/open-webui/pull/20172), [Commit](https://github.com/open-webui/open-webui/commit/fe84afd09a2bc8a89311f30186ec2608a4edda3a)
- 📰 Users can now dismiss the "What's New" changelog modal permanently using the X button, matching the behavior of the "Okay, Let's Go!" button. [#20258](https://github.com/open-webui/open-webui/pull/20258)
- 📧 Administrators can now configure the admin contact email displayed in the Account Pending overlay directly from the Admin Panel instead of only through environment variables. [#12500](https://github.com/open-webui/open-webui/issues/12500), [#20260](https://github.com/open-webui/open-webui/pull/20260)
- 📄 Administrators can now enable markdown header text splitting as a preprocessing step that works with either character or token splitting, through the new "ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER" setting. [Commit](https://github.com/open-webui/open-webui/commit/d3a682759f375c6cb0bc8c170f62863a070f712e), [Commit](https://github.com/open-webui/open-webui/commit/18a33a079bf07487edffc421a721c86194cc90c9), [Commit](https://github.com/open-webui/open-webui/commit/08bf4670ec862018f9dc57296cb19fd5eab14ef6)
- 🧩 Administrators can now set a minimum chunk size target using the "CHUNK_MIN_SIZE_TARGET" setting to merge small markdown header chunks with neighbors, which improves retrieval quality by eliminating tiny meaningless fragments, significantly speeds up document processing and embedding, reduces storage costs, and lowers embedding API costs or local compute requirements. [#19595](https://github.com/open-webui/open-webui/issues/19595), [#20314](https://github.com/open-webui/open-webui/pull/20314), [Commit](https://github.com/open-webui/open-webui/commit/c32435958073cf002d87e78544baa88bc4e15d7f)
- 💨 Administrators can now enable KV prefix caching optimization by setting "RAG_SYSTEM_CONTEXT" to true, which injects RAG context into the system message instead of user messages, enabling models to reuse cached tokens for follow-up questions instead of reprocessing the entire context on each turn, significantly improving response times and reducing costs for cloud-based models. [#20301](https://github.com/open-webui/open-webui/discussions/20301), [#20317](https://github.com/open-webui/open-webui/pull/20317)
- 🖼️ Administrators and Action developers can now control image generation denoising steps per-request using a steps parameter, allowing Actions and API calls to override the global IMAGE_STEPS configuration for both ComfyUI and Automatic1111 engines. [#20337](https://github.com/open-webui/open-webui/pull/20337)
- 🗄️ Administrators running multi-pod deployments can now designate a master pod to handle database migrations using the "ENABLE_DB_MIGRATIONS" environment variable. [Commit](https://github.com/open-webui/open-webui/commit/9824f0e33359a917ac07b60bf1f972074d5c8203)
- 🎙️ Administrators can now configure Whisper's compute type using the "WHISPER_COMPUTE_TYPE" environment variable to fix compatibility issues with CUDA/GPU deployments. [Commit](https://github.com/open-webui/open-webui/commit/26af1f92e21ddfd08348570bf54a6f345ac69648)
- 🔍 Administrators can now control sigmoid normalization for CrossEncoder reranking models using the "SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION" environment variable, enabled by default for proper relevance threshold behavior with MS MARCO models. [#20228](https://github.com/open-webui/open-webui/pull/20228)
- 🔒 Administrators can now disable SSL certificate verification for external tools using the "REQUESTS_VERIFY" environment variable, enabling integration with self-signed certificates for Tika, Ollama embeddings, and external rerankers. [#19968](https://github.com/open-webui/open-webui/issues/19968), [Commit](https://github.com/open-webui/open-webui/commit/dfc5dad63167eabb7fb027e63c324675b23f2e9d)
- 📈 Administrators can now control audit log output destinations using "ENABLE_AUDIT_STDOUT" and "ENABLE_AUDIT_LOGS_FILE" environment variables, allowing audit logs to be sent to container logs for centralized logging systems. [#20114](https://github.com/open-webui/open-webui/pull/20114), [Commit](https://github.com/open-webui/open-webui/commit/fdae5644e36972384b3e2513e3074f95f9f7381f)
- 🛡️ Administrators can now restrict non-admin user access to Interface Settings through per-user or per-group permissions. [#20424](https://github.com/open-webui/open-webui/pull/20424)
- 🧠 Administrators can now globally enable or disable the Memories feature and control access through per-user or per-group permissions, with the Personalization tab automatically hidden when the feature is disabled. [#20462](https://github.com/open-webui/open-webui/pull/20462)
- 🟢 Administrators can now globally enable or disable user status visibility through the "ENABLE_USER_STATUS" setting in Admin Settings. [#20488](https://github.com/open-webui/open-webui/pull/20488)
- 🪝 Channel managers can now create webhooks to allow external services to post messages to channels without authentication. [Commit](https://github.com/open-webui/open-webui/commit/cd296fcf0d79cecd1a6a3ee4e492c6b5246ca7ae)
- 📄 In the model editor users can now disable the "File Context" capability to skip automatic file content extraction and injection, forwarding raw messages with file attachment metadata instead for use with custom tools or future built-in file access tools. [Commit](https://github.com/open-webui/open-webui/commit/daccf0713e3ecd6d24f003a87b5f8b3c61852958), [Docs:Commit](https://github.com/open-webui/docs/commit/18ec6eaefc071a278ec57d4d1b8d66d686af0870)
- 🔊 In the model editor users can now configure a specific TTS voice for each model, overriding user preferences and global defaults to give different AI personas distinct voices. [#3097](https://github.com/open-webui/open-webui/issues/3097), [Commit](https://github.com/open-webui/open-webui/commit/bb6188abf04302f79d80b0d6cc42c232624b5757)
- 👥 Administrators now have three granular group sharing permission options instead of a simple on/off toggle, allowing them to choose between "No one", "Members", or "Anyone" for who can share content to each group. [Commit](https://github.com/open-webui/open-webui/commit/ca514cd3eda2524b8da472ef17c0ccb216bac2e8)
- 📦 Administrators can now export knowledge bases as zip files containing text files for backup and archival purposes. [#20120](https://github.com/open-webui/open-webui/issues/20120), [Commit](https://github.com/open-webui/open-webui/commit/c1147578c073a8c7fa7e7f836149e1cdfec8f18d)
- 🚀 Administrators can now create an admin account automatically at startup via "WEBUI_ADMIN_EMAIL", "WEBUI_ADMIN_PASSWORD", and "WEBUI_ADMIN_NAME" environment variables, enabling headless and automated deployments without exposing the signup page. [#17654](https://github.com/open-webui/open-webui/issues/17654), [Commit](https://github.com/open-webui/open-webui/commit/1138929f4d083931305f1f925899971b190562ae)
- 🦆 Administrators can now select a specific search backend for DDGS instead of random selection, with options including Bing, Brave, DuckDuckGo, Google, Wikipedia, Yahoo, and others. [#20330](https://github.com/open-webui/open-webui/issues/20330), [#20366](https://github.com/open-webui/open-webui/pull/20366)
- 🧭 Administrators can now configure custom Jina Search API endpoints using the "JINA_API_BASE_URL" environment variable, enabling region-specific deployments such as EU data processing. [#19718](https://github.com/open-webui/open-webui/pull/19718), [Commit](https://github.com/open-webui/open-webui/commit/f7f8a263b92289df8d4f8dbc3bae09bd009a5699)
- 🔥 Administrators can now configure Firecrawl timeout values using the "FIRECRAWL_TIMEOUT" environment variable to control web scraping wait times. [#19973](https://github.com/open-webui/open-webui/pull/19973), [Commit](https://github.com/open-webui/open-webui/commit/89ad1c68d1aadf849960b5e202aa4651096b05f5)
- 💾 Administrators can now use openGauss as the vector database backend for knowledge base document storage and retrieval. [#20179](https://github.com/open-webui/open-webui/pull/20179)
- 🔄 Various improvements were implemented across the application to enhance performance, stability, and security.
- 📊 Users can now sync their anonymous usage statistics to the Open WebUI Community platform to power community leaderboards, drive model evaluations, and contribute to open-source AI research that benefits everyone, all while keeping conversations completely private (only metadata like model names, message counts, and ratings are shared). By sharing your stats, you're helping the community identify which models perform best, contributing to transparent AI benchmarking, and supporting the collective effort to make AI better for all. You can also download your stats as JSON for personal analysis.
- 🌐 Translations for German, Portuguese (Brazil), Spanish, Simplified Chinese, Traditional Chinese, and Polish were enhanced and expanded.

### Fixed

- 🔊 Text-to-speech now correctly splits on newlines in addition to punctuation, so markdown bullet points and lists are spoken as separate sentences instead of being merged together. [#5924](https://github.com/open-webui/open-webui/issues/5924), [Commit](https://github.com/open-webui/open-webui/commit/869108a3e1ce2b8110084113c1b392072e98fd5f)
- 🔒 Users are now protected from stored XSS vulnerabilities in iFrame embeds for citations and response messages through configurable same-origin sandbox settings instead of hardcoded values. [#20209](https://github.com/open-webui/open-webui/pull/20209), [#20210](https://github.com/open-webui/open-webui/pull/20210)
- 🔑 Image Generation, Web Search, and Audio (TTS/STT) API endpoints now enforce permission checks on the backend, closing a security gap where disabled features could previously be accessed via direct API calls. [#20471](https://github.com/open-webui/open-webui/pull/20471)
- 🛠️ Tools and Tool Servers (MCP and OpenAPI) now enforce access control checks on the backend, ensuring users can only access tools they have permission to use even via direct API calls. [#20443](https://github.com/open-webui/open-webui/issues/20443), [Commit](https://github.com/open-webui/open-webui/commit/9b06fdc8fe1c933071610336be05f11e77e6c8eb)
- 🔁 System prompts are no longer duplicated when using native function calling, fixing an issue where the prompt would be applied twice during tool-calling workflows. [Commit](https://github.com/open-webui/open-webui/commit/9223efaff0db6e56bfa157ef214d9590005156d2)
- 🗂️ Knowledge base uploads to folders no longer fail when "FOLDER_MAX_FILE_COUNT" is unset, fixing an issue where the default null value caused all uploads to error. [Commit](https://github.com/open-webui/open-webui/commit/ef9cd0e0ad6e45b8a3efec6f3858b3d69d42f619)
- 📝 The "Create Note" button in the chat input now correctly hides for users without Notes permissions instead of showing and returning a 401 error when clicked. [#20486](https://github.com/open-webui/open-webui/issues/20486), [Commit](https://github.com/open-webui/open-webui/commit/9e9616b670c1c4389193b18500a7d80d86d7e280)
- 📊 The Evaluations page no longer crashes when administrators have large amounts of feedback data, as the leaderboard now fetches only the minimal required fields instead of loading entire conversation snapshots. [#20476](https://github.com/open-webui/open-webui/issues/20476), [#20489](https://github.com/open-webui/open-webui/pull/20489), [Commit](https://github.com/open-webui/open-webui/commit/b2a1f71d920e55b143f1c02e61104938d2588762)
- 💬 Users can now export chats, use the Ask/Explain popup, and view chat lists correctly again after these features were broken by recent refactoring changes that caused 500 and 400 server errors. [#20146](https://github.com/open-webui/open-webui/issues/20146), [#20205](https://github.com/open-webui/open-webui/issues/20205), [#20206](https://github.com/open-webui/open-webui/issues/20206), [#20212](https://github.com/open-webui/open-webui/pull/20212)
- 💭 Users no longer experience data corruption when switching between chats during background operations like image generation, where messages from one chat would appear in another chat's history. [#20266](https://github.com/open-webui/open-webui/pull/20266)
- 🛡️ Users no longer encounter critical chat stability errors, including duplicate key errors from circular message dependencies, null message access during chat loading, and errors in the chat overview visualization. [#20268](https://github.com/open-webui/open-webui/pull/20268)
- 📡 Users with Channels no longer experience infinite recursion and connection pool exhaustion when fetching threaded replies, preventing RecursionError crashes during chat history loading. [#20299](https://github.com/open-webui/open-webui/pull/20299), [Commit](https://github.com/open-webui/open-webui/commit/c144122f608759c2b79472e1f6948a7c1600a3d1)
- 📎 Users no longer encounter TypeError crashes when viewing messages with file attachments that have undefined URL properties. [#20343](https://github.com/open-webui/open-webui/pull/20343)
- 🔐 Users with MCP integrations now experience reliable OAuth 2.1 token refresh after access token expiration through proper Protected Resource discovery, preventing integration failures that caused sessions to be deleted. [#19794](https://github.com/open-webui/open-webui/issues/19794), [#20138](https://github.com/open-webui/open-webui/pull/20138), [#20291](https://github.com/open-webui/open-webui/issues/20291), [Commit](https://github.com/open-webui/open-webui/commit/bf2b2962399e341926bdbf9e0a82101f31a90b23), [Commit](https://github.com/open-webui/open-webui/commit/89565c58c6ae6b5b129559ef68b5a0c18c110765)
- 📚 Users who belong to multiple groups can now see Knowledge Bases shared with those groups, fixing an issue where they would disappear when shared with more than one group. [#20124](https://github.com/open-webui/open-webui/issues/20124), [#20229](https://github.com/open-webui/open-webui/issues/20229), [Commit](https://github.com/open-webui/open-webui/commit/61e25dc2dce9c12dcb5b88a6b814060c4338e67b)
- 📂 Users now see the correct Knowledge Base name when hovering over # file references in chat input instead of "undefined". [#20329](https://github.com/open-webui/open-webui/issues/20329), [#20333](https://github.com/open-webui/open-webui/pull/20333)
- 📋 Users now see notes displayed in correct chronological order within their time range groupings, fixing an issue where insertion order was not preserved. [Commit](https://github.com/open-webui/open-webui/commit/3f577c0c3fbfd9f09c02940e4ae474f987149277)
- 📑 Users collaborating on notes now experience proper content sync when initializing from both HTML and JSON formats, fixing sync failures in collaborative editing sessions. [Commit](https://github.com/open-webui/open-webui/commit/e27fb3e291a735c715a089a80e7a49d2c2209096)
- 🔎 Users searching notes can now find hyphenated words and variations with spaces, so searching "todo" now finds "to-do" and "to do". [Commit](https://github.com/open-webui/open-webui/commit/a3270648d8b8535443d8ce2ea719f8e678e4e358)
- 📥 Users no longer experience false duplicate file warnings when reuploading files after initial processing failed, as the file hash is now only stored after successful processing completion. [#19264](https://github.com/open-webui/open-webui/issues/19264), [#20282](https://github.com/open-webui/open-webui/pull/20282), [Commit](https://github.com/open-webui/open-webui/commit/d3ab9f4b96eee7f91c9b1355cee055fdabca9730)
- 💾 Users experience significantly improved page load performance as model profile images now cache properly in browsers, avoiding unnecessary image refetches. [Commit](https://github.com/open-webui/open-webui/commit/bb821ab654e93908a3b4632c359753eeff053264)
- 🎨 Users can now successfully edit uploaded images instead of having new images generated, fixing an issue introduced by the file storage refactor where images with type "file" and content_type starting with "image/" weren't being recognized as editable images. [#20237](https://github.com/open-webui/open-webui/issues/20237), [#20169](https://github.com/open-webui/open-webui/pull/20169), [#20239](https://github.com/open-webui/open-webui/pull/20239), [Commit](https://github.com/open-webui/open-webui/commit/1148d1c927d096e14917b6d762789fca3188f281)
- 🌐 Users writing in Persian and Arabic now see properly displayed right-to-left text in the notes section through automatic text direction detection. [#19743](https://github.com/open-webui/open-webui/issues/19743), [#20102](https://github.com/open-webui/open-webui/pull/20102), [Commit](https://github.com/open-webui/open-webui/commit/b619a157bc54c5bc44d223d2ae3acb9ce4ac6a6c)
- 🤖 Users can now successfully @ mention models in Channels instead of experiencing silent failures. [Commit](https://github.com/open-webui/open-webui/commit/59957715836acb635f4b1c4ddbfb4ba7b82b3281)
- 📋 Users on Windows now see correctly preserved line breaks when using the {{CLIPBOARD}} variable through CRLF to LF normalization. [#19370](https://github.com/open-webui/open-webui/issues/19370), [#20283](https://github.com/open-webui/open-webui/pull/20283)
- 📁 Users now see the Knowledge Selector dropdown correctly displayed above the Create Folder modal instead of being hidden behind it. [#20219](https://github.com/open-webui/open-webui/issues/20219), [#20213](https://github.com/open-webui/open-webui/pull/20213)
- 🌅 Users now see profile images in non-PNG formats like SVG, JPEG, and GIF displayed correctly instead of appearing broken. [#20171](https://github.com/open-webui/open-webui/pull/20171)
- 🆕 Non-admin users with disabled temporary chat permissions can now successfully create new chats and use pinned models from the sidebar. [#20336](https://github.com/open-webui/open-webui/issues/20336), [#20367](https://github.com/open-webui/open-webui/pull/20367), [Commit](https://github.com/open-webui/open-webui/commit/e754940c031f9689fb4f6edb3625aa06aeb53377)
- 🎛️ Users can now successfully use workspace models in chat, fixing "Model not found" errors that occurred when using custom model presets. [#20340](https://github.com/open-webui/open-webui/issues/20340), [#20344](https://github.com/open-webui/open-webui/pull/20344), [Commit](https://github.com/open-webui/open-webui/commit/b55a46ae99c32068ed306a5ecdaafa9f75504cd7), [Commit](https://github.com/open-webui/open-webui/commit/2bb13d5dbc6e233856e8aa26143222ceda8f6c11)
- 🔁 Users can now regenerate messages without crashes when the parent message is missing or corrupted in the chat history. [#20264](https://github.com/open-webui/open-webui/pull/20264)
- ✏️ Users no longer experience TipTap rich text editor crashes with "editor view is not available" errors when plugins or async methods try to access the editor after it has been destroyed. [#20266](https://github.com/open-webui/open-webui/pull/20266)
- 📗 Administrators with bypass access control enabled now correctly have write access to all knowledge bases. [#20371](https://github.com/open-webui/open-webui/pull/20371)
- 🔍 Administrators using local CrossEncoder reranking models now see proper relevance threshold behavior through MS MARCO model score normalization to the 0-1 range via sigmoid activation. [#19999](https://github.com/open-webui/open-webui/issues/19999), [#20228](https://github.com/open-webui/open-webui/pull/20228)
- 🎯 Administrators using local SentenceTransformers embedding engine now benefit from proper batch size settings, preventing excessive memory usage from the default batch size of 32. [#20053](https://github.com/open-webui/open-webui/issues/20053), [#20054](https://github.com/open-webui/open-webui/pull/20054), [Commit](https://github.com/open-webui/open-webui/commit/e4a5b06ca68303512678b4d2dc296bc78b9f983f)
- 🔧 Administrators and users in offline mode or restricted environments like uv, poetry, and NixOS no longer experience crashes when Tools and Functions have frontmatter requirements, as pip installation is now skipped when offline mode is enabled. [#20320](https://github.com/open-webui/open-webui/issues/20320), [#20321](https://github.com/open-webui/open-webui/pull/20321), [Commit](https://github.com/open-webui/open-webui/commit/bd07ef8)
- 📄 Administrators can now properly configure the MinerU document parsing service as the MinerU Cloud API key field is now available in the Admin Panel Documents settings. [#20319](https://github.com/open-webui/open-webui/issues/20319), [#20328](https://github.com/open-webui/open-webui/pull/20328)
- ⚠️ Administrators no longer see SyntaxWarnings for invalid escape sequences in password validation regex patterns. [#20298](https://github.com/open-webui/open-webui/pull/20298), [Commit](https://github.com/open-webui/open-webui/commit/e55bf2c2ac391caed871d41f0484820091081908)
- 🎨 Users with ComfyUI workflows now see only the intended final output images in chat instead of duplicate images from intermediate processing nodes like masks, crops, or segmentation previews. [#20158](https://github.com/open-webui/open-webui/issues/20158), [#20182](https://github.com/open-webui/open-webui/pull/20182)
- 🖼️ Users with image generation enabled no longer see false vision capability warnings, allowing them to send follow-up messages after generating images and to send images to non-vision models for image editing. [#20129](https://github.com/open-webui/open-webui/issues/20129), [#20256](https://github.com/open-webui/open-webui/pull/20256)
- 🔌 Administrators no longer experience infinite loading screens when invalid or MCP-style configurations are used with OpenAPI connection types for external tools. [#20207](https://github.com/open-webui/open-webui/issues/20207), [#20257](https://github.com/open-webui/open-webui/pull/20257)
- 📥 Administrators no longer encounter TypeError crashes during SHA256 verification when uploading GGUF models via URL, fixing 500 Internal Server Error crashes. [#20263](https://github.com/open-webui/open-webui/issues/20263)
- 🚦 Users with Brave Search now experience automatic retry with a 1-second delay when hitting rate limits, preventing failures when sequential requests exceed the 1 request per second limit, though this only works reliably when web search concurrency is set to a maximum of 1. [#15134](https://github.com/open-webui/open-webui/issues/15134), [#20255](https://github.com/open-webui/open-webui/pull/20255)
- 🗄️ Administrators with Redis Sentinel deployments no longer experience crashes during websocket disconnections due to improper async-generator handling in the YDocManager. [#20142](https://github.com/open-webui/open-webui/issues/20142), [#20145](https://github.com/open-webui/open-webui/pull/20145)
- 🔐 Administrators using SCIM group management no longer encounter 500 errors when working with groups that have no members. [#20187](https://github.com/open-webui/open-webui/pull/20187)
- 🔗 Users now experience more reliable citations from AI models, especially when using smaller or weaker models that may not format citation references perfectly. [Commit](https://github.com/open-webui/open-webui/commit/c0ec04935b4eea3d334bfdec2fc41278f1085a49)
- 🕸️ Administrators can now successfully save WebSearch settings without encountering validation errors for domain filter lists, YouTube language settings, or timeout values. [#20422](https://github.com/open-webui/open-webui/pull/20422)
- 📦 Administrators installing with the uv package manager now experience successful installation after deprecated dependencies that were causing conflicts were removed. [#20177](https://github.com/open-webui/open-webui/issues/20177), [#20192](https://github.com/open-webui/open-webui/pull/20192)
- ⏱️ Administrators using custom "AIOHTTP_CLIENT_TIMEOUT" settings now see the configured timeout correctly applied to embedding generation, OAuth discovery, webhook calls, and tool/function loading instead of falling back to the default 300-second timeout. [Commit](https://github.com/open-webui/open-webui/commit/e67891a374625d9888ec391da561f0b4ed79ed5d)

### Changed

- ⚠️ This release includes a major overhaul of database connection handling in the backend that requires all instances in multi-worker, multi-server, or load-balanced deployments to be updated simultaneously; running mixed versions will cause failures due to incompatible database connection management between old and new instances.
- 📝 Administrators who previously used the standalone "Markdown (Header)" text splitter must now switch to "character" or "token" mode with the new "ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER" toggle enabled, as document chunking now applies markdown header splitting as a preprocessing step before character or token splitting. [Commit](https://github.com/open-webui/open-webui/commit/d3a682759f375c6cb0bc8c170f62863a070f712e), [Commit](https://github.com/open-webui/open-webui/commit/18a33a079bf07487edffc421a721c86194cc90c9), [Commit](https://github.com/open-webui/open-webui/commit/08bf4670ec862018f9dc57296cb19fd5eab14ef6)
- 🖼️ Users no longer see the "Generate Image" action button in chat message interfaces; custom function should be used. [Commit](https://github.com/open-webui/open-webui/commit/f0829ba6e6fd200702fb76efc43dd785cf87fec9)
- 🔗 Administrators will find the Admin Evaluations page at the new URL "/admin/evaluations/feedback" instead of "/admin/evaluations/feedbacks" to use the correct uncountable form of the word. [#20296](https://github.com/open-webui/open-webui/pull/20296)
- 🔐 Scripts or integrations that directly called Image Generation, Web Search, or Audio APIs while those features were disabled in the Admin UI will now receive 403 Forbidden errors, as backend permission enforcement has been added to match frontend restrictions. [#20471](https://github.com/open-webui/open-webui/pull/20471)
- 👥 The default group sharing permission changed from "Members" to "Anyone", meaning users can now share content to any group configured with "Anyone" permission regardless of their membership in that group. [Commit](https://github.com/open-webui/open-webui/commit/ca514cd3eda2524b8da472ef17c0ccb216bac2e8)

## [0.6.43] - 2025-12-22

### Fixed

- 🐍 **Python dependency installation issues** were resolved by correcting pip dependency handling, preventing installation failures in certain environments and improving setup reliability. [Commit](https://github.com/open-webui/open-webui/commit/5c5f87a)
- 🎙️ **Speech-to-Text default content type handling** was fixed and refactored to ensure correct MIME type usage, improving compatibility across STT providers and preventing transcription errors caused by incorrect defaults. [Commit](https://github.com/open-webui/open-webui/commit/4ab917c)
- 🖼️ **Temporary chat image handling** was fixed and refactored, ensuring images generated or edited in temporary chats are correctly processed, stored, and displayed without inconsistencies or missing references. [Commit](https://github.com/open-webui/open-webui/commit/423983f)
- 🎨 **Image action button fixed**, restoring the ability to trigger image generation, editing, and related image actions from the chat UI. [Commit](https://github.com/open-webui/open-webui/commit/def8a00)

## [0.6.42] - 2025-12-21

### Added

- 📚 Knowledge base file management was overhauled with server-side pagination loading 30 files at a time instead of loading entire collections at once, dramatically improving performance and responsiveness for large knowledge bases with hundreds or thousands of files, reducing initial load times and memory usage while adding server-side search and filtering, view options for files added by the user versus shared files, customizable sorting by name or date, and file authorship tracking with upload timestamps. [Commit](https://github.com/open-webui/open-webui/commit/94a8439105f30203ea9d729787c9c5978f5c22a2)
- ✨ Knowledge base file management was enhanced with automatic list refresh after file operations ensuring immediate UI updates, improved permission validation at the model layer, and automatic channel-file association for files uploaded with channel metadata. [Commit](https://github.com/open-webui/open-webui/commit/c15201620d03a9b60b800a34d8dc3426722c5b8b)
- 🔎 Knowledge command in chat input now uses server-side search for massive performance increases when selecting knowledge bases and files. [Commit](https://github.com/open-webui/open-webui/commit/0addc1ea461d7b4eee8fe0ca2fedd615b3988b0e)
- 🗂️ Knowledge workspace listing now uses server-side pagination loading 30 collections at a time with new search endpoints supporting query filtering and view options for created versus shared collections. [Commit](https://github.com/open-webui/open-webui/commit/ceae3d48e603f53313d5483abe94099e20e914e8)
- 📖 Knowledge workspace now displays all collections with read access including shared read-only collections, enabling users to discover and explore knowledge bases they don't own while maintaining proper access controls through visual "Read Only" badges and automatically disabled editing controls for name, description, file uploads, content editing, and deletion operations. [Commit](https://github.com/open-webui/open-webui/commit/693636d971d0e8398fa0c9ec3897686750007af5)
- 📁 Bulk website and YouTube video attachment now supports adding multiple URLs at once (newline-separated) with automatic YouTube detection and transcript retrieval, processed sequentially to prevent resource strain, and both websites and videos can now be added directly to knowledge bases through the workspace UI. [Commit](https://github.com/open-webui/open-webui/commit/7746e9f4b831f09953ad2b659b96e0fd52911031), [#6202](https://github.com/open-webui/open-webui/issues/6202), [#19587](https://github.com/open-webui/open-webui/pull/19587), [#8231](https://github.com/open-webui/open-webui/pull/8231)
- 🪟 Sidebar width is now resizable on desktop devices with persistent storage in localStorage, enforcing minimum and maximum width constraints (220px to 480px) while all layout components now reference the dynamic sidebar width via CSS variables for consistent responsive behavior. [Commit](https://github.com/open-webui/open-webui/commit/b364cf43d3e8fd3557f65f17bc285bfaca5ed368)
- 📝 Notes feature now supports server-side search and filtering with view options for notes created by the user versus notes shared with them, customizable sorting by name or date in both list and grid view modes within a redesigned interface featuring consolidated note management controls in a unified header, group-based permission sharing with read, write, and read-only access control displaying note authorship and sharing status for better collaboration, and paginated infinite scroll for improved performance with large note collections. [Commit](https://github.com/open-webui/open-webui/commit/9b24cddef6c4862bd899eb8d6332cafff54e871d)
- 👁️ Notes now support read-only access permissions, allowing users to share notes for viewing without granting edit rights, with the editor automatically becoming non-editable and appropriate UI indicators when read-only access is detected. [Commit](https://github.com/open-webui/open-webui/commit/4363df175d50e0f9729381ac2ba9b37a3c3a966d)
- 📄 Notes can now be created directly from the chat input field, allowing users to save drafted messages or content as notes without navigation or retyping. [Commit](https://github.com/open-webui/open-webui/commit/00c2b6ca405d617e3d7520953a00a36c19c790ec)
- 🪟 Sidebar folders, channels, and pinned models sections now automatically expand when creating new items or pinning models, providing immediate visual feedback for user actions. [Commit](https://github.com/open-webui/open-webui/commit/f826d3ed75213a0a1b31b50d030bfb1d5e91d199), [#19929](https://github.com/open-webui/open-webui/pull/19929)
- 📋 Chat file associations are now properly tracked in the database through a new "chat_file" table, enabling accurate file management across chats and ensuring proper cleanup of files when chats are deleted, while improving database consistency in multi-node deployments. [Commit](https://github.com/open-webui/open-webui/commit/f1bf4f20c53e6493f0eb6fa2f12cb84c2d22da52)
- 🖼️ User-uploaded images are now automatically converted from base64 to actual file storage on the server, eliminating large inline base64 strings from being stored in chat history and reducing message payload sizes while enabling better image management and sharing across multiple chats. [Commit](https://github.com/open-webui/open-webui/commit/f1bf4f20c53e6493f0eb6fa2f12cb84c2d22da52)
- 📸 Shared chats with generated or edited images now correctly display images when accessed by other users by properly linking generated images to their chat and message through the chat_file table, ensuring images remain accessible in shared chat links. [Commit](https://github.com/open-webui/open-webui/commit/446cc0ac6063402a743e949f50612376ed5a8437), [#19393](https://github.com/open-webui/open-webui/issues/19393)
- 📊 File viewer modal was significantly enhanced with native-like viewers for Excel/CSV spreadsheets rendering as interactive scrollable tables with multi-sheet navigation support, Markdown documents displaying with full typography including headers, lists, links, and tables, and source code files showing syntax highlighting, all accessible through a tabbed interface defaulting to raw text view. [#20035](https://github.com/open-webui/open-webui/pull/20035), [#2867](https://github.com/open-webui/open-webui/issues/2867)
- 📏 Chat input now displays an expand button in the top-right corner when messages exceed two lines, providing optional access to a full-screen editor for composing longer messages with enhanced workspace and visibility while temporarily disabling the main input to prevent editing conflicts. [Commit](https://github.com/open-webui/open-webui/commit/205c7111200c22da42e9b5fe1e676aec9cca6daa)
- 💬 Channel message data lazy loading was implemented, deferring attachment and file metadata retrieval until needed to improve initial message list load performance. [Commit](https://github.com/open-webui/open-webui/commit/54b7ec56d6bcd2d79addc1694b757dab18cf18c5)
- 🖼️ Channel image upload handling was optimized to process and store compressed images directly as files rather than inline data, improving memory efficiency and message load times. [Commit](https://github.com/open-webui/open-webui/commit/22f1b764a7ea1add0a896906a9ef00b4b6743adc)
- 🎥 Video file playback support was added to channel messages, enabling inline video viewing with native player controls. [Commit](https://github.com/open-webui/open-webui/commit/7b126b23d50a0bd36a350fe09dc1dbe3df105318)
- 🔐 LDAP authentication now supports user entries with multiple username attributes, correctly handling cases where the username field contains a list of values. [Commit](https://github.com/open-webui/open-webui/commit/379f888c9dc6dce21c3ef7a1fc455258aff993dc), [#19878](https://github.com/open-webui/open-webui/issues/19878)
- 👨‍👩‍👧‍👦 The "ENABLE_PUBLIC_ACTIVE_USERS_COUNT" environment variable now allows restricting active user count visibility to administrators, reducing backend load and addressing privacy concerns in large deployments. [#20027](https://github.com/open-webui/open-webui/pull/20027), [#13026](https://github.com/open-webui/open-webui/issues/13026)
- 🚀 Models page search input performance was optimized with a 300ms debounce to reduce server load and improve responsiveness. [#19832](https://github.com/open-webui/open-webui/pull/19832)
- 💨 Frontend performance was optimized by preventing unnecessary API calls for API Keys and Channels features when they are disabled in admin settings, reducing backend noise and improving overall system efficiency. [#20043](https://github.com/open-webui/open-webui/pull/20043), [#19967](https://github.com/open-webui/open-webui/issues/19967)
- 📎 Channel file association tracking was implemented, automatically linking uploaded files to their respective channels with a dedicated association table enabling better organization and future file management features within channels. [Commit](https://github.com/open-webui/open-webui/commit/2bccf8350d0915f69b8020934bb179c52e81b7b5)
- 👥 User profile previews now display group membership information for easier identification of user roles and permissions. [Commit](https://github.com/open-webui/open-webui/commit/2b1a29d44bde9fbc20ff9f0a5ded1ce8ded9d90d)
- 🌍 The "SEARXNG_LANGUAGE" environment variable now allows configuring search language for SearXNG queries, replacing the hardcoded "en-US" default with a configurable setting that defaults to "all". [#19909](https://github.com/open-webui/open-webui/pull/19909)
- ⏳ The "MINERU_API_TIMEOUT" environment variable now allows configuring request timeouts for MinerU document processing operations. [#20016](https://github.com/open-webui/open-webui/pull/20016), [#18495](https://github.com/open-webui/open-webui/issues/18495)
- 🔧 The "RAG_EXTERNAL_RERANKER_TIMEOUT" environment variable now allows configuring request timeouts for external reranker operations. [#20049](https://github.com/open-webui/open-webui/pull/20049), [#19900](https://github.com/open-webui/open-webui/issues/19900)
- 🎨 OpenAI GPT-IMAGE 1.5 model support was added for image generation and editing with automatic image size capabilities. [Commit](https://github.com/open-webui/open-webui/commit/4c2e5c93e9287479f56f780708656136849ccaee)
- 🔑 The "OAUTH_AUDIENCE" environment variable now allows OAuth providers to specify audience parameters for JWT access token generation. [#19768](https://github.com/open-webui/open-webui/pull/19768)
- ⏰ The "REDIS_SOCKET_CONNECT_TIMEOUT" environment variable now allows configuring socket connection timeouts for Redis and Sentinel connections, addressing potential failover and responsiveness issues in distributed deployments. [#19799](https://github.com/open-webui/open-webui/pull/19799), [Docs:#882](https://github.com/open-webui/docs/pull/882)
- ⏱️ The "WEB_LOADER_TIMEOUT" environment variable now allows configuring request timeouts for SafeWebBaseLoader operations. [#19804](https://github.com/open-webui/open-webui/pull/19804), [#19734](https://github.com/open-webui/open-webui/issues/19734)
- 🚀 Models API endpoint performance was optimized through batched model loading, eliminating N+1 queries and significantly reducing response times when filtering models by user permissions. [Commit](https://github.com/open-webui/open-webui/commit/0dd2cfe1f273fbacdbe90300a97c021f2e678656)
- 🔀 Custom model fallback handling was added, allowing workspace-created custom models to automatically fall back to the default chat model when their configured base model is not found; set "ENABLE_CUSTOM_MODEL_FALLBACK" to true to enable, preventing workflow disruption when base models are removed or renamed, while ensuring other requests remain unaffected. [Commit](https://github.com/open-webui/open-webui/commit/b35aeb8f46e0e278c6f4538382c2b6838e24cc5a), [#19985](https://github.com/open-webui/open-webui/pull/19985)
- 📡 A new /feedbacks/all/ids API endpoint was added to return only feedback IDs without metadata, significantly improving performance for external integrations working with large feedback collections. [Commit](https://github.com/open-webui/open-webui/commit/53c1ca64b7205d85f6de06bd69e3e265d15546b8)
- 📈 An experimental chat usage statistics endpoint (GET /api/v1/chats/stats/usage) was added with pagination support (50 chats per page) and comprehensive per-chat analytics including model usage counts, user and assistant message breakdowns, average response times calculated from message timestamps, average content lengths, and last activity timestamps; this endpoint remains experimental and not suitable for production use as it performs intensive calculations by processing entire message histories for each chat without caching. [Commit](https://github.com/open-webui/open-webui/commit/a7993f6f4e4591cd2aaa4718ece9e5623557d019)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for German, Danish, Finnish, Korean, Portuguese (Brazil), Simplified Chinese, Traditional Chinese, Catalan, and Spanish were enhanced and expanded.

### Fixed

- ⚡ External reranker operations were optimized to prevent event loop blocking by offloading synchronous HTTP requests to a thread pool using asyncio.to_thread(), eliminating application freezes during RAG reranking queries. [#20049](https://github.com/open-webui/open-webui/pull/20049), [#19900](https://github.com/open-webui/open-webui/issues/19900)
- 💭 Text loss in the explanation feature when using the "CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE" environment variable was resolved by correcting newline handling in streaming responses. [#19829](https://github.com/open-webui/open-webui/pull/19829)
- 📚 Knowledge base batch file addition failures caused by Pydantic validation errors are now prevented by making the meta field optional in file metadata responses, allowing files without metadata to be processed correctly. [#20022](https://github.com/open-webui/open-webui/pull/20022), [#14220](https://github.com/open-webui/open-webui/issues/14220)
- 🗄️ PostgreSQL null byte insertion failures when attaching web pages or processing embedded content are now prevented by consolidating text sanitization logic across chat messages, web search results, and knowledge base documents, removing null bytes and invalid UTF-8 surrogates before database insertion. [#20072](https://github.com/open-webui/open-webui/pull/20072), [#19867](https://github.com/open-webui/open-webui/issues/19867), [#18201](https://github.com/open-webui/open-webui/issues/18201), [#15616](https://github.com/open-webui/open-webui/issues/15616)
- 🎫 MCP OAuth 2.1 token exchange failures are now fixed by removing duplicate credential passing that caused "ID1,ID1" concatenation and 401 errors from the token endpoint. [#20076](https://github.com/open-webui/open-webui/pull/20076), [#19823](https://github.com/open-webui/open-webui/issues/19823)
- 📝 Notes "Improve" action now works correctly after the streaming API change in v0.6.41 by ensuring uploaded files are fully retrieved with complete metadata before processing, restoring note improvement and summarization functionality. [Commit](https://github.com/open-webui/open-webui/commit/a3458f492c53a3b00405f59fbe1ea953fe364f18), [#20078](https://github.com/open-webui/open-webui/discussions/20078)
- 🔑 MCP OAuth 2.1 tool servers now work correctly in multi-node deployments through lazy-loading of OAuth clients from Redis-synced configuration, eliminating 404 errors when load balancers route requests to nodes that didn't process the original config update. [#20076](https://github.com/open-webui/open-webui/pull/20076), [#19902](https://github.com/open-webui/open-webui/pull/19902), [#19901](https://github.com/open-webui/open-webui/issues/19901)
- 🧩 Chat loading failures when channels permissions were disabled are now prevented through graceful error handling. [Commit](https://github.com/open-webui/open-webui/commit/5c2df97f04cce5cb7087d288f816f91a739688c1)
- 🔍 Search bar freezing and crashing issues in Models, Chat, and Archived Chat pages caused by excessively long queries exceeding server URL limits were resolved by truncating queries to 500 characters, and knowledge base layout shifting with long names was fixed by adjusting flex container properties. [#19832](https://github.com/open-webui/open-webui/pull/19832)
- 🎛️ Rate limiting errors (HTTP 429) with Brave Search free tier when generating multiple queries are now prevented through asyncio.Semaphore-based concurrency control applied globally to all search engines. [#20070](https://github.com/open-webui/open-webui/pull/20070), [#20003](https://github.com/open-webui/open-webui/issues/20003), [#14107](https://github.com/open-webui/open-webui/issues/14107), [#15134](https://github.com/open-webui/open-webui/issues/15134)
- 💥 UI crashes and white screen errors caused by null chat lists during loading or network failures were prevented by adding null safety checks to chat iteration in folder placeholders and archived chat modals. [#19898](https://github.com/open-webui/open-webui/pull/19898)
- 🧩 Chat overview tab crashes caused by undefined model references were resolved by adding proper null checks when accessing deleted or ejected models. [#19935](https://github.com/open-webui/open-webui/pull/19935)
- 🔄 MultiResponseMessages component crashes when navigating chat history after removing or changing selected models are now prevented through proper component re-initialization. [Commit](https://github.com/open-webui/open-webui/commit/870e29e3738da968c396b70532f365a3c2f71995), [#18599](https://github.com/open-webui/open-webui/issues/18599)
- 🚫 Channel API endpoint access is now correctly blocked when channels are globally disabled, preventing users with channel permissions from accessing channel data via API requests when the feature is turned off in admin settings. [#19957](https://github.com/open-webui/open-webui/pull/19957), [#19914](https://github.com/open-webui/open-webui/issues/19914)
- 👤 User list popup display in the admin panel was fixed to correctly track user identity when sorting or filtering changes the list order, preventing popups from showing incorrect user information. [Commit](https://github.com/open-webui/open-webui/commit/ae47101dc6aef2c7d8ae0d843985341fff820057), [#20046](https://github.com/open-webui/open-webui/issues/20046)
- 👥 User selection in the "Edit User Group" modal now preserves pagination position, allowing administrators to select multiple users across pages without resetting to page 1. [#19959](https://github.com/open-webui/open-webui/pull/19959)
- 📸 Model avatar images now update immediately in the admin models list through proper Cache-Control headers, eliminating the need for manual cache clearing. [#19959](https://github.com/open-webui/open-webui/pull/19959)
- 🔒 Temporary chat permission enforcement now correctly prevents users from enabling the feature through personal settings when disabled in default or group permissions. [#19785](https://github.com/open-webui/open-webui/issues/19785)
- 🎨 Image editing with reference images now correctly uses both previously generated images and newly uploaded reference images. [Commit](https://github.com/open-webui/open-webui/commit/bcd50ed8f1b7387fd700538ae0d74fc72f3c53d0)
- 🧠 Image generation and editing operations are now explicitly injected into system context, improving LLM comprehension even for weaker models so they reliably acknowledge operations instead of incorrectly claiming they cannot generate images. [Commit](https://github.com/open-webui/open-webui/commit/28b2fcab0cd036dbe646a66fe81890f288c77121)
- 📑 Source citation rendering errors when citation syntax appeared in user messages or contexts without source data were resolved. [Commit](https://github.com/open-webui/open-webui/commit/3c8f1cf8e58d52e86375634b0381374298b1b4f3)
- 📄 DOCX file parsing now works correctly in temporary chats through client-side text extraction, preventing raw data from being displayed. [Commit](https://github.com/open-webui/open-webui/commit/6993b0b40b10af8cdbe6626702cc94080fff9e22)
- 🔧 Pipeline settings save failures when valve properties contain null values are now handled correctly. [#19791](https://github.com/open-webui/open-webui/pull/19791)
- ⚙️ Model usage settings are now correctly preserved when switching between models instead of being unexpectedly cleared or reset. [#19868](https://github.com/open-webui/open-webui/pull/19868), [#19549](https://github.com/open-webui/open-webui/issues/19549)
- 🛡️ Invalid PASSWORD_VALIDATION_REGEX_PATTERN configurations no longer cause startup warnings, with automatic fallback to the default pattern when regex compilation fails. [#20058](https://github.com/open-webui/open-webui/pull/20058)
- 🎯 The DefaultFiltersSelector component in model settings now correctly displays when only global toggleable filters are present, enabling per-model default configuration. [#20066](https://github.com/open-webui/open-webui/pull/20066)
- 🎤 Audio file upload failures caused by MIME type matching issues with spacing variations and codec parameters were resolved by implementing proper MIME type parsing. [#17771](https://github.com/open-webui/open-webui/pull/17771), [#17761](https://github.com/open-webui/open-webui/issues/17761)
- ⌨️ Regenerate response keyboard shortcut now only activates when chat input is selected, preventing unintended regeneration when modals are open or other UI elements are focused. [#19875](https://github.com/open-webui/open-webui/pull/19875)
- 📋 Log truncation issues in Docker deployments during application crashes were resolved by disabling Python stdio buffering, ensuring complete diagnostic output is captured. [#19844](https://github.com/open-webui/open-webui/issues/19844)
- 🔴 Redis cluster compatibility issues with disabled KEYS command were resolved by replacing blocking KEYS operations with production-safe SCAN iterations. [#19871](https://github.com/open-webui/open-webui/pull/19871), [#15834](https://github.com/open-webui/open-webui/issues/15834)
- 🔤 File attachment container layout issues when using RTL languages were resolved by applying chat direction settings to file containers across all message types. [#19891](https://github.com/open-webui/open-webui/pull/19891), [#19742](https://github.com/open-webui/open-webui/issues/19742)
- 🔃 Ollama model list now automatically refreshes after model deletion, preventing deleted models from persisting in the UI and being inadvertently re-downloaded during subsequent pull operations. [#19912](https://github.com/open-webui/open-webui/pull/19912)
- 🌐 Ollama Cloud web search now correctly applies domain filtering to search results. [Commit](https://github.com/open-webui/open-webui/commit/d4bd938a77c22409a1643c058b937a06e07baca9)
- 📜 Tool specification serialization now preserves non-ASCII characters including Chinese text, improving LLM comprehension and tool selection accuracy by avoiding Unicode escape sequences. [#19942](https://github.com/open-webui/open-webui/pull/19942)
- 🛟 Model editor stability was improved with null safety checks for tools, functions, and file input operations, preventing crashes when stores are undefined or file objects are invalid. [#19939](https://github.com/open-webui/open-webui/pull/19939)
- 🗣️ MoA completion handling stability was improved with null safety checks for response objects, boolean casting for settings, and proper timeout type definitions. [#19921](https://github.com/open-webui/open-webui/pull/19921)
- 🎛️ Chat functionality failures caused by empty logit_bias parameter values are now prevented by properly handling empty strings in the parameter parsing middleware. [#19982](https://github.com/open-webui/open-webui/issues/19982)
- 🔏 Administrators can now delete read-only knowledge bases from deleted users, resolving permission issues that previously prevented cleanup of orphaned read-only content. [Commit](https://github.com/open-webui/open-webui/commit/59d6eb2badf46f9c2b1e879484ac33432915b575)
- 💾 Cloned prompts and tools now correctly preserve their access control settings instead of being reset to null, preventing unintended visibility changes when duplicating private or restricted items. [#19960](https://github.com/open-webui/open-webui/pull/19960), [#19360](https://github.com/open-webui/open-webui/issues/19360)
- 🎚️ Text scale adjustment buttons in Interface Settings were fixed to correctly increment and decrement the scale value. [#19699](https://github.com/open-webui/open-webui/pull/19699)
- 🎭 Group channel invite button text visibility in light theme was corrected to display properly against dark backgrounds. [#19828](https://github.com/open-webui/open-webui/issues/19828)
- 📁 The move button is now hidden when no folders exist, preventing display of non-functional controls. [#19705](https://github.com/open-webui/open-webui/pull/19705)
- 📦 Qdrant client dependency was updated to resolve startup version incompatibility warnings. [#19757](https://github.com/open-webui/open-webui/pull/19757)
- 🧮 The "ENABLE_ASYNC_EMBEDDING" environment variable is now correctly applied to embedding operations when configured exclusively via environment variables. [#19748](https://github.com/open-webui/open-webui/pull/19748)
- 🌄 The "COMFYUI_WORKFLOW_NODES" and "IMAGES_EDIT_COMFYUI_WORKFLOW_NODES" environment variables are now correctly loaded and parsed as JSON lists, and the configuration key name was corrected from "COMFYUI_WORKFLOW" to "COMFYUI_WORKFLOW_NODES". [#19918](https://github.com/open-webui/open-webui/pull/19918), [#19886](https://github.com/open-webui/open-webui/issues/19886)
- 💫 Channel name length is now limited to 128 characters with validation to prevent display issues caused by excessively long names. [Commit](https://github.com/open-webui/open-webui/commit/f509f5542dde384d34402f6df763f49a06bea109)
- 🔐 Invalid PASSWORD_VALIDATION_REGEX_PATTERN configurations no longer cause startup warnings, with automatic fallback to the default pattern when regex compilation fails. [#20058](https://github.com/open-webui/open-webui/pull/20058)
- 🔎 Bocha search with filter list functionality now works correctly by returning results as a list instead of a dictionary wrapper, ensuring compatibility with result filtering operations. [Commit](https://github.com/open-webui/open-webui/commit/b5bd8704fe1672da839bb3be6210d7cb494797ce), [#19733](https://github.com/open-webui/open-webui/issues/19733)

### Changed

- ⚠️ This release includes database schema changes; multi-worker, multi-server, or load-balanced deployments must update all instances simultaneously rather than performing rolling updates, as running mixed versions will cause application failures due to schema incompatibility between old and new instances.
- 📡 WEB_SEARCH_CONCURRENT_REQUESTS default changed from 10 to 0 (unlimited) — This setting now applies to all search engines instead of only DuckDuckGo; previously users were implicitly limited to 10 concurrent queries, but now have unlimited parallel requests by default; set to 1 for sequential execution if using rate-limited APIs like Brave free tier. [#20070](https://github.com/open-webui/open-webui/pull/20070)
- 💾 SQLCipher absolute path handling was fixed to properly support absolute database paths (e.g., "/app/data.db") instead of incorrectly stripping leading slashes and converting them to relative paths; this restores functionality for Docker volume mounts and explicit absolute path configurations while maintaining backward compatibility with relative paths. [#20074](https://github.com/open-webui/open-webui/pull/20074)
- 🔌 Knowledge base file listing API was redesigned with paginated responses and new filtering parameters; the GET /knowledge/{id}/files endpoint now returns paginated results with user attribution instead of embedding all files in the knowledge object, which may require updates to custom integrations or scripts accessing knowledge base data programmatically. [Commit](https://github.com/open-webui/open-webui/commit/94a8439105f30203ea9d729787c9c5978f5c22a2)
- 🗑️ Legacy knowledge base support for deprecated document collections and tag-based collections was removed; users with pre-knowledge base documents must migrate to the current knowledge base system as legacy items will no longer appear in selectors or command menus. [Commit](https://github.com/open-webui/open-webui/commit/a934dc997ed67a036dd7975e380f8036c447d3ed)
- 🔨 Source-level log environment variables (AUDIO_LOG_LEVEL, CONFIG_LOG_LEVEL, MODELS_LOG_LEVEL, etc.) were removed as they provided limited configuration options and added significant complexity across 100+ files; the GLOBAL_LOG_LEVEL environment variable, which already took precedence over source-level settings, now serves as the exclusive logging configuration method. [#20045](https://github.com/open-webui/open-webui/pull/20045)
- 🐍 LangChain was upgraded to version 1.2.0, representing a major dependency update and significant progress toward Python 3.13 compatibility while improving RAG pipeline functionality for document loading and retrieval operations. [#19991](https://github.com/open-webui/open-webui/pull/19991)

## [0.6.41] - 2025-12-02

### Added

- 🚦 Sign-in rate limiting was implemented to protect against brute force attacks, limiting login attempts to 15 per 3-minute window per email address using Redis with automatic fallback to in-memory storage when Redis is unavailable. [Commit](https://github.com/open-webui/open-webui/commit/7b166370432414ce8f186747fb098e0c70fb2d6b)
- 📂 Administrators can now globally disable the folders feature and control user-level folder permissions through the admin panel, enabling minimalist interface configurations for deployments that don't require workspace organization features. [#19529](https://github.com/open-webui/open-webui/pull/19529), [#19210](https://github.com/open-webui/open-webui/discussions/19210), [#18459](https://github.com/open-webui/open-webui/discussions/18459), [#18299](https://github.com/open-webui/open-webui/discussions/18299)
- 👥 Group channels were introduced as a new channel type enabling membership-based collaboration spaces where users explicitly join as members rather than accessing through permissions, with support for public or private visibility, automatic member inclusion from specified user groups, member role tracking with invitation metadata, and post-creation member management allowing channel managers to add or remove members through the channel info modal. [Commit](https://github.com/open-webui/open-webui/commit/f589b7c1895a6a77166c047891acfa21bc0936c4), [Commit](https://github.com/open-webui/open-webui/commit/3f1d9ccbf8443a2fa5278f36202bad930a216680)
- 💬 Direct Message channels were introduced with a dedicated channel type selector and multi-user member selection interface, enabling private conversations between specific users without requiring full channel visibility. [Commit](https://github.com/open-webui/open-webui/commit/64b4d5d9c280b926746584aaf92b447d09deb386)
- 📨 Direct Message channels now support a complete user-to-user messaging system with member-based access control, automatic deduplication for one-on-one conversations, optional channel naming, and distinct visual presentation using participant avatars instead of channel icons. [Commit](https://github.com/open-webui/open-webui/commit/acccb9afdd557274d6296c70258bb897bbb6652f)
- 🙈 Users can now hide Direct Message channels from their sidebar while preserving message history, with automatic reactivation when new messages arrive from other participants, providing a cleaner interface for managing active conversations. [Commit](https://github.com/open-webui/open-webui/commit/acccb9afdd557274d6296c70258bb897bbb6652f)
- ☑️ A comprehensive user selection component was added to the channel creation modal, featuring search functionality, sortable user lists, pagination support, and multi-select checkboxes for building Direct Message participant lists. [Commit](https://github.com/open-webui/open-webui/commit/acccb9afdd557274d6296c70258bb897bbb6652f)
- 🔴 Channel unread message count tracking was implemented with visual badge indicators in the sidebar, automatically updating counts in real-time and marking messages as read when users view channels, with join/leave functionality to manage membership status. [Commit](https://github.com/open-webui/open-webui/commit/64b4d5d9c280b926746584aaf92b447d09deb386)
- 📌 Message pinning functionality was added to channels, allowing users to pin important messages for easy reference with visual highlighting, a dedicated pinned messages modal accessible from the navbar, and complete backend support for tracking pinned status, pin timestamp, and the user who pinned each message. [Commit](https://github.com/open-webui/open-webui/commit/64b4d5d9c280b926746584aaf92b447d09deb386), [Commit](https://github.com/open-webui/open-webui/commit/aae2fce17355419d9c29f8100409108037895201)
- 🟢 Direct Message channels now display an active status indicator for one-on-one conversations, showing a green dot when the other participant is currently online or a gray dot when offline. [Commit](https://github.com/open-webui/open-webui/commit/4b6773885cd7527c5a56b963781dac5e95105eec), [Commit](https://github.com/open-webui/open-webui/commit/39645102d14f34e71b34e5ddce0625790be33f6f)
- 🆔 Users can now start Direct Message conversations directly from user profile previews by clicking the "Message" button, enabling quick access to private messaging without navigating away from the current channel. [Commit](https://github.com/open-webui/open-webui/commit/a0826ec9fedb56320532616d568fa59dda831d4e)
- ⚡ Channel messages now appear instantly when sent using optimistic UI rendering, displaying with a pending state while the server confirms delivery, providing a more responsive messaging experience. [Commit](https://github.com/open-webui/open-webui/commit/25994dd3da90600401f53596d4e4fb067c1b8eaa)
- 👍 Channel message reactions now display the names of users who reacted when hovering over the emoji, showing up to three names with a count for additional reactors. [Commit](https://github.com/open-webui/open-webui/commit/05e79bdd0c7af70b631e958924e3656db1013b80)
- 🛠️ Channel creators can now edit and delete their own group and DM channels without requiring administrator privileges, enabling users to manage the channels they create independently. [Commit](https://github.com/open-webui/open-webui/commit/f589b7c1895a6a77166c047891acfa21bc0936c4)
- 🔌 A new API endpoint was added to directly get or create a Direct Message channel with a specific user by their ID, streamlining programmatic DM channel creation for integrations and frontend workflows. [Commit](https://github.com/open-webui/open-webui/commit/f589b7c1895a6a77166c047891acfa21bc0936c4)
- 💭 Users can now set a custom status with an emoji and message that displays in profile previews, the sidebar user menu, and Direct Message channel items in the sidebar, with the ability to clear status at any time, providing visibility into availability or current focus similar to team communication platforms. [Commit](https://github.com/open-webui/open-webui/commit/51621ba91a982e52da168ce823abffd11ad3e4fa), [Commit](https://github.com/open-webui/open-webui/commit/f5e8d4d5a004115489c35725408b057e24dfe318)
- 📤 A group export API endpoint was added, enabling administrators to export complete group data including member lists for backup and migration purposes. [Commit](https://github.com/open-webui/open-webui/commit/09b6ea38c579659f8ca43ae5ea3746df3ac561ad)
- 📡 A new API endpoint was added to retrieve all users belonging to a specific group, enabling programmatic access to group membership information for administrative workflows. [Commit](https://github.com/open-webui/open-webui/commit/01868e856a10f474f74fbd1b4425dafdf949222f)
- 👁️ The admin user list now displays an active status indicator next to each user, showing a visual green dot for users who have been active within the last three minutes. [Commit](https://github.com/open-webui/open-webui/commit/1b095d12ff2465b83afa94af89ded9593f8a8655)
- 🔑 The admin user edit modal now displays OAuth identity information with a per-provider breakdown, showing each linked identity provider and its associated subject identifier separately. [#19573](https://github.com/open-webui/open-webui/pull/19573)
- 🧩 OAuth role claim parsing now respects the "OAUTH_ROLES_SEPARATOR" configuration, enabling proper parsing of roles returned as comma-separated strings and providing consistent behavior with group claim handling. [#19514](https://github.com/open-webui/open-webui/pull/19514)
- 🎛️ Channel feature access can now be controlled through both the "USER_PERMISSIONS_FEATURES_CHANNELS" environment variable and group permission toggles in the admin panel, allowing administrators to restrict channel functionality for specific users or groups while defaulting to enabled for all users. [Commit](https://github.com/open-webui/open-webui/commit/f589b7c1895a6a77166c047891acfa21bc0936c4)
- 🎨 The model editor interface was refined with access control settings moved to a dedicated modal, group member counts now displayed when configuring permissions, reorganized layout with improved visual hierarchy, and redesigned prompt suggestions cards with tooltips for field guidance. [Commit](https://github.com/open-webui/open-webui/commit/e65d92fc6f49da5ca059e1c65a729e7973354b99), [Commit](https://github.com/open-webui/open-webui/commit/9d39b9b42c653ee2acf2674b2df343ecbceb4954)
- 🏗️ Knowledge base file management was rebuilt with a dedicated database table replacing the previous JSON array storage, enabling pagination support for large knowledge bases, significantly faster file listing performance, and more reliable file-knowledge base relationship tracking. [Commit](https://github.com/open-webui/open-webui/commit/d19023288e2ca40f86e2dc3fd9f230540f3e70d7)
- ☁️ Azure Document Intelligence model selection was added, allowing administrators to specify which model to use for document processing via the "DOCUMENT_INTELLIGENCE_MODEL" environment variable or admin UI setting, with "prebuilt-layout" as the default. [#19692](https://github.com/open-webui/open-webui/pull/19692), [Docs:#872](https://github.com/open-webui/docs/pull/872)
- 🚀 Milvus multitenancy vector database performance was improved by removing manual flush calls after upsert operations, eliminating rate limit errors and reducing load on etcd and MinIO/S3 storage by allowing Milvus to manage segment persistence automatically via its WAL and auto-flush policies. [#19680](https://github.com/open-webui/open-webui/pull/19680)
- ✨ Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌍 Translations for German, French, Portuguese (Brazil), Catalan, Simplified Chinese, and Traditional Chinese were enhanced and expanded.

### Fixed

- 🔄 Tool call response token duplication was fixed by removing redundant message history additions in non-native function calling mode, resolving an issue where tool results were included twice in the context and causing 2x token consumption. [#19656](https://github.com/open-webui/open-webui/issues/19656), [Commit](https://github.com/open-webui/open-webui/commit/52ccab8)
- 🛡️ Web search domain filtering was corrected to properly block results when any resolved hostname or IP address matches a blocked domain, preventing blocked sites from appearing in search results due to permissive hostname resolution logic that previously allowed results through if any single resolved address passed the filter. [#19670](https://github.com/open-webui/open-webui/pull/19670), [#19669](https://github.com/open-webui/open-webui/issues/19669)
- 🧠 Custom models based on Ollama or OpenAI now properly inherit the connection type from their base model, ensuring they appear correctly in the "Local" or "External" model selection tabs instead of only appearing under "All". [#19183](https://github.com/open-webui/open-webui/issues/19183), [Commit](https://github.com/open-webui/open-webui/commit/39f7575)
- 🐍 SentenceTransformers embedding initialization was fixed by updating the transformers dependency to version 4.57.3, resolving a regression in v0.6.40 where document ingestion failed with "'NoneType' object has no attribute 'encode'" errors due to a bug in transformers 4.57.2. [#19512](https://github.com/open-webui/open-webui/issues/19512), [#19513](https://github.com/open-webui/open-webui/pull/19513)
- 📈 Active user count accuracy was significantly improved by replacing the socket-based USER_POOL tracking with a database-backed heartbeat mechanism, resolving long-standing issues where Redis deployments displayed inflated user counts due to stale sessions never being cleaned up on disconnect. [#16074](https://github.com/open-webui/open-webui/discussions/16074), [Commit](https://github.com/open-webui/open-webui/commit/70948f8803e417459d5203839f8077fdbfbbb213)
- 👥 Default group assignment now applies consistently across all user registration methods including OAuth/SSO, LDAP, and admin-created users, fixing an issue where the "DEFAULT_GROUP_ID" setting was only being applied to users who signed up via the email/password signup form. [#19685](https://github.com/open-webui/open-webui/pull/19685)
- 🔦 Model list filtering in workspaces was corrected to properly include models shared with user groups, ensuring members can view models they have write access to through group permissions. [#19461](https://github.com/open-webui/open-webui/issues/19461), [Commit](https://github.com/open-webui/open-webui/commit/69722ba973768a5f689f2e2351bf583a8db9bba8)
- 🖼️ User profile image display in preview contexts was fixed by resolving a Pydantic validation error that prevented proper rendering. [Commit](https://github.com/open-webui/open-webui/commit/c7eb7136893b0ddfdc5d55ffc7a05bd84a00f5d6)
- 🔒 Redis TLS connection failures were resolved by updating the python-socketio dependency to version 5.15.0, restoring support for the "rediss://" URL schema. [#19480](https://github.com/open-webui/open-webui/issues/19480), [#19488](https://github.com/open-webui/open-webui/pull/19488)
- 📝 MCP tool server configuration was corrected to properly handle the "Function Name Filter List" as both string and list types, preventing AttributeError when the field is empty and ensuring backward compatibility. [#19486](https://github.com/open-webui/open-webui/issues/19486), [Commit](https://github.com/open-webui/open-webui/commit/c5b73d71843edc024325d4a6e625ec939a747279), [Commit](https://github.com/open-webui/open-webui/commit/477097c2e42985c14892301d0127314629d07df1)
- 📎 Web page attachment failures causing TypeError on metadata checks were resolved by correcting async threadpool parameter passing in vector database operations. [#19493](https://github.com/open-webui/open-webui/issues/19493), [Commit](https://github.com/open-webui/open-webui/commit/4370dee79e19d77062c03fba81780cb3b779fca3)
- 💾 Model allowlist persistence in multi-worker deployments was fixed by implementing Redis-based shared state for the internal models dictionary, ensuring configuration changes are consistently visible across all worker processes. [#19395](https://github.com/open-webui/open-webui/issues/19395), [Commit](https://github.com/open-webui/open-webui/commit/b5e5617d7f7ad3e4eec9f15f4cc7f07cb5afc2fa)
- ⏳ Chat history infinite loading was prevented by enhancing message data structure to properly track parent message relationships, resolving issues where missing parentId fields caused perpetual loading states. [#19225](https://github.com/open-webui/open-webui/issues/19225), [Commit](https://github.com/open-webui/open-webui/commit/ff4b1b9862d15adfa15eac17d2ce066c3d8ae38f)
- 🩹 Database migration robustness was improved by automatically detecting and correcting missing primary key constraints on the user table, ensuring successful schema upgrades for databases with non-standard configurations. [#19487](https://github.com/open-webui/open-webui/discussions/19487), [Commit](https://github.com/open-webui/open-webui/commit/453ea9b9a167c0b03d86c46e6efd086bf10056ce)
- 🏷️ OAuth group assignment now updates correctly on first login when users transition from admin to user role, ensuring group memberships reflect immediately when group management is enabled. [#19475](https://github.com/open-webui/open-webui/issues/19475), [#19476](https://github.com/open-webui/open-webui/pull/19476)
- 💡 Knowledge base file tooltips now properly display the parent collection name when referencing files with the hash symbol, preventing confusion between identically-named files in different collections. [#19491](https://github.com/open-webui/open-webui/issues/19491), [Commit](https://github.com/open-webui/open-webui/commit/3fe5a47b0ff84ac97f8e4ff56a19fa2ec065bf66)
- 🔐 Knowledge base file access inconsistencies were resolved where authorized non-admin users received "Not found" or permission errors for certain files due to race conditions during upload causing mismatched collection_name values, with file access validation now properly checking against knowledge base file associations. [#18689](https://github.com/open-webui/open-webui/issues/18689), [#19523](https://github.com/open-webui/open-webui/pull/19523), [Commit](https://github.com/open-webui/open-webui/commit/e301d1962e45900ababd3eabb7e9a2ad275a5761)
- 📦 Knowledge API batch file addition endpoint was corrected to properly handle async operations, resolving 500 Internal Server Error responses when adding multiple files simultaneously. [#19538](https://github.com/open-webui/open-webui/issues/19538), [Commit](https://github.com/open-webui/open-webui/commit/28659f60d94feb4f6a99bb1a5b54d7f45e5ea10f)
- 🤖 Embedding model auto-update functionality was fixed to properly respect the "RAG_EMBEDDING_MODEL_AUTO_UPDATE" setting by correctly passing the flag to the model path resolver, ensuring models update as expected when the auto-update option is enabled. [#19687](https://github.com/open-webui/open-webui/pull/19687)
- 📉 API response payload sizes were dramatically reduced by removing base64-encoded profile images from most endpoints, eliminating multi-megabyte responses caused by high-resolution avatars and enabling better browser caching. [#19519](https://github.com/open-webui/open-webui/issues/19519), [Commit](https://github.com/open-webui/open-webui/commit/384753c4c17f62a68d38af4bbcf55a21ee08e0f2)
- 📞 Redundant API calls on the admin user overview page were eliminated by consolidating reactive statements, reducing four duplicate requests to a single efficient call and significantly improving page load performance. [#19509](https://github.com/open-webui/open-webui/issues/19509), [Commit](https://github.com/open-webui/open-webui/commit/9f89cc5e9f7e1c6c9e2bc91177e08df7c79f66f9)
- 🧹 Duplicate API calls on the workspace models page were eliminated by removing redundant model list fetching, reducing two identical requests to a single call and improving page responsiveness. [#19517](https://github.com/open-webui/open-webui/issues/19517), [Commit](https://github.com/open-webui/open-webui/commit/d1bbf6be7a4d1d53fa8ad46ca4f62fc4b2e6a8cb)
- 🔘 The model valves button was corrected to prevent unintended form submission by adding explicit button type attribute, ensuring it no longer triggers message sending when the input area contains text. [#19534](https://github.com/open-webui/open-webui/pull/19534)
- 🗑️ Ollama model deletion was fixed by correcting the request payload format and ensuring the model selector properly displays the placeholder option. [Commit](https://github.com/open-webui/open-webui/commit/0f3156651c64bc5af188a65fc2908bdcecf30c74)
- 🎨 Image generation in temporary chats was fixed by correctly handling local chat sessions that are not persisted to the database. [Commit](https://github.com/open-webui/open-webui/commit/a7c7993bbf3a21cb7ba416525b89233cf2ad877f)
- 🕵️‍♂️ Audit logging was fixed by correctly awaiting the async user authentication call, resolving failures where coroutine objects were passed instead of user data. [#19658](https://github.com/open-webui/open-webui/pull/19658), [Commit](https://github.com/open-webui/open-webui/commit/dba86bc)
- 🌙 Dark mode select dropdown styling was corrected to use proper background colors, fixing an issue where dropdown borders and hover states appeared white instead of matching the dark theme. [#19693](https://github.com/open-webui/open-webui/pull/19693), [#19442](https://github.com/open-webui/open-webui/issues/19442)
- 🔍 Milvus vector database query filtering was fixed by correcting string quote handling in filter expressions and using the proper parameter name for queries, resolving false "duplicate content detected" errors that prevented uploading multiple files to knowledge bases. [#19602](https://github.com/open-webui/open-webui/pull/19602), [#18119](https://github.com/open-webui/open-webui/issues/18119), [#16345](https://github.com/open-webui/open-webui/issues/16345), [#17088](https://github.com/open-webui/open-webui/issues/17088), [#18485](https://github.com/open-webui/open-webui/issues/18485)
- 🆙 Milvus multitenancy vector database was updated to use query_iterator() for improved robustness and consistency with the standard Milvus implementation, fixing the same false duplicate detection errors and improving handling of large result sets in multi-tenant deployments. [#19695](https://github.com/open-webui/open-webui/pull/19695)

### Changed

- ⚠️ **IMPORTANT for Multi-Instance Deployments** — This release includes database schema changes; multi-worker, multi-server, or load-balanced deployments must update all instances simultaneously rather than performing rolling updates, as running mixed versions will cause application failures due to schema incompatibility between old and new instances.
- 👮 Channel creation is now restricted to administrators only, with the channel add button hidden for regular users to maintain organizational control over communication channels. [Commit](https://github.com/open-webui/open-webui/commit/421aba7cd7cd708168b1f2565026c74525a67905)
- ➖ The active user count indicator was removed from the bottom-left user menu in the sidebar to streamline the interface. [Commit](https://github.com/open-webui/open-webui/commit/848f3fd4d86ca66656e0ff0335773945af8d7d8d)
- 🗂️ The user table was restructured with API keys migrated to a dedicated table supporting future multi-key functionality, OAuth data storage converted to a JSON structure enabling multiple identity providers per user account, and internal column types optimized from TEXT to JSON for the "info" and "settings" fields, with automatic migration preserving all existing data and associations. [#19573](https://github.com/open-webui/open-webui/pull/19573)
- 🔄 The knowledge base API was restructured to support the new file relationship model.

## [0.6.40] - 2025-11-25

### Fixed

- 🗄️ A critical PostgreSQL user listing performance issue was resolved by removing a redundant count operation that caused severe database slowdowns and potential timeouts when viewing user lists in admin panels.

## [0.6.39] - 2025-11-25

### Added

- 💬 A user list modal was added to channels, displaying all users with access and featuring search, sorting, and pagination capabilities. [Commit](https://github.com/open-webui/open-webui/commit/c0e120353824be00a2ef63cbde8be5d625bd6fd0)
- 💬 Channel navigation now displays the total number of users with access to the channel. [Commit](https://github.com/open-webui/open-webui/commit/3b5710d0cd445cf86423187f5ee7c40472a0df0b)
- 🔌 Tool servers and MCP connections now support function name filtering, allowing administrators to selectively enable or block specific functions using allow/block lists. [Commit](https://github.com/open-webui/open-webui/commit/743199f2d097ae1458381bce450d9025a0ab3f3d)
- ⚡ A toggle to disable parallel embedding processing was added via "ENABLE_ASYNC_EMBEDDING", allowing sequential processing for rate-limited or resource-constrained local embedding setups. [#19444](https://github.com/open-webui/open-webui/pull/19444)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Localization improvements were made for German (de-DE) and Portuguese (Brazil) translations.

### Fixed

- 📝 Inline citations now render correctly within markdown lists and nested elements instead of displaying as "undefined" values. [#19452](https://github.com/open-webui/open-webui/issues/19452)
- 👥 Group member selection now works correctly without randomly selecting other users or causing the user list to jump around. [#19426](https://github.com/open-webui/open-webui/issues/19426)
- 👥 Admin panel user list now displays the correct total user count and properly paginates 30 items per page after fixing database query issues with group member joins. [#19429](https://github.com/open-webui/open-webui/issues/19429)
- 🔍 Knowledge base reindexing now works correctly after resolving async execution chain issues by implementing threadpool workers for embedding operations. [#19434](https://github.com/open-webui/open-webui/pull/19434)
- 🖼️ OpenAI image generation now works correctly after fixing a connection adapter error caused by incorrect URL formatting. [#19435](https://github.com/open-webui/open-webui/pull/19435)

### Changed

- 🔧 BREAKING: Docling configuration has been consolidated from individual environment variables into a single "DOCLING_PARAMS" JSON configuration and now supports API key authentication via "DOCLING_API_KEY", requiring users to migrate existing Docling settings to the new format. [#16841](https://github.com/open-webui/open-webui/issues/16841), [#19427](https://github.com/open-webui/open-webui/pull/19427)
- 🔧 The environment variable "REPLACE_IMAGE_URLS_IN_CHAT_RESPONSE" has been renamed to "ENABLE_CHAT_RESPONSE_BASE64_IMAGE_URL_CONVERSION" for naming consistency.

## [0.6.38] - 2025-11-24

### Fixed

- 🔍 Hybrid search now works reliably after recent changes.
- 🛠️ Tool server saving now handles errors gracefully, preventing failed saves from impacting the UI.
- 🔐 SSO/OIDC code fixed to improve login reliability and better handle edge cases.

## [0.6.37] - 2025-11-24

### Added

- 🔐 Granular sharing permissions are now available with two-tiered control separating group sharing from public sharing, allowing administrators to independently configure whether users can share workspace items with groups or make them publicly accessible, with separate permission toggles for models, knowledge bases, prompts, tools, and notes, configurable via "USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_SHARING", "USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING", and corresponding environment variables for other workspace item types, while groups can now be configured to opt-out of sharing via the "Allow Group Sharing" setting. [Commit](https://github.com/open-webui/open-webui/commit/7be750bcbb40da91912a0a66b7ab791effdcc3b6), [Commit](https://github.com/open-webui/open-webui/commit/f69e37a8507d6d57382d6670641b367f3127f90a)
- 🔐 Password policy enforcement is now available with configurable validation rules, allowing administrators to require specific password complexity requirements via "ENABLE_PASSWORD_VALIDATION" and "PASSWORD_VALIDATION_REGEX_PATTERN" environment variables, with default pattern requiring minimum 8 characters including uppercase, lowercase, digit, and special character. [#17794](https://github.com/open-webui/open-webui/pull/17794)
- 🔐 Granular import and export permissions are now available for workspace items, introducing six separate permission toggles for models, prompts, and tools that are disabled by default for enhanced security. [#19242](https://github.com/open-webui/open-webui/pull/19242)
- 👥 Default group assignment is now available for new users, allowing administrators to automatically assign newly registered users to a specified group for streamlined access control to models, prompts, and tools, particularly useful for organizations with group-based model access policies. [#19325](https://github.com/open-webui/open-webui/pull/19325), [#17842](https://github.com/open-webui/open-webui/issues/17842)
- 🔒 Password-based authentication can now be fully disabled via "ENABLE_PASSWORD_AUTH" environment variable, enforcing SSO-only authentication and preventing password login fallback when SSO is configured. [#19113](https://github.com/open-webui/open-webui/pull/19113)
- 🖼️ Large stream chunk handling was implemented to support models that generate images directly in their output responses, with configurable buffer size via "CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE" environment variable, resolving compatibility issues with models like Gemini 2.5 Flash Image. [#18884](https://github.com/open-webui/open-webui/pull/18884), [#17626](https://github.com/open-webui/open-webui/issues/17626)
- 🖼️ Streaming response middleware now handles images in delta updates with automatic base64 conversion, enabling proper display of images from models using the "choices[0].delta.images.image_url" format such as Gemini 2.5 Flash Image Preview on OpenRouter. [#19073](https://github.com/open-webui/open-webui/pull/19073), [#19019](https://github.com/open-webui/open-webui/issues/19019)
- 📈 Model list API performance was optimized by pre-fetching user group memberships and removing profile image URLs from response payloads, significantly reducing both database queries and payload size for instances with large model lists, with profile images now served dynamically via dedicated endpoints. [#19097](https://github.com/open-webui/open-webui/pull/19097), [#18950](https://github.com/open-webui/open-webui/issues/18950)
- ⏩ Batch file processing performance was improved by reducing database queries by 67% while ensuring data consistency between vector and relational databases. [#18953](https://github.com/open-webui/open-webui/pull/18953)
- 🚀 Chat import performance was dramatically improved by replacing individual per-chat API requests with a bulk import endpoint, reducing import time by up to 95% for large chat collections and providing user feedback via toast notifications displaying the number of successfully imported chats. [#17861](https://github.com/open-webui/open-webui/pull/17861)
- ⚡ Socket event broadcasting performance was optimized by implementing user-specific rooms, significantly reducing server overhead particularly for users with multiple concurrent sessions. [#18996](https://github.com/open-webui/open-webui/pull/18996)
- 🗄️ Weaviate is now supported as a vector database option, providing an additional choice for RAG document storage alongside existing ChromaDB, Milvus, Qdrant, and OpenSearch integrations. [#14747](https://github.com/open-webui/open-webui/pull/14747)
- 🗄️ PostgreSQL pgvector now supports HNSW index types and large dimensional embeddings exceeding 2000 dimensions through automatic halfvec type selection, with configurable index methods via "PGVECTOR_INDEX_METHOD", "PGVECTOR_HNSW_M", "PGVECTOR_HNSW_EF_CONSTRUCTION", and "PGVECTOR_IVFFLAT_LISTS" environment variables. [#19158](https://github.com/open-webui/open-webui/pull/19158), [#16890](https://github.com/open-webui/open-webui/issues/16890)
- 🔍 Azure AI Search is now supported as a web search provider, enabling integration with Azure's cognitive search services via "AZURE_AI_SEARCH_API_KEY", "AZURE_AI_SEARCH_ENDPOINT", and "AZURE_AI_SEARCH_INDEX_NAME" configuration. [#19104](https://github.com/open-webui/open-webui/pull/19104)
- ⚡ External embedding generation now processes API requests in parallel instead of sequential batches, reducing document processing time by 10-50x when using OpenAI, Azure OpenAI, or Ollama embedding providers, with large PDFs now processing in seconds instead of minutes. [#19296](https://github.com/open-webui/open-webui/pull/19296)
- 💨 Base64 image conversion is now available for markdown content in chat responses, automatically uploading embedded images exceeding 1KB and replacing them with file URLs to reduce payload size and resource consumption, configurable via "REPLACE_IMAGE_URLS_IN_CHAT_RESPONSE" environment variable. [#19076](https://github.com/open-webui/open-webui/pull/19076)
- 🎨 OpenAI image generation now supports additional API parameters including quality settings for GPT Image 1, configurable via "IMAGES_OPENAI_API_PARAMS" environment variable or through the admin interface, enabling cost-effective image generation with low, medium, or high quality options. [#19228](https://github.com/open-webui/open-webui/issues/19228)
- 🖼️ Image editing can now be independently enabled or disabled via admin settings, allowing administrators to control whether sequential image prompts trigger image editing or new image generation, configurable via "ENABLE_IMAGE_EDIT" environment variable. [#19284](https://github.com/open-webui/open-webui/issues/19284)
- 🔐 SSRF protection was implemented with a configurable URL blocklist that prevents access to cloud metadata endpoints and private networks, with default protections for AWS, Google Cloud, Azure, and Alibaba Cloud metadata services, customizable via "WEB_FETCH_FILTER_LIST" environment variable. [#19201](https://github.com/open-webui/open-webui/pull/19201)
- ⚡ Workspace models page now supports server-side pagination dramatically improving load times and usability for instances with large numbers of workspace models.
- 🔍 Hybrid search now indexes file metadata including filenames, titles, headings, sources, and snippets alongside document content, enabling keyword queries to surface documents where search terms appear only in metadata, configurable via "ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS" environment variable. [#19095](https://github.com/open-webui/open-webui/pull/19095)
- 📂 Knowledge base upload page now supports folder drag-and-drop with recursive directory handling, enabling batch uploads of entire directory structures instead of requiring individual file selection. [#19320](https://github.com/open-webui/open-webui/pull/19320)
- 🤖 Model cloning is now available in admin settings, allowing administrators to quickly create workspace models based on existing base models through a "Clone" option in the model dropdown menu. [#17937](https://github.com/open-webui/open-webui/pull/17937)
- 🎨 UI scale adjustment is now available in interface settings, allowing users to increase the size of the entire interface from 1.0x to 1.5x for improved accessibility and readability, particularly beneficial for users with visual impairments. [#19186](https://github.com/open-webui/open-webui/pull/19186)
- 📌 Default pinned models can now be configured by administrators for all new users, mirroring the behavior of default models where admin-configured defaults apply only to users who haven't customized their pinned models, configurable via "DEFAULT_PINNED_MODELS" environment variable. [#19273](https://github.com/open-webui/open-webui/pull/19273)
- 🎙️ Text-to-Speech and Speech-to-Text services now receive user information headers when "ENABLE_FORWARD_USER_INFO_HEADERS" is enabled, allowing external TTS and STT providers to implement user-specific personalization, rate limiting, and usage tracking. [#19323](https://github.com/open-webui/open-webui/pull/19323), [#19312](https://github.com/open-webui/open-webui/issues/19312)
- 🎙️ Voice mode now supports custom system prompts via "VOICE_MODE_PROMPT_TEMPLATE" configuration, allowing administrators to control response style and behavior for voice interactions. [#18607](https://github.com/open-webui/open-webui/pull/18607)
- 🔧 WebSocket and Redis configuration options are now available including debug logging controls, custom ping timeout and interval settings, and arbitrary Redis connection options via "WEBSOCKET_SERVER_LOGGING", "WEBSOCKET_SERVER_ENGINEIO_LOGGING", "WEBSOCKET_SERVER_PING_TIMEOUT", "WEBSOCKET_SERVER_PING_INTERVAL", and "WEBSOCKET_REDIS_OPTIONS" environment variables. [#19091](https://github.com/open-webui/open-webui/pull/19091)
- 🔧 MCP OAuth dynamic client registration now automatically detects and uses the appropriate token endpoint authentication method from server-supported options, enabling compatibility with OAuth servers that only support "client_secret_basic" instead of "client_secret_post". [#19193](https://github.com/open-webui/open-webui/issues/19193)
- 🔧 Custom headers can now be configured for remote MCP and OpenAPI tool server connections, enabling integration with services that require additional authentication headers. [#18918](https://github.com/open-webui/open-webui/issues/18918)
- 🔍 Perplexity Search now supports custom API endpoints via "PERPLEXITY_SEARCH_API_URL" configuration and automatically forwards user information headers to enable personalized search experiences. [#19147](https://github.com/open-webui/open-webui/pull/19147)
- 🔍 User information headers can now be optionally forwarded to external web search engines when "ENABLE_FORWARD_USER_INFO_HEADERS" is enabled. [#19043](https://github.com/open-webui/open-webui/pull/19043)
- 📊 Daily active user metric is now available for monitoring, tracking unique users active since midnight UTC via the "webui.users.active.today" Prometheus gauge. [#19236](https://github.com/open-webui/open-webui/pull/19236), [#19234](https://github.com/open-webui/open-webui/issues/19234)
- 📊 Audit log file path is now configurable via "AUDIT_LOGS_FILE_PATH" environment variable, enabling storage in separate volumes or custom locations. [#19173](https://github.com/open-webui/open-webui/pull/19173)
- 🎨 Sidebar collapse states for model lists and group information are now persistent across page refreshes, remembering user preferences through browser-based storage. [#19159](https://github.com/open-webui/open-webui/issues/19159)
- 🎨 Background image display was enhanced with semi-transparent overlays for navbar and sidebar, creating a seamless and visually cohesive design across the entire interface. [#19157](https://github.com/open-webui/open-webui/issues/19157)
- 📋 Tables in chat messages now include a copy button that appears on hover, enabling quick copying of table content alongside the existing CSV export functionality. [#19162](https://github.com/open-webui/open-webui/issues/19162)
- 📝 Notes can now be created directly via the "/notes/new" URL endpoint with optional title and content query parameters, enabling faster note creation through bookmarks and shortcuts. [#19195](https://github.com/open-webui/open-webui/issues/19195)
- 🏷️ Tag suggestions are now context-aware, displaying only relevant tags when creating or editing models versus chat conversations, preventing confusion between model and chat tags. [#19135](https://github.com/open-webui/open-webui/issues/19135)
- ✍️ Prompt autocompletion is now available independently of the rich text input setting, improving accessibility to the feature. [#19150](https://github.com/open-webui/open-webui/issues/19150)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for Simplified Chinese, Traditional Chinese, Portuguese (Brazil), Catalan, Spanish (Spain), Finnish, Irish, Farsi, Swedish, Danish, German, Korean, and Thai were improved and expanded.

### Fixed

- 🤖 Model update functionality now works correctly, resolving a database parameter binding error that prevented saving changes to model configurations via the Save & Update button. [#19335](https://github.com/open-webui/open-webui/issues/19335)
- 🖼️ Multiple input images for image editing and generation are now correctly passed as an array using the "image[]" parameter syntax, enabling proper multi-image reference functionality with models like GPT Image 1. [#19339](https://github.com/open-webui/open-webui/issues/19339)
- 📱 PWA installations on iOS now properly refresh after server container restarts, resolving freezing issues by automatically unregistering service workers when version or deployment changes are detected. [#19316](https://github.com/open-webui/open-webui/pull/19316)
- 🗄️ S3 Vectors collection detection now correctly handles buckets with more than 2000 indexes by using direct index lookup instead of paginated list scanning, improving performance by approximately 8x and enabling RAG queries to work reliably at scale. [#19238](https://github.com/open-webui/open-webui/pull/19238), [#19233](https://github.com/open-webui/open-webui/issues/19233)
- 📈 Feedback retrieval performance was optimized by eliminating N+1 query patterns through database joins, adding server-side pagination and sorting, significantly reducing database load for instances with large feedback datasets. [#17976](https://github.com/open-webui/open-webui/pull/17976)
- 🔍 Chat search now works correctly with PostgreSQL when chat data contains null bytes, with comprehensive sanitization preventing null bytes during data writes, cleaning existing data on read, and stripping null bytes during search queries to ensure reliable search functionality. [#15616](https://github.com/open-webui/open-webui/issues/15616)
- 🔍 Hybrid search with reranking now correctly handles attribute validation, preventing errors when collection results lack expected structure. [#19025](https://github.com/open-webui/open-webui/pull/19025), [#17046](https://github.com/open-webui/open-webui/issues/17046)
- 🔎 Reranking functionality now works correctly after recent refactoring, resolving crashes caused by incorrect function argument handling. [#19270](https://github.com/open-webui/open-webui/pull/19270)
- 🤖 Azure OpenAI models now support the "reasoning_effort" parameter, enabling proper configuration of reasoning capabilities for models like GPT-5.1 which default to no reasoning without this setting. [#19290](https://github.com/open-webui/open-webui/issues/19290)
- 🤖 Models with very long IDs can now be deleted correctly, resolving URL length limitations that previously prevented management operations on such models. [#18230](https://github.com/open-webui/open-webui/pull/18230)
- 🤖 Model-level streaming settings now correctly apply to API requests, ensuring "Stream Chat Response" toggle properly controls the streaming parameter. [#19154](https://github.com/open-webui/open-webui/issues/19154)
- 🖼️ Image editing configuration now correctly preserves independent OpenAI API endpoints and keys, preventing them from being overwritten by image generation settings. [#19003](https://github.com/open-webui/open-webui/issues/19003)
- 🎨 Gemini image edit settings now display correctly in the admin panel, fixing an incorrect configuration key reference that prevented proper rendering of edit options. [#19200](https://github.com/open-webui/open-webui/pull/19200)
- 🖌️ Image generation settings menu now loads correctly, resolving validation errors with AUTOMATIC1111 API authentication parameters. [#19187](https://github.com/open-webui/open-webui/issues/19187), [#19246](https://github.com/open-webui/open-webui/issues/19246)
- 📅 Date formatting in chat search and admin user chat search now correctly respects the "DEFAULT_LOCALE" environment variable, displaying dates according to the configured locale instead of always using MM/DD/YYYY format. [#19305](https://github.com/open-webui/open-webui/pull/19305), [#19020](https://github.com/open-webui/open-webui/issues/19020)
- 📝 RAG template query placeholder escaping logic was corrected to prevent unintended replacements of context values when query placeholders appear in retrieved content. [#19102](https://github.com/open-webui/open-webui/pull/19102), [#19101](https://github.com/open-webui/open-webui/issues/19101)
- 📄 RAG template prompt duplication was eliminated by removing redundant user query section from the default template. [#19099](https://github.com/open-webui/open-webui/pull/19099), [#19098](https://github.com/open-webui/open-webui/issues/19098)
- 📋 MinerU local mode configuration no longer incorrectly requires an API key, allowing proper use of local content extraction without external API credentials. [#19258](https://github.com/open-webui/open-webui/issues/19258)
- 📊 Excel file uploads now work correctly with the addition of the missing msoffcrypto-tool dependency, resolving import errors introduced by the unstructured package upgrade. [#19153](https://github.com/open-webui/open-webui/issues/19153)
- 📑 Docling parameters now properly handle JSON serialization, preventing exceptions and ensuring configuration changes are saved correctly. [#19072](https://github.com/open-webui/open-webui/pull/19072)
- 🛠️ UserValves configuration now correctly isolates settings per tool, preventing configuration contamination when multiple tools with UserValves are used simultaneously. [#19185](https://github.com/open-webui/open-webui/pull/19185), [#15569](https://github.com/open-webui/open-webui/issues/15569)
- 🔧 Tool selection prompt now correctly handles user messages without duplication, removing redundant query prefixes and improving prompt clarity. [#19122](https://github.com/open-webui/open-webui/pull/19122), [#19121](https://github.com/open-webui/open-webui/issues/19121)
- 📝 Notes chat feature now correctly submits messages to the completions endpoint, resolving errors that prevented AI model interactions. [#19079](https://github.com/open-webui/open-webui/pull/19079)
- 📝 Note PDF downloads now sanitize HTML content using DOMPurify before rendering, preventing potential DOM-based XSS attacks from malicious content in notes. [Commit](https://github.com/open-webui/open-webui/commit/03cc6ce8eb5c055115406e2304fbf7e3338b8dce)
- 📁 Archived chats now have their folder associations automatically removed to prevent unintended deletion when their previous folder is deleted. [#14578](https://github.com/open-webui/open-webui/issues/14578)
- 🔐 ElevenLabs API key is now properly obfuscated in the admin settings page, preventing plain text exposure of sensitive credentials. [#19262](https://github.com/open-webui/open-webui/pull/19262), [#19260](https://github.com/open-webui/open-webui/issues/19260)
- 🔧 MCP OAuth server metadata discovery now follows the correct specification order, ensuring proper authentication flow compliance. [#19244](https://github.com/open-webui/open-webui/pull/19244)
- 🔒 API key endpoint restrictions now properly enforce access controls for all endpoints including SCIM, preventing unintended access when "API_KEY_ALLOWED_ENDPOINTS" is configured. [#19168](https://github.com/open-webui/open-webui/issues/19168)
- 🔓 OAuth role claim parsing now supports both flat and nested claim structures, enabling compatibility with OAuth providers that deliver claims as direct properties on the user object rather than nested structures. [#19286](https://github.com/open-webui/open-webui/pull/19286)
- 🔑 OAuth MCP server verification now correctly extracts the access token value for authorization headers instead of sending the entire token dictionary. [#19149](https://github.com/open-webui/open-webui/pull/19149), [#19148](https://github.com/open-webui/open-webui/issues/19148)
- ⚙️ OAuth dynamic client registration now correctly converts empty strings to None for optional fields, preventing validation failures in MCP package integration. [#19144](https://github.com/open-webui/open-webui/pull/19144), [#19129](https://github.com/open-webui/open-webui/issues/19129)
- 🔐 OIDC authentication now correctly passes client credentials in access token requests, ensuring compatibility with providers that require these parameters per RFC 6749. [#19132](https://github.com/open-webui/open-webui/pull/19132), [#19131](https://github.com/open-webui/open-webui/issues/19131)
- 🔗 OAuth client creation now respects configured token endpoint authentication methods instead of defaulting to basic authentication, preventing failures with servers that don't support basic auth. [#19165](https://github.com/open-webui/open-webui/pull/19165)
- 📋 Text copied from chat responses in Chrome now pastes without background formatting, improving readability when pasting into word processors. [#19083](https://github.com/open-webui/open-webui/issues/19083)

### Changed

- 🗄️ Group membership data storage was refactored from JSON arrays to a dedicated relational database table, significantly improving query performance and scalability for instances with large numbers of users and groups, while API responses now return member counts instead of full user ID arrays. [#19239](https://github.com/open-webui/open-webui/pull/19239)
- 📄 MinerU parameter handling was refactored to pass parameters directly to the API, improving flexibility and fixing VLM backend configuration. [#19105](https://github.com/open-webui/open-webui/pull/19105), [#18446](https://github.com/open-webui/open-webui/discussions/18446)
- 🔐 API key creation is now controlled by granular user and group permissions, with the "ENABLE_API_KEY" environment variable renamed to "ENABLE_API_KEYS" and disabled by default, requiring explicit configuration at both the global and user permission levels, while related environment variables "ENABLE_API_KEY_ENDPOINT_RESTRICTIONS" and "API_KEY_ALLOWED_ENDPOINTS" were renamed to "ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS" and "API_KEYS_ALLOWED_ENDPOINTS" respectively. [#18336](https://github.com/open-webui/open-webui/pull/18336)

## [0.6.36] - 2025-11-07

### Added

- 🔐 OAuth group parsing now supports configurable separators via the "OAUTH_GROUPS_SEPARATOR" environment variable, enabling proper handling of semicolon-separated group claims from providers like CILogon. [#18987](https://github.com/open-webui/open-webui/pull/18987), [#18979](https://github.com/open-webui/open-webui/issues/18979)

### Fixed

- 🛠️ Tool calling functionality is restored by correcting asynchronous function handling in tool parameter updates. [#18981](https://github.com/open-webui/open-webui/issues/18981)
- 🖼️ The ComfyUI image edit workflow editor modal now opens correctly when clicking the Edit button. [#18978](https://github.com/open-webui/open-webui/issues/18978)
- 🔥 Firecrawl import errors are resolved by implementing lazy loading and using the correct class name. [#18973](https://github.com/open-webui/open-webui/issues/18973)
- 🔌 Socket.IO CORS warning is resolved by properly configuring CORS origins for Socket.IO connections. [Commit](https://github.com/open-webui/open-webui/commit/639d26252e528c9c37a5f553b11eb94376d8792d)

## [0.6.35] - 2025-11-06

### Added

- 🖼️ Image generation system received a comprehensive overhaul with major new capabilities including full image editing support allowing users to modify existing images using text prompts with OpenAI, Gemini, or ComfyUI engines, adding Gemini 2.5 Flash Image (Nano Banana) support, Qwen Image Edit integration, resolution of base64-encoded image display issues, streamlined AUTOMATIC1111 configuration by consolidating parameters into a flexible JSON parameters field, and enhanced UI with a code editor modal for ComfyUI workflow management. [#17434](https://github.com/open-webui/open-webui/pull/17434), [#16976](https://github.com/open-webui/open-webui/issues/16976), [Commit](https://github.com/open-webui/open-webui/commit/8e5690aab4f632a57027e2acf880b8f89a8717c0), [Commit](https://github.com/open-webui/open-webui/commit/72f8539fd2e679fec0762945f22f4b8a6920afa0), [Commit](https://github.com/open-webui/open-webui/commit/8d34fcb586eeee1fac6da2f991518b8a68b00b72), [Commit](https://github.com/open-webui/open-webui/commit/72900cd686de1fa6be84b5a8a2fc857cff7b91b8)
- 🔒 CORS origin validation was added to WebSocket connections as a defense-in-depth security measure against cross-site WebSocket hijacking attacks. [#18411](https://github.com/open-webui/open-webui/pull/18411), [#18410](https://github.com/open-webui/open-webui/issues/18410)
- 🔄 Automatic page refresh now occurs when a version update is detected via WebSocket connection, ensuring users always run the latest version without cache issues. [Commit](https://github.com/open-webui/open-webui/commit/989f192c92d2fe55daa31336e7971e21798b96ae)
- 🐍 Experimental initial preparations for Python 3.13 compatibility by updating dependencies with security enhancements and cryptographic improvements. [#18430](https://github.com/open-webui/open-webui/pull/18430), [#18424](https://github.com/open-webui/open-webui/pull/18424)
- ⚡ Image compression now preserves the original image format instead of converting to PNG, significantly reducing file sizes and improving chat loading performance. [#18506](https://github.com/open-webui/open-webui/pull/18506)
- 🎤 Mistral Voxtral model support was added for text-to-speech, including voxtral-small and voxtral-mini models with both transcription and chat completion API support. [#18934](https://github.com/open-webui/open-webui/pull/18934)
- 🔊 Text-to-speech now uses a global audio queue system to prevent overlapping playback, ensuring only one TTS instance plays at a time with proper stop/start controls and automatic cleanup when switching between messages. [#16152](https://github.com/open-webui/open-webui/pull/16152), [#18744](https://github.com/open-webui/open-webui/pull/18744), [#16150](https://github.com/open-webui/open-webui/issues/16150)
- 🔊 ELEVENLABS_API_BASE_URL environment variable now allows configuration of custom ElevenLabs API endpoints, enabling support for EU residency API requirements. [#18402](https://github.com/open-webui/open-webui/issues/18402)
- 🔐 OAUTH_ROLES_SEPARATOR environment variable now allows custom role separators for OAuth roles that contain commas, useful for roles specified in LDAP syntax. [#18572](https://github.com/open-webui/open-webui/pull/18572)
- 📄 External document loaders can now optionally forward user information headers when ENABLE_FORWARD_USER_INFO_HEADERS is enabled, enabling cost tracking, audit logs, and usage analytics for external services. [#18731](https://github.com/open-webui/open-webui/pull/18731)
- 📄 MISTRAL_OCR_API_BASE_URL environment variable now allows configuration of custom Mistral OCR API endpoints for flexible deployment options. [Commit](https://github.com/open-webui/open-webui/commit/415b93c7c35c2e2db4425e6da1b88b3750f496b0)
- ⌨️ Keyboard shortcut hints are now displayed on sidebar buttons with a refactored shortcuts modal that accurately reflects all available hotkeys across different keyboard layouts. [#18473](https://github.com/open-webui/open-webui/pull/18473)
- 🛠️ Tooltips now display tool descriptions when hovering over tool names on the model edit page, improving usability and providing immediate context. [#18707](https://github.com/open-webui/open-webui/pull/18707)
- 📝 "Create a new note" from the search modal now immediately creates a new private note and opens it in the editor instead of navigating to the generic notes page. [#18255](https://github.com/open-webui/open-webui/pull/18255)
- 🖨️ Code block output now preserves whitespace formatting with monospace font to accurately reflect terminal behavior. [#18352](https://github.com/open-webui/open-webui/pull/18352)
- ✏️ Edit button is now available in the three-dot menu of models in the workspace section for quick access to model editing, with the menu reorganized for better user experience and Edit, Clone, Copy Link, and Share options logically grouped. [#18574](https://github.com/open-webui/open-webui/pull/18574)
- 📌 Sidebar models section is now collapsible, allowing users to expand and collapse the pinned models list for better sidebar organization. [Commit](https://github.com/open-webui/open-webui/commit/82c08a3b5d189f81c96b6548cc872198771015b0)
- 🌙 Dark mode styles for select elements were added using Tailwind CSS classes, improving consistency across the interface. [#18636](https://github.com/open-webui/open-webui/pull/18636)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for Portuguese (Brazil), Greek, German, Traditional Chinese, Simplified Chinese, Spanish, Georgian, Danish, and Estonian were enhanced and expanded.

### Fixed

- 🔒 Server-Sent Event (SSE) code injection vulnerability in Direct Connections is resolved by blocking event emission from untrusted external model servers; event emitters from direct connected model servers are no longer supported, preventing arbitrary JavaScript execution in user browsers. [Commit](https://github.com/open-webui/open-webui/commit/8af6a4cf21b756a66cd58378a01c60f74c39b7ca)
- 🛡️ DOM XSS vulnerability in "Insert Prompt as Rich Text" is resolved by sanitizing HTML content with DOMPurify before rendering. [Commit](https://github.com/open-webui/open-webui/commit/eb9c4c0e358c274aea35f21c2856c0a20051e5f1)
- ⚙️ MCP server cancellation scope corruption is prevented by reversing disconnection order to follow LIFO and properly handling exceptions, resolving 100% CPU usage when resuming chats with expired tokens or using multiple streamable MCP servers. [#18537](https://github.com/open-webui/open-webui/pull/18537)
- 🔧 UI freeze when querying models with knowledge bases containing inconsistent distance metrics is resolved by properly initializing the distances array in citations. [#18585](https://github.com/open-webui/open-webui/pull/18585)
- 🤖 Duplicate model IDs from multiple OpenAI endpoints are now automatically deduplicated server-side, preventing frontend crashes for users with unified gateway proxies that aggregate multiple providers. [Commit](https://github.com/open-webui/open-webui/commit/fdf7ca11d4f3cc8fe63e81c98dc0d1e48e52ba36)
- 🔐 Login failures with passwords longer than 72 bytes are resolved by safely truncating oversized passwords for bcrypt compatibility. [#18157](https://github.com/open-webui/open-webui/issues/18157)
- 🔐 OAuth 2.1 MCP tool connections now automatically re-register clients when stored client IDs become stale, preventing unauthorized_client errors after editing tool endpoints and providing detailed error messages for callback failures. [#18415](https://github.com/open-webui/open-webui/pull/18415), [#18309](https://github.com/open-webui/open-webui/issues/18309)
- 🔓 OAuth 2.1 discovery, metadata fetching, and dynamic client registration now correctly use HTTP proxy environment variables when trust_env is enabled. [Commit](https://github.com/open-webui/open-webui/commit/bafeb76c411483bd6b135f0edbcdce048120f264)
- 🔌 MCP server connection failures now display clear error messages in the chat interface instead of silently failing. [#18892](https://github.com/open-webui/open-webui/pull/18892), [#18889](https://github.com/open-webui/open-webui/issues/18889)
- 💬 Chat titles are now properly generated even when title auto-generation is disabled in interface settings, fixing an issue where chats would remain labeled as "New chat". [#18761](https://github.com/open-webui/open-webui/pull/18761), [#18717](https://github.com/open-webui/open-webui/issues/18717), [#6478](https://github.com/open-webui/open-webui/issues/6478)
- 🔍 Chat query errors are prevented by properly validating and handling the "order_by" parameter to ensure requested columns exist. [#18400](https://github.com/open-webui/open-webui/pull/18400), [#18452](https://github.com/open-webui/open-webui/pull/18452)
- 🔧 Root-level max_tokens parameter is no longer dropped when proxying to Ollama, properly converting to num_predict to limit output token length as intended. [#18618](https://github.com/open-webui/open-webui/issues/18618)
- 🔑 Self-hosted Marker instances can now be used without requiring an API key, while keeping it optional for datalab Marker service users. [#18617](https://github.com/open-webui/open-webui/issues/18617)
- 🔧 OpenAPI specification endpoint conflict between "/api/v1/models" and "/api/v1/models/" is resolved by changing the models router endpoint to "/list", preventing duplicate operationId errors when generating TypeScript API clients. [#18758](https://github.com/open-webui/open-webui/issues/18758)
- 🏷️ Model tags are now de-duplicated case-insensitively in both the model selector and workspace models page, preventing duplicate entries with different capitalization from appearing in filter dropdowns. [#18716](https://github.com/open-webui/open-webui/pull/18716), [#18711](https://github.com/open-webui/open-webui/issues/18711)
- 📄 Docling RAG parameter configuration is now correctly saved in the admin UI by fixing the typo in the "DOCLING_PARAMS" parameter name. [#18390](https://github.com/open-webui/open-webui/pull/18390)
- 📃 Tika document processing now automatically detects content types instead of relying on potentially incorrect browser-provided mime-types, improving file handling accuracy for formats like RTF. [#18765](https://github.com/open-webui/open-webui/pull/18765), [#18683](https://github.com/open-webui/open-webui/issues/18683)
- 🖼️ Image and video uploads to knowledge bases now display proper error messages instead of showing an infinite spinner when the content extraction engine does not support these file types. [#18514](https://github.com/open-webui/open-webui/issues/18514)
- 📝 Notes PDF export now properly detects and applies dark mode styling consistently across both the notes list and individual note pages, with a shared utility function to eliminate code duplication. [#18526](https://github.com/open-webui/open-webui/issues/18526)
- 💭 Details tags for reasoning content are now correctly identified and rendered even when the same tag is present in user messages. [#18840](https://github.com/open-webui/open-webui/pull/18840), [#18294](https://github.com/open-webui/open-webui/issues/18294)
- 📊 Mermaid and Vega rendering errors now display inline with the code instead of showing repetitive toast notifications, improving user experience when models generate invalid diagram syntax. [Commit](https://github.com/open-webui/open-webui/commit/fdc0f04a8b7dd0bc9f9dc0e7e30854f7a0eea3e9)
- 📈 Mermaid diagram rendering errors no longer cause UI unavailability or display error messages below the input box. [#18493](https://github.com/open-webui/open-webui/pull/18493), [#18340](https://github.com/open-webui/open-webui/issues/18340)
- 🔗 Web search SSL verification is now asynchronous, preventing the website from hanging during web search operations. [#18714](https://github.com/open-webui/open-webui/pull/18714), [#18699](https://github.com/open-webui/open-webui/issues/18699)
- 🌍 Web search results now correctly use HTTP proxy environment variables when WEB_SEARCH_TRUST_ENV is enabled. [#18667](https://github.com/open-webui/open-webui/pull/18667), [#7008](https://github.com/open-webui/open-webui/discussions/7008)
- 🔍 Google Programmable Search Engine now properly includes referer headers, enabling API keys with HTTP referrer restrictions configured in Google Cloud Console. [#18871](https://github.com/open-webui/open-webui/pull/18871), [#18870](https://github.com/open-webui/open-webui/issues/18870)
- ⚡ YouTube video transcript fetching now works correctly when using a proxy connection. [#18419](https://github.com/open-webui/open-webui/pull/18419)
- 🎙️ Speech-to-text transcription no longer deletes or replaces existing text in the prompt input field, properly preserving any previously entered content. [#18540](https://github.com/open-webui/open-webui/issues/18540)
- 🎙️ The "Instant Auto-Send After Voice Transcription" setting now functions correctly and automatically sends transcribed text when enabled. [#18466](https://github.com/open-webui/open-webui/issues/18466)
- ⚙️ Chat settings now load properly when reopening a tab or starting a new session by initializing defaults when sessionStorage is empty. [#18438](https://github.com/open-webui/open-webui/pull/18438)
- 🔎 Folder tag search in the sidebar now correctly handles folder names with multiple spaces by replacing all spaces with underscores. [Commit](https://github.com/open-webui/open-webui/commit/a8fe979af68e47e4e4bb3eb76e48d93d60cd2a45)
- 🛠️ Functions page now updates immediately after deleting a function, removing the need for a manual page reload. [#18912](https://github.com/open-webui/open-webui/pull/18912), [#18908](https://github.com/open-webui/open-webui/issues/18908)
- 🛠️ Native tool calling now properly supports sequential tool calls with shared context, allowing tools to access images and data from previous tool executions in the same conversation. [#18664](https://github.com/open-webui/open-webui/pull/18664)
- 🎯 Globally enabled actions in the model editor now correctly apply as global instead of being treated as disabled. [#18577](https://github.com/open-webui/open-webui/pull/18577)
- 📋 Clipboard images pasted via the "{{CLIPBOARD}}" prompt variable are now correctly converted to base64 format before being sent to the backend, resolving base64 encoding errors. [#18432](https://github.com/open-webui/open-webui/pull/18432), [#18425](https://github.com/open-webui/open-webui/issues/18425)
- 📋 File list is now cleared when switching to models that do not support file uploads, preventing files from being sent to incompatible models. [#18496](https://github.com/open-webui/open-webui/pull/18496)
- 📂 Move menu no longer displays when folders are empty. [#18484](https://github.com/open-webui/open-webui/pull/18484)
- 📁 Folder and channel creation now validates that names are not empty, preventing creation of folders or channels with no name and showing an error toast if attempted. [#18564](https://github.com/open-webui/open-webui/pull/18564)
- 🖊️ Rich text input no longer removes text between equals signs when pasting code with comparison operators. [#18551](https://github.com/open-webui/open-webui/issues/18551)
- ⌨️ Keyboard shortcuts now display the correct keys for international and non-QWERTY keyboard layouts by detecting the user's layout using the Keyboard API. [#18533](https://github.com/open-webui/open-webui/pull/18533)
- 🌐 "Attach Webpage" button now displays with correct disabled styling when a model does not support file uploads. [#18483](https://github.com/open-webui/open-webui/pull/18483)
- 🎚️ Divider no longer displays in the integrations menu when no integrations are enabled. [#18487](https://github.com/open-webui/open-webui/pull/18487)
- 📱 Chat controls button is now properly hidden on mobile for users without admin or explicit chat control permissions. [#18641](https://github.com/open-webui/open-webui/pull/18641)
- 📍 User menu, download submenu, and move submenu are now repositioned to prevent overlap with the Chat Controls sidebar when it is open. [Commit](https://github.com/open-webui/open-webui/commit/414ab51cb6df1ab0d6c85ac6c1f2c5c9a5f8e2aa)
- 🎯 Artifacts button no longer appears in the chat menu when there are no artifacts to display. [Commit](https://github.com/open-webui/open-webui/commit/ed6449d35f84f68dc75ee5c6b3f4748a3fda0096)
- 🎨 Artifacts view now automatically displays when opening an existing conversation containing artifacts, improving user experience. [#18215](https://github.com/open-webui/open-webui/pull/18215)
- 🖌️ Formatting toolbar is no longer hidden under images or code blocks in chat and now displays correctly above all message content.
- 🎨 Layout shift near system instructions is prevented by properly rendering the chat component when system prompts are empty. [#18594](https://github.com/open-webui/open-webui/pull/18594)
- 📐 Modal layout shift caused by scrollbar appearance is prevented by adding a stable scrollbar gutter. [#18591](https://github.com/open-webui/open-webui/pull/18591)
- ✨ Spacing between icon and label in the user menu dropdown items is now consistent. [#18595](https://github.com/open-webui/open-webui/pull/18595)
- 💬 Duplicate prompt suggestions no longer cause the webpage to freeze or throw JavaScript errors by implementing proper key management with composite keys. [#18841](https://github.com/open-webui/open-webui/pull/18841), [#18566](https://github.com/open-webui/open-webui/issues/18566)
- 🔍 Chat preview loading in the search modal now works correctly for all search results by fixing an index boundary check that previously caused out-of-bounds errors. [#18911](https://github.com/open-webui/open-webui/pull/18911)
- ♿ Screen reader support was enhanced by wrapping messages in semantic elements with descriptive aria-labels, adding "Assistant is typing" and "Response complete" announcements for improved accessibility. [#18735](https://github.com/open-webui/open-webui/pull/18735)
- 🔒 Incorrect await call in the OAuth 2.1 flow is removed, eliminating a logged exception during authentication. [#18236](https://github.com/open-webui/open-webui/pull/18236)
- 🛡️ Duplicate crossorigin attribute in the manifest file was removed. [#18413](https://github.com/open-webui/open-webui/pull/18413)

### Changed

- 🔄 Firecrawl integration was refactored to use the official Firecrawl SDK instead of direct HTTP requests and langchain_community FireCrawlLoader, improving reliability and performance with batch scraping support and enhanced error handling. [#18635](https://github.com/open-webui/open-webui/pull/18635)
- 📄 MinerU content extraction engine now only supports PDF files following the upstream removal of LibreOffice document conversion in version 2.0.0; users needing to process office documents should convert them to PDF format first. [#18448](https://github.com/open-webui/open-webui/issues/18448)

## [0.6.34] - 2025-10-16

### Added

- 📄 MinerU is now supported as a document parser backend, with support for both local and managed API deployments. [#18306](https://github.com/open-webui/open-webui/pull/18306)
- 🔒 JWT token expiration default is now set to 4 weeks instead of never expiring, with security warnings displayed in backend logs and admin UI when set to unlimited. [#18261](https://github.com/open-webui/open-webui/pull/18261), [#18262](https://github.com/open-webui/open-webui/pull/18262)
- ⚡ Page loading performance is improved by preventing unnecessary API requests when sidebar folders are not expanded. [#18179](https://github.com/open-webui/open-webui/pull/18179), [#17476](https://github.com/open-webui/open-webui/issues/17476)
- 📁 File hash values are now included in the knowledge endpoint response, enabling efficient file synchronization through hash comparison. [#18284](https://github.com/open-webui/open-webui/pull/18284), [#18283](https://github.com/open-webui/open-webui/issues/18283)
- 🎨 Chat dialog scrollbar visibility is improved by increasing its width, making it easier to use for navigation. [#18369](https://github.com/open-webui/open-webui/pull/18369), [#11782](https://github.com/open-webui/open-webui/issues/11782)
- 🔄 Various improvements were implemented across the frontend and backend to enhance performance, stability, and security.
- 🌐 Translations for Catalan, Chinese, Czech, Finnish, German, Kabyle, Korean, Portuguese (Brazil), Spanish, Thai, and Turkish were enhanced and expanded.

### Fixed

- 📚 Focused retrieval mode now works correctly, preventing the system from forcing full context mode and loading all documents in a knowledge base regardless of settings. [#18133](https://github.com/open-webui/open-webui/issues/18133)
- 🔧 Filter inlet functions now correctly execute on tool call continuations, ensuring parameter persistence throughout tool interactions. [#18222](https://github.com/open-webui/open-webui/issues/18222)
- 🛠️ External tool servers now properly support DELETE requests with body data. [#18289](https://github.com/open-webui/open-webui/pull/18289), [#18287](https://github.com/open-webui/open-webui/issues/18287)
- 🗄️ Oracle23ai vector database client now correctly handles variable initialization, resolving UnboundLocalError when retrieving items from collections. [#18356](https://github.com/open-webui/open-webui/issues/18356)
- 🔧 Model auto-pull functionality now works correctly even when user settings remain unmodified. [#18324](https://github.com/open-webui/open-webui/pull/18324)
- 🎨 Duplicate HTML content in artifacts is now prevented by improving code block detection logic. [#18195](https://github.com/open-webui/open-webui/pull/18195), [#6154](https://github.com/open-webui/open-webui/issues/6154)
- 💬 Pinned chats now appear in the Reference Chats list and can be referenced in conversations. [#18288](https://github.com/open-webui/open-webui/issues/18288)
- 📝 Misleading knowledge base warning text in documents settings is clarified to correctly instruct users about reindexing vectors. [#18263](https://github.com/open-webui/open-webui/pull/18263)
- 🔔 Toast notifications can now be dismissed even when a modal is open. [#18260](https://github.com/open-webui/open-webui/pull/18260)
- 🔘 The "Chats" button in the sidebar now correctly toggles chat list visibility without navigating away from the current page. [#18232](https://github.com/open-webui/open-webui/pull/18232)
- 🎯 The Integrations menu no longer closes prematurely when clicking outside the Valves modal. [#18310](https://github.com/open-webui/open-webui/pull/18310)
- 🛠️ Tool ID display issues where "undefined" was incorrectly shown in the interface are now resolved. [#18178](https://github.com/open-webui/open-webui/pull/18178)
- 🛠️ Model management issues caused by excessively long model IDs are now prevented through validation that limits model IDs to 256 characters. [#18125](https://github.com/open-webui/open-webui/issues/18125)

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
