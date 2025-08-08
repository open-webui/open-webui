import logging
import time
import os
import socket
from typing import List, Set, Tuple, Dict
from datetime import datetime

import pyodbc
from sqlalchemy.orm import Session

from .. import config
from ..models.users import UserModel
from ..models.groups import Groups, GroupForm, GroupModel

log = logging.getLogger(__name__)

# SQL Server Connection Configuration for Group Sync
# Priority: Environment Variables > Default Values
# Using GROUP_SYNC_MSSQL_ prefix to distinguish from backend database configuration
GROUP_SYNC_MSSQL_SERVER = os.getenv("GROUP_SYNC_MSSQL_SERVER", os.getenv("SQL_SERVER", ""))
GROUP_SYNC_MSSQL_DATABASE = os.getenv("GROUP_SYNC_MSSQL_DATABASE", os.getenv("SQL_DATABASE", ""))
GROUP_SYNC_MSSQL_USERNAME = os.getenv("GROUP_SYNC_MSSQL_USERNAME", os.getenv("SQL_USERNAME", ""))
GROUP_SYNC_MSSQL_PASSWORD = os.getenv("GROUP_SYNC_MSSQL_PASSWORD", os.getenv("SQL_PASSWORD", ""))
GROUP_SYNC_MSSQL_DRIVER = os.getenv("GROUP_SYNC_MSSQL_DRIVER", os.getenv("SQL_DRIVER", "ODBC Driver 17 for SQL Server"))
GROUP_SYNC_MSSQL_TIMEOUT = int(os.getenv("GROUP_SYNC_MSSQL_TIMEOUT", os.getenv("SQL_TIMEOUT", "5")))
GROUP_SYNC_MSSQL_ENCRYPT = "yes" if os.getenv("GROUP_SYNC_MSSQL_ENCRYPT", os.getenv("SQL_ENCRYPT", "yes")).lower() == "yes" else "no"
GROUP_SYNC_MSSQL_TRUST_CERT = "yes" if os.getenv("GROUP_SYNC_MSSQL_TRUST_CERT", os.getenv("SQL_TRUST_SERVER_CERT", "no")).lower() == "yes" else "no"

# Connection string with extended options
SQL_CONNECTION_STRING = (
    f"DRIVER={{{GROUP_SYNC_MSSQL_DRIVER}}};"
    f"SERVER={GROUP_SYNC_MSSQL_SERVER};"
    f"DATABASE={GROUP_SYNC_MSSQL_DATABASE};"
    f"UID={GROUP_SYNC_MSSQL_USERNAME};"
    f"PWD={GROUP_SYNC_MSSQL_PASSWORD};"
    f"Encrypt={GROUP_SYNC_MSSQL_ENCRYPT};"
    f"TrustServerCertificate={GROUP_SYNC_MSSQL_TRUST_CERT};"
    f"Connection Timeout={GROUP_SYNC_MSSQL_TIMEOUT}"
)

# Connection monitoring
_connection_stats = {
    "last_success": None,
    "last_error": None,
    "total_attempts": 0,
    "success_count": 0,
    "error_count": 0,
    "avg_connect_time": 0.0
}

def get_connection_string() -> str:
    """
    Get the current connection string configuration
    Returns sanitized version (password hidden) for logging
    """
    sanitized = SQL_CONNECTION_STRING.replace(GROUP_SYNC_MSSQL_PASSWORD, "********")
    log.debug(f"Current connection string (sanitized): {sanitized}")
    return SQL_CONNECTION_STRING

def get_connection_stats() -> Dict:
    """
    Get SQL Server connection statistics
    
    Returns:
        Dict containing connection statistics and health metrics
    """
    return {
        "last_success": _connection_stats["last_success"],
        "last_error": _connection_stats["last_error"],
        "success_rate": (_connection_stats["success_count"] / _connection_stats["total_attempts"] * 100) 
            if _connection_stats["total_attempts"] > 0 else 0,
        "avg_connect_time": _connection_stats["avg_connect_time"],
        "total_attempts": _connection_stats["total_attempts"],
        "status": "healthy" if (_connection_stats["last_success"] and 
            (not _connection_stats["last_error"] or 
             _connection_stats["last_success"] > _connection_stats["last_error"]))
            else "error"
    }

def diagnose_connection() -> Dict[str, any]:
    """
    Perform diagnostic tests on SQL Server connection
    
    Returns:
        Dict containing diagnostic results
    """
    diagnostics = {
        "server_reachable": False,
        "driver_available": False,
        "connection_possible": False,
        "auth_successful": False,
        "database_accessible": False,
        "errors": []
    }

    # Check if server is reachable
    try:
        host = GROUP_SYNC_MSSQL_SERVER.split(',')[0]  # Handle named instances
        port = 1433  # Default SQL Server port
        socket.create_connection((host, port), timeout=3)
        diagnostics["server_reachable"] = True
    except Exception as e:
        diagnostics["errors"].append(f"Server unreachable: {str(e)}")
        return diagnostics

    # Check if driver is available
    try:
        drivers = pyodbc.drivers()
        diagnostics["driver_available"] = SQL_DRIVER in drivers
        if not diagnostics["driver_available"]:
            diagnostics["errors"].append(f"Driver {SQL_DRIVER} not found. Available drivers: {drivers}")
            return diagnostics
    except Exception as e:
        diagnostics["errors"].append(f"Error checking drivers: {str(e)}")
        return diagnostics

    # Test basic connection (without database)
    try:
        base_conn_string = (
            f"DRIVER={{{SQL_DRIVER}}};"
            f"SERVER={GROUP_SYNC_MSSQL_SERVER};"
            f"UID={GROUP_SYNC_MSSQL_USERNAME};"
            f"PWD={GROUP_SYNC_MSSQL_PASSWORD}"
        )
        with pyodbc.connect(base_conn_string, timeout=5) as conn:
            diagnostics["connection_possible"] = True
            diagnostics["auth_successful"] = True
    except pyodbc.Error as e:
        diagnostics["errors"].append(f"Connection/auth error: {str(e)}")
        return diagnostics

    # Test database access
    try:
        with pyodbc.connect(SQL_CONNECTION_STRING, timeout=5) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchall()
                diagnostics["database_accessible"] = True
    except pyodbc.Error as e:
        diagnostics["errors"].append(f"Database access error: {str(e)}")

    return diagnostics

def verify_sql_schema() -> Dict[str, bool]:
    """
    Verify required SQL Server tables and schema
    
    Returns:
        Dict containing verification results
    """
    schema_status = {
        "table_exists": False,
        "required_columns": False,
        "errors": []
    }
    
    try:
        with pyodbc.connect(SQL_CONNECTION_STRING) as conn:
            with conn.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = 'sp_PBA_HC_Movement'
                """)
                schema_status["table_exists"] = cursor.fetchone()[0] > 0
                
                if not schema_status["table_exists"]:
                    schema_status["errors"].append("Table 'sp_PBA_HC_Movement' not found")
                    return schema_status

                # Check required columns
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'sp_PBA_HC_Movement'
                    AND COLUMN_NAME IN ('Email Address', 'HW_Purchase_Group', 'EndDate')
                """)
                column_count = cursor.fetchone()[0]
                schema_status["required_columns"] = column_count == 3
                
                if not schema_status["required_columns"]:
                    schema_status["errors"].append("Missing required columns")
    
    except Exception as e:
        schema_status["errors"].append(f"Schema verification error: {str(e)}")
    
    return schema_status

def test_sql_connection() -> Tuple[bool, str]:
    """
    Test the SQL Server connection and return status
    
    Returns:
        Tuple[bool, str]: (success status, message)
    """
    try:
        start_time = time.time()
        _connection_stats["total_attempts"] += 1
        
        with pyodbc.connect(SQL_CONNECTION_STRING, timeout=5) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchall()
        
        connect_time = time.time() - start_time
        _connection_stats["last_success"] = datetime.now()
        _connection_stats["success_count"] += 1
        _connection_stats["avg_connect_time"] = (
            (_connection_stats["avg_connect_time"] * (_connection_stats["success_count"] - 1) + connect_time) / 
            _connection_stats["success_count"]
        )
        
        log.info(f"SQL Server connection test successful. Connect time: {connect_time:.2f}s")
        return True, f"Connection successful (took {connect_time:.2f}s)"
    
    except pyodbc.Error as e:
        _connection_stats["last_error"] = datetime.now()
        _connection_stats["error_count"] += 1
        error_msg = f"SQL Server connection error: {str(e)}"
        log.error(error_msg)
        return False, error_msg
    except Exception as e:
        _connection_stats["last_error"] = datetime.now()
        _connection_stats["error_count"] += 1
        error_msg = f"Unexpected error testing SQL connection: {str(e)}"
        log.error(error_msg, exc_info=True)
        return False, error_msg

def execute_sql_query(query: str, params: tuple) -> List[str]:
    """
    Execute SQL query using pyodbc and return results
    """
    try:
        log.info(f"Connecting to SQL Server and executing query for user email: {params[0]}")
        start_time = time.time()
        
        with pyodbc.connect(SQL_CONNECTION_STRING) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                group_names = [row[0] for row in results if row[0]]
                
        query_time = time.time() - start_time
        log.info(f"SQL query completed in {query_time:.2f} seconds. Found {len(group_names)} groups.")
        return group_names
        
    except pyodbc.Error as e:
        log.error(f"SQL Server connection/query error: {str(e)}")
        return []
    except Exception as e:
        log.error(f"Unexpected error during SQL query execution: {str(e)}", exc_info=True)
        return []

async def synchronize_user_groups_from_sql(user: UserModel, db: Session):
    """
    Synchronizes a user's group memberships in Open WebUI with data from SQL Server.

    - Fetches group names for the user from SQL Server sp_PBA_HC_Movement table based on email
    - If no groups are found in SQL, assigns the user to an "Unassigned" group (creating it if needed).
    - Compares with the user's current groups in Open WebUI
    - Adds the user to groups they should be in (creating groups if needed)
    - Removes the user from groups they should no longer be in
    - All operations are logged, and errors are handled to prevent disruption
    """
    start_time = time.time()
    log.info(f"Starting group synchronization for user: {user.email} (ID: {user.id})")
    
    try:
        groups_table = Groups  # Use the Groups instance directly

        # 1. Execute SQL query to get target group names from SQL Server
        sql_query = """
            SELECT [HW_Purchase_Group] 
            FROM [dbo].[sp_PBA_HC_Movement] 
            WHERE [Email Address] = ? AND [EndDate] IS NULL
        """
        log.debug(f"Executing SQL query to fetch groups for user {user.email}")
        target_group_names_from_sql = execute_sql_query(sql_query, (user.email,))
        
        if not isinstance(target_group_names_from_sql, list):
            log.error(f"SQL query for user {user.email} did not return a list. Received: {target_group_names_from_sql}")
            # Consider if returning here is the best approach or if it should proceed to unassigned
            return 
        
        log.info(f"Found {len(target_group_names_from_sql)} target groups from SQL for user {user.email}")
        log.debug(f"Target groups from SQL: {target_group_names_from_sql}")

        # Initialize set for final target Open WebUI group IDs
        final_target_ouw_group_ids_set: Set[str] = set()
        unassigned_group_name = "Unassigned"

        if not target_group_names_from_sql:
            # SQL query returned no specific groups, assign to "Unassigned"
            log.info(f"No specific groups found for user {user.email} in SQL. Attempting to assign to '{unassigned_group_name}'.")
            unassigned_group = groups_table.get_group_by_name(unassigned_group_name)
            if not unassigned_group:
                log.info(f"'{unassigned_group_name}' group not found, creating it.")
                try:
                    form_data_unassigned = GroupForm(
                        name=unassigned_group_name,
                        description="Automatically created unassigned group for users with no specific groups from SQL"
                    )
                    # Ensure user_id for group creation is appropriate (e.g., admin or current user)
                    # Using user.id as per PRD, but consider if a system/admin ID is better for a shared group
                    unassigned_group = groups_table.insert_new_group(user_id=user.id, form_data=form_data_unassigned)
                    if unassigned_group:
                        log.info(f"Successfully created '{unassigned_group_name}' group (ID: {unassigned_group.id}).")
                    else:
                        log.error(f"Failed to create '{unassigned_group_name}' group.")
                except Exception as e_create_unassigned:
                    log.error(f"Error creating '{unassigned_group_name}' group: {str(e_create_unassigned)}", exc_info=True)
            
            if unassigned_group and unassigned_group.id:
                final_target_ouw_group_ids_set.add(unassigned_group.id)
                log.debug(f"User {user.email} will be targeted for '{unassigned_group_name}' group (ID: {unassigned_group.id}).")
            else:
                log.warning(f"Could not find or create '{unassigned_group_name}' group for user {user.email}. User will not be assigned to it.")
        else:
            # Process target group names from SQL as before
            for group_name_from_sql in target_group_names_from_sql:
                if not group_name_from_sql or not isinstance(group_name_from_sql, str):
                    log.warning(f"Invalid group name received from SQL: {group_name_from_sql}. Skipping.")
                    continue

                group_name_from_sql = group_name_from_sql.strip()
                if not group_name_from_sql:
                    log.warning(f"Empty group name after stripping. Skipping.")
                    continue

                ouw_group = groups_table.get_group_by_name(group_name_from_sql)
                if ouw_group:
                    final_target_ouw_group_ids_set.add(ouw_group.id)
                    log.debug(f"Existing group found: '{group_name_from_sql}' (ID: {ouw_group.id})")
                else:
                    log.info(f"Creating new group '{group_name_from_sql}' as it's not found in OpenWebUI.")
                    try:
                        form_data_sql_group = GroupForm(
                            name=group_name_from_sql,
                            description="Automatically created group from SQL Server sync" # Updated description
                        )
                        new_group = groups_table.insert_new_group(user_id=user.id, form_data=form_data_sql_group)
                        if new_group:
                            final_target_ouw_group_ids_set.add(new_group.id)
                            log.info(f"Successfully created new group '{new_group.name}' (ID: {new_group.id})")
                        else:
                            log.error(f"Failed to create group '{group_name_from_sql}' from SQL.")
                    except Exception as e_create_sql_group:
                        log.error(f"Error creating group '{group_name_from_sql}' from SQL: {str(e_create_sql_group)}", exc_info=True)
        
        log.info(f"Final target OpenWebUI group IDs for user {user.email}: {final_target_ouw_group_ids_set}")

        # 2.A. Get user's current Open WebUI group IDs (moved after determining final_target_ouw_group_ids_set)
        current_ouw_groups_models: List[GroupModel] = groups_table.get_groups_by_member_id(user.id)
        current_ouw_group_ids_set: Set[str] = {group.id for group in current_ouw_groups_models}
        log.info(f"User {user.email} currently belongs to {len(current_ouw_group_ids_set)} OpenWebUI groups.")
        log.debug(f"Current OpenWebUI group IDs: {current_ouw_group_ids_set}")

        # 2.C. Compare and execute sync operations
        groups_to_add_ids = final_target_ouw_group_ids_set - current_ouw_group_ids_set
        groups_to_remove_ids = current_ouw_group_ids_set - final_target_ouw_group_ids_set

        if groups_to_add_ids:
            log.info(f"Adding user {user.email} to {len(groups_to_add_ids)} new groups: {groups_to_add_ids}")
            for group_id_to_add in groups_to_add_ids:
                try:
                    success = groups_table.add_user_to_group(user_id=user.id, group_id=group_id_to_add)
                    if success:
                        log.info(f"Successfully added user {user.email} to group ID {group_id_to_add}")
                    else:
                        log.error(f"Failed to add user {user.email} to group ID {group_id_to_add}")
                except Exception as e_add:
                    log.error(f"Error adding user {user.email} to group ID {group_id_to_add}: {str(e_add)}", exc_info=True)
        
        if groups_to_remove_ids:
            log.info(f"Removing user {user.email} from {len(groups_to_remove_ids)} groups: {groups_to_remove_ids}")
            for group_id_to_remove in groups_to_remove_ids:
                try:
                    success = groups_table.remove_user_from_group(user_id=user.id, group_id=group_id_to_remove)
                    if success:
                        log.info(f"Successfully removed user {user.email} from group ID {group_id_to_remove}")
                    else:
                        log.error(f"Failed to remove user {user.email} from group ID {group_id_to_remove}")
                except Exception as e_remove:
                    log.error(f"Error removing user {user.email} from group ID {group_id_to_remove}: {str(e_remove)}", exc_info=True)

        total_time = time.time() - start_time
        log.info(f"Group synchronization completed for user {user.email} in {total_time:.2f} seconds")
        log.info(f"Summary for {user.email}: Added to {len(groups_to_add_ids)} groups, Removed from {len(groups_to_remove_ids)} groups.")

    except Exception as e:
        log.error(f"Unhandled error during group synchronization for user {user.email}: {str(e)}", exc_info=True)
        # Not re-raising the exception to avoid disrupting the main auth flow
