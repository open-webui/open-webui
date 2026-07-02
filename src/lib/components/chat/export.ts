const CHAT_EXPORT_WIDTH = 800;

export const renderChatMessagesToCanvas = async (containerElement: HTMLElement) => {
	const { default: html2canvas } = await import('html2canvas-pro');

	const isDarkMode = document.documentElement.classList.contains('dark');
	const clonedElement = containerElement.cloneNode(true) as HTMLElement;

	clonedElement.classList.add('text-black');
	clonedElement.classList.add('dark:text-white');
	clonedElement.style.width = `${CHAT_EXPORT_WIDTH}px`;
	clonedElement.style.position = 'absolute';
	clonedElement.style.left = '-9999px';
	clonedElement.style.top = '0';
	clonedElement.style.height = 'auto';

	document.body.appendChild(clonedElement);

	try {
		// Virtualized messages use content-visibility; force all messages into the export render.
		clonedElement.querySelectorAll<HTMLElement>('.message-listitem').forEach((el) => {
			el.style.contentVisibility = 'visible';
		});

		await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

		return await html2canvas(clonedElement, {
			backgroundColor: isDarkMode ? '#000' : '#fff',
			useCORS: true,
			scale: 2,
			width: CHAT_EXPORT_WIDTH
		});
	} finally {
		clonedElement.remove();
	}
};

export const canvasToBlob = async (
	canvas: HTMLCanvasElement,
	type = 'image/png',
	quality?: number
) => {
	return await new Promise<Blob>((resolve, reject) => {
		canvas.toBlob(
			(blob) => {
				if (blob) {
					resolve(blob);
				} else {
					reject(new Error('Failed to render canvas blob'));
				}
			},
			type,
			quality
		);
	});
};

export const copyBlobToClipboard = async (blob: Blob | PromiseLike<Blob>, type = 'image/png') => {
	if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
		return false;
	}

	await navigator.clipboard.write([
		new ClipboardItem({
			[type]: blob
		})
	]);

	return true;
};
