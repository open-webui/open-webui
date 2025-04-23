import { WEBUI_API_BASE_URL } from '$lib/constants';
import { handleApiUnauthorized } from '$lib/stores';

export const getGravatarUrl = async (token: string, email: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/utils/gravatar?email=${email}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err;
            return null;
        });

    // Original code didn't throw here, just returned null or the result
    if (error) {
        // Consider if throwing is the desired behavior or just returning null
        console.error("Error fetching Gravatar URL:", error);
        // throw error; // Uncomment if throwing is preferred over returning null
    }

    return res; // Returns null on error, or the JSON result on success
};

export const executeCode = async (token: string, code: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/utils/code/execute`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            code: code
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err; // Keep original error assignment logic
            if (err.detail) {
                error = err.detail;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const formatPythonCode = async (token: string, code: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/utils/code/format`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            code: code
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err; // Keep original error assignment logic
            if (err.detail) {
                error = err.detail;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const downloadChatAsPDF = async (token: string, title: string, messages: object[]) => {
    let error = null;

    const blob = await fetch(`${WEBUI_API_BASE_URL}/utils/pdf`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            title: title,
            messages: messages
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); throw new Error('Unauthorized'); } // Throw to trigger catch
            if (!res.ok) throw await res.json();
            return res.blob(); // Process blob only if OK
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err; // Extract error message
            return null;
        });

    // Original code didn't throw here, just returned null or the blob
    if (error) {
        console.error("Error downloading PDF:", error);
        // throw error; // Uncomment if throwing is preferred
    }

    return blob; // Returns null on error, or the Blob on success
};

export const getHTMLFromMarkdown = async (token: string, md: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/utils/markdown`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            md: md
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err;
            return null;
        });

    // Original code returned res.html or undefined on error
    if (error) {
        console.error("Error converting Markdown:", error);
        // return undefined; // Or throw if preferred
    }

    return res?.html; // Returns undefined on error, or the HTML string on success
};

export const downloadDatabase = async (token: string) => {
    let error = null;

    await fetch(`${WEBUI_API_BASE_URL}/utils/db/download`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json', // Likely expect binary response, but keep original header
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => {
            if (response.status === 401) { handleApiUnauthorized(); throw new Error('Unauthorized'); }
            if (!response.ok) {
                // Attempt to parse error JSON, fallback to status text
                let errorDetail = response.statusText;
                try {
                    const errJson = await response.json();
                    errorDetail = errJson.detail ?? errorDetail;
                } catch (e) { /* Ignore JSON parse error */ }
                throw new Error(errorDetail);
            }
            return response.blob(); // Process blob only if OK
        })
        .then((blob) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'webui.db';
            document.body.appendChild(a);
            a.click();
            a.remove(); // Clean up the link element
            window.URL.revokeObjectURL(url);
        })
        .catch((err) => {
            console.log(err);
            // Use error message from Error objects, fallback to detail or original error
            error = err instanceof Error ? err.message : err.detail ?? err;
            // No return null here, the function doesn't return anything on success either
        });

    if (error) {
        // This function doesn't return anything, so throwing seems appropriate
        throw error;
    }
    // No return value on success either
};

export const downloadLiteLLMConfig = async (token: string) => {
    let error = null;

    await fetch(`${WEBUI_API_BASE_URL}/utils/litellm/config`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json', // Likely expect YAML/text response, but keep original
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => {
            if (response.status === 401) { handleApiUnauthorized(); throw new Error('Unauthorized'); }
            if (!response.ok) {
                // Attempt to parse error JSON, fallback to status text
                let errorDetail = response.statusText;
                try {
                    const errJson = await response.json();
                    errorDetail = errJson.detail ?? errorDetail;
                } catch (e) { /* Ignore JSON parse error */ }
                throw new Error(errorDetail);
            }
            return response.blob(); // Process blob only if OK
        })
        .then((blob) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'config.yaml';
            document.body.appendChild(a);
            a.click();
            a.remove(); // Clean up the link element
            window.URL.revokeObjectURL(url);
        })
        .catch((err) => {
            console.log(err);
            // Use error message from Error objects, fallback to detail or original error
            error = err instanceof Error ? err.message : err.detail ?? err;
            // No return null here, the function doesn't return anything on success either
        });

    if (error) {
        // This function doesn't return anything, so throwing seems appropriate
        throw error;
    }
    // No return value on success either
};
