import axios, { type AxiosInstance, type AxiosResponse } from 'axios';
import { WEBUI_API_BASE_URL } from '$lib/constants';

export const createAxiosInstance = (baseURL: string): AxiosInstance => {
	const instance = axios.create({
		baseURL,
		headers: {
			'Content-Type': 'application/json',
			Accept: 'application/json'
		}
	});

	// Add a request interceptor to handle authentication
	instance.interceptors.request.use(
		(config) => {
			const token = config.headers?.authorization;
			if (token) {
				config.headers.authorization = `Bearer ${token.replace('Bearer ', '')}`;
			}
			return config;
		},
		(error) => {
			console.error('Request Error:', error);
			return Promise.reject(error);
		}
	);

	// Add a response interceptor to handle errors and unwrap data
	instance.interceptors.response.use(
		(response: AxiosResponse) => {
			console.log(response);
			return response;
		},
		(error) => {
			// Log the error with relevant details
			console.error('API Error:', {
				url: error.config?.url,
				method: error.config?.method,
				status: error.response?.status,
				data: error.response?.data
			});

			let errorMessage = 'Server connection failed';

			// If we have a response with data containing detail
			if (error.response?.data?.detail) {
				errorMessage = error.response.data.detail;
			}
			// If we have other response data
			else if (error.response?.data) {
				errorMessage = error.response.data;
			}

			return Promise.reject(errorMessage);
		}
	);

	return instance;
};

// Create default instance with WEBUI_API_BASE_URL
const apiAxiosInstance = createAxiosInstance(WEBUI_API_BASE_URL);

export default apiAxiosInstance;
