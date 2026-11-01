<script lang="ts">
	let canvas: HTMLCanvasElement;
	export const draw = async (packet: ArrayBuffer) => {
		if (packet.byteLength < 13) throw new Error('Invalid screen update');
		const header = new DataView(packet);
		const [width, height, x, y, w, h] = Array.from({ length: 6 }, (_, i) =>
			header.getUint16(i * 2)
		);
		if (!width || !height || width > 8192 || height > 8192 || x + w > width || y + h > height)
			throw new Error('Invalid screen dimensions');
		const image = await createImageBitmap(new Blob([packet.slice(12)], { type: 'image/jpeg' }));
		try {
			if (!canvas) return;
			if (canvas.width !== width || canvas.height !== height) {
				canvas.width = width;
				canvas.height = height;
			}
			canvas.getContext('2d')?.drawImage(image, x, y, w, h);
		} finally {
			image.close();
		}
	};
</script>

<canvas bind:this={canvas} class="max-h-full max-w-full select-none" style="object-fit:contain"
></canvas>
