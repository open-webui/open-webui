# Open WebUI 工具的註冊、發現與調用流程詳解

本文旨在詳細說明 Open WebUI 現有程式碼中，關於工具（Tools）的註冊（Registration）、發現（Discovery）與調用（Invocation/Execution）的完整流程。此流程涉及前端（Svelte）、後端（FastAPI/Python）以及可能的外部工具服務，**並特別涵蓋了新增的本地客戶端 MCP 工具伺服器整合機制。**

## I. 工具註冊 (Tool Registration)

工具的註冊主要有兩種方式：

1.  透過靜態環境變數配置 (`TOOL_SERVER_CONNECTIONS`)
2.  透過管理後台在資料庫中動態註冊
3.  **透過前端自動探索本地 MCP 伺服器 (新增)**

### A. 透過靜態配置 (`TOOL_SERVER_CONNECTIONS`)

1.  **設定：**
    管理員在 Open WebUI 的環境變數（例如 `.env` 文件或 Docker Compose 設定）中定義 `TOOL_SERVER_CONNECTIONS`。這通常是一個 JSON 字串陣列，每個物件包含工具服務的 URL、可能的 API 金鑰以及其他配置。
    範例：
    ```json
    [{"url": "http://my-static-tool:8000/openapi.json", "headers": {"X-API-KEY": "secret"}}]
    ```

2.  **後端啟動時加載配置：**
    Open WebUI 後端服務啟動時，會讀取這些環境變數並將 `TOOL_SERVER_CONNECTIONS` 解析到應用程式的配置中（例如 `request.app.state.config.TOOL_SERVER_CONNECTIONS`）。其實際處理見下方的「工具發現」階段。

### B. 透過管理後台動態註冊 (存入資料庫)

1.  **前端界面 (Admin Panel)：**
    管理員或有權限的使用者進入 Open WebUI 的管理後台，找到「工具連接」(Tool Connections) 或類似的管理界面。

2.  **填寫表單：**
    使用者填寫工具的相關資訊，主要包括：
    *   **名稱 (Name)：** 工具的顯示名稱（可選，若 Schema 中有 `info.title` 且此欄位為空，則會自動填充）。
    *   **Schema (對應後端的 `content` 欄位)：** 此處可填寫：
        *   指向該工具 `openapi.json` 的 **URL** (例如 `http://my-db-tool:8001/openapi.json`)。
        *   或者，直接貼上 **OpenAPI 規格的完整 JSON/YAML 內容**。
    *   **描述 (Description, 可能對應後端的 `meta.description`)：** 工具的描述（可選，若 Schema 中有 `info.description` 且此欄位為空，則會自動填充）。
    *   **標頭 (Headers, 可能對應後端的 `meta.headers` 或 `valves`)：** 若調用此工具需要特定的 HTTP 標頭（例如 API 金鑰）。
    *   **可見性/權限控制 (Access Control)：** 設定工具是公開的、私有的，還是與特定使用者/群組共享。

3.  **前端提交：**
    使用者提交表單後，前端會將這些數據發送到後端的工具創建 API 端點（例如 `POST /api/tools/create`）。請求的 body 通常是一個 JSON 物件。

4.  **後端處理創建請求 (例如 `POST /api/tools/create` 在 `routers/tools.py`)：**
    *   後端接收表單數據。
    *   **核心處理 `content` (Schema) 欄位：**
        *   若 `content` 為 URL：後端**嘗試從此 URL 獲取 `openapi.json`**。若成功，解析規格並提取 `info.title` 和 `info.description` 來填充工具記錄的 `name` 和 `meta.description` 欄位（通常在使用者未手動提供時）。若獲取或解析失敗，可能報錯或允許創建但相關欄位不完整。
        *   若 `content` 為直接貼上的 OpenAPI 規格內容：後端直接解析此內容，同樣提取 `info.title` 和 `info.description`。
    *   **儲存到資料庫：**
        *   後端將處理後的工具資訊（`id`, `user_id`, `name`, 原始的 `content` (URL 或規格內容), `meta` (含描述、標頭等), `access_control` 等）儲存到資料庫的 `tool` 表中。
        *   資料庫的 `content` 欄位通常儲存使用者最初提供的 URL 或規格內容。`name` 和 `meta` 則儲存最終確定的值。

### C. 透過前端自動探索本地 MCP 伺服器 (新增)

1.  **自動探索：**
    Open WebUI 前端在**每次應用程式載入時**，會自動嘗試連接至單一預設的本地 MCP 伺服器端點：`http://localhost:8000/sse` (此預設端點 URL 定義於 `src/lib/constants.ts` 中的 `DEFAULT_LOCAL_MCP_SSE_ENDPOINT` 常數)。此邏輯主要實作於 `src/routes/(app)/+layout.svelte` 的 `onMount` 生命週期鉤子中，透過呼叫 `discoverDefaultLocalMcpServer` 函數來完成。

2.  **MCP 初始化與能力獲取：**
    前端向該端點發送 MCP `initialize` 請求 (透過 `EventSource`，內含 `MCP_SSE_INIT_TIMEOUT_MS` 定義的 5 秒握手超時)。若連接成功並通過 MCP `initialize` 握手獲取到有效的工具能力，系統將解析回應，提取 `capabilities`、`serverInfo` 以及後續訊息傳輸所需的 `messagePath`。

3.  **本地儲存與啟用：**
    成功探索到的本地工具資訊（包括能力清單）將更新 `localStorage` 中對應的工具資訊 (key: `open-webui_local-mcp-tools`)。這些工具將被視為可用的本地工具，並預設為啟用狀態。

4.  **狀態同步：**
    此機制確保了每次載入應用程式時，本地工具的狀態和能力都與本地伺服器的最新狀態同步（類似於透過重新整理網頁更新能力）。

## II. 工具發現 (Tool Discovery)

指 Open WebUI 前端如何獲取可用工具列表以在聊天界面中顯示。

1.  **前端請求：**
    使用者打開聊天界面時，前端向後端發起 `GET /api/tools/` 請求，以獲取後端管理的工具列表。同時，前端也會執行本地 MCP 伺服器的自動探索。

2.  **後端處理 `/api/tools/` 請求 (在 `routers/tools.py` 的 `get_tools` 函數)：**
    *   **a. 處理靜態配置的工具：**
        *   檢查 `request.app.state.TOOL_SERVERS` 是否已快取。
        *   若未快取（通常是伺服器啟動後的首次請求）：調用 `get_tool_servers_data`，此函數會遍歷 `TOOL_SERVER_CONNECTIONS` 中的 URL，**為每個 URL 發起 HTTP GET 請求以獲取其 `openapi.json`**，解析後儲存在 `request.app.state.TOOL_SERVERS` 中（**實現了快取，直到伺服器重啟**）。
        *   從 `request.app.state.TOOL_SERVERS` 中提取已處理的靜態工具數據。
    *   **b. 處理資料庫註冊的工具：**
        *   調用 `Tools.get_tools()` (在 `models/tools.py`)。
        *   `Tools.get_tools()` **每次都會查詢資料庫的 `tool` 表**，獲取所有工具記錄。這些記錄已包含註冊階段處理好的 `name`, `content`, `meta` 等。
    *   **c. 合併與轉換：**
        *   後端將來自靜態配置和資料庫的工具合併，並轉換為 `ToolUserResponse` 模型。
        *   對於 `content` 是 URL 的資料庫工具，此階段後端通常**不會**再次從 URL 獲取完整規格。
    *   **d. 權限過濾：**
        *   非管理員使用者將只看到其擁有或有權限訪問的工具。管理員可見所有工具。
    *   **e. 返回列表：**
        後端將最終過濾後的工具列表 (`list[ToolUserResponse]`) 作為 JSON 回應給前端。

3.  **前端顯示與整合：**
    *   前端接收後端返回的工具列表。
    *   同時，前端會從 `localMcpTools` store (持久化在 `localStorage`) 中獲取已探索到的本地 MCP 工具列表。
    *   透過 Svelte 的 `derived` store (`allAvailableTools`，主要在 `src/lib/components/chat/ToolServersModal.svelte` 中使用)，將後端工具和本地 MCP 工具結合成統一的工具列表。
    *   此列表在聊天界面中顯示，通常透過一個「工具圖示 (Tool ICON)」觸發展開的下拉清單或彈出式選單。本地工具會被標記為 "Local"。
    *   使用者可以透過勾選框 (checkbox) 或開關按鈕 (switch button) 為每個工具進行獨立的啟用或停用操作，此選擇狀態與當前聊天會話的上下文相關聯。

## III. 工具調用 (Tool Invocation/Execution)

指當 LLM 決定使用某工具時，實際執行該工具的流程。

1.  **LLM 決定使用工具：**
    *   使用者輸入訊息。前端將訊息和可用工具的簡要描述發送給 LLM（透過後端代理）。
    *   LLM 分析後，若決定使用工具，會回應一個結構化的「函數調用」請求，指明工具 `id` (或 `name`/`operationId`) 及參數。

2.  **前端處理 LLM 的函數調用請求：**
    *   後端將 LLM 的函數調用請求轉發給前端。
    *   前端 JavaScript 根據工具 `id` 找到對應的工具定義。

3.  **執行工具 (區分 OpenAPI "Tool Server" 和本地 MCP 伺服器)：**

    *   **a. OpenAPI "Tool Server" (前端執行，透過後端代理或直接呼叫外部服務)：**
        *   前端調用 `executeToolServer` 函數 (在 `src/lib/apis/index.ts`)。
        *   **獲取完整的 OpenAPI 規格：** 若之前 `/api/tools/` 返回的 `content` 欄位是 URL，則前端**此時從該 URL 發起 HTTP GET 請求以獲取完整的 `openapi.json` 內容**（按需發生）。若 `content` 已是規格內容，則直接使用。
        *   **構造請求：** 前端根據 LLM 提供的 `operationId`、參數及解析後的 OpenAPI 規格，構造實際的 HTTP 請求（URL、方法、body、headers 等）。URL 基於 OpenAPI 規格中的 `servers` 陣列。
        *   **前端發起 API 呼叫：** 前端 JavaScript 使用 `fetch` API **直接向工具服務的實際端點發起 HTTP 請求**。
        *   **CORS 和網路可達性：** 此時，使用者瀏覽器必須能直接訪問工具服務 URL，且工具服務需配置正確的 CORS 標頭。
        *   **接收回應與處理錯誤：** 工具服務處理請求並返回回應給前端。前端需處理 API 呼叫失敗的情況。

    *   **b. 本地客戶端 MCP 伺服器 (前端直接執行)：**
        *   當觸發工具呼叫時，前端會檢查工具定義中的 `isLocalClientCall` 標記。
        *   如果為 `true`，則使用 `src/lib/utils/localClientToolExecutor.ts` 中的 `executeLocalClientTool` 函數執行前端呼叫。
        *   `executeLocalClientTool` 函數根據已獲取的 MCP 能力的 `http` `invocation` 細節和 `messagePath`，建構並向本地工具伺服器（使用 `mcpBaseUrl` 和 `messagePath` 組成目標 URL）發送標準 **HTTP POST** 請求 (`fetch` API)。
        *   **CORS 和網路可達性：** 本地 MCP 伺服器**必須**正確設定 CORS (Cross-Origin Resource Sharing) 標頭，允許來自 Open WebUI 前端的請求。這是確保瀏覽器前端能成功呼叫本地伺服器的最關鍵步驟。
        *   **接收回應與處理錯誤：** 本地工具伺服器處理請求並返回回應給前端。前端需強健地處理回應和錯誤（網路錯誤、CORS 錯誤、HTTP 錯誤、MCP 協議錯誤），並顯示本地工具呼叫的載入狀態和特定錯誤訊息。

4.  **將工具結果返回給 LLM：**
    *   前端將工具的成功回應（或錯誤信息）打包，發送回後端，後端再發送給 LLM。

5.  **LLM 生成最終回覆：**
    *   LLM 基於工具結果生成最終回覆，透過後端傳回前端顯示。

## 總結關鍵點

*   **註冊時：** 後端處理靜態配置和資料庫動態註冊的工具。**前端新增了自動探索本地 MCP 伺服器的機制，並將其資訊儲存在 `localStorage`。**
*   **發現時 (`/api/tools/`)：** 後端快取靜態配置工具的規格，並從資料庫讀取動態註冊工具的記錄。**前端將後端工具和本地 MCP 工具合併，統一顯示在聊天界面中，並為本地工具添加 "Local" 標籤。**
*   **調用時：**
    *   **OpenAPI Tool Server：** 前端負責執行，按需獲取完整 OpenAPI 規格，並直接呼叫工具服務端點，依賴瀏覽器網路可達性和工具服務的 CORS 設定。
    *   **本地客戶端 MCP 伺服器：** **前端直接向本地 MCP 伺服器發送 HTTP POST 請求，執行工具功能。本地伺服器必須正確配置 CORS。**
