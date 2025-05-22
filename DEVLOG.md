# 開發日誌 - 使用者登入時同步群組成員資格

## 2025-05-22

### 任務
根據 `lemon/GroupPRD.md` 和 `lemon/tooluse.md` 的需求，實作在使用者登入 Open WebUI 時，根據外部 SQL Server 資料自動指派群組的功能。

### 計劃
1.  **建立 `DEVLOG.md`**: (本檔案) 記錄開發過程。
2.  **建立 `backend/open_webui/services/group_sync_service.py`**: 包含 `synchronize_user_groups_from_sql` 函式，用於處理從 SQL Server 獲取群組資訊並同步到 Open WebUI 的邏輯。
3.  **修改 `backend/open_webui/models/groups.py`**:
    *   新增/確認 `get_group_by_name(self, name: str) -> Optional[GroupModel]` 方法。
    *   新增/確認 `add_user_to_group(self, user_id: str, group_id: str) -> bool` 方法。
    *   新增 `get_groups_by_user_id(self, user_id: str) -> List[GroupModel]` 方法。
    *   新增 `remove_user_from_group(self, user_id: str, group_id: str) -> bool` 方法。
4.  **修改 `backend/open_webui/routers/auths.py`**:
    *   引入 `synchronize_user_groups_from_sql` 服務函式。
    *   在 `signin` (傳統登入)、OIDC 登入處理邏輯中以及 `signup` (新使用者註冊) 函式成功驗證使用者後，呼叫 `synchronize_user_groups_from_sql` 進行群組同步。確保使用 `try-except` 包裹此呼叫，防止同步錯誤影響核心登入/註冊流程。
5.  **測試與驗證**: 確保功能按預期運作，錯誤處理機制健全。

### 進度
- [x] 建立 `DEVLOG.md`
- [x] 建立 `backend/open_webui/services/group_sync_service.py`
- [x] 修改 `backend/open_webui/models/groups.py`
    *   確認 `get_group_by_name` 方法存在。
    *   確認 `add_user_to_group` 方法存在 (透過 `update_group_by_id` 間接實現)。
    *   新增 `get_groups_by_user_id` 方法 (實際為 `get_groups_by_member_id`)。
    *   確認 `remove_user_from_group` 方法存在 (透過 `update_group_by_id` 間接實現)。
- [x] 修改 `backend/open_webui/routers/auths.py` 和 `backend/open_webui/utils/oauth.py`
    *   在 `signin` (傳統登入) 函式中加入同步邏輯。
    *   在 `signup` (新使用者註冊) 函式中加入同步邏輯。
    *   在 `ldap_auth` (LDAP 登入) 函式中加入同步邏輯。
    *   在 OIDC 回呼處理 (`OAuthManager.handle_callback`) 中加入同步邏輯。
- [ ] 測試與驗證 (待手動執行)
