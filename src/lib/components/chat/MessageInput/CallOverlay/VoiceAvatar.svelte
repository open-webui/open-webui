<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import {
		avatarAssetIds,
		type AnimationFiles,
		type VoiceAvatarConfig
	} from '$lib/utils/voice-avatar';
	import type { createAvatarRenderer } from '$lib/utils/voice-avatar-renderer';

	export let config: VoiceAvatarConfig;
	export let file: File | null = null;
	export let speaking = false;
	export let listening = false;
	export let level = 0;
	export let active = true;
	export let animationFiles: AnimationFiles = {};
	export let interruption = 0;
	let lastInterruption = interruption;
	let renderer: Awaited<ReturnType<typeof createAvatarRenderer>> | undefined;
	let syncAnimations: ((config: VoiceAvatarConfig, files: AnimationFiles) => void) | undefined;
	$: if (syncAnimations) syncAnimations(config, animationFiles);
	$: if (interruption !== lastInterruption) {
		renderer?.cancelGesture();
		lastInterruption = interruption;
	}
	export function playAnimation(name: string) {
		if (!active || document.hidden || window.matchMedia('(prefers-reduced-motion: reduce)').matches)
			return 'unavailable';
		const asset = config.gestures?.find((gesture) => gesture.name === name);
		return asset ? (renderer?.playGesture(asset.file_id) ?? 'unavailable') : 'unavailable';
	}
	export function cancelAnimation() {
		renderer?.cancelGesture();
	}
	const dispatch = createEventDispatcher();
	let canvas: HTMLCanvasElement;

	// The parent keys this component by file, keeping settings changes inexpensive.
	onMount(() => {
		const abort = new AbortController();
		let frame = 0,
			previous = 0;
		let visible = true;
		const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
		const animate = (now: number) => {
			if (abort.signal.aborted || document.hidden || !visible) {
				frame = 0;
				previous = 0;
				return;
			}
			try {
				renderer?.render(
					previous ? (now - previous) / 1000 : 0,
					config,
					{ speaking, listening, level, active },
					motion.matches
				);
				previous = now;
				frame = requestAnimationFrame(animate);
			} catch (error) {
				frame = 0;
				dispatch('error', error);
			}
		};
		const resume = () => {
			if (!frame && renderer && visible && !document.hidden) frame = requestAnimationFrame(animate);
		};
		const observer = new IntersectionObserver(([entry]) => {
			visible = entry.isIntersecting;
			resume();
		});
		observer.observe(canvas);
		document.addEventListener('visibilitychange', resume);
		const contextLost = (event: Event) => {
			event.preventDefault();
			dispatch('error', new Error('Avatar graphics context was lost.'));
		};
		canvas.addEventListener('webglcontextlost', contextLost);
		void (async () => {
			try {
				let data: ArrayBuffer;
				if (file) data = await file.arrayBuffer();
				else {
					if (!/^[a-f0-9-]{36}$/i.test(config.file_id)) throw new Error('Avatar file is missing.');
					const response = await fetch(`${WEBUI_API_BASE_URL}/files/${config.file_id}/content`, {
						headers: { Authorization: `Bearer ${localStorage.token}` },
						signal: abort.signal
					});
					if (!response.ok) throw new Error('Avatar file is unavailable. Upload it again.');
					data = await response.arrayBuffer();
				}
				const { createAvatarRenderer } = await import('$lib/utils/voice-avatar-renderer');
				abort.signal.throwIfAborted();
				renderer = await createAvatarRenderer(canvas, data, abort.signal);
				if (abort.signal.aborted) {
					renderer.dispose();
					return;
				}
				const pending = new Map<string, Promise<string | null>>();
				let revision = 0;
				let previousAssets = '';
				syncAnimations = (next, files) => {
					const ids = [...new Set(avatarAssetIds(next).filter((id) => id !== next.file_id))];
					const key = ids.join(',');
					if (key === previousAssets) return;
					previousAssets = key;
					const version = ++revision;
					dispatch('animations', { loading: ids.length > 0, errors: {} });
					void Promise.all(
						ids.map((id) => {
							if (!pending.has(id))
								pending.set(
									id,
									(async () => {
										try {
											let bytes: ArrayBuffer;
											if (files[id]) bytes = await files[id].arrayBuffer();
											else {
												const response = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/content`, {
													headers: { Authorization: `Bearer ${localStorage.token}` },
													signal: abort.signal
												});
												if (!response.ok)
													throw new Error('Animation file is unavailable. Upload it again.');
												bytes = await response.arrayBuffer();
											}
											abort.signal.throwIfAborted();
											await renderer!.loadAnimation(id, bytes);
											return null;
										} catch (error) {
											return error instanceof Error ? error.message : 'Could not load animation.';
										}
									})()
								);
							return pending.get(id)!.then((error) => [id, error] as const);
						})
					).then((results) => {
						if (!abort.signal.aborted && version === revision)
							dispatch('animations', {
								loading: false,
								errors: Object.fromEntries(results.filter(([, error]) => error))
							});
					});
				};
				syncAnimations(config, animationFiles);
				dispatch('ready', renderer.capabilities);
				resume();
			} catch (error) {
				if (!abort.signal.aborted) dispatch('error', error);
			}
		})();
		return () => {
			abort.abort();
			syncAnimations = undefined;
			cancelAnimationFrame(frame);
			observer.disconnect();
			document.removeEventListener('visibilitychange', resume);
			canvas.removeEventListener('webglcontextlost', contextLost);
			renderer?.dispose();
		};
	});
</script>

<canvas bind:this={canvas} aria-hidden="true" class="avatar-canvas"></canvas>

<style>
	.avatar-canvas {
		display: block;
		width: 100%;
		height: 100%;
		pointer-events: none;
	}
</style>
