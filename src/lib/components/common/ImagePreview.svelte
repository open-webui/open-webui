<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	export let show = false;
	export let src = '';
	export let alt = '';
	export let isMarkdown: boolean = true;

	let mounted = false;

	let previewElement = null;

	const MimeTypes: { [index: string]: string } = {
		jpeg: 'image/jpeg',
		jpg: 'image/jpeg',
		png: 'image/png',
		gif: 'image/gif',
		bmp: 'image/bmp',
		ico: 'image/x-icon',
		tif: 'image/tiff',
		tiff: 'image/tiff',
		webp: 'image/webp',
		svg: 'image/svg+xml',
		avif: 'image/avif',
		heic: 'image/heic',
		heif: 'image/heif',
		jxl: 'image/jxl',
		raw: 'image/x-raw'
	};

	function getMimeType(extension: string) {
		return MimeTypes[extension.toLowerCase()] || 'image/png';
	}

	const closeShow = () => {
		show = false;
	};

	const downloadImage = (url, prefixName = 'image') => {
		const isBase64 = url.startsWith('data:image/');
		let filename = 'image.png';
		let mimeType = 'image/png';

		if (isBase64) {
			const base64Parts = url.split(',');
			const mimeInfo = base64Parts[0].split(';')[0];
			mimeType = mimeInfo.split(':')[1];
			const extension = mimeType.split('/')[1];
			filename = `${prefixName}.${extension}`;

			const base64Data = base64Parts[1];
			const binaryData = atob(base64Data);
			const arrayBuffer = new ArrayBuffer(binaryData.length);
			const uint8Array = new Uint8Array(arrayBuffer);
			for (let i = 0; i < binaryData.length; i++) {
				uint8Array[i] = binaryData.charCodeAt(i);
			}
			const blob = new Blob([uint8Array], { type: mimeType });

			const objectUrl = window.URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = objectUrl;
			link.download = filename;
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			window.URL.revokeObjectURL(objectUrl);
		} else {
			// Handle normal URL download
			const urlParts = url.split('/');
			const fileNameWithExt = urlParts.pop().trim() || '';
			const splitted = fileNameWithExt.split('.');
			const extension = `${(splitted[splitted.length - 1] || 'png').toLowerCase()}`;
			filename = `${(splitted[splitted.length - 2] || 'image').toLowerCase()}.${extension}`;

			fetch(url)
				.then((response) => response.blob())
				.then((blob) => {
					mimeType = getMimeType(extension);
					const newBlob = new Blob([blob], { type: mimeType });
					const objectUrl = window.URL.createObjectURL(newBlob);
					const link = document.createElement('a');
					link.href = objectUrl;
					link.download = filename;
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
					window.URL.revokeObjectURL(objectUrl);
				})
				.catch((error) => console.error('Error downloading image:', error));
		}
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			console.log('Escape');
			closeShow();
		}
	};

	onMount(() => {
		mounted = true;
	});

	$: if (show && previewElement) {
		document.body.appendChild(previewElement);
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
	} else if (previewElement) {
		window.removeEventListener('keydown', handleKeyDown);
		document.body.removeChild(previewElement);
		document.body.style.overflow = 'unset';
	}

	onDestroy(() => {
		show = false;

		if (previewElement) {
			document.body.removeChild(previewElement);
		}
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={previewElement}
		class="modal fixed top-0 right-0 left-0 bottom-0 bg-black text-white w-full min-h-screen h-screen flex justify-center z-[9999] overflow-hidden overscroll-contain"
	>
		<div class=" absolute left-0 w-full flex justify-between select-none">
			<div>
				<button
					class=" p-5"
					on:click={() => {
						closeShow();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="w-6 h-6"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<div>
				<button
					class=" p-5"
					on:click={() => {
						if (isMarkdown) {
							window.open(src, '_blank').focus();
						} else {
							downloadImage(src, alt);
						}
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-6 h-6"
					>
						<path
							d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z"
						/>
						<path
							d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z"
						/>
					</svg>
				</button>
			</div>
		</div>
		<img {src} {alt} class=" mx-auto h-full object-scale-down select-none" draggable="false" />
	</div>
{/if}
