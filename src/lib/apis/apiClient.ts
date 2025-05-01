import { createAxiosInstance } from './axios';

export interface ApiOptions {
	token?: string;
	headers?: Record<string, string>;
	withCredentials?: boolean;
	signal?: AbortSignal;
}

type ApiHeaders = {
	authorization?: string;
	[key: string]: string | undefined;
};

export class ApiClient {
	private axiosInstance;
	private baseURL: string;

	constructor(baseURL: string) {
		this.baseURL = baseURL;
		this.axiosInstance = createAxiosInstance(baseURL);
	}

	private async handleApiCall<T>(apiCall: Promise<T>, errorMessage?: string): Promise<T> {
		try {
			return await apiCall;
		} catch (error) {
			console.error(errorMessage || 'API Error:', error);
			throw error;
		}
	}

	private createHeaders(token?: string, additionalHeaders: ApiHeaders = {}): ApiHeaders {
		return {
			...(token && { authorization: token }),
			...additionalHeaders
		};
	}

	private resolveUrl(url: string): string {
		// If the URL is absolute (starts with http:// or https://), use it as is
		if (url.startsWith('http://') || url.startsWith('https://')) {
			return url;
		}
		// Remove leading slash if present since baseURL will have trailing slash
		const cleanUrl = url.startsWith('/') ? url.slice(1) : url;
		// Return the URL relative to baseURL
		return cleanUrl;
	}

	async get<T>(url: string, options: ApiOptions = {}): Promise<T> {
		const headers = this.createHeaders(options.token, options.headers);
		return this.handleApiCall(
			this.axiosInstance
				.get<T>(this.resolveUrl(url), {
					headers,
					withCredentials: options.withCredentials,
					signal: options.signal
				})
				.then((response) => response.data),
			`GET ${url} failed`
		);
	}

	async post<T>(url: string, data: unknown, options: ApiOptions = {}): Promise<T> {
		const headers = this.createHeaders(options.token, options.headers);
		return this.handleApiCall(
			this.axiosInstance
				.post<T>(this.resolveUrl(url), data, {
					headers,
					withCredentials: options.withCredentials,
					signal: options.signal
				})
				.then((response) => response.data),
			`POST ${url} failed`
		);
	}

	async del<T>(url: string, data: unknown, options: ApiOptions = {}): Promise<T> {
		const headers = this.createHeaders(options.token, options.headers);
		return this.handleApiCall(
			this.axiosInstance
				.delete<T>(this.resolveUrl(url), {
					headers,
					withCredentials: options.withCredentials,
					signal: options.signal,
					data
				})
				.then((response) => response.data),
			`DELETE ${url} failed`
		);
	}
}

// Factory function to create API client instances
export const createApiClient = (baseURL: string): ApiClient => {
	return new ApiClient(baseURL);
};
