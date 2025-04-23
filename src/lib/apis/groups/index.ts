import { WEBUI_API_BASE_URL } from '$lib/constants';
import { handleApiUnauthorized } from '$lib/stores';

export const createNewGroup = async (token: string, group: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/groups/create`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            ...group
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            error = err.detail;
            console.log(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getGroups = async (token: string = '') => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/groups/`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .then((json) => {
            return json;
        })
        .catch((err) => {
            error = err.detail;
            console.log(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res ?? []; // Ensure return is always an array
};

export const getGroupById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/groups/id/${id}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .then((json) => {
            return json;
        })
        .catch((err) => {
            error = err.detail;
            console.log(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const updateGroupById = async (token: string, id: string, group: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/groups/id/${id}/update`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            ...group
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .then((json) => {
            return json;
        })
        .catch((err) => {
            error = err.detail;
            console.log(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const deleteGroupById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/groups/id/${id}/delete`, {
        method: 'DELETE',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .then((json) => {
            return json;
        })
        .catch((err) => {
            error = err.detail;
            console.log(err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};
