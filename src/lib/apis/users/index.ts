import { WEBUI_API_BASE_URL } from '$lib/constants';
import { getUserPosition } from '$lib/utils';
import { handleApiUnauthorized } from '$lib/stores'; // ADDED IMPORT

export const getUserGroups = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/groups`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching user groups:`, err); // Keep console for debugging
            error = err.detail ?? 'Failed to fetch user groups';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getUserDefaultPermissions = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/default/permissions`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching user default permissions:`, err);
            error = err.detail ?? 'Failed to fetch user default permissions';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateUserDefaultPermissions = async (token: string, permissions: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/default/permissions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            ...permissions
        })
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error updating user default permissions:`, err);
            error = err.detail ?? 'Failed to update user default permissions';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateUserRole = async (token: string, id: string, role: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/update/role`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            id: id,
            role: role
        })
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error updating user role:`, err);
            error = err.detail ?? 'Failed to update user role';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getUsers = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/`, { // Assuming API path is `/users/`
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching users:`, err);
            error = err.detail ?? 'Failed to fetch users';
            return null;
        });

    if (error && res === null) {
        // Allow returning empty array on error based on original logic `res ? res : []`
        return [];
    }
    // Original logic: return empty array if res is null or undefined
    return res ? res : [];
};

export const getUserSettings = async (token: string) => {
    let error = null;
    const res = await fetch(`${WEBUI_API_BASE_URL}/users/user/settings`, { // Corrected path based on logs
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching user settings:`, err);
            error = err.detail ?? 'Failed to fetch user settings';
            return null;
        });

    if (error && res === null) {
        throw error; // Re-throw error if fetch failed and res is null
    }

    return res;
};

export const updateUserSettings = async (token: string, settings: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/user/settings/update`, { // Corrected path
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            ...settings
        })
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error updating user settings:`, err);
            error = err.detail ?? 'Failed to update user settings';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getUserById = async (token: string, userId: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/${userId}`, { // Corrected path
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching user by ID:`, err);
            error = err.detail ?? 'Failed to fetch user by ID';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const getUserInfo = async (token: string) => {
    let error = null;
    const res = await fetch(`${WEBUI_API_BASE_URL}/users/user/info`, { // Corrected path
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching user info:`, err);
            error = err.detail ?? 'Failed to fetch user info';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

export const updateUserInfo = async (token: string, info: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/user/info/update`, { // Corrected path
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            ...info
        })
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error updating user info:`, err);
            error = err.detail ?? 'Failed to update user info';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

// getAndUpdateUserLocation indirectly calls updateUserInfo which is now handled
export const getAndUpdateUserLocation = async (token: string) => {
    const location = await getUserPosition().catch((err) => {
        console.log(err);
        return null;
    });

    if (location) {
        // updateUserInfo will handle its own potential 401
        await updateUserInfo(token, { location: location });
        return location;
    } else {
        console.log('Failed to get user location');
        return null;
    }
};

export const deleteUserById = async (token: string, userId: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/users/${userId}`, { // Corrected path
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error deleting user by ID:`, err);
            error = err.detail ?? 'Failed to delete user';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};

// Define the type if not already defined somewhere accessible
type UserUpdateForm = {
    profile_image_url: string;
    email: string;
    name: string;
    password?: string; // Make password optional as it might not always be updated
};

export const updateUserById = async (token: string, userId: string, user: UserUpdateForm) => {
    let error = null;

    // Construct body, omitting password if empty string
    const body: Partial<UserUpdateForm> & { password?: string } = {
            profile_image_url: user.profile_image_url,
            email: user.email,
            name: user.name
    };
    if (user.password && user.password !== '') {
        body.password = user.password;
    }


    const res = await fetch(`${WEBUI_API_BASE_URL}/users/${userId}/update`, { // Corrected path
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(body)
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error updating user by ID:`, err);
            error = err.detail ?? 'Failed to update user';
            return null;
        });

    if (error && res === null) {
        throw error;
    }
    return res;
};
