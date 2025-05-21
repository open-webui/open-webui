# 產品需求文件：Open WebUI 本地 MCP 工具整合

## 1. 簡介

本文件概述了 Open WebUI 的一項新功能需求，旨在無縫整合並調用運行在使用者本機上的 Model Context Protocol (MCP) 工具伺服器。這將允許使用者利用本地工具（例如，自訂腳本、本地 AI 模型、特定硬體的公用程式），支援多種 HTTP-based 傳輸方式，並與現有的後端代理 OpenAPI 工具的機制協同運作。此功能旨在增強使用者自訂性、降低延遲，並提供潛在的隱私優勢。

## 2. 現行系統概覽

目前 Open WebUI 支援透過後端代理來調用外部 OpenAPI 工具伺服器。當 LLM 決定使用一個 OpenAPI 工具時，後端會接收到此調用請求，並直接向外部工具伺服器發起 HTTP 請求，處理通訊、認證和錯誤，然後將結果返回給 LLM。

## 3. 提案功能：本地客戶端 MCP 工具整合

### 3.1. 概念

本提案的核心概念是將部分工具的執行責任從後端轉移到前端，實現**客戶端直接調用運行在使用者本機上的 MCP 伺服器**。
*   **探索與註冊：** 前端將透過嘗試連接預設埠號（例如 `http://localhost:8000/sse`）來自動探索本地 MCP 伺服器。成功探索後，將解析其 MCP `initialize` 回應，獲取伺服器能力清單，並將這些工具納入前端的可用工具列表。
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
    *   **輕微修改根佈局：** 在 `src/routes/(app)/+layout.svelte` 中，僅需**導入並使用**這個新的 `LocalMcpInitializer.svelte` 組件，將對核心佈局文件的修改降到最低。
    *   **狀態管理：** 在 `src/lib/stores/index.ts` 中新增 `localMcpTools` writable store，用於儲存探索到的本地工具資訊（類型為 `LocalClientToolServerConfig[]`，定義於 `src/lib/types/tools.ts`）。
    *   **核心邏輯：** 探索和初始化邏輯將集中在新的 `src/lib/utils/localClientToolExecutor.ts` 文件中。此模組將負責向預設的本地 MCP 伺服器端點（例如 `http://localhost:8000/sse`）發起 `initialize` 請求。MCP `initialize` 回應中的 `invocation` 物件將明確指示後續通訊應使用的傳輸類型（例如 `type: 'http'`）和 `messagePath`。

2.  **統一的工具發現與顯示：**
    *   **數據整合：** 在 `src/lib/stores/index.ts` 中，創建一個 `derived` store (`allAvailableTools`)，它將後端提供的工具列表與 `localMcpTools` 進行合併，形成一個統一的可用工具集合。
    *   **組件修改：** 修改 `src/lib/components/chat/ToolServersModal.svelte`，使其使用 `allAvailableTools` 來統一渲染工具列表，並為本地工具添加「Local」標籤和啟用/停用開關。此修改將集中在一個專門處理工具列表的組件內。

3.  **前端直接調用本地 MCP 工具 (支援多傳輸處理)：**
    *   **核心執行邏輯：** 核心的調用執行邏輯將集中在新的 `src/lib/utils/localClientToolExecutor.ts` 文件中。
    *   **最小化調度修改：** 在處理 LLM 工具調用指令的現有邏輯中（例如 `src/lib/components/chat/Chat.svelte` 或相關的訊息處理函數），引入一個**單一的條件判斷**。當後端轉發的 LLM 回應中包含一個指示本地工具調用的特定結構（例如，一個包含 `tool_id` 和 `tool_args` 的 `local_tool_call` 字段），前端將判斷為本地 MCP 工具調用，並將調用委託給 `localClientToolExecutor.ts` 中的函數；否則，維持現有的 OpenAPI 工具調用邏輯。這將對現有核心邏輯的修改降到最低。
    *   **執行細節：** `localClientToolExecutor.ts` 中的函數將根據儲存的傳輸類型（SSE 或 Streamable HTTP）直接與本地 MCP 伺服器通訊。對於 Streamable HTTP，可能需要引入專門的 JavaScript/TypeScript MCP 客戶端函式庫，或者進行更複雜的自訂實作。
    *   **CORS 強制：** **至關重要的一點是，本地 MCP 伺服器必須正確設定 CORS (Cross-Origin Resource Sharing) 標頭**，以允許來自 Open WebUI 前端的請求。這對於瀏覽器端的直接通訊至關重要。

4.  **錯誤處理與使用者回饋：**
    *   錯誤處理邏輯將主要在 `localClientToolExecutor.ts` 中實現，並透過 Svelte 的事件或 store 更新來觸發 UI 顯示（例如使用 `svelte-sonner` 的 toast 通知），盡量不修改現有錯誤處理框架。

#### 3.2.2. 後端變更 (FastAPI/Python) - 最小化改動策略

1.  **後端在工具調用中的角色 (精確化與最小化改動)：**
    *   當 LLM 發起工具調用請求時，後端會接收到此請求。
    *   後端將需要**區分**這是針對 **OpenAPI 工具**的調用，還是針對**本地 MCP 工具**的調用：
        *   **對於 OpenAPI 工具調用：** 後端將維持其現有行為，直接執行/代理對外部 OpenAPI 工具伺服器的呼叫（如 `open_webui/utils/tools.py:execute_tool_server` 中所示）。工具執行結果將由後端接收，並返回給 LLM。
        *   **對於本地 MCP 工具調用：** 後端**不會**嘗試執行此工具。相反，它會將此工具調用請求（包括工具 ID 和參數）**轉發給前端**。
            *   **前端傳遞 `local_tool_ids`：** 前端在發送聊天完成請求（`POST /api/chat/completions`）給後端時，將在請求體中**額外傳遞一個新的字段，例如 `form_data["local_tool_ids"]`**，其中包含當前會話中所有已啟用且為本地 MCP 工具的 `tool_id`s 列表。
            *   **後端判斷邏輯：** 後端在處理 LLM 的 `function_call` 回應時（主要在 `open_webui/utils/chat.py` 或 `open_webui/functions.py` 內），將檢查 LLM 請求調用的 `tool_id` 是否存在於前端傳遞的 `local_tool_ids` 列表中。

2.  **後端工具定義 (無需修改)：**
    *   **無需修改後端資料庫模式或 `ToolModel`** 來增加 `is_local_client_call` 標誌。後端將完全依賴前端在請求中提供的 `local_tool_ids` 列表來判斷工具類型。

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

#### 3.2.3. 挑戰與考量

*   **CORS 設定：** 這是使用者面臨的主要技術障礙。本地 MCP 伺服器必須正確設定 CORS 標頭。
*   **前端 Streamable HTTP 實作複雜度：** 支援 Streamable HTTP 將增加前端的開發複雜度，可能需要引入或開發專門的客戶端函式庫。
*   **錯誤報告與偵錯：** 針對本地連線，特別是 CORS 問題和 MCP 協議交互，提供更完善的錯誤報告和偵錯工具。

## 4. 實作計畫 (高層次)

本計畫將分為以下主要階段：

1.  **前端本地 MCP 探索與管理模組開發：**
    *   實作自動探索邏輯，支援 SSE 和 Streamable HTTP。
    *   建立本地儲存機制（`localStorage`）來持久化探索到的工具配置。
    *   更新前端工具列表 UI，整合並顯示本地工具。

2.  **後端工具調用邏輯調整：**
    *   在 LLM 工具調用處理流程中，增加判斷邏輯，區分 OpenAPI 工具（後端代理）和本地 MCP 工具（轉發前端），**無需修改後端工具定義的資料庫模式**。
    *   實作後端轉發本地 MCP 工具調用指令給前端的機制（透過 WebSocket 事件）。

3.  **前端本地 MCP 工具調用執行模組開發：**
    *   開發前端執行邏輯，根據傳輸類型（SSE 或 Streamable HTTP）直接與本地 MCP 伺服器通訊。
    *   實作強健的錯誤處理和 UI 回饋機制。

4.  **文件與範例提供：**
    *   提供清晰的 CORS 設定指引和本地 MCP 伺服器範例，以協助使用者部署。
