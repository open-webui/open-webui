# Frontend PRD - Open WebUI
# 前端產品需求文檔 - Open WebUI

## Overview
## 概述
Open WebUI is a progressive web application (PWA) built with SvelteKit, a modern Svelte framework. It provides a user-friendly interface for interacting with various AI models and services. The frontend is designed to be responsive, accessible, feature-rich, and is built as a static site (using `@sveltejs/adapter-static`) typically served by the backend or a dedicated web server. It leverages TailwindCSS for styling and Svelte's built-in stores for state management.
Open WebUI 是一個基於 SvelteKit (現代Svelte框架) 構建的漸進式網頁應用程序(PWA)，提供了一個友好的用戶界面來與各種 AI 模型和服務進行交互。前端設計注重響應式、可訪問性和豐富的功能特性，並使用 `@sveltejs/adapter-static` 构建为静态站点，通常由後端或專用Web服務器提供服務。它利用 TailwindCSS 進行樣式設計，並使用 Svelte 的內建 stores 進行狀態管理。

## Key Feature Flags (from `src/lib/stores/index.ts` - `Config` type)
## 關鍵功能開關 (來自 `src/lib/stores/index.ts` - `Config` 類型)
The frontend dynamically adapts to features enabled on the backend. These are typically received via the `config` store (`Config` type).
前端會動態適應後端啟用的功能。這些通常通過 `config` 存儲 (`Config` 類型) 接收。
```typescript
// Example structure from the Config type in src/lib/stores/index.ts
// 來自 src/lib/stores/index.ts 中 Config 類型的示例結構
interface ConfigFeatures {
  auth: boolean;                     // Authentication system 認證系統
  auth_trusted_header: boolean;      // Trusted header auth 可信標頭認證
  enable_api_key: boolean;           // API key support API密鑰支持
  enable_signup: boolean;            // User registration 用戶註冊
  enable_login_form: boolean;        // Login form display 登錄表單顯示
  enable_web_search?: boolean;       // Web search integration 網頁搜索集成
  enable_google_drive_integration: boolean; // Google Drive integration
  enable_onedrive_integration: boolean;   // OneDrive integration
  enable_image_generation: boolean;  // Image generation 圖像生成
  enable_admin_export: boolean;      // Admin exports 管理員導出
  enable_admin_chat_access: boolean; // Admin chat access 管理員聊天訪問
  enable_community_sharing: boolean; // Community features 社區功能
  enable_autocomplete_generation: boolean; // Autocomplete generation
  // Note: Other features like websocket, direct_connections, channels, code_execution, etc.,
  // are also present and managed, often through specific store values or component logic.
  // 注意：其他功能如 websocket、direct_connections、channels、code_execution 等也存在並被管理，
  // 通常通過特定的存儲值或組件邏輯。
}
```

## Architecture
## 架構

### Code Structure (Root level `package.json`)
### 代碼結構 (根目錄 `package.json`)
```
.
├── package.json            # Project dependencies and scripts 項目依賴和腳本
├── svelte.config.js        # SvelteKit configuration SvelteKit配置
├── vite.config.ts          # Vite configuration Vite配置
├── tsconfig.json           # TypeScript configuration TypeScript配置
├── postcss.config.cjs      # PostCSS configuration PostCSS配置 (for TailwindCSS)
├── src/
│   ├── app.html            # Main HTML shell 主HTML外殼
│   ├── app.d.ts            # Global TypeScript type definitions 全局TypeScript類型定義
│   ├── hooks.server.ts     # SvelteKit server hooks SvelteKit服務器鉤子 (if any)
│   ├── lib/                # Core library code 核心庫代碼
│   │   ├── apis/           # API integration modules API集成模塊
│   │   │   ├── index.ts
│   │   │   ├── auths.ts    # Authentication API calls 認證API調用
│   │   │   ├── chats.ts    # Chat operations API calls 聊天操作API調用
│   │   │   └── ... (models.ts, openai.ts, etc.)
│   │   ├── components/     # Reusable UI components 可重用UI組件
│   │   │   ├── chat/
│   │   │   ├── layout/
│   │   │   └── ...
│   │   ├── stores/         # Svelte stores for global state Svelte全局狀態存儲
│   │   │   └── index.ts    # Defines and exports all stores 定義並導出所有存儲
│   │   ├── utils/          # Utility functions and classes 工具函數和類
│   │   ├── workers/        # Web workers (e.g., Pyodide) Web Worker (例如Pyodide)
│   │   │   └── pyodide.worker.ts
│   │   ├── i18n/           # Internationalization setup 國際化設置
│   │   │   └── index.ts
│   │   └── constants.ts    # Application constants 應用常量
│   ├── routes/             # SvelteKit file-system based routing SvelteKit基於文件系統的路由
│   │   ├── +layout.svelte  # Root layout component 根佈局組件
│   │   ├── +error.svelte   # Root error page 根錯誤頁面
│   │   ├── (app)/          # Main authenticated app routes 主認證應用路由
│   │   │   ├── +layout.svelte
│   │   │   ├── +page.svelte  # Main app page (Chat UI) 主應用頁面 (聊天界面)
│   │   │   └── c/[id]/+page.svelte # Individual chat page 單個聊天頁面
│   │   ├── auth/           # Authentication pages (login, register) 認證頁面 (登錄、註冊)
│   │   │   └── +page.svelte
│   │   └── s/[id]/+page.svelte # Shared chat page 共享聊天頁面
│   └── static/             # Static assets (images, fonts, etc.) 靜態資源 (圖像、字體等)
└── tailwind.css            # Main TailwindCSS entry point TailwindCSS主入口點
```

### Key Files & Responsibilities
### 關鍵文件和職責

*   **`package.json`**: Defines dependencies (SvelteKit, TailwindCSS, i18next, Socket.IO client, Pyodide, etc.) and project scripts.
    定義依賴項 (SvelteKit, TailwindCSS, i18next, Socket.IO客戶端, Pyodide等) 和項目腳本。
*   **`svelte.config.js`**: Configures SvelteKit, notably using `@sveltejs/adapter-static` for static site generation.
    配置SvelteKit，特別是使用 `@sveltejs/adapter-static` 進行靜態站點生成。
*   **`src/app.html`**: The application's HTML shell. Includes PWA manifest link, favicons, initial theme handling script (dark/light/system/custom themes to prevent FOUC), and a splash screen.
    應用程序的HTML外殼。包含PWA清單鏈接、網站圖標、初始主題處理腳本 (深色/淺色/系統/自定義主題以防止FOUC) 和啟動畫面。
*   **`src/routes/+layout.svelte`**: The root layout component. Handles:
    根佈局組件。處理：
    *   Global state initialization (fetching backend config, user session).
        全局狀態初始化 (獲取後端配置、用戶會話)。
    *   Socket.IO connection setup and event handling (`chat-events`, `channel-events`).
        Socket.IO連接設置和事件處理 (`chat-events`, `channel-events`)。
    *   Internationalization (i18n) setup.
        國際化 (i18n) 設置。
    *   Authentication checks and redirection.
        認證檢查和重定向。
    *   Pyodide worker integration (`executePythonAsWorker`).
        Pyodide Worker集成 (`executePythonAsWorker`)。
    *   Tool server execution logic (`executeTool`).
        工具服務器執行邏輯 (`executeTool`)。
    *   Electron app specific integrations.
        Electron應用程序特定集成。
    *   Active tab management using BroadcastChannel.
        使用BroadcastChannel進行活動標籤頁管理。
*   **`src/routes/(app)/+page.svelte`**: The main page for authenticated users, rendering the core `<Chat />` and `<Help />` components.
    認證用戶的主頁面，渲染核心的 `<Chat />` 和 `<Help />` 組件。
*   **`src/lib/stores/index.ts`**: Centralized definition and export of all Svelte stores, managing global application state (user session, config, UI states, chat data, models, etc.) and TypeScript type definitions.
    集中定義和導出所有Svelte存儲，管理全局應用程序狀態 (用戶會話、配置、UI狀態、聊天數據、模型等) 和TypeScript類型定義。
*   **`src/lib/apis/`**: Modules for interacting with the backend API endpoints (auth, chats, models, etc.).
    與後端API端點交互的模塊 (認證、聊天、模型等)。
*   **`src/lib/components/`**: Collection of reusable Svelte components.
    可重用Svelte組件的集合。
*   **`src/lib/workers/pyodide.worker.ts`**: Web worker for running Python code using Pyodide.
    用於使用Pyodide運行Python代碼的Web Worker。

### Core Technologies
### 核心技術
- **Framework 框架**: SvelteKit
- **Styling 樣式**: TailwindCSS
- **State Management 狀態管理**: Svelte stores (defined in `src/lib/stores/index.ts`)
- **Real-time Communication 實時通信**: Socket.IO (client)
- **Internationalization 國際化**: i18next
- **Client-side Python 客戶端Python**: Pyodide
- **Build Tool 构建工具**: Vite

### Key Components (Illustrative)
### 主要組件 (示例性)

#### 1. Layout System (`src/routes/+layout.svelte`, `src/routes/(app)/+layout.svelte`)
#### 1. 佈局系統
- Manages global application structure, navigation (implicitly via SvelteKit routing), and initializes global state.
  管理全局應用程序結構、導航 (通過SvelteKit路由隱式實現) 並初始化全局狀態。
- `AppSidebar.svelte` for Electron app navigation.
  `AppSidebar.svelte` 用於Electron應用導航。

#### 2. Authentication System (`src/lib/apis/auths.ts`, `src/routes/auth/`)
#### 2. 認證系統
- API calls for login, registration, session management.
  用於登錄、註冊、會話管理的API調用。
- UI components for login/registration forms in `src/routes/auth/`.
  `src/routes/auth/` 中的登錄/註冊表單UI組件。

#### 3. Chat Interface (`src/lib/components/chat/Chat.svelte`, rendered in `src/routes/(app)/+page.svelte`)
#### 3. 聊天界面
- Core component for displaying chat messages, handling input, and interacting with AI models.
  用於顯示聊天消息、處理輸入以及與AI模型交互的核心組件。
- Sub-components like `ChatMessage.svelte`, `ChatInput.svelte`, `CodeBlock.svelte`, `FileUpload.svelte`, `MarkdownRenderer.svelte`.
  子組件如 `ChatMessage.svelte`、`ChatInput.svelte`、`CodeBlock.svelte`、`FileUpload.svelte`、`MarkdownRenderer.svelte`。

## Technical Implementation
## 技術實現

### State Management (`src/lib/stores/index.ts`)
### 狀態管理
- Centralized Svelte stores are defined in `src/lib/stores/index.ts` using `writable()`.
  集中的Svelte存儲在 `src/lib/stores/index.ts` 中使用 `writable()` 定義。
- Key stores include `user`, `config`, `settings`, `theme`, `chats`, `models`, `socket`, and various UI state flags.
  關鍵存儲包括 `user`、`config`、`settings`、`theme`、`chats`、`models`、`socket` 以及各種UI狀態標誌。
- Types for store values (e.g., `SessionUser`, `Config`, `Settings`, `Model`) are also defined in this file.
  存儲值的類型 (例如 `SessionUser`, `Config`, `Settings`, `Model`) 也在此文件中定義。
- The PRD's `createSessionStore` for localStorage persistence is a common pattern but not directly seen in `index.ts`; persistence might be handled within components or specific store subscriptions if needed.
  PRD中用於localStorage持久化的 `createSessionStore` 是一個常見模式，但在 `index.ts` 中未直接看到；如果需要，持久化可能在組件內或特定的存儲訂閱中處理。

### WebSocket Integration (`src/routes/+layout.svelte`)
### WebSocket集成
- Socket.IO client is initialized and managed in the root layout.
  Socket.IO客戶端在根佈局中初始化和管理。
- Event handlers (`chatEventHandler`, `channelEventHandler`) process real-time messages and updates.
  事件處理程序 (`chatEventHandler`, `channelEventHandler`) 處理實時消息和更新。
- The `socket` store holds the client instance.
  `socket` 存儲保存客戶端實例。

### Pyodide Worker System (`src/lib/workers/pyodide.worker.ts`, `src/routes/+layout.svelte`)
### Pyodide Worker系統
- A dedicated web worker (`pyodide.worker.ts`) runs Python code.
  一個專用的Web Worker (`pyodide.worker.ts`) 運行Python代碼。
- The `executePythonAsWorker` function in `+layout.svelte` communicates with this worker.
  `+layout.svelte` 中的 `executePythonAsWorker` 函數與此Worker通信。

### PWA Features & Theming
### PWA特性和主題
- `src/app.html` includes a link to `manifest.json` for PWA capabilities.
  `src/app.html` 包含指向 `manifest.json` 的鏈接以實現PWA功能。
- Inline scripts in `src/app.html` handle early theme application (dark, light, system, custom themes like 'oled-dark', 'her') to prevent FOUC.
  `src/app.html` 中的內聯腳本處理早期主題應用 (深色、淺色、系統、自定義主題如 'oled-dark', 'her') 以防止FOUC。
- The `theme` store tracks the current theme, and `Toaster` components adapt their appearance.
  `theme` 存儲跟踪當前主題，`Toaster` 組件會適應其外觀。

### Security Considerations (Frontend Perspective)
### 安全考慮 (前端視角)
- Relies on backend for primary authentication and authorization.
  主要依賴後端進行認證和授權。
- Token-based session management (`localStorage.token`).
  基於令牌的會話管理 (`localStorage.token`)。
- Token expiry check implemented in `src/routes/+layout.svelte`.
  令牌過期檢查在 `src/routes/+layout.svelte` 中實現。
- DOMPurify is a dependency, likely used for sanitizing HTML content.
  DOMPurify 是一個依賴項，可能用於淨化HTML內容。

## Performance Considerations
## 性能考慮
- Static site generation via `@sveltejs/adapter-static`.
  通過 `@sveltejs/adapter-static` 進行靜態站點生成。
- Splash screen in `src/app.html` improves perceived loading performance.
  `src/app.html` 中的啟動畫面改善了感知加載性能。
- Code splitting is inherent with SvelteKit's route-based splitting.
  代碼分割是SvelteKit基於路由的分割所固有的。
- The PRD mentions dynamic imports (`lazyLoad`) and asset preloading; these are good practices but their specific implementation details are not yet fully visible from the files read.
  PRD提到了動態導入 (`lazyLoad`) 和資源預加載；這些是良好實踐，但其具體實現細節尚未從已讀文件中完全可見。

## Error Handling
## 錯誤處理
- SvelteKit provides default error pages (`+error.svelte`).
  SvelteKit提供默認錯誤頁面 (`+error.svelte`)。
- `svelte-sonner` is used for toast notifications, which can display errors.
  `svelte-sonner` 用於toast通知，可以顯示錯誤。
- API call error handling is typically done using try/catch blocks and updating UI accordingly (e.g., showing toasts).
  API調用錯誤處理通常使用try/catch塊並相應更新UI (例如顯示toast)。
