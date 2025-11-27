<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';
	import panzoom, { type PanZoom } from 'panzoom';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let src = '';
	export let alt = '';

	const i18n = getContext('i18n');

	let mounted = false;

	let previewElement = null;

	let instance: PanZoom;

	let sceneParentElement: HTMLElement;
	let sceneElement: HTMLElement;

	$: if (sceneElement) {
		instance = panzoom(sceneElement, {
			bounds: true,
			boundsPadding: 0.1,

			zoomSpeed: 0.065
		});
	}
	const resetPanZoomViewport = () => {
		instance.moveTo(0, 0);
		instance.zoomAbs(0, 0, 1);
		console.log(instance.getTransform());
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			console.log('Escape');
			show = false;
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
		class="modal fixed top-0 right-0 left-0 bottom-0 bg-black text-white w-full min-h-screen h-screen flex justify-center z-9999 overflow-hidden overscroll-contain"
	>
		<div class=" absolute left-0 w-full flex justify-between select-none z-20">
			<div>
				<button
					class=" p-5"
					on:pointerdown={(e) => {
						e.stopImmediatePropagation();
						e.preventDefault();
						show = false;
					}}
					on:click={(e) => {
						show = false;
					}}
				>
					<XMark className={'size-6'} />
				</button>
			</div>

			<div>
				<button
					class=" p-5 z-999"
					on:click={() => {
						if (src.startsWith('data:image/')) {
							const base64Data = src.split(',')[1];
							const blob = new Blob([Uint8Array.from(atob(base64Data), (c) => c.charCodeAt(0))], {
								type: 'image/png'
							});

							const mimeType = blob.type || 'image/png';
							// create file name based on the MIME type, alt should be a valid file name with extension
							const fileName = `${$i18n
								.t('Generated Image')
								.toLowerCase()
								.replace(/ /g, '_')}.${mimeType.split('/')[1]}`;

							// Use FileSaver to save the blob
							saveAs(blob, fileName);
							return;
						} else if (src.startsWith('blob:')) {
							// Handle blob URLs
							fetch(src)
								.then((response) => response.blob())
								.then((blob) => {
									// detect the MIME type from the blob
									const mimeType = blob.type || 'image/png';

									// Create a new Blob with the correct MIME type
									const blobWithType = new Blob([blob], { type: mimeType });

									// create file name based on the MIME type, alt should be a valid file name with extension
									const fileName = `${$i18n
										.t('Generated Image')
										.toLowerCase()
										.replace(/ /g, '_')}.${mimeType.split('/')[1]}`;

									// Use FileSaver to save the blob
									saveAs(blobWithType, fileName);
								})
								.catch((error) => {
									console.error('Error downloading blob:', error);
								});
							return;
						} else if (
							src.startsWith('/') ||
							src.startsWith('http://') ||
							src.startsWith('https://')
						) {
							// Handle remote URLs
							fetch(src)
								.then((response) => response.blob())
								.then((blob) => {
									// detect the MIME type from the blob
									const mimeType = blob.type || 'image/png';

									// Create a new Blob with the correct MIME type
									const blobWithType = new Blob([blob], { type: mimeType });

									// create file name based on the MIME type, alt should be a valid file name with extension
									const fileName = `${$i18n
										.t('Generated Image')
										.toLowerCase()
										.replace(/ /g, '_')}.${mimeType.split('/')[1]}`;

									// Use FileSaver to save the blob
									saveAs(blobWithType, fileName);
								})
								.catch((error) => {
									console.error('Error downloading remote image:', error);
								});
							return;
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
		<div class="flex h-full max-h-full justify-center items-center z-0">
			<img
				bind:this={sceneElement}
				{src}
				{alt}
				class=" mx-auto h-full object-scale-down select-none"
				draggable="false"
			/>
		</div>
	</div>
{/if}
