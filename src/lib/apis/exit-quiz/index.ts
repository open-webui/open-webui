import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface ExitQuizForm {
  child_id: string;
  answers: Record<string, unknown>;
  score?: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

export interface ExitQuizResponse {
  id: string;
  user_id: string;
  child_id: string;
  answers: Record<string, unknown>;
  score?: Record<string, unknown>;
  meta?: Record<string, unknown>;
  created_at: number;
  updated_at: number;
}

export const createExitQuiz = async (token: string, form: ExitQuizForm): Promise<ExitQuizResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/exit-quiz`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      authorization: `Bearer ${token}`
    },
    body: JSON.stringify(form)
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create exit quiz');
  }
  return res.json();
};

export const listExitQuiz = async (token: string, child_id?: string): Promise<ExitQuizResponse[]> => {
  const url = new URL(`${WEBUI_API_BASE_URL}/exit-quiz`);
  if (child_id) url.searchParams.set('child_id', child_id);

  const res = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      authorization: `Bearer ${token}`
    }
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to list exit quiz');
  }
  return res.json();
};


