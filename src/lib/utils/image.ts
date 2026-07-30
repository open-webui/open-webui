import { WEBUI_BASE_URL } from '$lib/constants';

export interface GalleryImageFile {
	id: string;
	filename: string;
	meta: {
		name?: string;
		content_type?: string;
		size?: number;
		data?: Record<string, unknown>;
	};
	created_at: number;
}

export const resolveFileUrl = (url: string): string => {
	if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
		return url;
	}
	return `${WEBUI_BASE_URL}${url}`;
};

export const readFileAsDataUrl = (file: File): Promise<string> => {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result as string);
		reader.onerror = reject;
		reader.readAsDataURL(file);
	});
};

const fetchImageBlob = async (url: string, token: string): Promise<Blob> => {
	const response = await fetch(resolveFileUrl(url), {
		headers: { Authorization: `Bearer ${token}` }
	});
	if (!response.ok) {
		throw new Error(`Failed to fetch image: ${response.status}`);
	}
	return await response.blob();
};

export const copyImageToClipboard = async (url: string, token: string): Promise<void> => {
	const blob = await fetchImageBlob(url, token);

	const pngBlob =
		blob.type === 'image/png'
			? blob
			: await new Promise<Blob>((resolve, reject) => {
					const objectUrl = URL.createObjectURL(blob);
					const img = new Image();
					img.onload = () => {
						const canvas = document.createElement('canvas');
						canvas.width = img.naturalWidth;
						canvas.height = img.naturalHeight;
						canvas.getContext('2d')?.drawImage(img, 0, 0);
						canvas.toBlob((b) => {
							URL.revokeObjectURL(objectUrl);
							resolve(b || blob);
						}, 'image/png');
					};
					img.onerror = () => {
						URL.revokeObjectURL(objectUrl);
						reject(new Error('Failed to decode image for clipboard'));
					};
					img.src = objectUrl;
				});

	await navigator.clipboard.write([new ClipboardItem({ 'image/png': pngBlob })]);
};

export const downloadImage = async (
	url: string,
	filename: string,
	token: string
): Promise<void> => {
	const blob = await fetchImageBlob(url, token);
	const blobUrl = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = blobUrl;
	a.download = filename || 'generated-image.png';
	a.click();
	setTimeout(() => URL.revokeObjectURL(blobUrl), 0);
};

export const getFileModel = (data: Record<string, unknown> | undefined): string | null => {
	if (!data) return null;
	if (data.model) return data.model as string;
	const info = data.info as string | undefined;
	if (info) {
		const match = info.match(/Model:\s*([^,\n]+)/i);
		if (match) return match[1].trim();
	}
	return null;
};

export const getFileSize = (data: Record<string, unknown> | undefined): string | null => {
	if (!data) return null;
	if (typeof data.size === 'string') return data.size;
	if (data.width && data.height) return `${data.width}x${data.height}`;
	return null;
};
