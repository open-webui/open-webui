import { webuiApiClient } from '../clients';

interface Config {
	[key: string]: unknown;
}

interface Feedback {
	id: string;
	[key: string]: unknown;
}

export const getConfig = async (token: string = '') =>
	webuiApiClient.get<Config>('/evaluations/config', { token });

export const updateConfig = async (token: string, config: Record<string, unknown>) =>
	webuiApiClient.post<Config>('/evaluations/config', config, { token });

export const getAllFeedbacks = async (token: string = '') =>
	webuiApiClient.get<Feedback[]>('/evaluations/feedbacks/all', { token });

export const exportAllFeedbacks = async (token: string = '') =>
	webuiApiClient.get('/evaluations/feedbacks/all/export', { token });

export const createNewFeedback = async (token: string, feedback: Record<string, unknown>) =>
	webuiApiClient.post<Feedback>('/evaluations/feedback', feedback, { token });

export const getFeedbackById = async (token: string, feedbackId: string) =>
	webuiApiClient.get<Feedback>(`/evaluations/feedback/${feedbackId}`, { token });

export const updateFeedbackById = async (
	token: string,
	feedbackId: string,
	feedback: Record<string, unknown>
) => webuiApiClient.post<Feedback>(`/evaluations/feedback/${feedbackId}`, feedback, { token });

export const deleteFeedbackById = async (token: string, feedbackId: string) =>
	webuiApiClient.del<Feedback>(`/evaluations/feedback/${feedbackId}`, null, { token });
