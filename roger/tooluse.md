# Open WebUI 工具的註冊、發現與調用流程詳解

本文旨在詳細說明 Open WebUI 現有程式碼中，關於工具（Tools）的註冊（Registration）、發現（Discovery）與調用（Invocation/Execution）的完整流程。此流程涉及前端（Svelte）、後端（FastAPI/Python）以及可能的外部工具服務。

## I. 工具註冊 (Tool Registration)

工具的註冊主要有兩種方式：

1.  透過靜態環境變數配置 (`TOOL_SERVER_CONNECTIONS`)
2.  透過管理後台在資料庫中動態註冊

### A. 透過靜態配置 (`TOOL_SERVER_CONNECTIONS`) - 外部 OpenAPI Tool Servers

1.  **設定：**
    管理員在 Open WebUI 的環境變數（例如 `.env` 文件或 Docker Compose 設定）中定義 `TOOL_SERVER_CONNECTIONS`。這通常是一個 JSON 字串陣列，每個物件包含工具服務的 URL、可能的 API 金鑰以及其他配置。
    範例：
    ```json
    [{"url": "http://my-static-tool:8000/openapi.json", "headers": {"X-API-KEY": "secret"}}]
    ```

2.  **後端啟動時加載配置：**
    Open WebUI 後端服務啟動時，會讀取這些環境變數並將 `TOOL_SERVER_CONNECTIONS` 解析到應用程式的配置中（例如 `request.app.state.config.TOOL_SERVER_CONNECTIONS`）。其實際處理見下方的「工具發現」階段。

### B. 透過管理後台動態註冊 (存入資料庫) - 內部 Python 工具

1.  **前端界面 (Admin Panel)：**
    管理員或有權限的使用者進入 Open WebUI 的管理後台，找到「工具連接」(Tool Connections) 或類似的管理界面。

2.  **填寫表單：**
    使用者填寫工具的相關資訊，主要包括：
    *   **名稱 (Name)：** 工具的顯示名稱（可選，若工具 Python 程式碼中有 `name` 屬性且此欄位為空，則會自動填充）。
    *   **程式碼 (對應後端的 `content` 欄位)：** 此處應貼上工具的 **Python 程式碼**。此程式碼應包含工具的邏輯及必要的元數據（例如透過 `__tool_code__` 變數定義）。
    *   **描述 (Description, 可能對應後端的 `meta.description`)：** 工具的描述（可選，若工具 Python 程式碼中有 `description` 屬性且此欄位為空，則會自動填充）。
    *   **標頭 (Headers, 可能對應後端的 `meta.headers` 或 `valves`)：** 若調用此工具需要特定的 HTTP 標頭（例如 API 金鑰）。
    *   **可見性/權限控制 (Access Control)：** 設定工具是公開的、私有的，還是與特定使用者/群組共享。

3.  **前端提交：**
    使用者提交表單後，前端會將這些數據發送到後端的工具創建 API 端點（`POST /api/tools/create`）。請求的 body 通常是一個 JSON 物件。

4.  **後端處理創建請求 (`POST /api/tools/create` 在 `routers/tools.py`)：**
    *   後端接收表單數據。
    *   **核心處理 `content` (程式碼) 欄位：**
        *   後端會將 `content` 中的 Python 程式碼載入為一個模組。
        *   從載入的模組中提取工具的 `specs` (OpenAPI-like 規格) 和 `meta` (包含 `name` 和 `description` 等元數據，通常來自程式碼中的 `frontmatter` 或特定屬性)。
    *   **儲存到資料庫：**
        *   後端將處理後的工具資訊（`id`, `user_id`, `name`, 原始的 `content` (Python 程式碼), `specs`, `meta` (含描述、標頭等), `access_control` 等）儲存到資料庫的 `tool` 表中。
        *   資料庫的 `content` 欄位儲存使用者提供的 Python 程式碼。`name`, `specs` 和 `meta` 則儲存從程式碼中解析出的值。

## II. 工具發現 (Tool Discovery)

指 Open WebUI 前端如何獲取可用工具列表以在聊天界面中顯示。

1.  **前端請求：**
    使用者打開聊天界面時，前端向後端發起 `GET /api/tools/` 請求。

2.  **後端處理 `/api/tools/` 請求 (在 `routers/tools.py` 的 `get_tools` 函數)：**
    *   **a. 處理靜態配置的工具 (外部 OpenAPI Tool Servers)：**
        *   檢查 `request.app.state.TOOL_SERVERS` 是否已快取。
        *   若未快取（通常是伺服器啟動後的首次請求）：調用 `get_tool_servers_data`，此函數會遍歷 `TOOL_SERVER_CONNECTIONS` 中的 URL，**為每個 URL 發起 HTTP GET 請求以獲取其 `openapi.json`**，解析後儲存在 `request.app.state.TOOL_SERVERS` 中（**實現了快取，直到伺服器重啟**）。
        *   從 `request.app.state.TOOL_SERVERS` 中提取已處理的靜態工具數據。
    *   **b. 處理資料庫註冊的工具 (內部 Python 工具)：**
        *   調用 `Tools.get_tools()` (在 `models/tools.py`)。
        *   `Tools.get_tools()` **每次都會查詢資料庫的 `tool` 表**，獲取所有工具記錄。這些記錄已包含註冊階段處理好的 `name`, `content` (Python 程式碼), `specs`, `meta` 等。
    *   **c. 合併與轉換：**
        *   後端將來自靜態配置和資料庫的工具合併，並轉換為 `ToolUserResponse` 模型。
        *   對於資料庫中的內部 Python 工具，此階段後端直接使用已儲存的 `specs` 和 `meta`，**不會**再次處理其 `content` (Python 程式碼)。
    *   **d. 權限過濾：**
        *   非管理員使用者將只看到其擁有或有權限訪問的工具。管理員可見所有工具。
    *   **e. 返回列表：**
        後端將最終過濾後的工具列表 (`list[ToolUserResponse]`) 作為 JSON 回應給前端。

3.  **前端顯示：**
    前端接收工具列表，使用 `name` 和 `meta.description` 在 UI 中顯示。

## III. 工具調用 (Tool Invocation/Execution)

指當 LLM 決定使用某工具時，實際執行該工具的流程。

1.  **LLM 決定使用工具：**
    *   使用者輸入訊息。前端將訊息和可用工具的簡要描述發送給 LLM（透過後端代理）。
    *   LLM 分析後，若決定使用工具，會回應一個結構化的「函數調用」請求，指明工具 `id` (或 `name`/`operationId`) 及參數。

2.  **後端處理 LLM 的函數調用請求：**
    *   後端接收 LLM 的函數調用請求。
    *   **判斷工具類型：** 後端根據工具 `id` 判斷是外部 OpenAPI Tool Server 還是內部 Python 工具。

### A. 調用外部 OpenAPI Tool Server (前端或後端執行)

外部 OpenAPI 工具的調用可能由前端或後端執行，具體取決於其註冊方式和配置。

1.  **前端執行 (針對部分外部 OpenAPI 工具)：**
    *   後端將 LLM 的函數調用請求轉發給前端。
    *   前端 JavaScript 根據工具 `id` 找到對應的工具定義。
    *   執行工具 (在 `src/lib/apis/index.ts` 的 `executeToolServer` 函數)：
        *   `executeToolServer` 需要工具的完整 OpenAPI 規格 (`serverData.openapi`)。
        *   若之前 `/api/tools/` 返回的 `content` 欄位是 URL，則前端**此時從該 URL 發起 HTTP GET 請求以獲取完整的 `openapi.json` 內容**（按需發生）。
        *   若 `content` 已是規格內容，則直接使用。
        *   前端根據 LLM 提供的 `operationId`、參數及解析後的 OpenAPI 規格，構造實際的 HTTP 請求（URL、方法、body、headers 等）。URL 基於 OpenAPI 規格中的 `servers` 陣列。
        *   前端 JavaScript 使用 `fetch` API **直接向工具服務的實際端點發起 HTTP 請求**。
        *   **CORS 和網路可達性：** 此時，使用者瀏覽器必須能直接訪問工具服務 URL，且工具服務需配置正確的 CORS 標頭。
        *   **接收回應與處理錯誤：** 工具服務處理請求並返回回應給前端。前端需處理 API 呼叫失敗的情況。

2.  **後端執行 (針對靜態配置的外部 OpenAPI 工具)：**
    *   當 LLM 決定調用一個對應於靜態配置 (`TOOL_SERVER_CONNECTIONS`) 的外部 OpenAPI 工具時，後端會接收到此調用請求。
    *   後端會根據工具 `id` (通常以 `server:` 開頭) 識別出這類工具。
    *   後端會調用 `backend/open_webui/utils/tools.py` 中的 `execute_tool_server` 函數。
    *   `execute_tool_server` 函數會從**後端**向外部工具服務的實際端點發起 HTTP 請求，處理通訊、認證和錯誤。
    *   **網路可達性：** 此時，Open WebUI 後端服務必須能直接訪問工具服務 URL。
    *   **接收回應與處理錯誤：** 工具服務處理請求並返回回應給後端。後端需處理 API 呼叫失敗的情況。

### B. 調用內部 Python 工具 (後端執行)

1.  **後端處理 LLM 的函數調用請求：**
    *   後端接收 LLM 的函數調用請求。
    *   後端根據工具 `id` 從 `request.app.state.TOOLS` 中找到對應的 Python 工具模組。
    *   後端直接調用該 Python 模組中定義的函數，並傳入 LLM 提供的參數。
    *   **錯誤處理：** 後端處理 Python 工具執行過程中可能發生的錯誤。

### C. 將工具結果返回給 LLM

*   無論是前端執行的外部工具還是後端執行的內部工具，其結果（或錯誤信息）都會被打包，發送回後端，後端再發送給 LLM。

### D. LLM 生成最終回覆

*   LLM 基於工具結果生成最終回覆，透過後端傳回前端顯示。

## 總結關鍵點

*   **工具類型：** Open WebUI 支援兩種主要工具：
    1.  **外部 OpenAPI Tool Servers：** 透過靜態配置 (`TOOL_SERVER_CONNECTIONS`) 註冊，其 OpenAPI 規格由後端在啟動時快取，並由**前端直接調用**。
    2.  **內部 Python 工具：** 透過管理後台動態註冊，其 Python 程式碼儲存在資料庫中，並由**後端執行**。
*   **註冊時：**
    *   靜態配置工具：後端獲取並快取其 OpenAPI 規格。
    *   動態註冊工具：後端儲存其 Python 程式碼，並從程式碼中解析出 `specs` 和 `meta`。
*   **發現時 (`/api/tools/`)：**
    *   後端合併靜態配置工具（使用快取的 OpenAPI 規格）和資料庫工具（使用已解析的 `specs` 和 `meta`），返回給前端。
*   **調用時：**
    *   **前端負責調用外部 OpenAPI Tool Servers**，直接向其端點發起 HTTP 請求。
    *   **後端負責調用內部 Python 工具**，直接執行其 Python 程式碼。
