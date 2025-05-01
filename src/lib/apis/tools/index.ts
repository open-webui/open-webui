import { webuiApiClient } from '../clients';

export const createNewTool = async (token: string, tool: object) =>
	webuiApiClient.post('/tools/create', tool, { token });

export const getTools = async (token: string = '') => webuiApiClient.get('/tools/', { token });

export const getToolList = async (token: string = '') =>
	webuiApiClient.get('/tools/list', { token });

export const exportTools = async (token: string = '') =>
	webuiApiClient.get('/tools/export', { token });

export const getToolById = async (token: string, id: string) =>
	webuiApiClient.get(`/tools/id/${id}`, { token });

export const updateToolById = async (token: string, id: string, tool: object) =>
	webuiApiClient.post(`/tools/id/${id}/update`, tool, { token });

export const deleteToolById = async (token: string, id: string) =>
	webuiApiClient.del(`/tools/id/${id}/delete`, null, { token });

export const getToolValvesById = async (token: string, id: string) =>
	webuiApiClient.get(`/tools/id/${id}/valves`, { token });

export const getToolValvesSpecById = async (token: string, id: string) =>
	webuiApiClient.get(`/tools/id/${id}/valves/spec`, { token });

export const updateToolValvesById = async (token: string, id: string, valves: object) =>
	webuiApiClient.post(`/tools/id/${id}/valves/update`, valves, { token });

export const getUserValvesById = async (token: string, id: string) =>
	webuiApiClient.get(`/tools/id/${id}/valves/user`, { token });

export const getUserValvesSpecById = async (token: string, id: string) =>
	webuiApiClient.get(`/tools/id/${id}/valves/user/spec`, { token });

export const updateUserValvesById = async (token: string, id: string, valves: object) =>
	webuiApiClient.post(`/tools/id/${id}/valves/user/update`, valves, { token });
