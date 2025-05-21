# lemon/initial.py
# 一次性腳本：為 Open WebUI 現有使用者初始化群組設定

import logging
import time
import os
import sys

# --- 配置區 ---
LOG_FILE = "group_initialization.log"
# !!! 重要：請替換為實際的 Open WebUI 管理員 User ID !!!
ADMIN_USER_ID_FOR_GROUP_CREATION = "your_admin_user_id_here" # 例如 "04931460-3c0b-47f0-9c29-9002db091e9a"

# SQL Server 連接配置 (根據您的實際情況調整)
# 建議從環境變數或安全配置文件中讀取敏感資訊
SQL_SERVER_CONFIG = {
    "driver": os.getenv("SQL_DRIVER", "{ODBC Driver 17 for SQL Server}"),
    "server": os.getenv("SQL_SERVER_ADDRESS", "your_sql_server_address"),
    "database": os.getenv("SQL_DATABASE_NAME", "your_database_name"),
    "uid": os.getenv("SQL_USERNAME", "your_sql_username"),
    "pwd": os.getenv("SQL_PASSWORD", "your_sql_password"),
    "trust_cert": os.getenv("SQL_TRUST_CERT", "yes") # "yes" or "no"
}

# --- 設定日誌 ---
# 檢查LOG_FILE是否可寫
try:
    with open(LOG_FILE, 'a') as f:
        pass # Test writability
except IOError:
    print(f"錯誤：日誌文件 '{LOG_FILE}' 不可寫。請檢查權限或路徑。")
    # 可以選擇一個備用路徑或直接退出
    # LOG_FILE = os.path.join(os.path.expanduser("~"), "group_initialization.log")
    # print(f"嘗試將日誌寫入: {LOG_FILE}")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# --- Open WebUI 環境與模型導入 ---
# 腳本需要能夠訪問 Open WebUI 的模型和資料庫會話。
# 執行此腳本前，請確保環境已正確設定 (例如，在 Open WebUI 的 venv 中執行，
# 或將此腳本放置於能正確解析以下導入的路徑，並可能需要設定 PYTHONPATH)。
# 例如，如果此腳本放在 open-webui/backend/scripts/ 目录下，
# 且 open-webui/backend 在 PYTHONPATH 中，或從 backend 目錄執行此腳本。

# 嘗試將可能的 Open WebUI 後端目錄添加到 sys.path
# 這是一個嘗試，可能需要根據實際部署情況調整
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 假設此腳本在 lemon/ 子目錄，而 backend 在上一層的同級
PROJECT_ROOT_GUESS = os.path.abspath(os.path.join(SCRIPT_DIR, '..')) # 指向 open-webui
BACKEND_DIR_GUESS = os.path.join(PROJECT_ROOT_GUESS, 'backend')

if BACKEND_DIR_GUESS not in sys.path:
    sys.path.insert(0, BACKEND_DIR_GUESS)
if PROJECT_ROOT_GUESS not in sys.path: # 有些導入可能相對於專案根目錄
    sys.path.insert(0, PROJECT_ROOT_GUESS)


try:
    from open_webui.internal.db import get_db
    from open_webui.models.users import UsersTable
    from open_webui.models.groups import GroupTable, GroupForm
    
    # 實例化 Table 操作類
    Users = UsersTable()
    Groups = GroupTable()

except ImportError as e:
    log.error(f"無法導入 Open WebUI 模組: {e}")
    log.error(f"目前的 sys.path: {sys.path}")
    log.error("請確保腳本在正確的 Open WebUI 環境中執行，且 PYTHONPATH 設定正確 (可能需要將 Open WebUI 的 backend 目錄加入 PYTHONPATH)。")
    sys.exit(1)
except Exception as e:
    log.error(f"導入 Open WebUI 模組時發生非預期的錯誤: {e}", exc_info=True)
    sys.exit(1)

# --- SQL Server 連接與查詢 ---
def get_sql_server_connection():
    try:
        import pyodbc
    except ImportError:
        log.error("pyodbc 套件未安裝。請執行 'pip install pyodbc' (確保在正確的 Python 環境中)。")
        return None

    conn_str_parts = [
        f"DRIVER={SQL_SERVER_CONFIG['driver']}",
        f"SERVER={SQL_SERVER_CONFIG['server']}",
        f"DATABASE={SQL_SERVER_CONFIG['database']}",
    ]
    # 根據身份驗證方式添加 UID/PWD 或 trusted_connection
    if SQL_SERVER_CONFIG['uid'] and SQL_SERVER_CONFIG['pwd']:
        conn_str_parts.append(f"UID={SQL_SERVER_CONFIG['uid']}")
        conn_str_parts.append(f"PWD={SQL_SERVER_CONFIG['pwd']}")
    elif os.name == 'nt': # Windows 環境下可以嘗試信任連接
        conn_str_parts.append("Trusted_Connection=yes")
    else: # 其他系統如果沒有 UID/PWD，可能連接失敗
        log.warning("未提供 SQL Server 的 UID/PWD，且非 Windows 環境，可能無法使用信任連接。")


    if SQL_SERVER_CONFIG['trust_cert'].lower() == 'yes':
        conn_str_parts.append("TrustServerCertificate=yes")
    
    conn_str = ";".join(conn_str_parts)
    log.info(f"嘗試連接 SQL Server，連接字串 (部分隱藏): DRIVER={SQL_SERVER_CONFIG['driver']};SERVER={SQL_SERVER_CONFIG['server']};DATABASE={SQL_SERVER_CONFIG['database']};...")

    try:
        conn = pyodbc.connect(conn_str, timeout=5) # 添加連接超時
        log.info("成功連接到 SQL Server。")
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        log.error(f"連接 SQL Server 失敗: {sqlstate} - {ex}")
        return None

def query_external_sql_for_group(conn, email: str) -> str | None:
    """
    查詢外部 SQL Server 以獲取使用者的 HW_Purchase_Group。
    預期每個 email 最多返回一個群組名稱。
    """
    query = """
    SELECT DISTINCT [HW_Purchase_Group]
    FROM [dbo].[sp_PBA_HC_Movement]
    WHERE [Email Address] = ? AND [EndDate] IS NULL
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, email)
            row = cursor.fetchone()
            if row and row[0]:
                group_name = str(row[0]).strip()
                if group_name:
                    return group_name
            return None
    except pyodbc.Error as e:
        log.error(f"查詢 SQL Server 時發生錯誤 (Email: {email}): {e}")
        return None
    except Exception as e:
        log.error(f"查詢 SQL Server 時發生非 pyodbc 錯誤 (Email: {email}): {e}", exc_info=True)
        return None


# --- 主腳本邏輯 ---
def initialize_groups_for_existing_users():
    log.info("開始為現有使用者初始化群組設定...")

    if ADMIN_USER_ID_FOR_GROUP_CREATION == "your_admin_user_id_here" or not ADMIN_USER_ID_FOR_GROUP_CREATION:
        log.error("錯誤：ADMIN_USER_ID_FOR_GROUP_CREATION 未設定。請在腳本中設定一個有效的管理員 User ID。")
        return

    sql_conn = get_sql_server_connection()
    if not sql_conn:
        log.error("無法連接到 SQL Server，腳本中止。")
        return

    processed_users_count = 0
    assigned_to_group_count = 0
    groups_created_count = 0
    users_already_in_group_count = 0

    try:
        with get_db() as ow_db:
            log.info("成功連接到 Open WebUI 資料庫。")

            all_ow_users = Users.get_users(db=ow_db)
            if not all_ow_users:
                log.info("在 Open WebUI 中沒有找到任何使用者。")
                return
            
            total_users = len(all_ow_users)
            log.info(f"在 Open WebUI 中找到 {total_users} 位使用者。")

            for i, ow_user in enumerate(all_ow_users):
                processed_users_count += 1
                log.info(f"處理中 ({i+1}/{total_users}): {ow_user.email} (ID: {ow_user.id})")

                if not ow_user.email:
                    log.warning(f"使用者 ID {ow_user.id} (名稱: {ow_user.name}) 的 Email 為空，跳過 SQL 查詢。")
                    continue

                hw_purchase_group_name = query_external_sql_for_group(sql_conn, ow_user.email)

                if hw_purchase_group_name:
                    log.info(f"使用者 {ow_user.email} 從 SQL Server 對應到 HW_Purchase_Group: '{hw_purchase_group_name}'")

                    target_group_model = Groups.get_group_by_name(db=ow_db, name=hw_purchase_group_name)

                    if not target_group_model:
                        log.info(f"群組 '{hw_purchase_group_name}' 在 Open WebUI 中不存在，正在建立...")
                        try:
                            group_form = GroupForm(
                                name=hw_purchase_group_name,
                                description="由批次初始化程序自動建立"
                            )
                            target_group_model = Groups.insert_new_group(
                                db=ow_db,
                                user_id=ADMIN_USER_ID_FOR_GROUP_CREATION,
                                form_data=group_form
                            )
                            if target_group_model:
                                log.info(f"成功建立群組 '{target_group_model.name}' (ID: {target_group_model.id})")
                                groups_created_count += 1
                            else:
                                log.error(f"建立群組 '{hw_purchase_group_name}' 失敗 (insert_new_group 返回 None)。跳過此使用者於此群組的指派。")
                                continue
                        except Exception as e:
                            log.error(f"建立群組 '{hw_purchase_group_name}' 時發生錯誤: {e}。跳過此使用者於此群組的指派。", exc_info=True)
                            continue
                    else:
                        log.info(f"群組 '{target_group_model.name}' (ID: {target_group_model.id}) 已在 Open WebUI 中找到。")

                    if target_group_model and target_group_model.id:
                        try:
                            # 檢查使用者是否已在群組中 (add_user_to_group 內部通常會處理，但明確檢查更好)
                            # GroupModel 應該有 user_ids 屬性
                            if hasattr(target_group_model, 'user_ids') and ow_user.id in target_group_model.user_ids:
                                log.info(f"使用者 {ow_user.email} 已在群組 '{target_group_model.name}' 中。無需操作。")
                                users_already_in_group_count +=1
                                assigned_to_group_count +=1 # 也算作已指派
                            else:
                                success = Groups.add_user_to_group(db=ow_db, user_id=ow_user.id, group_id=target_group_model.id)
                                if success:
                                    log.info(f"已成功將使用者 {ow_user.email} 加入到群組 '{target_group_model.name}'。")
                                    assigned_to_group_count +=1
                                else:
                                    # add_user_to_group 應該在內部記錄更詳細的失敗原因
                                    log.warning(f"未能將使用者 {ow_user.email} 加入群組 '{target_group_model.name}' (add_user_to_group 返回 False)。")
                        except Exception as e:
                            log.error(f"將使用者 {ow_user.email} 加入群組 '{target_group_model.name}' 時發生錯誤: {e}", exc_info=True)
                    else:
                        log.error(f"目標群組 '{hw_purchase_group_name}' 無效或無 ID，無法加入使用者 {ow_user.email}。")
                else:
                    log.info(f"使用者 {ow_user.email} 在 SQL Server 中沒有對應的 HW_Purchase_Group (或其 EndDate 不為 NULL，或群組名稱為空)。")
    
    except Exception as e:
        log.error(f"處理 Open WebUI 資料庫操作時發生未預期錯誤: {e}", exc_info=True)
    finally:
        if sql_conn:
            try:
                sql_conn.close()
                log.info("已關閉 SQL Server 連接。")
            except pyodbc.Error as e:
                log.error(f"關閉 SQL Server 連接時發生錯誤: {e}")


    log.info(f"""
    --------------------------------------------------
    現有使用者群組初始化腳本執行完畢。
    總共處理 Open WebUI 使用者數: {processed_users_count}
    成功指派或確認已在群組中的使用者數: {assigned_to_group_count}
    其中，新加入到群組的使用者數: {assigned_to_group_count - users_already_in_group_count}
    其中，已在目標群組中的使用者數: {users_already_in_group_count}
    新建立的 Open WebUI 群組數: {groups_created_count}
    詳細日誌請見: {LOG_FILE}
    --------------------------------------------------
    """)

if __name__ == "__main__":
    log.info("="*50)
    log.info("執行 Open WebUI 現有使用者群組初始化腳本")
    log.info("="*50)
    
    print("\n警告：此腳本將嘗試修改 Open WebUI 資料庫並與外部 SQL Server 互動。")
    print("在執行前，請確保：")
    print(f"1. ADMIN_USER_ID_FOR_GROUP_CREATION 已在腳本中正確設定 (目前: '{ADMIN_USER_ID_FOR_GROUP_CREATION}')。")
    print(f"2. SQL Server 連接參數 (SQL_SERVER_CONFIG) 已正確設定 (或透過環境變數)。")
    print(f"   目前伺服器: {SQL_SERVER_CONFIG.get('server')}, 資料庫: {SQL_SERVER_CONFIG.get('database')}")
    print(f"3. Python 環境中已安裝 'pyodbc' 套件。")
    print(f"4. 此腳本可以正確導入 Open WebUI 的內部模組 (環境/PYTHONPATH 設定正確)。")
    print(f"5. 您已備份 Open WebUI 資料庫，並建議首先在測試環境中運行此腳本。")
    print(f"6. 日誌將寫入到 '{os.path.abspath(LOG_FILE)}'。")
    
    confirm = input("\n請仔細閱讀以上說明。是否確認執行此腳本? (yes/no): ")
    if confirm.lower() == 'yes':
        log.info("使用者確認執行。")
        initialize_groups_for_existing_users()
    else:
        log.info("腳本執行已由使用者取消。")
        print("腳本執行已取消。")
