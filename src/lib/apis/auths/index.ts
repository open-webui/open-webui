import { WEBUI_API_BASE_URL } from '$lib/constants';
import { handleApiUnauthorized } from '$lib/stores';

export const getAdminDetails = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/details`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching admin details:`, err);
        error = err.detail ?? 'Failed to fetch admin details';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getAdminConfig = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching admin config:`, err);
        error = err.detail ?? 'Failed to fetch admin config';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateAdminConfig = async (token: string, body: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(body)
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error updating admin config:`, err);
        error = err.detail ?? 'Failed to update admin config';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getSessionUser = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        credentials: 'include'
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching session user:`, err);
        error = err.detail ?? 'Failed to fetch session user';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const ldapUserSignIn = async (user: string, password: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/ldap`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
            user: user,
            password: password
        })
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

export const getLdapConfig = async (token: string = '') => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (token && response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching ldap config:`, err);
        error = err.detail ?? 'Failed to fetch ldap config';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateLdapConfig = async (token: string = '', enable_ldap: boolean) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({
            enable_ldap: enable_ldap
        })
    })
    .then(async (response) => {
        if (!response.ok) {
            if (token && response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error updating ldap config:`, err);
        error = err.detail ?? 'Failed to update ldap config';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getLdapServer = async (token: string = '') => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (token && response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching ldap server config:`, err);
        error = err.detail ?? 'Failed to fetch ldap server config';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateLdapServer = async (token: string = '', body: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify(body)
    })
    .then(async (response) => {
        if (!response.ok) {
            if (token && response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error updating ldap server config:`, err);
        error = err.detail ?? 'Failed to update ldap server config';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const userSignIn = async (email: string, password: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signin`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
            email: email,
            password: password
        })
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

export const userSignUp = async (
    name: string,
    email: string,
    password: string,
    profile_image_url: string
) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
            name: name,
            email: email,
            password: password,
            profile_image_url: profile_image_url
        })
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

export const userSignOut = async () => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signout`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include'
    })
    .then(async (res) => {
        if (!res.ok) throw await res.json();
        return res;
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

export const addUser = async (
    token: string,
    name: string,
    email: string,
    password: string,
    role: string = 'pending'
) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/add`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({
            name: name,
            email: email,
            password: password,
            role: role
        })
    })
    .then(async (response) => {
        if (!response.ok) {
            if (token && response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error adding user:`, err);
        error = err.detail ?? 'Failed to add user';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateUserProfile = async (token: string, name: string, profileImageUrl: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/update/profile`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({
            name: name,
            profile_image_url: profileImageUrl
        })
    })
    .then(async (response) => {
        if (!response.ok) {
            if (token && response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error updating user profile:`, err);
        error = err.detail ?? 'Failed to update profile';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateUserPassword = async (token: string, password: string, newPassword: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/update/password`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({
            password: password,
            new_password: newPassword
        })
    })
    .then(async (response) => {
        if (!response.ok) {
            if (token && response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error updating user password:`, err);
        error = err.detail ?? 'Failed to update password';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getSignUpEnabledStatus = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/enabled`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching signup enabled status:`, err);
        error = err.detail ?? 'Failed to fetch signup status';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getDefaultUserRole = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching default user role:`, err);
        error = err.detail ?? 'Failed to fetch default role';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateDefaultUserRole = async (token: string, role: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            role: role
        })
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error updating default user role:`, err);
        error = err.detail ?? 'Failed to update default role';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const toggleSignUpEnabledStatus = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/enabled/toggle`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error toggling signup status:`, err);
        error = err.detail ?? 'Failed to toggle signup status';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getJWTExpiresDuration = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/token/expires`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching JWT expires duration:`, err);
        error = err.detail ?? 'Failed to fetch JWT duration';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateJWTExpiresDuration = async (token: string, duration: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/token/expires/update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            duration: duration
        })
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error updating JWT expires duration:`, err);
        error = err.detail ?? 'Failed to update JWT duration';
        return null;
    });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const createAPIKey = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api_key`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error creating API key:`, err);
        error = err.detail ?? 'Failed to create API key';
        return null;
    });
    if (error && res === null) {
        throw error;
    }
    // Original code returned res.api_key directly on success
  // Ensure res is not null before accessing api_key
    return res ? res.api_key : undefined;
};

export const getAPIKey = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api_key`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error fetching API key:`, err);
        error = err.detail ?? 'Failed to fetch API key';
        return null;
    });
    if (error && res === null) {
        throw error;
    }
  // Original code returned res.api_key directly on success
    return res ? res.api_key : undefined;
};

export const deleteAPIKey = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api_key`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
    .then(async (response) => {
        if (!response.ok) {
            if (response.status === 401) {
                handleApiUnauthorized();
                const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                throw errorBody;
            }
            throw await response.json();
        }
        return response.json();
    })
    .catch((err) => {
        console.error(`Error deleting API key:`, err);
        error = err.detail ?? 'Failed to delete API key';
        return null;
    });
    if (error && res === null) {
        throw error;
    }
    return res;
};
