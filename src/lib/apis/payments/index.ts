import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getSubscriptionPlans = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/payments/subscription-plans/`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
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

export const createSubscriptionSession = async (token: string, plan_id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/payments/create-subscription-session/`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			plan_id
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

export const getCurrentSubscription = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/payments/subscription/`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
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