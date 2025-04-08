import { WEBUI_API_BASE_URL } from "../../constants";
import { getUserPosition } from "../../utils";

export const getFeedback = async (token: string) => {
    let error = null;
    const res = await fetch(`${WEBUI_API_BASE_URL}/feedback`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err.detail;
            return null;
        });
    if (error) {
        throw error;
    }
    return res;
};

export const postFeedback = async (token: string, feedback: object) => {
    let error = null;
    const res = await fetch(`${WEBUI_API_BASE_URL}/feedback`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(feedback),
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err.detail;
            return null;
        });
    if (error) {
        throw error;
    }
    return res;
}

export const getNotes = async (token: string) => {
    let error = null;
    const res = await fetch(`${WEBUI_API_BASE_URL}/notes`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err.detail;
            return null;
        });
    if (error) {
        throw error;
    }
    return res;
}

export const saveNotes = async (token: string, notes: object) => {
    let error = null;
    const res = await fetch(`${WEBUI_API_BASE_URL}/notes`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(notes),
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err.detail;
            return null;
        });
    if (error) {
        throw error;
    }
    return res;
}