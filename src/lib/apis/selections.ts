import type { User } from '$lib/stores';

export interface Selection {
  id: string;
  user_id: string;
  chat_id: string;
  message_id: string;
  role: 'user' | 'assistant';
  selected_text: string;
  child_marker?: string;
  context?: string;
  meta?: Record<string, any>;
  created_at: number;
  updated_at: number;
}

export interface SelectionForm {
  chat_id: string;
  message_id: string;
  role: 'user' | 'assistant';
  selected_text: string;
  child_marker?: string;
  context?: string;
  meta?: Record<string, any>;
}

export interface BulkSelectionForm {
  selections: SelectionForm[];
}

export interface SelectionStats {
  total_selections: number;
  unique_users: number;
  assistant_selections: number;
  user_selections: number;
}

class SelectionsAPI {
  private baseUrl = '/api/v1/selections';

  async createSelection(selection: SelectionForm): Promise<Selection> {
    const response = await fetch(`${this.baseUrl}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(selection),
    });

    if (!response.ok) {
      throw new Error(`Failed to create selection: ${response.statusText}`);
    }

    return response.json();
  }

  async createBulkSelections(selections: SelectionForm[]): Promise<Selection[]> {
    const response = await fetch(`${this.baseUrl}/bulk`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ selections }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create bulk selections: ${response.statusText}`);
    }

    return response.json();
  }

  async getUserSelections(limit: number = 100): Promise<Selection[]> {
    const response = await fetch(`${this.baseUrl}/user?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get user selections: ${response.statusText}`);
    }

    return response.json();
  }

  async getChatSelections(chatId: string): Promise<Selection[]> {
    const response = await fetch(`${this.baseUrl}/chat/${chatId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get chat selections: ${response.statusText}`);
    }

    return response.json();
  }

  async deleteSelection(selectionId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/${selectionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to delete selection: ${response.statusText}`);
    }
  }

  async getSelectionStats(): Promise<SelectionStats> {
    const response = await fetch(`${this.baseUrl}/stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get selection stats: ${response.statusText}`);
    }

    return response.json();
  }

  async getAnalyticsData(
    startDate?: number,
    endDate?: number,
    role?: string,
    limit: number = 1000
  ): Promise<Selection[]> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate.toString());
    if (endDate) params.append('end_date', endDate.toString());
    if (role) params.append('role', role);
    params.append('limit', limit.toString());

    const response = await fetch(`${this.baseUrl}/analytics?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get analytics data: ${response.statusText}`);
    }

    return response.json();
  }
}

export const selectionsAPI = new SelectionsAPI();
