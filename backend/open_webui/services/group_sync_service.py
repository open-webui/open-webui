import logging
import time
from typing import List, Set

from sqlalchemy.orm import Session

from .. import config
from ..models.users import UserModel
from ..models.groups import Groups, GroupForm, GroupModel # Assuming GroupModel is the Pydantic model for a group
# Placeholder for MCP tool usage, actual import might differ
# from ..utils.mcp_utils import mcp_execute_sql # Or however MCP tools are accessed

log = logging.getLogger(__name__) # Changed to use __name__

# This is a placeholder. The actual MCP tool usage will depend on its integration.
# For now, we'll simulate the call and its expected response structure.
def _execute_sql_via_mcp(query: str, params: tuple) -> List[str]:
    """
    Placeholder function to simulate calling the 'mssql' MCP tool's 'execute_sql'.
    In a real scenario, this would use the <use_mcp_tool> mechanism.
    """
    log.info(f"Simulating MCP SQL execution for query: {query} with params: {params}")
    # Simulate a response: list of group names
    # Example: if params[0] (email) is "test@example.com", return ["GroupA", "GroupB"]
    if params and params[0] == "test@example.com":
        return ["HR_Group", "Finance_Group"]
    return []

async def synchronize_user_groups_from_sql(user: UserModel, db: Session):
    """
    Synchronizes a user's group memberships in Open WebUI with data from an external SQL Server.

    - Fetches group names for the user from the SQL Server's sp_PBA_HC_Movement table based on email.
    - Compares with the user's current groups in Open WebUI.
    - Adds the user to groups they should be in (creating groups if they don't exist in Open WebUI).
    - Removes the user from groups they should no longer be in.
    - All operations are logged, and errors are handled to prevent disruption of the main login/signup flow.
    """
    log.info(f"Starting group synchronization for user: {user.email} (ID: {user.id})")
    try:
        groups_table = Groups(db)

        # 1. Execute SQL query to get target group names from SQL Server
        # IMPORTANT: Use parameterized queries to prevent SQL injection.
        # The exact placeholder (%s, ?, etc.) depends on the DB driver used by the MCP tool.
        sql_query = """
            SELECT [HW_Purchase_Group] 
            FROM [dbo].[sp_PBA_HC_Movement] 
            WHERE [Email Address] = %s AND [EndDate] IS NULL
        """
        # In a real scenario, this would be:
        # target_group_names_from_sql_result = await mcp_client.execute_sql("mssql", "execute_sql", {"query": sql_query, "params": [user.email]})
        # For now, using the placeholder:
        # Note: The MCP tool is synchronous in the example, but if it's async, this call should be awaited.
        # For simplicity in this plan, assuming a synchronous or wrapped call.
        # The PRD implies using use_mcp_tool, which is an action taken by the AI, not directly callable Python code.
        # This function would be called *after* the AI has used the tool and has the result.
        # So, this function should ideally receive target_group_names_from_sql as a parameter,
        # or the calling code in auths.py should handle the MCP call.
        # For now, let's assume the MCP call happens here for encapsulation, using a simulated function.

        # SIMULATED MCP CALL
        # In reality, the AI would use <use_mcp_tool> and pass the result to this function,
        # or this function would be structured to be called after the tool use.
        # For the purpose of generating this file, we'll use a placeholder.
        # The actual call would be something like:
        # mcp_response = await some_mcp_handler.call_tool(
        #     server_name="mssql",
        #     tool_name="execute_sql",
        #     arguments={"query": sql_query, "parameters": [user.email]} # Assuming 'parameters' is the arg name
        # )
        # target_group_names_from_sql = mcp_response.get("result", []) # Adjust based on actual MCP response

        # Using a direct simulated call for now:
        target_group_names_from_sql = _execute_sql_via_mcp(sql_query, (user.email,))
        
        if not isinstance(target_group_names_from_sql, list):
            log.error(f"SQL query for user {user.email} did not return a list. Received: {target_group_names_from_sql}")
            target_group_names_from_sql = []
        
        log.info(f"Target groups from SQL for {user.email}: {target_group_names_from_sql}")

        # 2.A. Get user's current Open WebUI group IDs
        current_ouw_groups_models: List[GroupModel] = groups_table.get_groups_by_user_id(user.id)
        current_ouw_group_ids_set: Set[str] = {group.id for group in current_ouw_groups_models}
        log.info(f"User {user.email} is currently in OpenWebUI groups (IDs): {current_ouw_group_ids_set}")

        # 2.B. Process target group names from SQL and get/create their Open WebUI group IDs
        final_target_ouw_group_ids_set: Set[str] = set()
        for group_name_from_sql in target_group_names_from_sql:
            if not group_name_from_sql or not isinstance(group_name_from_sql, str):
                log.warning(f"Invalid group name received from SQL for user {user.email}: {group_name_from_sql}. Skipping.")
                continue

            group_name_from_sql = group_name_from_sql.strip()
            if not group_name_from_sql:
                log.warning(f"Empty group name after stripping for user {user.email}. Skipping.")
                continue

            ouw_group = groups_table.get_group_by_name(group_name_from_sql)
            if ouw_group:
                final_target_ouw_group_ids_set.add(ouw_group.id)
                log.info(f"Group '{group_name_from_sql}' found in OpenWebUI with ID: {ouw_group.id}")
            else:
                log.info(f"Group '{group_name_from_sql}' not found in OpenWebUI. Creating it...")
                try:
                    # The user_id for group creation can be the current user or a system admin ID.
                    # PRD suggests user.id for now.
                    form_data = GroupForm(
                        name=group_name_from_sql,
                        description="由系統根據 SQL Server 資料自動建立/同步"
                    )
                    # insert_new_group expects user_id and form_data
                    # Assuming user_id here refers to the creator of the group.
                    # If the group is system-generated, a dedicated system user ID might be better.
                    # For now, following PRD's user.id.
                    new_group = groups_table.insert_new_group(user_id=user.id, form_data=form_data)
                    if new_group:
                        final_target_ouw_group_ids_set.add(new_group.id)
                        log.info(f"Successfully created group '{new_group.name}' with ID: {new_group.id} for user {user.email}")
                    else:
                        log.error(f"Failed to create group '{group_name_from_sql}' for user {user.email}")
                except Exception as e_create:
                    log.error(f"Exception creating group '{group_name_from_sql}' for user {user.email}: {e_create}", exc_info=True)
        
        log.info(f"Final target OpenWebUI group IDs for {user.email} based on SQL data: {final_target_ouw_group_ids_set}")

        # 2.C. Compare and execute sync operations
        groups_to_add_ids = final_target_ouw_group_ids_set - current_ouw_group_ids_set
        groups_to_remove_ids = current_ouw_group_ids_set - final_target_ouw_group_ids_set

        if groups_to_add_ids:
            log.info(f"Adding user {user.email} to OpenWebUI groups (IDs): {groups_to_add_ids}")
            for group_id_to_add in groups_to_add_ids:
                try:
                    success = groups_table.add_user_to_group(user_id=user.id, group_id=group_id_to_add)
                    if success:
                        log.info(f"Successfully added user {user.email} to group ID {group_id_to_add}")
                    else:
                        log.error(f"Failed to add user {user.email} to group ID {group_id_to_add}")
                except Exception as e_add:
                    log.error(f"Exception adding user {user.email} to group ID {group_id_to_add}: {e_add}", exc_info=True)
        
        if groups_to_remove_ids:
            log.info(f"Removing user {user.email} from OpenWebUI groups (IDs): {groups_to_remove_ids}")
            for group_id_to_remove in groups_to_remove_ids:
                try:
                    success = groups_table.remove_user_from_group(user_id=user.id, group_id=group_id_to_remove)
                    if success:
                        log.info(f"Successfully removed user {user.email} from group ID {group_id_to_remove}")
                    else:
                        log.error(f"Failed to remove user {user.email} from group ID {group_id_to_remove}")
                except Exception as e_remove:
                    log.error(f"Exception removing user {user.email} from group ID {group_id_to_remove}: {e_remove}", exc_info=True)

        log.info(f"Group synchronization completed for user: {user.email}")

    except Exception as e:
        # Catch-all for any unexpected errors during the sync process
        log.error(f"Unhandled exception during group synchronization for user {user.email}: {e}", exc_info=True)
        # IMPORTANT: Do not re-raise the exception here, to avoid breaking login/signup.
        # The error is logged, and the main auth flow should continue.
