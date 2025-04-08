import { WEBUI_API_BASE_URL } from "../../constants";

export const getGrantsFeedback = async (token: string = '', chatID: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/grants_feedback/${chatID}`, {
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

export const createNewGrantFeedback = async (token: string = '', chatID: string, feedback: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/grants_feedback/${chatID}`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ feedback })
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

export const updateGrantFeedback = async (token: string = '', chatID: string, feedback: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/grants_feedback/update_feedback/${chatID}`, {
        method: 'PUT',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ feedback })
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