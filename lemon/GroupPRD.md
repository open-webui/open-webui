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

第五部分：新功能 - 使用者註冊時自動指派群組 (基於 SQL Server 資料)

功能目標：
在新使用者註冊成功後，系統將自動查詢外部 SQL Server 資料庫中的 `sp_PBA_HC_Movement` 表。根據使用者的 Email，將其指派到對應的 `[HW_Purchase_Group]` (此欄位儲存群組名稱)。如果 Open WebUI 系統中不存在具有該名稱的群組，則自動建立該群組。此自動指派功能僅在使用者首次註冊完成後執行一次。

詳細實施步驟：

1.  修改觸發點：使用者註冊流程
    -   影響檔案： `backend/open_webui/routers/auths.py`
    -   影響函數： `signup`
    -   具體邏輯： 在 `Auths.insert_new_auth(...)` 函數成功執行並返回 `user` 物件之後，但在向前端返回註冊成功響應之前，插入自動指派群組的相關程式碼。

2.  獲取新註冊使用者的資訊
    -   從 `signup` 函數中成功建立的 `user` 物件中提取：
        -   `user_email = user.email`
        -   `new_user_id = user.id`

3.  執行 SQL 查詢以獲取目標群組名稱
    -   構建 SQL 查詢語句 (應使用參數化查詢以防 SQL 注入)：
        ```sql
        SELECT DISTINCT [HW_Purchase_Group] 
        FROM [dbo].[sp_PBA_HC_Movement] 
        WHERE [Email Address] = %s AND [EndDate] IS NULL 
        ```
        *(註：`%s` 為參數佔位符，實際使用的佔位符需根據所用資料庫驅動程式的語法確定。)*
    -   執行方式： 使用 `use_mcp_tool`
        -   `server_name`: "mssql"
        -   `tool_name`: "execute_sql"
        -   `arguments`: `{"query": "SQL_QUERY_STRING_HERE", "params": [user_email]}` (假設 `execute_sql` 工具支援傳遞參數列表)。
    -   預期查詢結果：一個列表。由於查詢中 `EndDate IS NULL` 的條件以及 `DISTINCT [HW_Purchase_Group]` 的使用，預期此列表最多只包含一個元素（如果該使用者在 SQL 表中有對應的有效記錄），該元素代表目標群組的名稱。

4.  處理 SQL 查詢結果並完成群組指派
    -   檢查 SQL 查詢是否成功執行並且返回了結果 (例如，一個群組名稱列表 `group_names_from_sql`)。
    -   遍歷 `group_names_from_sql` 列表中的每一個 `group_name`：（註：根據預期，此 `group_names_from_sql` 列表最多包含一個 `group_name`）。
        -   查找或建立 Open WebUI 內部群組：
            -   調用 `Groups.get_group_by_name(group_name)` 查找群組 (此方法需在 `GroupTable` 中實現或確認已存在)。
            -   如果 `target_group` (查找到的群組物件) 為 `None` (即群組不存在)：
                -   準備群組表單資料：`group_form_data = GroupForm(name=group_name, description="由系統根據 SQL Server 資料自動建立")`。
                -   調用 `target_group = Groups.insert_new_group(user_id=new_user_id, form_data=group_form_data)` 建立新群組。
                    *(群組建立者 `user_id` 使用新註冊使用者的 ID)*
                -   記錄群組建立的日誌。如果建立失敗，記錄錯誤並繼續處理列表中的下一個 `group_name`。
            -   如果 `target_group` 成功獲取 (無論是查找到的還是新建的)，則取得其 ID：`target_group_id = target_group.id`。
        -   將使用者加入到目標群組：
            -   如果 `target_group_id` 有效：
                -   調用 `success = Groups.add_user_to_group(user_id=new_user_id, group_id=target_group_id)` 將使用者加入群組 (此方法需在 `GroupTable` 中實現或確認已存在)。
                -   記錄指派結果的日誌。

5.  必要的程式碼修改點：
    -   於 `backend/open_webui/routers/auths.py` (在 `signup` 函數內):
        -   引入 `Groups` 模型及 `GroupForm` Pydantic 模型。
        -   實現上述步驟 2、3、4 的主要業務邏輯，包括完整的錯誤處理機制 (try-except 區塊) 和詳細的日誌記錄。
    -   於 `backend/open_webui/models/groups.py` (在 `GroupTable` 類別內):
        -   實現或確認 `get_group_by_name(self, name: str) -> Optional[GroupModel]` 方法:
            ```python
            # 參考實現 (需引入相關模組如 time, func, get_db, Group, GroupModel, logging)
            def get_group_by_name(self, name: str) -> Optional[GroupModel]:
                try:
                    with get_db() as db:
                        # 建議使用不區分大小寫的方式查詢群組名稱
                        group_record = db.query(Group).filter(func.lower(Group.name) == func.lower(name)).first()
                        return GroupModel.model_validate(group_record) if group_record else None
                except Exception as e:
                    log.error(f"Error getting group by name '{name}': {e}")
                    return None
            ```
        -   實現或確認 `add_user_to_group(self, user_id: str, group_id: str) -> bool` 方法:
            ```python
            # 參考實現
            def add_user_to_group(self, user_id: str, group_id: str) -> bool:
                try:
                    group_to_update = self.get_group_by_id(group_id)
                    if not group_to_update:
                        log.error(f"Group with id '{group_id}' not found when trying to add user '{user_id}'.")
                        return False

                    current_user_ids = list(group_to_update.user_ids) # 確保操作的是列表副本
                    if user_id not in current_user_ids:
                        current_user_ids.append(user_id)
                        
                        update_data = {"user_ids": current_user_ids, "updated_at": int(time.time())}
                        
                        with get_db() as db:
                            db.query(Group).filter_by(id=group_id).update(update_data)
                            db.commit()
                        log.info(f"User '{user_id}' successfully added to group '{group_id}'.")
                        return True
                    else:
                        log.info(f"User '{user_id}' already in group '{group_id}'. No action taken.")
                        return True # 使用者已在群組中，也視為成功操作
                except Exception as e:
                    log.error(f"Error adding user '{user_id}' to group '{group_id}': {e}")
                    return False
            ```
            *(註：在 `add_user_to_group` 的實現中，更新群組時建議僅更新 `user_ids` 和 `updated_at` 欄位，以避免不必要的 `GroupUpdateForm` 構造和潛在的其他欄位意外覆寫。同時，需確保 `time` 模組已正確匯入以使用 `int(time.time())`。)*

6.  錯誤處理與日誌記錄的總體要求：
    -   在 `signup` 函數中，整個自動指派群組的邏輯區塊應被一個總的 `try-except` 結構包圍。這樣可以確保即使自動指派功能出現任何未預期的失敗，也不會影響核心的使用者註冊流程的完成。
    -   應詳細記錄流程中的每一步操作及任何潛在的錯誤，例如 SQL 連線失敗、查詢無結果、群組建立失敗等情況，以便於後續追蹤和調試。

第六部分：現有使用者群組初始化腳本

功能目標：
- 為 Open WebUI 中所有現有的使用者，根據其 Email 從外部 SQL Server 資料庫的 `sp_PBA_HC_Movement` 表中查詢對應的 `[HW_Purchase_Group]`。
- 將使用者指派到 Open WebUI 內部相應的群組。
- 如果群組不存在，則自動建立。
- 此操作旨在作為一次性的初始化過程，由管理員手動執行。

執行方式：
- 透過一個獨立的 Python 腳本 (`lemon/initial.py`) 執行。
- 此腳本需要配置資料庫連接資訊和 Open WebUI 管理員 ID。

主要邏輯：
- 連接資料庫：
    - 同時連接到 Open WebUI 的內部資料庫和外部的 SQL Server。
- 獲取現有使用者：
    - 從 Open WebUI 讀取所有使用者列表。
- 遍歷使用者（對每一位使用者）：
    - 使用其 Email 查詢 SQL Server 中的 `sp_PBA_HC_Movement` 表，獲取 `[HW_Purchase_Group]` (條件為 `EndDate IS NULL`)。
    - 如果查詢到群組名稱：
        - 在 Open WebUI 中查找是否存在同名群組。
        - 若群組不存在，則使用預設的管理員 ID 作為建立者，自動建立該群組。
        - 將目前使用者加入到該 Open WebUI 群組中（如果尚未加入）。
- 日誌記錄：
    - 詳細記錄腳本執行的每一步、成功指派、新建群組以及任何錯誤。

腳本實現：
- 完整的 Python 腳本實現細節、配置說明及執行注意事項，請參閱 `lemon/initial.py` 文件。
- 該腳本設計為可獨立運行，但需確保其執行環境能夠正確導入 Open WebUI 的相關模組並連接到所需資料庫。

重要提示：
*   在生產環境中使用此腳本前，務必在測試環境中進行充分測試。
*   執行前請備份您的 Open WebUI 資料庫。
*   腳本中的 SQL Server 連接資訊和 Open WebUI 管理員 ID 需要根據實際情況配置。
