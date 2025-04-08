import { WEBUI_API_BASE_URL } from "../../constants";

export const getGrantsNote = async (token: string = '', chatID: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/grants_notes/${chatID}`, {
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

export const createNewGrantNote = async (token: string = '', chatID: string, note: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/grants_notes/${chatID}`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ note })
    })
        .then(async (res) => {
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
}

export const updateGrantNote = async (token: string = '', chatID: string, note: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/grants_notes/update/${chatID}`, {
        method: 'PUT',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ note })
    })
        .then(async (res) => {
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
}