# 產品需求文件：本地客戶端工具伺服器整合

## 1. 簡介

本文件概述了 Open WebUI 的一項新功能需求，該功能允許使用者直接從其網頁瀏覽器整合並呼叫運行在其本機上的「工具伺服器」。這與現有的所有工具伺服器呼叫都透過 Open WebUI 後端代理的機制不同。此功能旨在讓本地工具的探索、新增與使用更加便利，並將其整合至現有的聊天工具管理流程中。

**目標：** 讓使用者能夠在其 Open WebUI 聊天介面中無縫地探索、新增並利用本地工具（例如，自訂腳本、本地 AI 模型、特定硬體的公用程式）。這些工具的呼叫將由前端發起至 `localhost` 端點，並使用 MCP 的 HTTP 呼叫方法。本地 MCP 伺服器可使用如 FastMCP 等函式庫開發。新增的本地工具將與現有工具一同顯示在聊天介面的工具清單中，並可由使用者自由啟用或停用。

## 2. 現行系統概覽（後端呼叫的工具伺服器）

- **設定：** 定義於 `TOOL_SERVER_CONNECTIONS`（環境變數或資料庫）。
- **探索：** 後端從設定的遠端工具伺服器獲取 OpenAPI 規格（`backend/open_webui/utils/tools.py` 中的 `get_tool_servers_data`）。
- **執行：** 後端 Python（`backend/open_webui/utils/tools.py` 中的 `execute_tool_server`）使用 `aiohttp` 向遠端工具伺服器發出 HTTP 請求。
- **安全性：** API 金鑰和敏感設定由後端管理。
- **CORS：** 由後端作為代理處理。

## 3. 提案功能：本地客戶端工具伺服器呼叫（MCP via HTTP）

### 3.1. 概念

使用者可以透過手動設定或利用新的探索機制，讓 Open WebUI 識別運行在其個人電腦上的 MCP 工具伺服器（例如，位於 `http://localhost:8000`）。一旦本地工具被新增至系統，當聊天互動需要此類工具時，Open WebUI 前端 JavaScript 將直接：
1.  與本地工具伺服器的 **MCP (Model Context Protocol) SSE (Server-Sent Events) 端點**（例如 `http://localhost:8000/sse`，若使用 FastMCP 並設定 `transport="sse"`，此為預設 SSE 連線路徑，前端將透過 **HTTP GET** 請求與此端點進行 MCP `initialize` 握手）以獲取伺服器提供的能力清單 (capabilities)、其他元數據以及後續訊息傳輸所需的特定路徑 (`messagePath`)。此步驟在探索階段時執行。
2.  解析從 `initialize` 回應中獲得的**能力 (capabilities)**、其參數、**HTTP 呼叫細節**（如 `invocation` 物件中 `type: 'http'` 所定義）以及 `messagePath`。
3.  根據解析出的能力呼叫細節和 `messagePath`，建構並向本地工具伺服器的 `messagePath` 端點（例如 `http://localhost:8000/messages/`，如果伺服器使用預設值且 `mcpBaseUrl` 為 `http://localhost:8000`）發送標準 **HTTP POST** 請求（`fetch` API）。
4.  接收 HTTP 回應並將其整合回聊天流程中。
新增的本地工具將與其他工具一同顯示在「Tool ICON 下的清單」，使用者可以方便地啟用或停用它們。若本地 MCP 伺服器的能力 (capabilities) 發生變更，使用者可以透過重新整理 Open WebUI 網頁來觸發前端重新進行探索，以獲取並更新本地工具的能力清單。

### 3.2. 使用者故事

作為一名使用者，我希望能夠輕鬆地將運行在我的 `localhost` 上的 MCP 工具伺服器（例如，一個使用 FastMCP 或其他 MCP 函式庫開發的 Python 腳本，並提供 HTTP 介面）整合到 Open WebUI 中。我希望能有一個選項可以掃描我本機上常見的埠號以自動探索這些服務，或者手動輸入其 MCP 端點。一旦新增，這些本地工具應該出現在聊天介面的可用工具清單中，我可以像選擇其他工具一樣選擇啟用它們。啟用後，Open WebUI 應能根據 MCP 協議直接從我的瀏覽器使用標準 HTTP 請求呼叫其功能，讓我能夠使用我的本地自訂工具，而無需使其可公開存取或在 Open WebUI 後端伺服器中進行複雜設定。本地伺服器將負責正確的 CORS 設定。

### 3.3. 關鍵需求與考量

#### 3.3.1. 使用者端的本地 MCP 伺服器 (基於 HTTP)
- **必須運行一個 HTTP 伺服器，並在特定端點上提供 MCP **SSE (Server-Sent Events)** 服務** (例如，若使用 FastMCP 執行 `mcp.run(transport="sse")`，預設的 SSE 連線端點為 `/sse`，客戶端會對此路徑發起 **HTTP GET** 請求進行初始化。伺服器會在 SSE 握手期間提供後續執行請求所需的路徑 (`messagePath`)，客戶端將對此 `messagePath` 發起 **HTTP POST** 請求來執行工具)。
- **必須實現 MCP 協議**，能夠回應前端的 `initialize` 請求，並在其回應中描述其能力 (capabilities) 以及如何透過 **HTTP（如 `capability.invocation` 物件中 `type: 'http'` 所定義）** 呼叫它們。這包括方法、URL 模板和參數對應。
- **至關重要的一點是，必須正確設定 CORS (Cross-Origin Resource Sharing) 標頭。** 這是確保瀏覽器前端能成功呼叫本地伺服器的最關鍵步驟。
    - `Access-Control-Allow-Origin`: 必須包含 Open WebUI 前端的來源 (例如，如果 Open WebUI 在本地運行於 `http://localhost:3000`，則為該地址，或者是其部署的網域)。
    - `Access-Control-Allow-Methods`: 必須包含必要的 HTTP 方法 (例如，`GET`, `POST`, `OPTIONS`)。
    - `Access-Control-Allow-Headers`: 必須包含必要的標頭 (例如，`Content-Type`, 以及 MCP 協議可能需要的其他標頭)。
- **HTTPS/混合內容：** 如果 Open WebUI 透過 HTTPS 提供服務，本地工具伺服器最好也透過 HTTPS 提供服務，以避免混合內容問題。自我簽署憑證可能需要瀏覽器信任。
- **驗證：** 假設對 `localhost` 的呼叫驗證需求極簡或無。

#### 3.3.2. Open WebUI 前端變更
- **前端工具執行邏輯 (新服務/模組)：**
    - **MCP 初始化與能力探索**：向使用者設定的本地 MCP 伺服器端點發送 MCP `initialize` 請求。解析回應以獲取伺服器提供的 `capabilities` 陣列、每個能力的 `id`、`parameters` (JSON Schema)，以及其 `invocation` 物件 (特別是 `type: 'http'`，詳細說明 HTTP 方法、URL 模板，以及參數如何對應到請求的查詢/路徑/主體)。
    - 根據**解析後的 MCP 能力的 `http` `invocation` 細節**和所需參數，動態建構並發送 HTTP 請求 (`fetch` API) 到本地工具伺服器。
    - 強健地處理回應和錯誤（網路錯誤、CORS 錯誤、HTTP 錯誤、MCP 協議錯誤）。
- **工具分派邏輯：**
    - 當需要呼叫工具時，前端必須檢查其是否為 `localClientCall` 類型。
    - 如果是，則使用新的前端執行邏輯（包括 MCP 初始化和工具呼叫）。
    - 如果否，則使用現有機制。
- **使用者介面/體驗 (UI/UX)：**
    - **本地工具自動探索與新增 (單一預設端點)：**
        - Open WebUI 前端將在**每次應用程式載入時**自動嘗試連接至單一預設的本地 MCP 伺服器端點：`http://localhost:8000/sse` (此預設端點 URL 定義於 `src/lib/constants.ts` 中的 `DEFAULT_LOCAL_MCP_SSE_ENDPOINT` 常數)。此邏輯主要實作於 `src/routes/(app)/+layout.svelte` 的 `onMount` 生命週期鉤子中，透過呼叫 `discoverDefaultLocalMcpServer` 函數來完成。
        - 如果連接成功並通過 MCP `initialize` 握手獲取到有效的工具能力，系統將更新 `localStorage` 中對應的工具資訊（包括能力清單）。這些工具將被視為可用的本地工具。
        - 此機制確保了每次載入應用程式時，本地工具的狀態和能力都與本地伺服器的最新狀態同步（類似於透過重新整理網頁更新能力）。
        - 系統不會掃描其他埠號或路徑，也不提供手動輸入其他本地 MCP 伺服器 URL 的介面。
        - 顯示掃描結果（針對此單一端點的嘗試結果），若成功則列出其提供的工具並更新存儲。
    - **統一的工具列表顯示與互動 (於聊天介面):**
        - **位置:** 在聊天輸入框附近或與模型選擇器關聯的區域，通常透過一個「工具圖示 (Tool ICON)」觸發展開一個下拉清單或彈出式選單。此列表的實現主要位於 `src/lib/components/chat/ToolServersModal.svelte` 元件中。
        - **內容:** 此列表將統一展示所有使用者已新增並可用的工具（資料來源於 `allAvailableTools` 衍生 store，該 store 結合了後端工具和 `localMcpTools` store 中的本地工具），包括：
            - 後端代理的外部工具伺服器提供的工具。
            - 使用者新增的本地 MCP 工具（透過自動探索或未來可能的手動設定新增）。
        - **顯示資訊:** 每個工具條目應至少清晰顯示工具的名稱。`ToolServersModal.svelte` 中會為本地工具加入一個文字標籤（"Local"）來區分本地工具與遠端工具。
        - **互動機制:**
            - 使用者可以透過 `ToolServersModal.svelte` 中的勾選框 (checkbox) 為每個工具進行獨立的啟用或停用操作。此操作決定了哪些工具將參與到當前的聊天對話中。
            - 工具的選擇狀態（啟用/停用）應在介面上清晰反映。
            - 此選擇狀態與當前聊天會話的上下文相關聯，其狀態管理涉及 `src/lib/stores/index.ts` 中的 `localMcpTools` store (用於本地工具的啟用狀態持久化) 和傳遞給 Modal 的 `selectedToolIds` prop。
        - **工具列表互動機制更新：** 工具列表中的啟用/停用勾選框將替換為開關按鈕 (switch button)。這些開關按鈕將預設為啟用狀態，以反映工具預設為可用的需求。使用者可以透過切換按鈕來停用特定工具。
        - **即時性與響應性:** 當使用者在應用程式設定中新增、移除或修改工具組態後，聊天介面中呈現的此工具列表應能動態更新以反映最新狀態（例如，即時更新或在下一次聊天會話載入時更新）。
    - 清晰標示本地工具呼叫。
    - 針對本地呼叫失敗的特定錯誤訊息（例如，「無法連線至本地伺服器」、「本地伺服器 CORS 問題：請檢查您的本地伺服器 CORS 設定」、「MCP 初始化失敗或無效的能力清單」）。
    - 針對探索機制的錯誤訊息（例如，「掃描超時」、「在指定埠號上未找到 MCP 服務」）。

#### 3.3.3. Open WebUI 後端變更 (最小幅度)
- 主要用於可選的本地工具設定持久化。這些本地工具的核心執行將**不**透過後端。

### 3.4. 優點
- **增強的使用者自訂性。**
- **低延遲。**
- **潛在的隱私優勢。**
- **離線能力。**
- **與 MCP 標準化。**

### 3.5. 挑戰
- **CORS 設定：** 這仍然是**使用者面臨的主要技術障礙**。本地 MCP 伺服器**必須**正確設定以回應適當的 CORS 標頭，允許來自 Open WebUI 前端的請求。為使用者提供清晰的指引和範例至關重要，特別是針對使用 FastMCP 等函式庫時的 CORS 設定。
- **MCP 的採用與成熟度。**
- **本地伺服器的安全性。**
- **前端複雜性** (MCP 協議處理、`initialize` 流程、HTTP 請求建構)。
- **錯誤處理。**
- **HTTPS/混合內容。**

## 4. 前端實作計畫 (預估檔案變更)

基於 Open WebUI 典型的 SvelteKit 結構 (`src/` 目錄)：


**4.3. 狀態管理 (主要實作於 `src/lib/stores/index.ts`)**
- 在 `src/lib/stores/index.ts` 中：
    - 新增 `localMcpTools: Writable<LocalClientToolServerConfig[]>` store，用於儲存本地 MCP 伺服器的設定（包括從 `initialize` 請求中獲取的能力清單 `discoveredCapabilities`、`serverInfo`、`messagePath` 等），並將其持久化到瀏覽器的 `localStorage` (key: `open-webui_local-mcp-tools`)。
    - 現有的 `tools: Writable<Tool[] | null>` store 用於儲存後端提供的工具。
    - `Tool` 型別 (定義於 `src/lib/types/tools.ts`) 已擴展，增加了 `isLocalClientCall?: boolean`、`localMcpServerUrl?: string` 和 `capabilities?: McpCapability[]` 欄位以支援本地工具。
    - `availableTools` store (`writable<Tool[]>([])`) 作為一個整合的工具列表，其內容會由 `src/lib/components/chat/ToolServersModal.svelte` 中的衍生 store `allAvailableTools` 動態產生，結合後端工具和啟用的本地 MCP 工具。


**4.4. 新增核心前端邏輯 (主要實作於 `src/lib/utils/localClientToolExecutor.ts`)**
- 在 `src/lib/utils/localClientToolExecutor.ts` 中定義並導出以下核心函數：
    - `initializeAndGetCapabilities(mcpSseEndpointUrl: string): Promise<McpSseInitializeResult>`: 向指定的 MCP SSE 端點 URL (例如 `http://localhost:{port}/sse`，其中 `/sse` 路徑來自 `MCP_DEFAULT_PATH` 常數) 發送初始 **HTTP GET** 請求 (透過 `EventSource`，內含 `MCP_SSE_INIT_TIMEOUT_MS` 定義的 5 秒握手超時)。解析回應，提取 `capabilities`、`serverInfo` 以及 `messagePath`。
    - `executeLocalClientTool(params: any, capabilityInvocationDetails: McpHttpInvocation, mcpBaseUrl: string, messagePath: string): Promise<any>`: (簽名已更新) 根據已獲取的 MCP 能力的 `http` `invocation` 細節和 `messagePath`，建構並向本地工具伺服器（使用 `mcpBaseUrl` 和 `messagePath` 組成目標 URL）發送標準 **HTTP POST** 請求 (`fetch` API)。
    - `discoverLocalMcpServers(ports: number[], mcpSsePath: string = '/sse'): Promise<DiscoveredServer[]>`: (參數 `mcpSsePath` 預設值為 `/sse`，來自 `MCP_DEFAULT_PATH`) 嘗試在指定的本地埠號列表上的 `mcpSsePath` 路徑進行 MCP `initialize` **HTTP GET** 握手 (透過呼叫 `initializeAndGetCapabilities`)，並返回成功回應的伺服器及其能力摘要。
    - 掃描超時時間: 每個埠號的探索嘗試（呼叫 `initializeAndGetCapabilities`）包含一個 5 秒的 SSE 初始化握手超時 (`MCP_SSE_INIT_TIMEOUT_MS`)。PRD 原提及的 10 秒掃描超時 (`DISCOVERY_TIMEOUT_MS` 在程式碼中定義但未直接用於 `discoverLocalMcpServers` 的整體超時控制) 可能是指對單一埠號整體探索嘗試的期望時間上限。


**4.5. 修改聊天邏輯與使用者介面**
- **本地工具自動探索 (主要實作於 `src/routes/(app)/+layout.svelte`)**:
    - 在 `onMount` 生命週期鉤子中呼叫 `discoverDefaultLocalMcpServer` 函數。
    - 此函數使用 `src/lib/utils/localClientToolExecutor.ts` 中的 `initializeAndGetCapabilities` 嘗試連接預設本地 MCP 端點 (`DEFAULT_LOCAL_MCP_SSE_ENDPOINT`，定義於 `src/lib/constants.ts`)。
    - 成功後，更新 `src/lib/stores/index.ts` 中的 `localMcpTools` store。
- **工具清單整合與啟用/停用 (主要實作於 `src/lib/components/chat/ToolServersModal.svelte`)**:
    - **資料獲取:** 從 `src/lib/stores/index.ts` 獲取 `tools` (後端工具) 和 `localMcpTools` (本地工具設定)。透過 Svelte 的 `derived` store (`allAvailableTools`) 將兩者結合成統一的工具列表。
    - **列表渲染與互動:**
        - 動態渲染 `allAvailableTools` 列表，為每個工具提供一個勾選框 (checkbox)，允許使用者為當前聊天會話啟用或停用該工具。
        - 為本地工具在列表中添加視覺提示（"Local" 標籤）。
    - **狀態管理:** 使用者對工具的啟用/停用選擇會更新傳入的 `selectedToolIds` prop，並間接影響 `localMcpTools` store 中對應工具的 `enabled` 狀態（此部分邏輯可能在父元件或更高層次處理，Modal 本身主要反映和修改 `selectedToolIds`）。
- **工具分派邏輯 (預期在例如 `src/lib/components/chat/Chat.svelte` 或相關的訊息處理邏輯中修改):**
    - 當觸發工具呼叫時，檢查 `tool.isLocalClientCall` 標記。
    - 如果為 `true`，則使用 `src/lib/utils/localClientToolExecutor.ts` 中的 `executeLocalClientTool` 執行前端呼叫。
    - 否則，繼續使用後端介導的呼叫。
- **UI 回饋：** 顯示本地工具呼叫的載入狀態和特定錯誤訊息 (相關 UI 元件如 `src/lib/components/chat/Messages/ResponseMessage/ToolCalls.svelte` 和 `src/lib/components/chat/ToolCall.svelte` 可能會被複用或調整以顯示本地工具的呼叫狀態和結果)。
- `src/lib/components/chat/ChatMessage.svelte`: 可能需要更新以正確顯示包含本地工具呼叫或其結果的訊息。

**4.6. 型別定義 (主要實作於 `src/lib/types/tools.ts` 並由 `src/lib/types/index.ts` 導出)**
- 在 `src/lib/types/tools.ts` 中定義：
    - `LocalClientToolServerConfig`: 用於儲存本地 MCP 伺服器的設定，包括 `mcpEndpointUrl`, `name`, `enabled`, `discoveredCapabilities`, `serverInfo`, `messagePath`。
    - `McpServerInfo`, `McpCapability`, `McpHttpInvocation`, `McpSseInitializeResult`, `DiscoveredServer`: MCP 通訊協定相關的核心型別。
    - 擴展現有的 `Tool` 型別，增加 `isLocalClientCall?: boolean`, `localMcpServerUrl?: string`, `capabilities?: McpCapability[]` 欄位。
- `src/lib/types/index.ts` 使用 `export * from './tools';` 導出上述型別。

**4.7. 後端 API (可選 - 用於設定持久化)**
- 如先前定義。

## 5. 安全性考量

- **CORS 指引：** 提供**詳盡且清晰的文件，可包含針對常用語言/框架 (例如使用 FastMCP 的 Python/FastAPI, 或 Node.js/Express) 的範例**，說明如何在本地 MCP 伺服器上安全地設定 CORS。強調將 `Access-Control-Allow-Origin` 限制為 Open WebUI 實例的來源。
- **前端不處理敏感資料。**
- **本地伺服器的責任。**

## 6. 未來考量
- **提供一個簡單、文件完善的 MCP 伺服器範例 (例如，使用 Python FastMCP 搭配 **`SSETransport`**，執行 `mcp.run(transport="sse")`，該範例應能正確處理前端發起的 `/sse` **HTTP GET** 初始化請求和伺服器指定的 `messagePath` (預設 `/messages/`) **HTTP POST** 執行請求)，其中包含正確的 CORS 設定**，供使用者參考調整。
- 針對本地連線，特別是 CORS 問題和 MCP 協議交互，提供更完善的錯誤報告和偵錯工具。
- 研究是否可以利用現有的 JavaScript/TypeScript MCP 客客戶端函式庫來簡化前端的 `initialize` 和請求/回應處理。
- **支援自訂本地 MCP 端點：** 考慮未來允許使用者手動設定或掃描多個/非預設的本地 MCP 伺服器端點，以支援更廣泛的本地工具部署情境。
