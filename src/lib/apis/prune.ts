import { WEBUI_API_BASE_URL } from '$lib/constants';

export const pruneData = async (
  token: string,
  days: number | null,
  exempt_archived_chats: boolean,
  exempt_chats_in_folders: boolean,
  delete_orphaned_chats: boolean = true,
  delete_orphaned_tools: boolean = false,
  delete_orphaned_functions: boolean = false,
  delete_orphaned_prompts: boolean = true,
  delete_orphaned_knowledge_bases: boolean = true,
  delete_orphaned_models: boolean = true,
  delete_orphaned_notes: boolean = true,
  delete_orphaned_folders: boolean = true,
  audio_cache_max_age_days: number | null = 30,
  delete_inactive_users_days: number | null = null,
  exempt_admin_users: boolean = true,
  exempt_pending_users: boolean = true,
  dry_run: boolean // Removed default value to ensure explicit passing
) => {
  let error = null;

  const res = await fetch(`${WEBUI_API_BASE_URL}/prune/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      days,
      exempt_archived_chats,
      exempt_chats_in_folders,
      delete_orphaned_chats,
      delete_orphaned_tools,
      delete_orphaned_functions,
      delete_orphaned_prompts,
      delete_orphaned_knowledge_bases,
      delete_orphaned_models,
      delete_orphaned_notes,
      delete_orphaned_folders,
      audio_cache_max_age_days,
      delete_inactive_users_days,
      exempt_admin_users,
      exempt_pending_users,
      dry_run
    })
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err;
      console.log(err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
};
