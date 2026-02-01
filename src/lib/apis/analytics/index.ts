import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getModelAnalytics = async (
    token: string = '',
    startDate: number | null = null,
    endDate: number | null = null
) => {
    let error = null;

    const searchParams = new URLSearchParams();
    if (startDate) searchParams.append('start_date', startDate.toString());
    if (endDate) searchParams.append('end_date', endDate.toString());

    const res = await fetch(`${WEBUI_API_BASE_URL}/analytics/models?${searchParams.toString()}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            error = err.detail;
            console.error(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getUserAnalytics = async (
    token: string = '',
    startDate: number | null = null,
    endDate: number | null = null,
    limit: number = 50
) => {
    let error = null;

    const searchParams = new URLSearchParams();
    if (startDate) searchParams.append('start_date', startDate.toString());
    if (endDate) searchParams.append('end_date', endDate.toString());
    if (limit) searchParams.append('limit', limit.toString());

    const res = await fetch(`${WEBUI_API_BASE_URL}/analytics/users?${searchParams.toString()}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            error = err.detail;
            console.error(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getMessages = async (
    token: string = '',
    modelId: string | null = null,
    userId: string | null = null,
    chatId: string | null = null,
    startDate: number | null = null,
    endDate: number | null = null,
    skip: number = 0,
    limit: number = 50
) => {
    let error = null;

    const searchParams = new URLSearchParams();
    if (modelId) searchParams.append('model_id', modelId);
    if (userId) searchParams.append('user_id', userId);
    if (chatId) searchParams.append('chat_id', chatId);
    if (startDate) searchParams.append('start_date', startDate.toString());
    if (endDate) searchParams.append('end_date', endDate.toString());
    if (skip) searchParams.append('skip', skip.toString());
    if (limit) searchParams.append('limit', limit.toString());

    const res = await fetch(`${WEBUI_API_BASE_URL}/analytics/messages?${searchParams.toString()}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            error = err.detail;
            console.error(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getSummary = async (
    token: string = '',
    startDate: number | null = null,
    endDate: number | null = null
) => {
    let error = null;

    const searchParams = new URLSearchParams();
    if (startDate) searchParams.append('start_date', startDate.toString());
    if (endDate) searchParams.append('end_date', endDate.toString());

    const res = await fetch(`${WEBUI_API_BASE_URL}/analytics/summary?${searchParams.toString()}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            error = err.detail;
            console.error(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getDailyStats = async (
    token: string = '',
    startDate: number | null = null,
    endDate: number | null = null,
    granularity: 'hourly' | 'daily' = 'daily'
) => {
    let error = null;

    const searchParams = new URLSearchParams();
    if (startDate) searchParams.append('start_date', startDate.toString());
    if (endDate) searchParams.append('end_date', endDate.toString());
    searchParams.append('granularity', granularity);

    const res = await fetch(`${WEBUI_API_BASE_URL}/analytics/daily?${searchParams.toString()}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            error = err.detail;
            console.error(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};
