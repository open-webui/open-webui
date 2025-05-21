# 產品需求文件：Open WebUI 本地 MCP 工具整合

## 1. 簡介

本文件概述了 Open WebUI 的一項新功能需求，旨在無縫整合並調用運行在使用者本機上的 Model Context Protocol (MCP) 工具伺服器。這將允許使用者利用本地工具（例如，自訂腳本、本地 AI 模型、特定硬體的公用程式），支援多種 HTTP-based 傳輸方式，並與現有的後端代理 OpenAPI 工具的機制協同運作。此功能旨在增強使用者自訂性、降低延遲，並提供潛在的隱私優勢。

## 2. 現行系統概覽

目前 Open WebUI 支援調用外部 OpenAPI 工具伺服器，其執行方式可能由前端或後端負責。
*   **前端執行：** 對於部分外部 OpenAPI 工具，當 LLM 決定使用時，後端會將調用請求轉發給前端，由前端直接向外部工具伺服器發起 HTTP 請求，處理通訊、認證和錯誤，然後將結果返回給後端。
*   **後端執行：** 對於透過靜態配置 (`TOOL_SERVER_CONNECTIONS`) 註冊的外部 OpenAPI 工具，當 LLM 決定使用時，後端會識別出這類工具，並由後端直接向外部工具伺服器發起 HTTP 請求，處理通訊、認證和錯誤，然後將結果返回給 LLM。

## 3. 提案功能：本地客戶端 MCP 工具整合

### 3.1. 概念

本提案的核心概念是將部分工具的執行責任從後端轉移到前端，實現**客戶端直接調用運行在使用者本機上的 MCP 伺服器**。
*   **探索與註冊：** 前端將透過嘗試連接預設埠號和路徑（例如 SSE 為 `http://localhost:8000/sse`，Streamable HTTP 為 `http://localhost:8000/mcp`）來自動探索本地 MCP 伺服器。成功探索後，將解析其 MCP `initialize` 回應，獲取伺服器能力清單，並將這些工具納入前端的可用工具列表。**後續的工具調用將使用 MCP 伺服器在 `initialize` 回應中提供的完整 URL，該 URL 將包含正確的埠號和路徑。**
*   **調用流程：** 當 LLM 決定調用一個工具時，後端會根據前端提供的資訊判斷工具類型：
    *   對於**外部 OpenAPI 工具**，後端將繼續其現有的代理執行機制（透過 `open_webui/utils/tools.py:execute_tool_server`）。
    *   對於**本地 MCP 工具**，後端會將 LLM 的調用指令（包含工具 ID 和參數）**轉發**給前端，而不是自行執行。
*   **前端執行：** 前端接收到後端轉發的本地 MCP 工具調用指令後，將直接與本地 MCP 伺服器通訊（支援 SSE 或 Streamable HTTP 傳輸），執行工具功能。
*   **結果回傳：** 本地工具的執行結果將由前端接收，並回傳給後端，最終由 LLM 生成最終回覆。
*   **配置管理：** 本地工具的探索結果和啟用狀態將主要在前端進行管理和持久化（透過瀏覽器 `localStorage`），後端無需額外支援。

### 3.2. 關鍵需求與考量

#### 3.2.1. 前端變更 (SvelteKit) - 最小化改動策略

1.  **自動探索與註冊 (支援 Streamable HTTP 和 SSE)：**
    *   **新增獨立初始化組件：** 創建一個新的 Svelte 組件（例如 `src/lib/components/layout/LocalMcpInitializer.svelte`），該組件將包含在 `onMount` 生命週期中執行本地 MCP 伺服器自動探索的邏輯。
    *   **輕微修改根佈局：** 在 `src/routes/(app)/+layout.svelte` 中，僅需**導入並使用**這個新的 `LocalMcpInitializer.svelte` 組件，將對核心佈局文件的修改降到最低。請注意，`src/routes/(app)/+layout.svelte` 目前也負責協調對工具伺服器的調用。
    *   **狀態管理：** 在 `src/lib/stores/index.ts` 中新增 `localMcpTools` writable store，用於儲存探索到的本地工具資訊（類型為 `LocalClientToolServerConfig[]`，定義於 `src/lib/types/tools.ts`）。此類型應包含足夠的資訊以供前端調用工具，例如 `id` (工具唯一識別符)、`name` (工具名稱)、`url` (工具服務基礎 URL)、`invocation` (包含 `type` 和 `messagePath` 等調用細節)。
    *   **核心邏輯：** 探索和初始化邏輯將集中在新的 `src/lib/utils/localClientToolExecutor.ts` 文件中。此模組將負責向預設的本地 MCP 伺服器端點（例如 SSE 為 `http://localhost:8000/sse`，Streamable HTTP 為 `http://localhost:8000/mcp`）發起 `initialize` 請求。MCP `initialize` 回應中的 `invocation` 物件將明確指示後續通訊應使用的傳輸類型（例如 `type: 'http'`）和 `messagePath`。

2.  **統一的工具發現與顯示：**
    *   **數據整合：** 在 `src/lib/stores/index.ts` 中，創建一個 `derived` store (`allAvailableTools`)，它將後端提供的工具列表與 `localMcpTools` 進行合併，形成一個統一的可用工具集合。
    *   **組件修改：** 修改 `src/lib/components/chat/ToolServersModal.svelte`。此組件目前作為使用者配置外部工具伺服器連接的界面，並將被擴展以：
        *   使用 `allAvailableTools` 來渲染工具列表。
        *   為本地工具添加「Local」標籤和啟用/停用開關。
        *   `ToolServersModal.svelte` 將根據其接收到的 `selectedToolIds` 屬性來顯示工具列表。
            *   當從「+」號圖標觸發時，調用組件將傳遞所有工具的 `id`（包括啟用和停用的）。
            *   當從「板手」圖標觸發時，調用組件將僅傳遞所有已啟用工具的 `id`。
        *   此修改將集中在一個專門處理工具列表的組件內。

3.  **前端直接調用本地 MCP 工具 (支援多傳輸處理)：**
    *   **核心執行邏輯：** 核心的調用執行邏輯將集中在新的 `src/lib/utils/localClientToolExecutor.ts` 文件中。
    *   **最小化調度修改：** 在處理 LLM 工具調用指令的現有邏輯中（例如 `src/lib/components/chat/Chat.svelte` 或相關的訊息處理函數），引入一個**單一的條件判斷**。當後端轉發的 LLM 回應中包含一個指示本地工具調用的特定結構（例如，一個包含 `tool_id` 和 `tool_args` 的 `local_tool_call` 字段），前端將判斷為本地 MCP 工具調用，並將調用委託給 `localClientToolExecutor.ts` 中的函數；否則，維持現有的 OpenAPI 工具調用邏輯。這將對現有核心邏輯的修改降到最低。
    *   **執行細節：** `localClientToolExecutor.ts` 中的函數將根據儲存的傳輸類型（SSE 或 Streamable HTTP）直接與本地 MCP 伺服器通訊。對於 Streamable HTTP，可能需要引入專門的 JavaScript/TypeScript MCP 客戶端函式庫，或者進行更複雜的自訂實作。
    *   **CORS 強制：** **至關重要的一點是，本地 MCP 伺服器必須正確設定 CORS (Cross-Origin Resource Sharing) 標頭**，以允許來自 Open WebUI 前端的請求。這對於瀏覽器端的直接通訊至關重要。

4.  **錯誤處理與使用者回饋：**
    *   錯誤處理邏輯將主要在 `localClientToolExecutor.ts` 中實現。這應涵蓋不同類型的錯誤，例如網路連接問題、MCP 協議解析錯誤、工具執行失敗等。
    *   錯誤訊息應透過 Svelte 的事件或 store 更新來觸發 UI 顯示（例如使用 `svelte-sonner` 的 toast 通知），並盡量提供使用者友好的訊息，以幫助使用者理解問題並進行排查。

#### 3.2.2. 後端變更 (FastAPI/Python) - 最小化改動策略

1.  **後端在工具調用中的角色 (精確化與最小化改動)：**
    *   當 LLM 發起工具調用請求時，後端會接收到此請求。
    *   後端將需要**區分**這是針對 **OpenAPI 工具**的調用，還是針對**本地 MCP 工具**的調用：
        *   **對於 OpenAPI 工具調用：** 後端將維持其現有行為，直接執行/代理對外部 OpenAPI 工具伺服器的呼叫（如 `open_webui/utils/tools.py:execute_tool_server` 中所示）。工具執行結果將由後端接收，並返回給 LLM。
        *   **對於本地 MCP 工具調用：** 後端**不會**嘗試執行此工具。相反，它會將此工具調用請求（包括工具 ID 和參數）**轉發給前端**。
            *   **前端傳遞工具 ID 列表：** 前端在發送聊天完成請求（`POST /api/chat/completions`）給後端時，將在請求體中的 `metadata` 字段內傳遞兩個相關的工具 ID 列表：
                *   `tool_ids`：包含應由後端執行（包括後端內部 Python 工具和靜態配置的外部 OpenAPI 工具）的工具 `id` 列表。
                *   `tool_servers`：包含應由前端本地執行（即本地 MCP 工具）的工具規格列表。
                後端將根據 `tool_servers` 字段的存在來判斷哪些工具應被標記為 `direct: True` 並轉發給前端。
            *   **後端判斷邏輯：** 後端在處理 LLM 的 `function_call` 回應時（主要在 `open_webui/utils/chat.py` 或 `open_webui/functions.py` 內），將根據工具的 `direct` 標誌（由 `tool_servers` 字段推導而來）來決定是自行執行工具還是將其轉發給前端。

2.  **後端工具定義與發現 (無需修改)：**
    *   **無需修改後端資料庫模式或 `ToolModel`** 來增加 `is_local_client_call` 標誌。後端將完全依賴前端在請求中提供的 `local_tool_ids` 列表來判斷工具類型。
    *   後端現有的 `/api/tools/` 工具發現端點**不會**被修改以探索本地 MCP 工具。本地 MCP 工具的發現將完全由前端獨立完成。

3.  **後端轉發本地 MCP 工具調用機制：**
    *   在後端的聊天完成管道中（主要在 `open_webui/utils/chat.py` 或 `open_webui/functions.py` 內），需要實作一個新的機制。
    *   當後端識別出 LLM 請求調用的是一個本地 MCP 工具時，它將不再執行該工具，而是透過 **WebSocket 發送一個特定的事件**給前端。
    *   **WebSocket 事件格式：** 建議事件名稱為 `chat:local_tool_call`，其 payload 將包含 LLM 請求的工具 ID 和參數，例如：
        ```json
        {
          "tool_id": "tool_name_from_llm",
          "tool_args": { "param1": "value1", "param2": "value2" },
          "chat_id": "...",
          "message_id": "..."
        }
        ```
    *   前端的 Socket.IO 客戶端將監聽此事件，並觸發本地工具的執行。

4.  **本地工具配置持久化：**
    *   **無需任何後端調整**，因為本地工具的配置持久化將完全在前端處理（透過 `localStorage`）。

#### 3.2.3. 與現有 Python 程式碼執行機制的區別

本提案專注於整合運行在使用者本機上的外部 MCP 伺服器，並由前端直接調用。這與 Open WebUI 現有的兩種 Python 程式碼執行機制有所區別：
*   **後端執行的內部 Python 工具：** 這些工具的 Python 程式碼儲存在資料庫中，並由後端直接執行。
*   **前端 Pyodide Web Worker 執行的自訂 Python 程式碼：** 這是 `chatflow.md` 中描述的「Custom Python Tool Execution Flow (via Pyodide Worker)」，允許前端在瀏覽器環境中執行 Python 程式碼片段。

本本地 MCP 工具整合功能是獨立於上述兩種機制的，旨在擴展 Open WebUI 與外部本地服務的互動能力。

#### 3.2.4. 挑戰與考量

*   **CORS 設定：** 這是使用者面臨的主要技術障礙。本地 MCP 伺服器必須正確設定 CORS 標頭。
*   **前端 Streamable HTTP 實作複雜度：** 支援 Streamable HTTP 將增加前端的開發複雜度，可能需要引入或開發專門的客戶端函式庫。
*   **錯誤報告與偵錯：** 針對本地連線，特別是 CORS 問題和 MCP 協議交互，提供更完善的錯誤報告和偵錯工具。

### 3.3. 使用者體驗流程 (User Experience Flow)

本節將詳細說明使用者如何與本地 MCP 工具進行互動，並確保與現有工具管理流程的一致性。

1.  **本地 MCP 伺服器自動探索 (背景執行)**
    *   當使用者啟動 Open WebUI 應用程式時，或是當使用者按下 Refresh 強制更新 Open WebUI 網頁時，前端會自動在背景嘗試連接預設的本地 MCP 伺服器埠號和路徑（例如 SSE 為 `http://localhost:8000/sse`，Streamable HTTP 為 `http://localhost:8000/mcp`）。
    *   如果成功連接並解析到 MCP `initialize` 回應，這些本地 MCP 工具將會被自動發現並納入前端的可用工具列表中。
    *   此過程對使用者是透明的，無需手動操作。

2.  **統一的工具列表顯示與管理**
    *   **點擊「+」號圖標：**
        *   在聊天介面中，使用者點擊訊息輸入框旁的「+」號圖標。
        *   系統會彈出一個工具列表 Modal (即 `ToolServersModal.svelte`)。
        *   此 Modal 將統一顯示所有可用的工具，包括：
            *   透過靜態配置或後台動態註冊的**外部 OpenAPI 工具**。
            *   透過自動探索發現的**本地 MCP 工具**。
        *   每個工具旁邊都會有一個開關，允許使用者啟用或停用該工具。
        *   為了清晰區分，本地 MCP 工具將會帶有明顯的「Local」標籤或圖標。
    *   **點擊「板手」圖標：**
        *   在聊天介面中，使用者點擊「板手」圖標。
        *   「板手」圖標旁會顯示一個數字，該數字反映了當前會話中已啟用工具的總數量（包括外部 OpenAPI 工具和本地 MCP 工具）。
        *   系統會彈出一個工具列表 Modal (即 `ToolServersModal.svelte`)。
        *   此 Modal 將統一顯示**所有已啟用的工具**，其顯示內容與「+」號圖標彈出的列表**不一定一致**（因為「+」號列表包含關閉的工具）。

3.  **工具的啟用/停用**
    *   使用者可以透過點擊工具列表 Modal 中每個工具旁的開關，來控制該工具在當前聊天會話中的可用性。
    *   啟用或停用狀態將即時反映在 UI 上。

4.  **工具調用時的視覺回饋**
    *   當 LLM 決定調用一個工具時，聊天介面可能會提供視覺提示（例如，在 AI 回覆生成前顯示工具正在執行的狀態，或在工具輸出後明確標示其來源）。具體實現細節將在開發階段確定，以確保使用者能清晰感知工具的互動過程。

## 4. 檔案修改清單與工作事項摘要 (File Modification List and Work Item Summary)

本章節根據「3.2. 關鍵需求與考量」中的最小化改動策略，列出前後端需要修改或新增的檔案及其具體工作事項摘要。

### 4.1. 前端檔案修改 (Frontend File Modifications)

1.  **`src/lib/components/layout/LocalMcpInitializer.svelte` (新增檔案)**
    *   **工作事項摘要：** 創建此新的 Svelte 組件。它將包含 `onMount` 生命週期邏輯，用於自動探索本地 MCP 伺服器。這包括向預設的本地 MCP 伺服器端點（例如 SSE 為 `http://localhost:8000/sse`，Streamable HTTP 為 `http://localhost:8000/mcp`）發起 `initialize` 請求，並解析其回應以獲取伺服器能力和調用細節。

2.  **`src/routes/(app)/+layout.svelte`**
    *   **工作事項摘要：** 在此檔案中，僅需導入並使用新的 `LocalMcpInitializer.svelte` 組件。對核心佈局文件的修改應最小化，僅限於整合此初始化器。

3.  **`src/lib/stores/index.ts`**
    *   **工作事項摘要：**
        *   新增一個 `writable` store，命名為 `localMcpTools`，用於儲存探索到的本地工具資訊（類型為 `LocalClientToolServerConfig[]`）。
        *   創建一個 `derived` store，命名為 `allAvailableTools`，它將後端提供的工具列表與 `localMcpTools` store 進行合併，形成一個統一的可用工具集合。

4.  **`src/lib/utils/localClientToolExecutor.ts` (新增檔案)**
    *   **工作事項摘要：** 創建此新檔案。此模組將集中處理本地 MCP 伺服器的核心探索和初始化邏輯。
    *   **工作事項摘要：** 實作直接調用本地 MCP 工具的核心執行邏輯。這將根據儲存的傳輸類型（SSE 或 Streamable HTTP）與本地 MCP 伺服器進行通訊。

5.  **`src/lib/components/chat/ToolServersModal.svelte`**
    *   **工作事項摘要：** 修改此組件。此組件目前作為使用者配置外部工具伺服器連接的界面，並將被擴展以：
        *   使用 `allAvailableTools` 來渲染工具列表。
        *   為本地工具添加「Local」標籤和啟用/停用開關。
        *   `ToolServersModal.svelte` 將根據其接收到的 `selectedToolIds` 屬性來顯示工具列表。調用組件將負責傳遞所有工具的 `id`（包括啟用和停用的）或僅傳遞所有已啟用工具的 `id`。
        *   此修改將集中在一個專門處理工具列表的組件內。

6.  **`src/lib/components/chat/Chat.svelte` (或相關的訊息處理函數)**
    *   **工作事項摘要：** 在處理 LLM 工具調用指令的現有邏輯中，引入一個單一的條件判斷。當後端轉發的 LLM 回應中包含指示本地工具調用的特定結構時，將調用委託給 `src/lib/utils/localClientToolExecutor.ts` 中的函數；否則，維持現有的 OpenAPI 工具調用邏輯。這將對現有核心邏輯的修改降到最低。

### 4.2. 後端檔案修改 (Backend File Modifications)

1.  **`backend/open_webui/utils/chat.py`**
    *   **工作事項摘要：**
        *   在 LLM 工具調用處理流程中，增加判斷邏輯，區分 OpenAPI 工具（後端代理）和本地 MCP 工具（轉發前端）。
        *   實作後端轉發本地 MCP 工具調用指令給前端的機制（透過 WebSocket 發送 `chat:local_tool_call` 事件，payload 包含工具 ID 和參數）。
        *   處理前端在聊天完成請求中傳遞的 `local_tool_ids` 字段，用於判斷工具類型。

2.  **`backend/open_webui/functions.py`**
    *   **工作事項摘要：**
        *   在 LLM 工具調用處理流程中，增加判斷邏輯，區分 OpenAPI 工具（後端代理）和本地 MCP 工具（轉發前端）。
        *   實作後端轉發本地 MCP 工具調用指令給前端的機制（透過 WebSocket 發送 `chat:local_tool_call` 事件，payload 包含工具 ID 和參數）。
        *   處理前端在聊天完成請求中傳遞的 `local_tool_ids` 字段，用於判斷工具類型。
