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

export interface ModerationResetResponse {
  status: string;
  new_attempt: number;
  completed_scenario_indices: number[];
  message: string;
}

export interface CompletedScenariosResponse {
  completed_scenario_indices: number[];
  count: number;
}

export interface StudyStatusResponse {
  completed_at: number | null;
  completion_date: string | null;
  can_retake: boolean;
  current_attempt: number;
  message: string;
}

export interface UserSubmissionsResponse {
  user_info: { id: string; name: string; email: string };
  child_profiles: any[];
  moderation_sessions: any[];
  exit_quiz_responses: any[];
  session_activity_totals?: Record<string, number>;
}

export const finalizeModeration = async (
  token: string,
  payload: { child_id?: string; session_number?: number }
): Promise<{ updated: number }> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/moderation/finalize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const resetModerationWorkflow = async (token: string): Promise<ModerationResetResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/reset-moderation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const getCompletedScenarios = async (token: string): Promise<CompletedScenariosResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/completed-scenarios`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const getStudyStatus = async (token: string): Promise<StudyStatusResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/study-status`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const getUserSubmissions = async (token: string, userId: string): Promise<UserSubmissionsResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/admin/user-submissions/${userId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

