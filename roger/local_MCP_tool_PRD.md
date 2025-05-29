# 產品需求文件：Open WebUI 本地工具整合 (透過 MCPO 代理 OpenAPI 工具)

## 1. 簡介

本文件概述了 Open WebUI 的一項新功能需求，旨在無縫整合並調用運行在使用者本機上的 `mcpo` 實例。`mcpo` 是一個代理伺服器，它將多個 Model Context Protocol (MCP) 工具轉換並暴露為標準的 OpenAPI 服務。此功能將允許使用者利用本地工具（例如，自訂腳本、本地 AI 模型、特定硬體的公用程式），並透過前端直接調用這些工具，繞過後端靜態配置的限制（如 Docker 網路問題和無法為每個使用者提供不同工具集的問題）。此功能旨在增強使用者自訂性、降低延遲，並提供潛在的隱私優勢。

## 2. 現行系統概覽

目前 Open WebUI 支援三種主要方式來管理和調用工具：

1.  **靜態配置的外部 OpenAPI 工具伺服器：** 透過環境變數 (`TOOL_SERVER_CONNECTIONS`) 進行配置。後端在啟動時獲取其 OpenAPI 規格並快取，工具的實際調用由後端發起。
2.  **動態註冊的內部 Python 工具：** 透過管理後台（`POST /api/tools/create`）上傳 Python 程式碼並儲存到資料庫。後端在運行時載入並執行這些工具。
3.  **動態註冊的外部 OpenAPI 工具伺服器：** 透過管理後台（如「工具連接」界面）輸入 URL 進行註冊。後端會獲取其 OpenAPI 規格並儲存到資料庫，工具的實際調用由前端直接發起。

## 3. 提案功能：本地工具整合 (透過 MCPO 代理 OpenAPI 工具)

### 3.1. 概念

本提案的核心概念是讓 Open WebUI 前端能夠自動探索並整合運行在使用者本機上的 `mcpo` 實例。`mcpo` 將代理多個 MCP 工具並將其暴露為標準的 OpenAPI 服務。工具的執行責任將從後端轉移到前端，實現**客戶端直接調用運行在使用者本機上的 `mcpo` 代理服務**。

*   **探索與註冊：** 前端將透過嘗試連接預設埠號（例如 `http://localhost:8000`）來自動探索本地 `mcpo` 實例。成功連接後，前端將執行一個**兩階段的探索過程**來獲取 `mcpo` 所代理的所有工具的 OpenAPI 規格：
    1.  **獲取主 OpenAPI 規格：** 前端首先請求 `mcpo` 的主 `openapi.json` 端點（例如 `http://localhost:8000/openapi.json`）。
    2.  **解析並獲取子工具規格：**
        *   前端將首先檢查主 `openapi.json` 的 `paths` 字段。如果 `paths` 字段包含工具定義，則直接從中提取工具規格。
        *   如果 `paths` 字段為空（例如 `mcpo` 代理多個工具時），前端將需要從其 `info.description` 字段中解析出所有被代理工具的名稱和各自的 OpenAPI 規格路徑（例如 `/time/openapi.json`, `/mcp_in_memory/openapi.json`）。然後，前端將逐一請求這些子路徑，獲取每個工具的獨立 OpenAPI 規格。
    3.  **聚合與納入：** 前端將聚合所有發現的工具規格（無論是從主 `paths` 還是從子路徑獲取），並將這些工具納入前端的可用工具列表。
*   **調用流程：** 當 LLM 決定調用一個工具時，後端會根據前端提供的資訊判斷工具類型：
    *   對於**外部 OpenAPI 工具**（非 `mcpo` 代理的），後端將繼續其現有的代理執行機制（透過 `open_webui/utils/tools.py:execute_tool_server`）。
    *   對於**本地 OpenAPI 工具**（透過 `mcpo` 代理的），後端會將 LLM 的調用指令（包含工具 ID 和參數）**轉發**給前端，而不是自行執行。
*   **前端執行：** 前端接收到後端轉發的本地 OpenAPI 工具調用指令後，將直接向運行在使用者本機上的 `mcpo` 代理服務發起標準的 HTTP 請求，執行工具功能。
*   **結果回傳：** 本地工具的執行結果將由前端接收，並回傳給後端，最終由 LLM 生成最終回覆。
*   **配置管理：** 本地工具的探索結果和啟用狀態將主要在前端進行管理和持久化（透過瀏覽器 `localStorage`），後端無需額外支援。

### 3.2. 關鍵需求與考量

#### 3.2.1. 前端變更 (SvelteKit) - 最小化改動策略

1.  **自動探索與註冊 (支援 MCPO OpenAPI 探索)：**
    *   **新增獨立初始化組件：** 創建一個新的 Svelte 組件（例如 `src/lib/components/layout/LocalMcpoInitializer.svelte`），該組件將包含在 `onMount` 生命週期中執行本地 `mcpo` 實例自動探索的邏輯。
    *   **輕微修改根佈局：** 在 `src/routes/(app)/+layout.svelte` 中，僅需**導入並使用**這個新的 `LocalMcpoInitializer.svelte` 組件，將對核心佈局文件的修改降到最低。請注意，`src/routes/(app)/+layout.svelte` 目前也負責協調對工具伺服器的調用。
    *   **狀態管理：** 在 `src/lib/stores/index.ts` 中新增 `localMcpoTools` writable store，用於儲存探索到的本地 `mcpo` 代理工具資訊（類型為 `LocalMcpoToolConfig[]`，定義於 `src/lib/types/tools.ts`）。此類型應包含足夠的資訊以供前端調用工具，例如 `id` (工具唯一識別符)、`name` (工具名稱)、`baseUrl` (mcpo 基礎 URL，例如 `http://localhost:8000`)、`openapiPath` (工具在 mcpo 上的 OpenAPI 規格路徑，例如 `/time/openapi.json`)。
    *   **核心邏輯：** 探索和初始化邏輯將集中在新的 `src/lib/utils/localMcpoToolDiscoverer.ts` 文件中。此模組將負責向預設的 `mcpo` 端點（例如 `http://localhost:8000/openapi.json`）發起主 OpenAPI 規格請求，並執行兩階段的解析和子工具規格獲取。

2.  **統一的工具發現與顯示：**
    *   **數據整合：** 在 `src/lib/stores/index.ts` 中，創建一個 `derived` store (`allAvailableTools`)，它將後端提供的工具列表與 `localMcpoTools` 進行合併，形成一個統一的可用工具集合。
    *   **組件修改：** 修改 `src/lib/components/chat/ToolServersModal.svelte`。此組件目前作為使用者配置外部工具伺服器連接的界面，並將被擴展以：
        *   使用 `allAvailableTools` 來渲染工具列表。
        *   為本地 `mcpo` 代理工具添加「Local (MCPO)」標籤和啟用/停用開關。
        *   `ToolServersModal.svelte` 將根據其接收到的 `selectedToolIds` 屬性來顯示工具列表。
            *   當從「+」號圖標觸發時，調用組件將傳遞所有工具的 `id`（包括啟用和停用的）。
            *   當從「板手」圖標觸發時，調用組件將僅傳遞所有已啟用工具的 `id`。
        *   此修改將集中在一個專門處理工具列表的組件內。

3.  **前端直接調用本地 OpenAPI 工具 (透過 MCPO)：**
    *   **核心執行邏輯：** 核心的調用執行邏輯將集中在新的 `src/lib/utils/localMcpoToolExecutor.ts` 文件中。此模組將根據從 `mcpo` 獲取的 OpenAPI 規格和調用細節，直接向運行在使用者本機上的 `mcpo` 代理服務發起標準的 HTTP 請求。
    *   **最小化調度修改：** 在處理 LLM 工具調用指令的現有邏輯中（例如 `src/lib/components/chat/Chat.svelte` 或相關的訊息處理函數），引入一個**單一的條件判斷**。當後端轉發的 LLM 回應中包含一個指示本地工具調用的特定結構（例如，一個包含 `tool_id` 和 `tool_args` 的 `local_tool_call` 字段），前端將判斷為本地 OpenAPI 工具（透過 `mcpo` 代理），並將調用委託給 `localMcpoToolExecutor.ts` 中的函數；否則，維持現有的 OpenAPI 工具調用邏輯。這將對現有核心邏輯的修改降到最低。
    *   **CORS 強制：** **至關重要的一點是，`mcpo` 實例必須正確設定 CORS (Cross-Origin Resource Sharing) 標頭**，以允許來自 Open WebUI 前端的請求。這對於瀏覽器端的直接通訊至關重要。

4.  **錯誤處理與使用者回饋：**
    *   錯誤處理邏輯將主要在 `localMcpoToolDiscoverer.ts` 和 `localMcpoToolExecutor.ts` 中實現。這應涵蓋不同類型的錯誤，例如網路連接問題、OpenAPI 規格解析錯誤、`mcpo` 代理工具執行失敗等。
    *   錯誤訊息應透過 Svelte 的事件或 store 更新來觸發 UI 顯示（例如使用 `svelte-sonner` 的 toast 通知），並盡量提供使用者友好的訊息，以幫助使用者理解問題並進行排查。

#### 3.2.2. 後端變更 (FastAPI/Python) - 最小化改動策略

1.  **後端在工具調用中的角色 (精確化與最小化改動)：**
    *   當 LLM 發起工具調用請求時，後端會接收到此請求。
    *   後端將需要**區分**這是針對 **OpenAPI 工具**的調用，還是針對**本地 OpenAPI 工具**（透過 `mcpo` 代理的）：
        *   **對於外部 OpenAPI 工具調用：** 後端將維持其現有行為，直接執行/代理對外部 OpenAPI 工具伺服器的呼叫（如 `open_webui/utils/tools.py:execute_tool_server` 中所示）。工具執行結果將由後端接收，並返回給 LLM。
        *   **對於本地 OpenAPI 工具調用：** 後端**不會**嘗試執行此工具。相反，它會將此工具調用請求（包括工具 ID 和參數）**轉發**給前端。
            *   **前端傳遞工具 ID 列表：** 前端在發送聊天完成請求（`POST /api/chat/completions`）給後端時，將在請求體中的 `metadata` 字段內傳遞兩個相關的工具 ID 列表：
                *   `tool_ids`：包含應由後端執行（包括後端內部 Python 工具和靜態配置的外部 OpenAPI 工具）的工具 `id` 列表。
                *   `tool_servers`：包含應由前端本地執行（即透過 `mcpo` 代理的本地 OpenAPI 工具）的**完整 OpenAPI 規格列表**。這些規格是前端從 `mcpo` 探索並聚合後傳遞給後端的。
                後端將根據 `tool_servers` 字段的存在來判斷哪些工具應被標記為 `direct: True` 並轉發給前端。
            *   **後端判斷邏輯與 `direct: True` 設置：** 後端（在 `backend/open_webui/utils/middleware.py` 中的 `process_chat_payload` 函數中）接收到前端傳來的 `form_data` 後，會執行以下邏輯來設置 `direct` 標誌：
                *   對於 `tool_ids` 列表中的工具，後端會調用 `get_tools()` 獲取其規格，這些工具**不會**被明確設置 `direct: True`（即預設為 `False`）。
                *   對於 `tool_servers` 列表中的工具，後端會遍歷這個列表。由於 `tool_servers` 列表中的每個元素都已經是前端獲取到的完整 OpenAPI 規格，後端會將這些工具添加到其內部維護的工具字典中，並**明確地為這些工具設置 `direct: True` 標誌**。
                *   最終，後端在處理 LLM 的 `function_call` 回應時（主要在 `open_webui/utils/chat.py` 或 `open_webui/functions.py` 內），將根據工具的 `direct` 標誌來決定是自行執行工具還是將其轉發給前端。
            *   **多使用者環境下的隔離性：** `process_chat_payload` 函數對 `tool_servers` 字段的處理是基於「每請求」的。這意味著每個聊天請求的 `form_data` 和其內部生成的 `tools_dict` 都是獨立的，不會在不同使用者或不同請求之間共享。這種設計確保了即使有多個使用者同時運行各自的本地 `mcpo` 實例，它們的工具處理也是完全隔離且互不影響的避免了潛在的並發問題和數據混淆。
            *   **重要發現：** 經程式碼檢視，`backend/open_webui/utils/middleware.py` 中處理 `tool_servers` 並設置 `direct: True` 的邏輯**已存在**。

2.  **後端工具定義與發現 (無需修改)：**
    *   **無需修改後端資料庫模式或 `ToolModel`** 來增加 `is_local_client_call` 標誌。後端將完全依賴前端在請求中提供的 `tool_servers` 列表來判斷工具類型。
    *   後端現有的 `/api/tools/` 工具發現端點**不會**被修改以探索本地 `mcpo` 代理的 OpenAPI 工具。本地 `mcpo` 代理工具的發現將完全由前端獨立完成。

3.  **後端轉發本地 OpenAPI 工具調用機制：**
    *   在後端的聊天完成管道中（主要在 `open_webui/utils/chat.py` 或 `open_webui/functions.py` 內），需要實作一個新的機制。
    *   當後端識別出 LLM 請求調用的是一個本地 OpenAPI 工具時，它將不再執行該工具，而是透過 **WebSocket 發送一個特定的事件**給前端。
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
    *   **重要發現：** 經程式碼檢視，`backend/open_webui/functions.py` 中已存在判斷 `direct: True` 工具並透過 `event_caller`（即 WebSocket 事件發送器）轉發工具調用（使用 `execute:tool` 事件）的邏輯。因此，此部分功能**已實現**，前端將監聽 `execute:tool` 事件。

4.  **本地工具配置持久化：**
    *   **無需任何後端調整**，因為本地工具的配置持久化將完全在前端處理（透過 `localStorage`）。

#### 3.2.3. 與現有 Python 程式碼執行機制的區別

本提案專注於整合運行在使用者本機上的 `mcpo` 代理服務，並由前端直接調用其暴露的 OpenAPI 工具。這與 Open WebUI 現有的兩種 Python 程式碼執行機制有所區別：
*   **後端執行的內部 Python 工具：** 這些工具的 Python 程式碼儲存在資料庫中，並由後端直接執行。
*   **前端 Pyodide Web Worker 執行的自訂 Python 程式碼：** 這是 `chatflow.md` 中描述的「Custom Python Tool Execution Flow (via Pyodide Worker)」，允許前端在瀏覽器環境中執行 Python 程式碼片段。

本本地工具整合功能是獨立於上述兩種機制的，旨在擴展 Open WebUI 與外部本地服務的互動能力。

#### 3.2.4. 挑戰與考量

*   **`mcpo` OpenAPI 規格解析：** 由於 `mcpo` 的主 `openapi.json` 僅在 `info.description` 中以非標準方式列出子工具，前端需要實現穩健的解析邏輯來提取這些信息。
*   **CORS 設定：** `mcpo` 實例必須正確設定 CORS (Cross-Origin Resource Sharing) 標頭，以允許來自 Open WebUI 前端的請求。
*   **前端 HTTP 實作複雜度：** 處理 `mcpo` 的兩階段 OpenAPI 探索和後續的標準 HTTP 請求將增加前端的開發複雜度。
*   **錯誤報告與偵錯：** 針對本地連線和 `mcpo` 代理的工具，提供更完善的錯誤報告和偵錯工具。

### 3.3. 使用者體驗流程 (User Experience Flow)

本節將詳細說明使用者如何與本地 `mcpo` 代理的 OpenAPI 工具進行互動，並確保與現有工具管理流程的一致性。

1.  **本地 `mcpo` 代理服務自動探索 (背景執行)**
    *   當使用者啟動 Open WebUI 應用程式時，或是當使用者按下 Refresh 強制更新 Open WebUI 網頁時，前端會自動在背景嘗試連接預設的 `mcpo` 埠號（例如 `http://localhost:8000`）。
    *   如果成功連接並獲取到 `mcpo` 的主 `openapi.json`，前端將執行兩階段的探索過程：解析 `info.description` 獲取子工具路徑，然後逐一請求並聚合這些子工具的 OpenAPI 規格。
    *   這些透過 `mcpo` 代理的本地 OpenAPI 工具將會被自動發現並納入前端的可用工具列表中。
    *   此過程對使用者是透明的，無需手動操作。

2.  **統一的工具列表顯示與管理**
    *   **點擊「+」號圖標：**
        *   在聊天介面中，使用者點擊訊息輸入框旁的「+」號圖標。
        *   系統會彈出一個工具列表 Modal (即 `ToolServersModal.svelte`)。
        *   此 Modal 將統一顯示所有可用的工具，包括：
            *   透過靜態配置或後台動態註冊的**外部 OpenAPI 工具**。
            *   透過自動探索發現的**本地 `mcpo` 代理的 OpenAPI 工具**。
        *   每個工具旁邊都會有一個開關，允許使用者啟用或停用該工具。
        *   為了清晰區分，本地 `mcpo` 代理的 OpenAPI 工具將會帶有明顯的「Local (MCPO)」標籤或圖標。
    *   **點擊「板手」圖標：**
        *   在聊天介面中，使用者點擊「板手」圖標。
        *   「板手」圖標旁會顯示一個數字，該數字反映了當前會話中已啟用工具的總數量（包括外部 OpenAPI 工具和本地 `mcpo` 代理的 OpenAPI 工具）。
        *   系統會彈出一個工具列表 Modal (即 `ToolServersModal.svelte`)。
        *   此 Modal 將統一顯示**所有已啟用的工具**，其顯示內容與「+」號圖標彈出的列表**不一定一致**（因為「+」號列表包含關閉的工具）。

3.  **工具的啟用/停用**
    *   使用者可以透過點擊工具列表 Modal 中每個工具旁的開關，來控制該工具在當前聊天會話中的可用性。
    *   啟用或停用狀態將即時反映在 UI 上。

4.  **工具調用時的視覺回饋**
    *   當 LLM 決定調用一個工具時，聊天介面可能會提供視覺提示（例如，在 AI 回覆生成前顯示工具正在執行的狀態，或在工具輸出後明確標示其來源）。具體實現細節將在開發階段確定，以確保使用者能清晰感知工具的互動過程。

### 3.4. 未來考量 (Future Considerations)

本節列出當前版本未包含，但未來可能考慮的功能或改進：

*   **`mcpo` 標準化探索端點：** 鼓勵 `mcpo` 項目未來提供一個標準的、機器可讀的端點（例如 `/mcpo-tools-list`），用於直接列出所有代理工具的名稱和其 OpenAPI 規格路徑，以簡化 Open WebUI 的探索邏輯。
*   **支援自訂本地 `mcpo` 端點：** 考慮未來允許使用者手動設定或掃描多個/非預設的本地 `mcpo` 實例端點，以支援更廣泛的本地工具部署情境。
*   **研究現有 JavaScript/TypeScript OpenAPI 客戶端函式庫：** 評估並研究是否可以利用現有的 JavaScript/TypeScript OpenAPI 客戶端函式庫來簡化前端的 OpenAPI 規格解析和請求/回應處理，以降低開發複雜度。
*   **提供範例 `mcpo` 配置：** 提供一個簡單、文件完善的 `mcpo` 配置 文件範例，展示如何代理常見的 MCP 工具，並包含正確的 CORS 設定，供使用者參考調整。

## 4. 檔案修改清單與工作事項摘要 (File Modification List and Work Item Summary)

本章節根據「3.2. 關鍵需求與考量」中的最小化改動策略，列出前後端需要修改或新增的檔案及其具體工作事項摘要。

### 4.1. 前端檔案修改 (Frontend File Modifications)

1.  **`src/lib/components/layout/LocalMcpoInitializer.svelte` (新增)**
    *   **工作事項：** 創建此新的 Svelte 組件。它將包含 `onMount` 生命週期邏輯，用於自動探索本地 `mcpo` 實例。這包括向預設的 `mcpo` 端點（例如 `http://localhost:8000/openapi.json`）發起主 OpenAPI 規格請求，並啟動兩階段的解析和子工具規格獲取。

2.  **`src/routes/(app)/+layout.svelte` (修改)**
    *   **工作事項：** 在此檔案中，僅需導入並使用新的 `LocalMcpoInitializer.svelte` 組件。同時，需要新增 WebSocket 監聽器，用於接收後端轉發的 `chat:local_tool_call` 事件，並將對核心佈局文件的修改降到最低。

3.  **`src/lib/stores/index.ts` (修改)**
    *   **工作事項：**
        *   新增一個 `writable` store，命名為 `localMcpoTools`，用於儲存探索到的本地 `mcpo` 代理工具資訊（類型為 `LocalMcpoToolConfig[]`）。
        *   創建一個 `derived` store，命名為 `allAvailableTools`，它將後端提供的工具列表與 `localMcpoTools` store 進行合併，形成一個統一的可用工具集合。

4.  **`src/lib/utils/localMcpoToolDiscoverer.ts` (新增)**
    *   **工作事項：** 創建此新檔案。此模組將集中處理本地 `mcpo` 實例的核心探索和 OpenAPI 規格聚合邏輯。它將實現兩階段的探索過程：獲取主 `openapi.json`，解析 `info.description` 獲取子工具路徑，然後逐一請求並聚合這些子工具的 OpenAPI 規格。

5.  **`src/lib/utils/localMcpoToolExecutor.ts` (新增)**
    *   **工作事項：** 創建此新檔案。此模組將根據從 `mcpo` 獲取的 OpenAPI 規格和調用細節，直接向運行在使用者本機上的 `mcpo` 代理服務發起標準的 HTTP 請求。

6.  **`src/lib/components/chat/ToolServersModal.svelte` (修改)**
    *   **工作事項：** 修改此組件。此組件目前作為使用者配置外部工具伺服器連接的界面，並將被擴展以：
        *   使用 `allAvailableTools` 來渲染工具列表。
        *   為本地 `mcpo` 代理工具添加「Local (MCPO)」標籤和啟用/停用開關。
        *   `ToolServersModal.svelte` 將根據其接收到的 `selectedToolIds` 屬性來顯示工具列表。
            *   當從「+」號圖標觸發時，調用組件將傳遞所有工具的 `id`（包括啟用和停用的）。
            *   當從「板手」圖標觸發時，調用組件將僅傳遞所有已啟用工具的 `id`。
        *   此修改將集中在一個專門處理工具列表的組件內。

7.  **`src/lib/components/chat/Chat.svelte` (或相關的訊息處理函數) (修改)**
    *   **工作事項：** 在處理 LLM 工具調用指令的現有邏輯中，引入一個單一的條件判斷。當後端轉發的 LLM 回應中包含一個指示本地工具調用的特定結構（例如，一個包含 `tool_id` 和 `tool_args` 的 `local_tool_call` 字段），前端將判斷為本地 OpenAPI 工具（透過 `mcpo` 代理），並將調用委託給 `localMcpoToolExecutor.ts` 中的函數；否則，維持現有的 OpenAPI 工具調用邏輯。這將對現有核心邏輯的修改降到最低。

8.  **`src/lib/types/tools.ts` (修改/新增)**
    *   **工作事項：** 定義 `LocalMcpoToolConfig` 類型。確保能夠正確表示從 `mcpo` 獲取的 OpenAPI 規格相關型別。

9.  **UI 錯誤訊息顯示 (跨多個組件)**
    *   **工作事項：** 確保 `localMcpoToolDiscoverer.ts` 和 `localMcpoToolExecutor.ts` 報告的錯誤能清晰地在 UI 上顯示（例如透過 `svelte-sonner` 或調整 `ResponseMessage`）。

### 4.2. 後端檔案修改 (Backend File Modifications)

1.  **`backend/open_webui/utils/middleware.py` (修改)**
    *   **工作事項：** 修改 `process_chat_payload` 函數，使其能夠處理前端傳遞的 `tool_servers` 字段。
    *   根據 `tool_servers` 字段中包含的工具規格，為這些工具在內部工具字典中設置 `direct: True` 標誌，以便後續判斷由前端執行。

2.  **`backend/open_webui/utils/chat.py` (修改)**
    *   **工作事項：** 在 LLM 工具調用處理流程中，增加判斷邏輯，區分外部 OpenAPI 工具和本地 OpenAPI 工具（透過 `mcpo` 代理的）。
    *   實作後端轉發本地 OpenAPI 工具調用指令給前端的機制（透過 WebSocket 發送 `chat:local_tool_call` 事件，payload 包含工具 ID 和參數）。
    *   使用 `middleware.py` 處理後的 `tools_dict`（其中已包含 `direct` 標誌）來進行工具分派。

3.  **`backend/open_webui/functions.py` (修改)**
    *   **工作事項：** 在 LLM 工具調用處理流程中，增加判斷邏輯，區分外部 OpenAPI 工具和本地 OpenAPI 工具（透過 `mcpo` 代理的）。
    *   實作後端轉發本地 OpenAPI 工具調用指令給前端的機制（透過 WebSocket 發送 `chat:local_tool_call` 事件，payload 包含工具 ID 和參數）。
    *   使用 `middleware.py` 處理後的 `tools_dict`（其中已包含 `direct` 標誌）來進行工具分派。
