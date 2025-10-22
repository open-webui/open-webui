import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface WorkflowResetResponse {
  status: string;
  new_attempt: number;
  message: string;
}

export interface CurrentAttemptResponse {
  current_attempt: number;
  moderation_attempt: number;
  child_attempt: number;
  exit_attempt: number;
}

export const resetUserWorkflow = async (token: string): Promise<WorkflowResetResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/reset`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const getCurrentAttempt = async (token: string): Promise<CurrentAttemptResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/current-attempt`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};
