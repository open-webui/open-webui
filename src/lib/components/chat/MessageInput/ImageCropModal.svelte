<script lang="ts">
	import { onDestroy, tick } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let imageFile: File | null = null;
	export let onConfirm: (croppedFile: File) => void = () => {};
	export let onCancel: () => void = () => {};

	type AspectRatio = 'free' | '1:1' | '4:3' | '16:9' | '3:4';
	let selectedRatio: AspectRatio = 'free';

	let canvasEl: HTMLCanvasElement;
	let imgEl: HTMLImageElement | null = null;
	let imgSrc = '';

	// crop rect in image-pixel space
	let cropX = 0, cropY = 0, cropW = 0, cropH = 0;

	// display scale: canvas-px / image-px
	let scaleX = 1, scaleY = 1;

	// drag state
	let dragging = false;
	let dragStartX = 0, dragStartY = 0;
	let dragStartCropX = 0, dragStartCropY = 0;
	let dragStartCropW = 0, dragStartCropH = 0;
	let dragEdge: 'move' | 'tl' | 'tr' | 'bl' | 'br' | null = null;

	const MAX_CANVAS_W = 520;
	const MAX_CANVAS_H = 380;
	const HANDLE_SIZE = 10;
	const HANDLE_HIT_RADIUS = 14;

	$: if (show && imageFile) {
		selectedRatio = 'free';
		loadImage();
	}

	$: if (!show) {
		imgEl = null;
		imgSrc = '';
	}

	const loadImage = async () => {
		if (!imageFile) return;

		const reader = new FileReader();
		reader.onload = (e) => {
			imgSrc = e.target?.result as string;
			const img = new Image();
			img.onload = async () => {
				// imgSrc 설정 후 Svelte 리렌더가 완료되어 canvasEl이 visible canvas를 가리킴
				await tick();
				if (!canvasEl) return;

				imgEl = img;

				const ratio = img.naturalWidth / img.naturalHeight;
				let displayW = Math.min(MAX_CANVAS_W, img.naturalWidth);
				let displayH = displayW / ratio;
				if (displayH > MAX_CANVAS_H) {
					displayH = MAX_CANVAS_H;
					displayW = displayH * ratio;
				}

				canvasEl.width = Math.round(displayW);
				canvasEl.height = Math.round(displayH);
				scaleX = canvasEl.width / img.naturalWidth;
				scaleY = canvasEl.height / img.naturalHeight;

				cropX = 0;
				cropY = 0;
				cropW = img.naturalWidth;
				cropH = img.naturalHeight;

				drawFrame();
			};
			img.src = imgSrc;
		};
		reader.readAsDataURL(imageFile);
	};

	const drawFrame = () => {
		if (!canvasEl || !imgEl) return;
		const ctx = canvasEl.getContext('2d');
		if (!ctx) return;

		const cw = canvasEl.width;
		const ch = canvasEl.height;

		// 1. Draw full image
		ctx.drawImage(imgEl, 0, 0, cw, ch);

		// 2. Convert crop rect to display coords
		const cx = cropX * scaleX;
		const cy = cropY * scaleY;
		const cw2 = cropW * scaleX;
		const ch2 = cropH * scaleY;

		// 3. Dark overlay on 4 surrounding areas
		ctx.fillStyle = 'rgba(0,0,0,0.5)';
		ctx.fillRect(0, 0, cw, cy);                        // top
		ctx.fillRect(0, cy + ch2, cw, ch - cy - ch2);     // bottom
		ctx.fillRect(0, cy, cx, ch2);                      // left
		ctx.fillRect(cx + cw2, cy, cw - cx - cw2, ch2);   // right

		// 4. Crop border
		ctx.strokeStyle = '#ffffff';
		ctx.lineWidth = 2;
		ctx.strokeRect(cx, cy, cw2, ch2);

		// 5. Rule of thirds grid lines
		ctx.strokeStyle = 'rgba(255,255,255,0.3)';
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.moveTo(cx + cw2 / 3, cy);
		ctx.lineTo(cx + cw2 / 3, cy + ch2);
		ctx.moveTo(cx + (cw2 * 2) / 3, cy);
		ctx.lineTo(cx + (cw2 * 2) / 3, cy + ch2);
		ctx.moveTo(cx, cy + ch2 / 3);
		ctx.lineTo(cx + cw2, cy + ch2 / 3);
		ctx.moveTo(cx, cy + (ch2 * 2) / 3);
		ctx.lineTo(cx + cw2, cy + (ch2 * 2) / 3);
		ctx.stroke();

		// 6. Corner handles
		ctx.fillStyle = '#ffffff';
		const hs = HANDLE_SIZE;
		[
			[cx, cy],
			[cx + cw2 - hs, cy],
			[cx, cy + ch2 - hs],
			[cx + cw2 - hs, cy + ch2 - hs]
		].forEach(([x, y]) => ctx.fillRect(x, y, hs, hs));
	};

	const applyRatio = (ratio: AspectRatio) => {
		if (!imgEl) return;
		selectedRatio = ratio;
		if (ratio === 'free') {
			drawFrame();
			return;
		}

		const [rw, rh] = ratio.split(':').map(Number);
		const imgW = imgEl.naturalWidth;
		const imgH = imgEl.naturalHeight;

		let newW: number, newH: number;
		if (imgW / imgH > rw / rh) {
			newH = imgH;
			newW = imgH * (rw / rh);
		} else {
			newW = imgW;
			newH = imgW * (rh / rw);
		}

		cropX = (imgW - newW) / 2;
		cropY = (imgH - newH) / 2;
		cropW = newW;
		cropH = newH;
		drawFrame();
	};

	const getImageCoords = (clientX: number, clientY: number) => {
		const rect = canvasEl.getBoundingClientRect();
		const canvasScaleX = canvasEl.width / rect.width;
		const canvasScaleY = canvasEl.height / rect.height;
		return {
			x: ((clientX - rect.left) * canvasScaleX) / scaleX,
			y: ((clientY - rect.top) * canvasScaleY) / scaleY
		};
	};

	const getCornerHitRadius = () => {
		// Hit radius in image-pixel space
		return HANDLE_HIT_RADIUS / scaleX;
	};

	const isFullImage = (): boolean => {
		if (!imgEl) return false;
		return (
			cropX <= 0 &&
			cropY <= 0 &&
			cropW >= imgEl.naturalWidth - 1 &&
			cropH >= imgEl.naturalHeight - 1
		);
	};

	const detectEdge = (ix: number, iy: number): 'move' | 'tl' | 'tr' | 'bl' | 'br' | null => {
		const r = getCornerHitRadius();
		const x2 = cropX + cropW;
		const y2 = cropY + cropH;

		if (Math.abs(ix - cropX) < r && Math.abs(iy - cropY) < r) return 'tl';
		if (Math.abs(ix - x2) < r && Math.abs(iy - cropY) < r) return 'tr';
		if (Math.abs(ix - cropX) < r && Math.abs(iy - y2) < r) return 'bl';
		if (Math.abs(ix - x2) < r && Math.abs(iy - y2) < r) return 'br';

		// 자유 모드 + 크롭이 전체 이미지일 때: 내부 클릭도 새 크롭 시작
		if (selectedRatio === 'free' && isFullImage()) return null;

		if (ix >= cropX && ix <= x2 && iy >= cropY && iy <= y2) return 'move';
		return null;
	};

	const handleMouseDown = (e: MouseEvent) => {
		e.preventDefault();
		if (!imgEl) return;
		const { x, y } = getImageCoords(e.clientX, e.clientY);
		dragEdge = detectEdge(x, y);
		if (!dragEdge) {
			// Start a new crop from scratch
			dragEdge = 'br';
			cropX = Math.max(0, Math.min(x, imgEl.naturalWidth));
			cropY = Math.max(0, Math.min(y, imgEl.naturalHeight));
			cropW = 0;
			cropH = 0;
		}
		dragging = true;
		dragStartX = e.clientX;
		dragStartY = e.clientY;
		dragStartCropX = cropX;
		dragStartCropY = cropY;
		dragStartCropW = cropW;
		dragStartCropH = cropH;
		drawFrame();
	};

	const handleTouchStart = (e: TouchEvent) => {
		e.preventDefault();
		if (!imgEl || !e.touches[0]) return;
		const touch = e.touches[0];
		const { x, y } = getImageCoords(touch.clientX, touch.clientY);
		dragEdge = detectEdge(x, y);
		if (!dragEdge) {
			dragEdge = 'br';
			cropX = Math.max(0, Math.min(x, imgEl.naturalWidth));
			cropY = Math.max(0, Math.min(y, imgEl.naturalHeight));
			cropW = 0;
			cropH = 0;
		}
		dragging = true;
		dragStartX = touch.clientX;
		dragStartY = touch.clientY;
		dragStartCropX = cropX;
		dragStartCropY = cropY;
		dragStartCropW = cropW;
		dragStartCropH = cropH;
		drawFrame();
	};

	const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));

	const handleMouseMove = (e: MouseEvent) => {
		if (!dragging || !dragEdge || !imgEl) return;
		const imgW = imgEl.naturalWidth;
		const imgH = imgEl.naturalHeight;

		const dx = (e.clientX - dragStartX) / scaleX;
		const dy = (e.clientY - dragStartY) / scaleY;

		if (dragEdge === 'move') {
			cropX = clamp(dragStartCropX + dx, 0, imgW - cropW);
			cropY = clamp(dragStartCropY + dy, 0, imgH - cropH);
		} else if (dragEdge === 'br') {
			const newW = clamp(dragStartCropW + dx, 10, imgW - cropX);
			const newH = clamp(dragStartCropH + dy, 10, imgH - cropY);
			if (selectedRatio !== 'free') {
				const [rw, rh] = selectedRatio.split(':').map(Number);
				cropW = newW;
				cropH = cropW * (rh / rw);
				if (cropY + cropH > imgH) {
					cropH = imgH - cropY;
					cropW = cropH * (rw / rh);
				}
			} else {
				cropW = newW;
				cropH = newH;
			}
		} else if (dragEdge === 'tl') {
			const newX = clamp(dragStartCropX + dx, 0, dragStartCropX + dragStartCropW - 10);
			const newY = clamp(dragStartCropY + dy, 0, dragStartCropY + dragStartCropH - 10);
			cropW = dragStartCropX + dragStartCropW - newX;
			cropH = dragStartCropY + dragStartCropH - newY;
			cropX = newX;
			cropY = newY;
		} else if (dragEdge === 'tr') {
			const newY = clamp(dragStartCropY + dy, 0, dragStartCropY + dragStartCropH - 10);
			cropH = dragStartCropY + dragStartCropH - newY;
			cropY = newY;
			cropW = clamp(dragStartCropW + dx, 10, imgW - cropX);
		} else if (dragEdge === 'bl') {
			const newX = clamp(dragStartCropX + dx, 0, dragStartCropX + dragStartCropW - 10);
			cropW = dragStartCropX + dragStartCropW - newX;
			cropX = newX;
			cropH = clamp(dragStartCropH + dy, 10, imgH - cropY);
		}

		drawFrame();
	};

	const handleTouchMove = (e: TouchEvent) => {
		e.preventDefault();
		if (!dragging || !e.touches[0]) return;
		handleMouseMove({ clientX: e.touches[0].clientX, clientY: e.touches[0].clientY } as MouseEvent);
	};

	const handleMouseUp = () => {
		if (!dragging) return;
		dragging = false;
		dragEdge = null;
		// Ensure minimum size
		if (cropW < 10) cropW = 10;
		if (cropH < 10) cropH = 10;
		drawFrame();
	};

	const handleConfirm = () => {
		if (!imgEl || !imageFile) return;
		const off = document.createElement('canvas');
		off.width = Math.max(1, Math.round(cropW));
		off.height = Math.max(1, Math.round(cropH));
		const ctx = off.getContext('2d');
		if (!ctx) return;
		ctx.drawImage(imgEl, cropX, cropY, cropW, cropH, 0, 0, off.width, off.height);
		off.toBlob(
			(blob) => {
				if (!blob) return;
				const ext = imageFile!.name.split('.').pop() || 'png';
				const baseName = imageFile!.name.replace(/\.[^/.]+$/, '');
				const croppedFile = new File([blob], `${baseName}_cropped.png`, { type: 'image/png' });
				onConfirm(croppedFile);
				show = false;
			},
			'image/png'
		);
	};

	onDestroy(() => {
		imgEl = null;
	});
</script>

<svelte:window
	on:mousemove={handleMouseMove}
	on:mouseup={handleMouseUp}
	on:touchmove|passive={handleTouchMove}
	on:touchend={handleMouseUp}
/>

<Modal bind:show size="lg">
	<div class="flex flex-col gap-3 p-4">
		<!-- Header -->
		<div class="flex justify-between items-center">
			<h2 class="text-base font-semibold text-gray-900 dark:text-white">이미지 자르기</h2>
			<button
				type="button"
				class="p-1.5 rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
				on:click={() => {
					onCancel();
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<!-- Canvas area -->
		<div class="flex justify-center bg-gray-100 dark:bg-gray-900 rounded-xl overflow-hidden min-h-40">
			{#if imgSrc}
				<div class="relative select-none">
					<canvas bind:this={canvasEl} class="block max-w-full" style="cursor: crosshair;"></canvas>
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div
						class="absolute inset-0"
						style="cursor: crosshair;"
						on:mousedown={handleMouseDown}
						on:touchstart|passive={handleTouchStart}
					></div>
				</div>
			{:else}
				<div class="w-full h-40 flex items-center justify-center">
					<div class="text-gray-400 dark:text-gray-600 text-sm">이미지를 불러오는 중...</div>
				</div>
			{/if}
		</div>

		<!-- Ratio buttons -->
		<div class="flex gap-2 flex-wrap justify-center">
			{#each [['free', '자유'], ['1:1', '1:1'], ['4:3', '4:3'], ['16:9', '16:9'], ['3:4', '3:4']] as [value, label]}
				<button
					type="button"
					class="px-3 py-1 rounded-lg text-sm border transition font-medium {selectedRatio ===
					value
						? 'bg-blue-600 text-white border-blue-600'
						: 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
					on:click={() => applyRatio(value as AspectRatio)}
				>
					{label}
				</button>
			{/each}
		</div>

		<!-- Action buttons -->
		<div class="flex justify-end gap-2 pt-1">
			<button
				type="button"
				class="px-4 py-2 rounded-xl text-sm text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition font-medium"
				on:click={() => {
					onCancel();
					show = false;
				}}
			>
				취소
			</button>
			<button
				type="button"
				class="px-4 py-2 rounded-xl text-sm bg-blue-600 hover:bg-blue-700 text-white transition font-medium"
				on:click={handleConfirm}
			>
				자르기 적용
			</button>
		</div>
	</div>
</Modal>
