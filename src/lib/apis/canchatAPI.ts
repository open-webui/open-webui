import axios from 'axios';
import { WEBUI_BASE_URL } from '$lib/constants';

import { goto } from '$app/navigation';

const canchatAPI = axios.create({
	baseURL: WEBUI_BASE_URL,
	headers: {
		Accept: 'application/json',
		'Content-Type': 'application/json'
	}
});

// Request interceptor to add authorization token
canchatAPI.interceptors.request.use(
	(config) => {
		const token = localStorage.getItem('token');
		if (token) {
			config.headers.Authorization = `Bearer ${token}`;
		}
		return config;
	},
	(error) => {
		return Promise.reject(error);
	}
);

// Response interceptor to handle 401 errors
canchatAPI.interceptors.response.use(
	(response) => {
		return response;
	},
	(error) => {
		if (error.response && error.response.status === 401) {
			localStorage.removeItem('token'); // Clear invalid token
			goto('/auth');
			return new Promise(() => {}); // Prevent further execution in the component
		}
		return Promise.reject(error);
	}
);

export default canchatAPI;
