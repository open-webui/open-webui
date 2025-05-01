import { imagesApiClient } from '../clients';

interface ImageConfig {
	[key: string]: unknown;
}

interface ImageGenerationConfig {
	[key: string]: unknown;
}

interface ImageModel {
	id: string;
	name: string;
	[key: string]: unknown;
}

export const getConfig = async (token: string = '') =>
	imagesApiClient.get<ImageConfig>('/config', { token }).catch((error) => {
		console.error('Failed to get image config:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	});

export const updateConfig = async (token: string = '', config: Record<string, unknown>) =>
	imagesApiClient.post<ImageConfig>('/config/update', config, { token }).catch((error) => {
		console.error('Failed to update image config:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	});

export const verifyConfigUrl = async (token: string = '') =>
	imagesApiClient.get('/config/url/verify', { token }).catch((error) => {
		console.error('Failed to verify config URL:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	});

export const getImageGenerationConfig = async (token: string = '') =>
	imagesApiClient.get<ImageGenerationConfig>('/image/config', { token }).catch((error) => {
		console.error('Failed to get image generation config:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	});

export const updateImageGenerationConfig = async (
	token: string = '',
	config: Record<string, unknown>
) =>
	imagesApiClient
		.post<ImageGenerationConfig>('/image/config/update', config, { token })
		.catch((error) => {
			console.error('Failed to update image generation config:', error);
			throw error instanceof Error ? error.message : 'Server connection failed';
		});

export const getImageGenerationModels = async (token: string = '') =>
	imagesApiClient.get<ImageModel[]>('/models', { token }).catch((error) => {
		console.error('Failed to get image generation models:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	});

export const imageGenerations = async (token: string = '', prompt: string) =>
	imagesApiClient.post('/generations', { prompt }, { token }).catch((error) => {
		console.error('Failed to generate image:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	});
