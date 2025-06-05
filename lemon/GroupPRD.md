Open WebUI 功能說明：使用者、群組與工具管理

本文檔說明 Open WebUI 系統中關於使用者註冊、使用者管理、群組指派以及工具使用權限的現有流程，並包含一項新功能規劃：在使用者註冊時根據外部 SQL Server 資料自動指派群組。

第一部分：使用者註冊與身份驗證

1.  註冊流程 (路由: /signup, 檔案: backend/open_webui/routers/auths.py)
    -   使用者需提供：名稱、電子郵件、密碼。
    -   後端檢查：
        -   註冊功能是否已啟用 (依據 `ENABLE_SIGNUP` 設定)。
        -   電子郵件格式及是否已被註冊。
    -   角色指派：
        -   系統首位使用者自動獲得 "admin" 角色。
        -   其他使用者則獲得預設角色 (依據 `DEFAULT_USER_ROLE` 設定)。
    -   密碼處理：進行雜湊加密 (使用 `get_password_hash`)。
    -   資料庫操作 (透過 `Auths.insert_new_auth`):
        -   於 `auth` 資料表：建立身份驗證記錄 (使用者 ID, 電子郵件, 加密密碼)。
        -   於 `user` 資料表 (透過 `Users.insert_new_user`)：建立使用者詳細記錄 (ID, 名稱, 電子郵件, 角色, 個人圖片 URL 等)。
    -   註冊成功後：
        -   產生 JWT (JSON Web Token) 並存入 cookie，用於後續驗證。
        -   可選：觸發 Webhook 通知。

2.  登入流程 (路由: /signin, 檔案: backend/open_webui/routers/auths.py)
    -   一般登入方式：
        -   使用者提供：電子郵件、密碼。
        -   後端驗證 (透過 `Auths.authenticate_user`)：
            -   查詢 `auth` 資料表。
            -   比對提供的密碼與儲存的雜湊密碼 (使用 `verify_password`)。
            -   成功則返回使用者資訊。
    -   受信任標頭登入 (若設定 `WEBUI_AUTH_TRUSTED_EMAIL_HEADER`):
        -   系統信任請求標頭中的電子郵件。
        -   若使用者不存在，則自動註冊。
        -   透過 `Auths.authenticate_user_by_trusted_header` 進行驗證。
    -   無驗證模式 (若 `WEBUI_AUTH == False`):
        -   若系統無使用者，自動建立預設管理員帳號 "admin@localhost"。
    -   登入成功後：產生 JWT 並存入 cookie。
    -   OIDC (例如 Microsoft) 登入:
        -   系統支援透過 OpenID Connect (OIDC) 進行第三方身份驗證，允許使用者例如使用其 Microsoft 帳號登入。
        -   啟用與設定:
            -   需要在環境變數中設定 `ENABLE_OAUTH_SIGNUP=True` 以允許透過 OIDC 提供者註冊新使用者。
            -   同時，需要設定 OIDC 提供者的相關資訊。有兩種主要方式：
                1.  Microsoft 專用設定: 設定 `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_CLIENT_TENANT_ID`, 和 `MICROSOFT_REDIRECT_URI`。
                2.  通用 OIDC 設定: 設定 `OPENID_PROVIDER_URL` (指向 Microsoft 的 OpenID 端點，例如 `https://login.microsoftonline.com/{TENANT_ID}/v2.0`)，以及 `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, 和 `OPENID_REDIRECT_URI`。
        -   運作流程:
            1.  使用者在前端介面選擇透過 OIDC (例如 Microsoft) 登入。
            2.  系統將使用者重新導向至 Microsoft 的登入和授權頁面。
            3.  使用者在 Microsoft 端完成身份驗證和授權。
            4.  Microsoft 將使用者重新導向回應用程式設定的重新導向 URI (`MICROSOFT_REDIRECT_URI` 或 `OPENID_REDIRECT_URI`)，並附帶授權碼或 ID Token。
            5.  後端 (`auths.py` 中透過 OAuth 函式庫間接處理，並由 `config.py` 中的 `load_oauth_providers` 函數設定) 處理此回呼：
                -   使用授權碼向 Microsoft 換取 Access Token 和 ID Token。
                -   從 ID Token 中解析出使用者資訊，包括唯一識別碼 (`sub`)、電子郵件和名稱。
            6.  使用者帳號處理:
                -   系統使用 `Users.get_user_by_oauth_sub` 檢查該 `sub` 是否已存在於本地 `user` 資料表的 `oauth_sub` 欄位。
                -   若已存在，則直接登入該使用者。
                -   若不存在且 `ENABLE_OAUTH_SIGNUP` 為 `True`，則呼叫 `Auths.insert_new_auth` (內部會呼叫 `Users.insert_new_user`) 在本地資料庫中建立新使用者，並將 `oauth_sub` 存入。
                -   若不存在且 `ENABLE_OAUTH_SIGNUP` 為 `False`，則登入失敗。
            7.  成功登入或註冊後，產生 JWT 並設定到 cookie。

3.  LDAP 驗證流程 (路由: /ldap, 檔案: backend/open_webui/routers/auths.py)
    -   啟用條件：`ENABLE_LDAP` 設定為 true。
    -   使用者提供：LDAP 使用者名稱、密碼。
    -   系統操作：
        -   連接至設定的 LDAP 伺服器。
        -   使用應用程式帳號 (App DN) 搜尋使用者。
        -   使用使用者憑證嘗試繫結以驗證密碼。
    -   驗證成功後：
        -   若使用者在本地資料庫不存在，則自動建立相應記錄。
        -   產生 JWT 並存入 cookie。

4.  獲取目前登入使用者資訊 (路由: /, GET 方法, 檔案: backend/open_webui/routers/auths.py)
    -   透過 `Depends(get_current_user)` 從 cookie 解析 JWT，驗證並獲取使用者資訊。
    -   同時返回使用者權限 (`get_permissions`)。

第二部分：使用者管理

1.  使用者資料模型 (檔案: backend/open_webui/models/users.py)
    -   `User` (SQLAlchemy 模型)：定義 `user` 資料表結構，包含 ID, 名稱, 電子郵件, 角色, 個人圖片 URL, API 金鑰, 設定 (JSON), 資訊 (JSON), OAuth Subject ID 等。
    -   `UserModel` (Pydantic 模型)：用於資料驗證與序列化。
    -   `UsersTable` 類別：提供使用者資料的 CRUD 操作介面。

2.  更新個人資料 (路由: /update/profile, 檔案: backend/open_webui/routers/auths.py)
    -   已驗證使用者可更新：名稱、個人資料圖片 URL。
    -   透過 `Users.update_user_by_id` 更新資料庫。

3.  更新密碼 (路由: /update/password, 檔案: backend/open_webui/routers/auths.py)
    -   已驗證使用者提供：舊密碼、新密碼。
    -   系統驗證舊密碼 (透過 `Auths.authenticate_user`)。
    -   驗證通過後，新密碼雜湊處理並透過 `Auths.update_user_password_by_id` 更新。

4.  新增使用者 (管理員功能) (路由: /add, 檔案: backend/open_webui/routers/auths.py)
    -   權限：僅限管理員 (`Depends(get_admin_user)`)。
    -   管理員提供：新使用者名稱、電子郵件、密碼、角色。
    -   流程類似使用者註冊。

5.  API 金鑰管理 (檔案: backend/open_webui/routers/auths.py)
    -   產生 API 金鑰 (路由: /api_key, POST)：已登入使用者可產生，需啟用 `ENABLE_API_KEY`。金鑰存於 `user` 表。
    -   刪除 API 金鑰 (路由: /api_key, DELETE)：使用者可刪除自己的金鑰。
    -   取得 API 金鑰 (路由: /api_key, GET)：使用者可獲取自己的金鑰。

第三部分：群組管理與使用者指派

1.  群組資料模型 (檔案: backend/open_webui/models/groups.py)
    -   `Group` (SQLAlchemy 模型)：定義 `group` 資料表結構，包含 ID, 群組建立者 ID, 名稱, 描述, 資料 (JSON), 元資料 (JSON), 權限 (JSON), 成員 ID 列表 (`user_ids`, JSON 陣列)。
    -   `GroupModel` (Pydantic 模型)：用於資料驗證與序列化。
    -   `GroupTable` 類別：提供群組資料的 CRUD 操作介面。

2.  建立新群組 (路由: /create, 檔案: backend/open_webui/routers/groups.py)
    -   權限：僅限管理員。
    -   管理員提供：群組名稱、描述、可選權限。
    -   透過 `Groups.insert_new_group` 建立記錄。

3.  更新群組 (路由: /id/{id}/update, 檔案: backend/open_webui/routers/groups.py)
    -   權限：僅限管理員。
    -   可更新：名稱、描述、權限、成員 ID 列表 (`user_ids`)。
    -   後端使用 `Users.get_valid_user_ids` 驗證傳入的使用者 ID。
    -   透過 `Groups.update_group_by_id` 更新資料。

4.  獲取群組列表 (路由: /, GET 方法, 檔案: backend/open_webui/routers/groups.py)
    -   管理員：可見所有群組 (`Groups.get_groups()`)。
    -   普通使用者：僅可見自己所屬群組 (`Groups.get_groups_by_member_id(user.id)`)。

5.  刪除使用者時的處理 (於 `Users.delete_user_by_id` 內部, 檔案: backend/open_webui/models/users.py)
    -   觸發 `Groups.remove_user_from_all_groups(id)`，將該使用者從其所有屬組的 `user_ids` 列表中移除。

第四部分：工具的使用權限 (與使用者和群組的關聯)

1.  工具資料模型 (檔案: backend/open_webui/models/tools.py)
    -   `Tool` (SQLAlchemy 模型)：定義 `tool` 資料表結構。
    -   關鍵欄位 `access_control` (JSON)：
        -   `None` (空值)：公開，所有 "user" 角色的使用者皆可存取。
        -   `{}` (空物件)：私有，僅限工具擁有者存取。
        -   自訂權限物件範例：
            ```json
            {
              "read": { "group_ids": ["id1"], "user_ids": ["uid1"] },
              "write": { "group_ids": ["id1"], "user_ids": ["uid1"] }
            }
            ```
            (`group_ids` 對應群組管理中的群組 ID)。

2.  工具的存取控制邏輯 (函式: `ToolsTable.get_tools_by_user_id` 及 `has_access`)
    -   判斷使用者對工具的存取權限時：
        -   檢查是否公開。
        -   若非公開，檢查是否為擁有者。
        -   若非擁有者，檢查自訂權限：
            -   使用者 ID 是否在允許列表。
            -   使用者所屬群組 ID 是否在允許列表。

總結現有流程：
1.  使用者註冊/登入：驗證身份並賦予角色。
2.  群組建立與指派 (管理員操作)：管理員建立群組並透過更新 `user_ids` 指派成員。
3.  工具建立與權限設定：工具擁有者設定 `access_control` (公開、私有、或指定使用者/群組)。
4.  工具使用：系統根據 `access_control`、使用者身份、角色及所屬群組判斷權限。

此流程透過使用者、群組及工具的 `access_control` 機制，實現了精細化的工具使用權限管理。

---

**第五部分：新功能 - 使用者登入時同步群組成員資格 (基於 SQL Server 資料)**

**功能目標：**

在使用者每次成功登入 Open WebUI 系統後（無論是透過傳統註冊表單、傳統帳號密碼登入，還是 OIDC 單一登入流程），系統將自動查詢外部 SQL Server 資料庫中的 `sp_PBA_HC_Movement` 表。根據使用者的 Email，系統會將其 Open WebUI 中的群組成員資格與 SQL Server 中 `[HW_Purchase_Group]` 欄位指定的群組進行同步。SQL Server 將作為這些特定群組成員資格的權威來源。

*   **新增成員**：如果 SQL Server 的記錄顯示使用者應屬於某個（或某些）群組，而使用者在 Open WebUI 中尚未加入，則系統會將使用者加入到這些群組中。如果 Open WebUI 系統中不存在具有相應名稱的群組，則會自動建立該群組。
*   **移除成員**：如果 SQL Server 的記錄顯示使用者不應再屬於某個（或某些）群組（例如，該群組不再與該使用者關聯，或使用者在 SQL Server 中已無有效的群組記錄），而使用者在 Open WebUI 中仍是該群組的成員，則系統會將使用者從這些群組中移除。
*   **執行時機**：此同步邏輯在每次使用者成功登入後執行。

**詳細實施步驟：**

1.  **建立群組同步服務 (`group_sync_service.py`)**
    *   在後端應用中建立一個新的 Python 檔案，例如 `backend/open_webui/services/group_sync_service.py`。
    *   此檔案將包含一個主要的函式，例如 `synchronize_user_groups_from_sql(user: UserModel, db: Session)`，用於封裝所有群組同步的邏輯。
    *   **函式職責**：
        *   接收已成功驗證的 `user` 物件 (包含 `email` 和 `id`) 和資料庫會話 `db`。
        *   **執行 SQL 查詢**：
            *   構建 SQL 查詢語句 (應使用參數化查詢以防 SQL 注入)：
                ```sql
                SELECT [HW_Purchase_Group] 
                FROM [dbo].[sp_PBA_HC_Movement] 
                WHERE [Email Address] = ? AND [EndDate] IS NULL 
                ```
                *(註：`?` 為 `pyodbc` 常用的參數佔位符。)*
            *   在 `group_sync_service.py` 內部，使用 Python 資料庫連接庫 (例如 `pyodbc`) 直接連接到 SQL Server 並執行此查詢，傳遞使用者 Email 作為參數。
            *   處理預期的查詢結果：一個群組名稱的列表 (`target_group_names_from_sql`)。
        *   **處理 SQL 查詢結果並同步群組成員資格**：
            *   **A. 判斷 SQL 查詢結果並準備目標群組列表**：
                *   初始化一個空集合 `final_target_ouw_group_ids_set`。
                *   定義未分配群組的名稱，例如 `unassigned_group_name = "Unassigned"`。
                *   如果 `target_group_names_from_sql` 為空（即 SQL 中未找到該使用者的特定群組指派）：
                    *   記錄此情況，並準備將使用者加入 `"Unassigned"` 群組。
                    *   呼叫 `groups_table.get_group_by_name(unassigned_group_name)` 查找 `"Unassigned"` 群組。
                    *   如果群組不存在，則使用 `groups_table.insert_new_group(user_id=user.id, form_data=GroupForm(name=unassigned_group_name, description="由系統指派，SQL中無特定群組的使用者"))` 建立新群組。*(群組建立者 `user_id` 可考慮使用一個系統帳號 ID，或首次建立該群組的使用者 ID。此處暫定為 `user.id`)*。記錄建立日誌及處理建立失敗的情況。
                    *   將獲取到或新建的 `"Unassigned"` 群組 ID 加入 `final_target_ouw_group_ids_set`。
                *   如果 `target_group_names_from_sql` 不為空：
                    *   對於 `target_group_names_from_sql` 中的每一個 `group_name_from_sql`：
                        *   調用 `groups_table.get_group_by_name(group_name_from_sql)` 查找群組。
                        *   如果群組不存在，則使用 `groups_table.insert_new_group(user_id=user.id, form_data=GroupForm(name=group_name_from_sql, description="由系統根據 SQL Server 資料自動建立/同步"))` 建立新群組。記錄建立日誌及處理建立失敗的情況。
                        *   將獲取到或新建的群組 ID 加入 `final_target_ouw_group_ids_set`。
            *   **B. 獲取使用者在 Open WebUI 中的現有群組ID集合**：
                *   實例化 `GroupsTable(db)` (如果尚未實例化)。
                *   調用 `groups_table.get_groups_by_user_id(user.id)`。
                *   從結果中提取群組 ID，形成一個集合 `current_ouw_group_ids_set`。
            *   **C. 比較並執行同步操作 (基於 `final_target_ouw_group_ids_set` 和 `current_ouw_group_ids_set`)**：
                *   **要加入的群組** (`groups_to_add_ids = final_target_ouw_group_ids_set - current_ouw_group_ids_set`)：對於每個 ID，調用 `groups_table.add_user_to_group(user_id=user.id, group_id=group_id_to_add)`。記錄結果。
                *   **要移除的群組** (`groups_to_remove_ids = current_ouw_group_ids_set - final_target_ouw_group_ids_set`)：對於每個 ID，調用 `groups_table.remove_user_from_group(user_id=user.id, group_id=group_id_to_remove)`。記錄結果。
    *   **錯誤處理與日誌**：函式內部應包含完整的 `try-except` 結構，詳細記錄操作和錯誤，確保任何同步失敗都不會影響核心登入/註冊流程（即不應向上拋出未處理的異常給呼叫它的 `auths.py` 中的函式）。
    *   **依賴**：此服務函式需要引入 `UserModel`, `Groups`, `GroupForm`, `Session`, `log`。

2.  **修改觸發點：在 `auths.py` 中呼叫同步服務**
    *   **引入服務函式**：在 `backend/open_webui/routers/auths.py` 頂部引入：
        ```python
        from ..services.group_sync_service import synchronize_user_groups_from_sql
        # 可能還需要引入 Session, Depends, get_db 如果尚未引入
        ```
    *   **情境1：傳統帳號密碼登入 (`/signin` 路由)**
        *   影響函數： `signin`
        *   具體邏輯： 在成功驗證使用者身份 (`user` 物件被獲取) 之後，但在向前端返回 JWT 之前，呼叫 `synchronize_user_groups_from_sql(user=user, db=db)`。
    *   **情境2：OIDC 單一登入 (例如 Microsoft 登入)**
        *   影響檔案：處理 OIDC 回呼並完成本地使用者驗證/建立的相關邏輯區塊。
        *   具體邏輯：在 OIDC 登入流程中，當本地 `user` 物件被獲取或建立後，但在完成 OIDC 登入流程並返回 JWT 給前端之前，呼叫 `synchronize_user_groups_from_sql(user=user, db=db)`。
    *   **情境3：新使用者透過傳統註冊表單首次建立帳號 (`/signup` 路由)**
        *   影響函數： `signup`
        *   具體邏輯： 在 `Auths.insert_new_auth(...)` 成功執行並返回 `user` 物件之後，但在向前端返回註冊成功響應之前，呼叫 `synchronize_user_groups_from_sql(user=user, db=db)`。
    *   **核心原則**：確保在 `auths.py` 的各個成功認證使用者身份的節點，都以 `try-except` 包裹對 `synchronize_user_groups_from_sql` 的呼叫，以捕獲同步服務本身可能發生的任何異常，防止影響主流程。

3.  **必要的程式碼修改點：**
    *   **`backend/open_webui/services/group_sync_service.py` (新建)**:
        *   實現上述第 1 點描述的 `synchronize_user_groups_from_sql` 函式及其所有內部邏輯。
    *   **`backend/open_webui/routers/auths.py`**:
        *   引入 `synchronize_user_groups_from_sql`。
        *   在 `signin`, `signup` 函數內，以及處理 OIDC 登入成功的相關邏輯區塊中，於適當時機加入對 `synchronize_user_groups_from_sql(user=user, db=db)` 的呼叫，並使用 `try-except` 包裹此呼叫。
    *   **`backend/open_webui/models/groups.py` (在 `GroupTable` 類別內)**:
        *   實現或確認 `get_group_by_name(self, name: str) -> Optional[GroupModel]` 方法 (參考先前版本，建議使用不區分大小寫查詢)。
        *   實現或確認 `add_user_to_group(self, user_id: str, group_id: str) -> bool` 方法 (參考先前版本)。
        *   **新增** `get_groups_by_user_id(self, user_id: str) -> List[GroupModel]` 方法:
            ```python
            # 參考實現 (需引入相關模組)
            from typing import List, Optional
            # ... 其他引入 ...
            # from .. import models # 假設 Group 和 GroupModel 在這裡
            # from ..internal.db import get_db # 假設 get_db 在這裡
            # from sqlalchemy.orm import Session # 假設 Session 在這裡
            # from .. import config # 用於日誌
            # import logging
            # log = logging.getLogger(config.LOGGER_NAME)

            def get_groups_by_user_id(self, user_id: str) -> List[GroupModel]:
                # (此處的 db 應為 self.db，假設 GroupTable 實例化時傳入 db)
                # try:
                #     # 較為可靠的方式是遍歷所有群組，檢查 user_id 是否在其 user_ids 列表中
                #     # 這在群組數量不多時可行，但群組多時效能不佳
                #     # 更好的方式是如果資料庫支援 JSON 查詢，則使用 JSON 查詢
                #     all_groups = self.db.query(Group).all()
                #     user_groups = []
                #     for group_record in all_groups:
                #         if group_record.user_ids and user_id in group_record.user_ids:
                #             user_groups.append(GroupModel.model_validate(group_record))
                #     return user_groups
                # except Exception as e:
                #     log.error(f"Error getting groups for user_id '{user_id}': {e}")
                #     return []
                # 簡化版，假設 GroupTable 內部有 self.db
                try:
                    # 假設 user_ids 是 JSON 陣列，且資料庫支援 JSON 查詢 (例如 PostgreSQL 的 contains)
                    # 若不支援，則需要遍歷或使用其他方法
                    # groups_records = self.db.query(Group).filter(Group.user_ids.contains([user_id])).all()
                    # 為了通用性，這裡遍歷 (如原PRD建議，但需注意效能)
                    all_groups_records = self.db.query(Group).all()
                    user_groups_models = []
                    for group_record in all_groups_records:
                        if group_record.user_ids and user_id in group_record.user_ids:
                            user_groups_models.append(GroupModel.model_validate(group_record))
                    return user_groups_models
                except Exception as e:
                    log.error(f"Error getting groups for user_id '{user_id}': {e}", exc_info=True)
                    return []
            ```
        *   **新增** `remove_user_from_group(self, user_id: str, group_id: str) -> bool` 方法:
            ```python
            # 參考實現 (此處的 db 應為 self.db)
            # import time
            def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
                try:
                    group_to_update_model = self.get_group_by_id(group_id) # 假設此方法返回 GroupModel
                    if not group_to_update_model:
                        log.error(f"Group with id '{group_id}' not found when trying to remove user '{user_id}'.")
                        return False

                    # GroupModel.user_ids 可能是 tuple，轉為 list 操作
                    current_user_ids = list(group_to_update_model.user_ids) if group_to_update_model.user_ids else []
                    
                    if user_id in current_user_ids:
                        current_user_ids.remove(user_id)
                        
                        update_data = {"user_ids": current_user_ids, "updated_at": int(time.time())}
                        
                        self.db.query(Group).filter_by(id=group_id).update(update_data)
                        self.db.commit()
                        log.info(f"User '{user_id}' successfully removed from group '{group_id}'.")
                        return True
                    else:
                        log.info(f"User '{user_id}' not in group '{group_id}'. No removal action taken.")
                        return True 
                except Exception as e:
                    log.error(f"Error removing user '{user_id}' from group '{group_id}': {e}", exc_info=True)
                    return False
            ```

4.  **錯誤處理與日誌記錄的總體要求：**
    *   在 `backend/open_webui/routers/auths.py` 的 `signin`, `signup` 及 OIDC 處理函數中，對 `synchronize_user_groups_from_sql` 的呼叫應被一個總的 `try-except` 結構包圍。
    *   在 `backend/open_webui/services/group_sync_service.py` 的 `synchronize_user_groups_from_sql` 函式內部，也應有詳細的錯誤處理和日誌記錄。
    *   核心目標：確保即使群組同步功能出現任何未預期的失敗（例如 SQL Server 連線問題、資料庫操作錯誤等），也**不會影響核心的使用者登入/註冊流程的完成**。
    *   應詳細記錄流程中的每一步操作及任何潛在的錯誤，例如 SQL 連線失敗、查詢無結果、群組建立/更新失敗、使用者加入/移除群組失敗等情況，以便於後續追蹤和調試。
