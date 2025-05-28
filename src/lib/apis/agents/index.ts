import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface AgentData {
  name: string;
  role: string;
  system_message: string | null;
  llm_model: string;
  skills: string | null; // Sending as string for now
}

export const createAgent = async (token: string, agentData: AgentData) => {
  let error = null;

  const res = await fetch(`${WEBUI_API_BASE_URL}/agents/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(agentData)
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json();
        throw err;
      }
      return res.json();
    })
    .catch((err) => {
      console.error(err);
      error = err.detail || 'Server connection failed';
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
};
