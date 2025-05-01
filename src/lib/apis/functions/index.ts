import { webuiApiClient } from '../clients';

interface FunctionData {
	id: string;
	[key: string]: unknown;
}

interface Valves {
	[key: string]: unknown;
}

export const createNewFunction = async (token: string, func: Record<string, unknown>) =>
	webuiApiClient.post<FunctionData>('/functions/create', func, { token });

export const getFunctions = async (token: string = '') =>
	webuiApiClient.get<FunctionData[]>('/functions/', { token });

export const exportFunctions = async (token: string = '') =>
	webuiApiClient.get('/functions/export', { token });

export const getFunctionById = async (token: string, id: string) =>
	webuiApiClient.get<FunctionData>(`/functions/id/${id}`, { token });

export const updateFunctionById = async (
	token: string,
	id: string,
	func: Record<string, unknown>
) => webuiApiClient.post<FunctionData>(`/functions/id/${id}/update`, func, { token });

export const deleteFunctionById = async (token: string, id: string) =>
	webuiApiClient.del<FunctionData>(`/functions/id/${id}/delete`, null, { token });

export const toggleFunctionById = async (token: string, id: string) =>
	webuiApiClient.post<FunctionData>(`/functions/id/${id}/toggle`, {}, { token });

export const toggleGlobalById = async (token: string, id: string) =>
	webuiApiClient.post<FunctionData>(`/functions/id/${id}/toggle/global`, {}, { token });

export const getFunctionValvesById = async (token: string, id: string) =>
	webuiApiClient.get<Valves>(`/functions/id/${id}/valves`, { token });

export const getFunctionValvesSpecById = async (token: string, id: string) =>
	webuiApiClient.get<Valves>(`/functions/id/${id}/valves/spec`, { token });

export const updateFunctionValvesById = async (
	token: string,
	id: string,
	valves: Record<string, unknown>
) => webuiApiClient.post<Valves>(`/functions/id/${id}/valves/update`, valves, { token });

export const getUserValvesById = async (token: string, id: string) =>
	webuiApiClient.get<Valves>(`/functions/id/${id}/valves/user`, { token });

export const getUserValvesSpecById = async (token: string, id: string) =>
	webuiApiClient.get<Valves>(`/functions/id/${id}/valves/user/spec`, { token });

export const updateUserValvesById = async (
	token: string,
	id: string,
	valves: Record<string, unknown>
) => webuiApiClient.post<Valves>(`/functions/id/${id}/valves/user/update`, valves, { token });
