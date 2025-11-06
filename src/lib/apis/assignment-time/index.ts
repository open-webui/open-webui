import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface AssignmentSessionActivityPayload {
  user_id: string;
  session_number: number;
  active_ms_cumulative: number;
}

export interface AssignmentSessionActivityResponse {
  id: string;
  user_id: string;
  session_number: number;
  active_ms_delta: number;
  cumulative_ms: number;
  created_at: number;
}

export const postAssignmentActivity = async (
  token: string,
  payload: AssignmentSessionActivityPayload
): Promise<AssignmentSessionActivityResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/assignment/session-activity`, {
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



