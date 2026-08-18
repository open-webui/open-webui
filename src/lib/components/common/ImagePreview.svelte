<script lang="ts">
	import { onDestroy, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import ZoomReset from '$lib/components/icons/ZoomReset.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	export let show = false;
	export let src = '';
	export let alt = '';

	const i18n = getContext('i18n');

	let previewElement: HTMLElement | null = null;
	let scale = 1;
	let translateX = 0;
	let translateY = 0;
	let isDragging = false;
	let startX = 0;
	let startY = 0;
	let copied = false;

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			closeModal();
		} else if (event.key === '+' || event.key === '=') {
			zoomIn();
		} else if (event.key === '-') {
			zoomOut();
		} else if (event.key === '0') {
			resetZoom();
		}
	};

	const closeModal = () => {
		show = false;
		resetZoom();
	};

	const zoomIn = () => {
		scale = Math.min(scale + 0.25, 4);
	};

	const zoomOut = () => {
		scale = Math.max(scale - 0.25, 0.5);
		if (scale <= 1) {
			translateX = 0;
			translateY = 0;
		}
	};

	const resetZoom = () => {
		scale = 1;
		translateX = 0;
		translateY = 0;
	};

	const handleWheel = (e: WheelEvent) => {
		e.preventDefault();
		if (e.deltaY < 0) {
			zoomIn();
		} else {
			zoomOut();
		}
	};

	const handleMouseDown = (e: MouseEvent) => {
		if (scale > 1) {
			isDragging = true;
			startX = e.clientX - translateX;
			startY = e.clientY - translateY;
		}
	};

	const handleMouseMove = (e: MouseEvent) => {
		if (isDragging && scale > 1) {
			translateX = e.clientX - startX;
			translateY = e.clientY - startY;
		}
	};

	const handleMouseUp = () => {
		isDragging = false;
	};

	const copyImageHandler = async () => {
		try {
			if (src.startsWith('data:image/')) {
				const base64Data = src.split(',')[1];
				const byteCharacters = atob(base64Data);
				const byteNumbers = new Array(byteCharacters.length);
				for (let i = 0; i < byteCharacters.length; i++) {
					byteNumbers[i] = byteCharacters.charCodeAt(i);
				}
				const byteArray = new Uint8Array(byteNumbers);
				const blob = new Blob([byteArray], { type: 'image/png' });
				await navigator.clipboard.write([
					new ClipboardItem({ 'image/png': blob })
				]);
				copied = true;
				toast.success($i18n.t('Image copied to clipboard'));
				setTimeout(() => {
					copied = false;
				}, 2000);
			} else {
				const response = await fetch(src);
				const blob = await response.blob();
				const pngBlob = blob.type === 'image/png' ? blob : new Blob([blob], { type: 'image/png' });
				await navigator.clipboard.write([
					new ClipboardItem({ 'image/png': pngBlob })
				]);
				copied = true;
				toast.success($i18n.t('Image copied to clipboard'));
				setTimeout(() => {
					copied = false;
				}, 2000);
			}
		} catch (err) {
			console.error(err);
			try {
				await navigator.clipboard.writeText(src);
				copied = true;
				toast.success($i18n.t('Image URL copied to clipboard'));
				setTimeout(() => {
					copied = false;
				}, 2000);
			} catch (copyErr) {
				toast.error($i18n.t('Failed to copy image'));
			}
		}
	};

	const downloadHandler = () => {
		try {
			if (src.startsWith('data:image/')) {
				const base64Data = src.split(',')[1];
				const blob = new Blob([Uint8Array.from(atob(base64Data), (c) => c.charCodeAt(0))], {
					type: 'image/png'
				});
				const fileName = `${(alt || 'image').toLowerCase().replace(/[^a-z0-9]/gi, '_')}.png`;
				saveAs(blob, fileName);
			} else {
				fetch(src)
					.then((response) => response.blob())
					.then((blob) => {
						const mimeType = blob.type || 'image/png';
						const ext = mimeType.split('/')[1] || 'png';
						const fileName = `${(alt || 'image').toLowerCase().replace(/[^a-z0-9]/gi, '_')}.${ext}`;
						saveAs(blob, fileName);
					})
					.catch((error) => {
						console.error('Error downloading remote image:', error);
						toast.error($i18n.t('Error downloading image'));
					});
			}
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Error downloading image'));
		}
	};

	$: if (show && previewElement) {
		document.body.appendChild(previewElement);
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
		resetZoom();
	} else if (previewElement) {
		window.removeEventListener('keydown', handleKeyDown);
		if (previewElement.parentNode === document.body) {
			document.body.removeChild(previewElement);
		}
		document.body.style.overflow = 'unset';
	}

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeyDown);
		show = false;
		if (previewElement && previewElement.parentNode === document.body) {
			document.body.removeChild(previewElement);
		}
		document.body.style.overflow = 'unset';
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={previewElement}
		class="fixed inset-0 bg-black/90 backdrop-blur-md text-white w-full h-full flex flex-col justify-between items-center z-[99999] select-none overflow-hidden"
		on:wheel={handleWheel}
		on:click={(e) => {
			if (e.target === previewElement) {
				closeModal();
			}
		}}
	>
		<!-- Top Controls Bar -->
		<div class="w-full flex items-center justify-between px-6 py-4 z-30 pointer-events-auto bg-gradient-to-b from-black/60 to-transparent">
			<!-- Left: Alt or Title -->
			<div class="text-sm font-medium text-gray-300 truncate max-w-[30%]">
				{alt || $i18n.t('Image Preview')}
			</div>

			<!-- Center: Floating Toolbar -->
			<div class="flex items-center gap-1.5 bg-gray-900/80 backdrop-blur-lg px-3 py-1.5 rounded-2xl border border-white/10 shadow-2xl">
				<!-- Zoom Out -->
				<Tooltip content={$i18n.t('Zoom Out (-)')}>
					<button
						type="button"
						class="p-2 rounded-xl text-gray-300 hover:text-white hover:bg-white/10 transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
						disabled={scale <= 0.5}
						on:click={zoomOut}
					>
						<Minus className="size-4" />
					</button>
				</Tooltip>

				<!-- Zoom Percentage Display -->
				<button
					type="button"
					class="px-2 py-1 text-xs font-mono font-semibold text-gray-200 hover:text-white rounded-lg hover:bg-white/10 transition cursor-pointer"
					on:click={resetZoom}
					title={$i18n.t('Reset Zoom')}
				>
					{Math.round(scale * 100)}%
				</button>

				<!-- Zoom In -->
				<Tooltip content={$i18n.t('Zoom In (+)')}>
					<button
						type="button"
						class="p-2 rounded-xl text-gray-300 hover:text-white hover:bg-white/10 transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
						disabled={scale >= 4}
						on:click={zoomIn}
					>
						<Plus className="size-4" />
					</button>
				</Tooltip>

				<!-- Reset Zoom -->
				<Tooltip content={$i18n.t('Reset Zoom (0)')}>
					<button
						type="button"
						class="p-2 rounded-xl text-gray-300 hover:text-white hover:bg-white/10 transition cursor-pointer"
						on:click={resetZoom}
					>
						<ZoomReset className="size-4" />
					</button>
				</Tooltip>

				<div class="w-[1px] h-4 bg-white/20 mx-1"></div>

				<!-- Copy Image -->
				<Tooltip content={copied ? $i18n.t('Copied!') : $i18n.t('Copy Image')}>
					<button
						type="button"
						class="p-2 rounded-xl text-gray-300 hover:text-white hover:bg-white/10 transition cursor-pointer flex items-center gap-1 text-xs font-medium"
						on:click={copyImageHandler}
					>
						{#if copied}
							<Check className="size-4 text-emerald-400" />
						{:else}
							<Clipboard className="size-4" />
						{/if}
						<span class="hidden sm:inline">{$i18n.t('Copy')}</span>
					</button>
				</Tooltip>

				<!-- Download -->
				<Tooltip content={$i18n.t('Download')}>
					<button
						type="button"
						class="p-2 rounded-xl text-gray-300 hover:text-white hover:bg-white/10 transition cursor-pointer flex items-center gap-1 text-xs font-medium"
						on:click={downloadHandler}
					>
						<Download className="size-4" />
						<span class="hidden sm:inline">{$i18n.t('Download')}</span>
					</button>
				</Tooltip>
			</div>

			<!-- Right: Close Button -->
			<div class="flex items-center">
				<Tooltip content={$i18n.t('Close (Esc)')}>
					<button
						type="button"
						class="p-2.5 rounded-2xl bg-white/10 hover:bg-white/20 text-gray-300 hover:text-white transition cursor-pointer"
						on:click={closeModal}
					>
						<XMark className="size-5" />
					</button>
				</Tooltip>
			</div>
		</div>

		<!-- Main Image Viewport -->
		<div
			class="flex-1 w-full h-full flex items-center justify-center overflow-hidden relative cursor-default {scale > 1 ? (isDragging ? 'cursor-grabbing' : 'cursor-grab') : ''}"
			on:mousedown={handleMouseDown}
			on:mousemove={handleMouseMove}
			on:mouseup={handleMouseUp}
			on:mouseleave={handleMouseUp}
			on:click={(e) => {
				if (e.target === e.currentTarget) {
					closeModal();
				}
			}}
		>
			<img
				{src}
				{alt}
				class="max-w-[90vw] max-h-[82vh] object-contain select-none pointer-events-none rounded-lg shadow-2xl transition-transform duration-100 ease-out"
				style="transform: translate({translateX}px, {translateY}px) scale({scale}); transform-origin: center center;"
				draggable="false"
			/>
		</div>
	</div>
{/if}
