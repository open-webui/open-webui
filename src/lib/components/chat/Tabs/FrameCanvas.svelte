<script lang="ts">
	import { onDestroy } from 'svelte';
	let canvas: HTMLCanvasElement;
	// Browsers only offer WebCodecs over HTTPS or localhost; the server sends JPEG otherwise.
	let h264 = typeof VideoDecoder !== 'undefined';
	let decoder: VideoDecoder | null = null;
	let decoded = (frame: VideoFrame | null) => frame?.close();
	export const supportsH264 = () => h264;

	const stopVideo = () => {
		if (decoder && decoder.state !== 'closed') decoder.close();
		decoder = null;
	};
	onDestroy(stopVideo);

	// Resolves with the frame, or null when this browser cannot decode the stream.
	const decode = (packet: ArrayBuffer, configLength: number) =>
		new Promise<VideoFrame | null>((resolve) => {
			const timeout = setTimeout(() => decoded(null), 3000);
			decoded = (frame) => {
				clearTimeout(timeout);
				decoded = (late) => late?.close();
				resolve(frame);
			};
			try {
				if (configLength) {
					stopVideo();
					const description = new Uint8Array(packet, 14, configLength);
					const profile = Array.from(description.subarray(1, 4), (byte) =>
						byte.toString(16).padStart(2, '0')
					).join('');
					decoder = new VideoDecoder({
						output: (frame) => decoded(frame),
						error: () => decoded(null)
					});
					decoder.configure({
						codec: `avc1.${profile}`,
						description,
						optimizeForLatency: true
					});
				}
				if (!decoder) throw new Error('Video started without a configuration');
				decoder.decode(
					new EncodedVideoChunk({
						type: configLength ? 'key' : 'delta',
						timestamp: performance.now() * 1000,
						data: new Uint8Array(packet, 14 + configLength)
					})
				);
			} catch {
				decoded(null);
			}
		});

	const paint = (image: CanvasImageSource, width: number, height: number, x: number, y: number) => {
		if (!canvas) return;
		if (canvas.width !== width || canvas.height !== height) {
			canvas.width = width;
			canvas.height = height;
		}
		canvas.getContext('2d', { alpha: false })?.drawImage(image, x, y);
	};
	export const draw = async (packet: ArrayBuffer) => {
		if (packet.byteLength < 13) throw new Error('Invalid screen update');
		const header = new DataView(packet);
		const [width, height, x, y, w, h] = Array.from({ length: 6 }, (_, i) =>
			header.getUint16(i * 2)
		);
		if (!width || !height || width > 8192 || height > 8192 || x + w > width || y + h > height)
			throw new Error('Invalid screen dimensions');
		if (!w && !h) {
			if (!h264) return;
			const frame = await decode(packet, header.getUint16(12));
			if (!frame) {
				// The next acknowledgment asks the server for JPEG and a full picture.
				h264 = false;
				stopVideo();
				return;
			}
			try {
				paint(frame, width, height, 0, 0);
			} finally {
				frame.close();
			}
			return;
		}
		const image = await createImageBitmap(
			new Blob([new Uint8Array(packet, 12)], { type: 'image/jpeg' })
		);
		try {
			paint(image, width, height, x, y);
		} finally {
			image.close();
		}
	};
</script>

<canvas bind:this={canvas} class="max-h-full max-w-full select-none" style="object-fit:contain"
></canvas>
