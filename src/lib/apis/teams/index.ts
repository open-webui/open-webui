import { WEBUI_API_BASE_URL } from '$lib/constants';

export const downloadMembersList = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/team_utils/db/downloadMembers`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => {
            if (!response.ok) {
                throw await response.json();
            }
            return response.blob();
        })
        .then((blob) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'members.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch((err) => {
            console.log(err);
            error = err.detail;
            return null;
        });

    if (error) {
        throw error;
    }
};