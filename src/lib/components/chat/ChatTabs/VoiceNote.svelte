<script lang="ts">
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import { config, settings } from '$lib/stores';
	import { transcribeAudio } from '$lib/apis/audio';
	import { getCwd, uploadNewFileToTerminal, type TerminalConnection } from '$lib/apis/terminal';
	import { matchKeybinding, Shortcut } from '$lib/shortcuts';
	import Icon from '../FileNav/Icon.svelte';
	type VoiceNoteDraft = {
		name: string;
		directory: string;
		audio: Blob;
		duration: number;
		transcript: string;
		audioPath?: string;
	};

	const validVoiceNoteName = (name: string) =>
		!!name.trim() && !['.', '..'].includes(name.trim()) && !/[\\/\0]/.test(name);

	const voiceNoteExtension = (type: string) =>
		type.includes('mp4')
			? 'm4a'
			: type.includes('ogg')
				? 'ogg'
				: type.includes('wav')
					? 'wav'
					: 'webm';

	const voiceNoteMarkdown = (draft: VoiceNoteDraft) => {
		const audioName = draft.audioPath!.replace(/\\/g, '/').split('/').pop()!;
		const link = encodeURIComponent(audioName).replace(
			/[()]/g,
			(c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`
		);
		return `# ${draft.name.trim()}\n\n${draft.transcript.trim() ? `${draft.transcript.trim()}\n\n` : ''}[Audio](./${link})\n`;
	};

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	export let connection: TerminalConnection;
	export let chatId: string | null = null;
	export let directory: string | undefined = undefined;
	export let canTranscribe = false;
	export let onclose: () => void;
	export let onsaved: (path: string) => void;

	let panel: HTMLElement;
	let nameInput: HTMLInputElement;
	let returnFocus: HTMLElement | null = null;
	let position: { x: number; y: number } | null = null;
	let drag: { pointerId: number; startX: number; startY: number; x: number; y: number } | null =
		null;
	let dragged = false;
	let draft: VoiceNoteDraft | undefined;
	let initializing = true;
	let recording = false;
	let busy = false;
	let error = '';
	let elapsed = 0;
	let levels = Array(38).fill(2);
	let recorder: MediaRecorder | undefined;
	let stream: MediaStream | undefined;
	let audioContext: AudioContext | undefined;
	let frame = 0;
	let timer: ReturnType<typeof setInterval>;
	let disposed = false;
	let player: HTMLAudioElement;
	let playing = false;
	let audioUrl = '';
	let previewBlob: Blob | undefined;
	const buttonClass =
		'flex h-7 min-w-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-1.5 text-xs text-gray-500 hover:bg-gray-50/60 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800/60 dark:hover:text-gray-200 disabled:opacity-40';
	const primaryButtonClass =
		'flex h-7 items-center justify-center rounded-lg bg-gray-100 px-2.5 text-xs font-normal text-gray-700 transition hover:bg-gray-200/60 disabled:opacity-40 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700/60';
	$: transcriptionAvailable =
		canTranscribe &&
		!!$config?.audio?.stt &&
		$config?.audio?.stt?.engine !== 'web' &&
		($settings?.audio?.stt?.engine ?? '') !== 'web';
	$: if (!disposed && draft?.audio && draft.audio !== previewBlob) {
		if (audioUrl) URL.revokeObjectURL(audioUrl);
		previewBlob = draft.audio;
		audioUrl = URL.createObjectURL(draft.audio);
	}
	const duration = (seconds: number) =>
		`${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
	const releaseMicrophone = () => {
		clearInterval(timer);
		cancelAnimationFrame(frame);
		stream?.getTracks().forEach((track) => track.stop());
		stream = undefined;
		void audioContext?.close().catch(() => {});
		audioContext = undefined;
	};
	const stop = () => {
		if (recorder?.state === 'recording') {
			busy = true;
			recorder.stop();
		}
	};
	const start = async () => {
		error = '';
		player?.pause();
		playing = false;
		initializing = true;
		try {
			if (!directory) {
				const cwd = await getCwd(connection.baseUrl, connection.key, chatId ?? undefined);
				if (!cwd) throw new Error($i18n.t('Could not load the recording folder.'));
				directory = cwd.cwd ?? cwd.home ?? cwd.root?.path;
				if (!directory) throw new Error($i18n.t('Could not load the recording folder.'));
			}
			if (disposed) return;
			stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			if (disposed) {
				releaseMicrophone();
				return;
			}
			const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'].find(
				(type) => MediaRecorder.isTypeSupported(type)
			);
			recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
			const chunks: Blob[] = [];
			recorder.ondataavailable = (event) => {
				if (event.data.size) chunks.push(event.data);
			};
			recorder.onstop = () => {
				recording = false;
				releaseMicrophone();
				if (disposed) return;
				const audio = new Blob(chunks, {
					type: recorder?.mimeType || chunks[0]?.type || 'audio/webm'
				});
				if (!audio.size) {
					error = $i18n.t('No audio was recorded.');
					busy = false;
					return;
				}
				draft = {
					name: draft?.name || $i18n.t('Voice Note'),
					directory: directory!,
					audio,
					duration: elapsed,
					transcript: ''
				};
				busy = false;
				void tick().then(() => {
					if (!disposed) nameInput?.focus();
				});
			};
			recorder.onerror = () => {
				error = $i18n.t('Error starting recording.');
				stop();
				releaseMicrophone();
			};
			recorder.start(250);
			recording = true;
			elapsed = 0;
			timer = setInterval(() => elapsed++, 1000);
			try {
				audioContext = new AudioContext();
				const analyser = audioContext.createAnalyser();
				analyser.fftSize = 256;
				audioContext.createMediaStreamSource(stream).connect(analyser);
				void audioContext.resume().catch(() => {});
				const samples = new Uint8Array(analyser.fftSize);
				let lastSample = 0;
				levels = Array(38).fill(2);
				const draw = (time: number) => {
					if (time - lastSample >= 60) {
						analyser.getByteTimeDomainData(samples);
						const energy = samples.reduce((sum, sample) => sum + ((sample - 128) / 128) ** 2, 0);
						const height = Math.max(2, Math.min(28, Math.sqrt(energy / samples.length) * 200));
						levels = [...levels.slice(1), height];
						lastSample = time;
					}
					frame = requestAnimationFrame(draw);
				};
				frame = requestAnimationFrame(draw);
			} catch {
				/* Recording still works when visualisation is unavailable. */
			}
		} catch (reason) {
			releaseMicrophone();
			error = reason instanceof Error ? reason.message : $i18n.t('Error accessing media devices.');
		} finally {
			initializing = false;
		}
	};
	const close = () => {
		if (!busy) onclose();
	};
	const transcribe = async () => {
		if (!draft || busy || !transcriptionAvailable) return;
		busy = true;
		error = '';
		try {
			const result = await transcribeAudio(
				localStorage.token,
				new File([draft.audio], `recording.${voiceNoteExtension(draft.audio.type)}`, {
					type: draft.audio.type
				}),
				$settings?.audio?.stt?.language
			);
			if (!result || typeof result.text !== 'string')
				throw new Error($i18n.t('Could not transcribe the recording.'));
			draft.transcript = result.text;
		} catch {
			error = $i18n.t('Could not transcribe the recording.');
		} finally {
			busy = false;
		}
	};
	const save = async () => {
		if (!draft || busy) return;
		if (!validVoiceNoteName(draft.name)) {
			error = $i18n.t('Enter a file name without slashes.');
			return;
		}
		busy = true;
		error = '';
		playing = false;
		player?.pause();
		try {
			if (!draft.audioPath) {
				const result = await uploadNewFileToTerminal(
					connection.baseUrl,
					connection.key,
					draft.directory,
					new File([draft.audio], `${draft.name.trim()}.${voiceNoteExtension(draft.audio.type)}`, {
						type: draft.audio.type
					}),
					chatId ?? undefined
				);
				if (!result?.path) throw new Error();
				draft.audioPath = result.path;
			}
			const note = await uploadNewFileToTerminal(
				connection.baseUrl,
				connection.key,
				draft.directory,
				new File([voiceNoteMarkdown(draft)], `${draft.name.trim()}.md`, { type: 'text/markdown' }),
				chatId ?? undefined
			);
			if (!note?.path) throw new Error();
			draft = undefined;
			// onsaved reads the target that onclose clears
			onsaved(note.path);
			onclose();
		} catch {
			error = $i18n.t('Could not save the voice note. Retry or download the recording.');
		} finally {
			busy = false;
		}
	};
	const fitPosition = () => {
		if (!position || !panel) return;
		const { width, height } = panel.getBoundingClientRect();
		const margin = recording || initializing ? 48 : 12;
		const x = Math.max(margin, Math.min(position.x, window.innerWidth - width - margin));
		const y = Math.max(12, Math.min(position.y, window.innerHeight - height - 24));
		if (x !== position.x || y !== position.y) position = { x, y };
	};
	const beginDrag = (event: PointerEvent) => {
		if (event.button !== 0) return;
		const { left: x, top: y } = panel.getBoundingClientRect();
		dragged = false;
		drag = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, x, y };
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
	};
	const moveDrag = (event: PointerEvent) => {
		if (!drag || event.pointerId !== drag.pointerId) return;
		const dx = event.clientX - drag.startX;
		const dy = event.clientY - drag.startY;
		if (!dragged && Math.hypot(dx, dy) < 5) return;
		dragged = true;
		position = { x: drag.x + dx, y: drag.y + dy };
		fitPosition();
	};
	const endDrag = (event: PointerEvent) => {
		if (event.pointerId !== drag?.pointerId) return;
		drag = null;
		if (event.type === 'pointercancel') dragged = false;
		const target = event.currentTarget as HTMLElement;
		if (target.hasPointerCapture(event.pointerId)) target.releasePointerCapture(event.pointerId);
	};
	const moveWithKeyboard = (event: KeyboardEvent) => {
		const directions = {
			ArrowLeft: [-1, 0],
			ArrowRight: [1, 0],
			ArrowUp: [0, -1],
			ArrowDown: [0, 1]
		};
		const direction = directions[event.key as keyof typeof directions];
		if (!direction) return;
		event.preventDefault();
		event.stopPropagation();
		const { left: x, top: y } = panel.getBoundingClientRect();
		position = { x: x + direction[0] * 16, y: y + direction[1] * 16 };
		fitPosition();
	};
	const portal = (node: HTMLElement) => {
		document.body.appendChild(node);
		const observer = new ResizeObserver(fitPosition);
		observer.observe(node);
		window.addEventListener('resize', fitPosition);
		return {
			destroy: () => {
				observer.disconnect();
				window.removeEventListener('resize', fitPosition);
				node.remove();
			}
		};
	};
	export const finishRecording = () => {
		if (recording) stop();
		else nameInput?.focus();
	};
	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.defaultPrevented || event.repeat || event.isComposing) return;
		if (document.querySelector('.modal, [role="alertdialog"], [role="menu"], [role="listbox"]'))
			return;
		if (event.key === 'Escape') {
			event.preventDefault();
			event.stopPropagation();
			close();
		} else if (
			panel?.contains(event.target as Node) &&
			$settings?.keyboardShortcuts !== false &&
			matchKeybinding(event) === Shortcut.VOICE_NOTE
		) {
			event.preventDefault();
			finishRecording();
		}
	};
	onMount(() => {
		returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
		panel.focus({ preventScroll: true });
		void start();
	});
	onDestroy(() => {
		disposed = true;
		stop();
		releaseMicrophone();
		if (audioUrl) URL.revokeObjectURL(audioUrl);
		if (panel?.contains(document.activeElement) && returnFocus?.isConnected) {
			returnFocus.focus({ preventScroll: true });
		}
	});
</script>

<svelte:window on:keydown={handleKeyDown} />

<div
	use:portal
	bind:this={panel}
	role="dialog"
	aria-modal="false"
	aria-label={$i18n.t('Voice Note')}
	tabindex="-1"
	style:left={position ? `${position.x}px` : undefined}
	style:top={position ? `${position.y}px` : undefined}
	style:bottom={position ? 'auto' : undefined}
	style:translate={position ? 'none' : undefined}
	class="voice-note-panel fixed bottom-6 left-1/2 z-[9998] max-w-[calc(100vw-2rem)] -translate-x-1/2 font-normal text-gray-700 outline-none dark:text-gray-200"
>
	<span id="voice-note-move-hint" class="sr-only">{$i18n.t('Use arrow keys to move.')}</span>
	{#if recording || initializing}
		<div class="group relative">
			<button
				class="absolute -left-9 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-lg text-gray-500 opacity-0 transition-opacity hover:bg-gray-50/60 focus-visible:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100 dark:text-gray-400 dark:hover:bg-gray-800/60 max-sm:opacity-100"
				aria-label={$i18n.t('Cancel')}
				title={`${$i18n.t('Cancel')} (Esc)`}
				aria-disabled={busy}
				on:click={close}><Icon name="xmark" size={14} /></button
			>
			<button
				class="voice-note-pill relative flex h-14 w-56 items-center justify-center touch-none select-none cursor-grab active:cursor-grabbing rounded-full border border-gray-100 bg-white shadow-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gray-400 dark:border-gray-800 dark:bg-gray-850"
				disabled={busy || initializing}
				aria-label={$i18n.t(initializing ? 'Loading...' : 'Stop recording')}
				title={`${$i18n.t('Stop recording')} · ${$i18n.t('Drag to move')}`}
				aria-describedby="voice-note-move-hint"
				on:pointerdown={beginDrag}
				on:pointermove={moveDrag}
				on:pointerup={endDrag}
				on:pointercancel={endDrag}
				on:keydown={moveWithKeyboard}
				on:click={(event) => {
					if (dragged) {
						event.preventDefault();
						dragged = false;
						return;
					}
					stop();
				}}
			>
				{#if initializing}
					<span role="status" class="text-xs text-gray-500 dark:text-gray-400"
						>{$i18n.t('Loading...')}</span
					>
				{:else}
					<div
						class="voice-note-wave flex h-8 w-[11.5rem] items-center gap-[0.1875rem] transition-opacity"
						aria-hidden="true"
					>
						{#each levels as height}<span
								class="min-w-0 flex-1 rounded-full bg-gray-500 dark:bg-gray-400"
								style:height={`${height / 16}rem`}
							></span>{/each}
					</div>
					<span
						class="voice-note-stop pointer-events-none absolute flex size-6 items-center justify-center rounded-lg bg-white text-gray-700 opacity-0 transition-opacity dark:bg-gray-850 dark:text-gray-300"
						aria-hidden="true"><span class="size-2.5 rounded-[0.125rem] bg-current"></span></span
					>
				{/if}
			</button>
			{#if recording}<span
					class="pointer-events-none absolute top-full left-1/2 mt-1 -translate-x-1/2 text-[0.6875rem] leading-4 tabular-nums text-gray-500 dark:text-gray-400"
					>{duration(elapsed)}</span
				>{/if}
		</div>
	{:else}
		<div
			class="voice-note-review w-[22rem] max-w-full max-h-[calc(100dvh-3rem)] overflow-y-auto rounded-xl border border-gray-100 bg-white px-3 py-2 shadow-lg dark:border-gray-800 dark:bg-gray-850"
		>
			{#if draft}
				<div class="flex items-center gap-2">
					<input
						id="voice-note-name"
						bind:this={nameInput}
						bind:value={draft.name}
						disabled={busy}
						spellcheck="false"
						autocomplete="off"
						aria-label={$i18n.t('File name')}
						class="h-7 min-w-0 flex-1 bg-transparent text-[0.8125rem] leading-5 outline-none"
					/>
					<button
						type="button"
						aria-label={$i18n.t('Move')}
						aria-describedby="voice-note-move-hint"
						title={$i18n.t('Drag to move')}
						class="flex h-4 w-5 touch-none select-none cursor-grab items-center justify-center rounded text-gray-400 hover:text-gray-600 active:cursor-grabbing dark:text-gray-500 dark:hover:text-gray-300"
						on:pointerdown={beginDrag}
						on:pointermove={moveDrag}
						on:pointerup={endDrag}
						on:pointercancel={endDrag}
						on:keydown={moveWithKeyboard}
					>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"
							><circle cx="9" cy="5" r="1.5" /><circle cx="15" cy="5" r="1.5" /><circle
								cx="9"
								cy="12"
								r="1.5"
							/><circle cx="15" cy="12" r="1.5" /><circle cx="9" cy="19" r="1.5" /><circle
								cx="15"
								cy="19"
								r="1.5"
							/></svg
						>
					</button>
				</div>
				<p
					class="truncate text-[0.6875rem] leading-4 text-gray-500 dark:text-gray-400"
					title={draft.directory}
				>
					{draft.directory}
				</p>
				<audio
					bind:this={player}
					src={audioUrl}
					on:ended={() => {
						playing = false;
					}}
				></audio>
				{#if draft.transcript}<textarea
						aria-label={$i18n.t('Transcript')}
						bind:value={draft.transcript}
						disabled={busy}
						rows="2"
						class="mt-2 max-h-24 w-full resize-y bg-transparent text-xs leading-5 text-gray-600 dark:text-gray-300 outline-none"
					></textarea>{/if}
				<div class="mt-2 flex items-center gap-1">
					<button
						class={buttonClass}
						disabled={busy}
						aria-label={$i18n.t(playing ? 'Pause' : 'Play')}
						title={$i18n.t(playing ? 'Pause' : 'Play')}
						on:click={async () => {
							if (playing) player.pause();
							else await player.play().catch(() => {});
							playing = !player.paused;
						}}
					>
						{#if playing}<svg
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.5"
								stroke-linecap="round"
								aria-hidden="true"><path d="M8 5v14M16 5v14" /></svg
							>{:else}<Icon name="play" size={14} />{/if}
					</button>
					<span class="text-xs leading-4 tabular-nums text-gray-500 dark:text-gray-400"
						>{duration(draft.duration)}</span
					>
					<div class="ms-auto flex items-center gap-0.5">
						{#if transcriptionAvailable}<button
								class={buttonClass}
								disabled={busy}
								aria-label={$i18n.t('Transcribe')}
								title={$i18n.t('Transcribe')}
								on:click={transcribe}><Icon name="page-text" size={14} /></button
							>{/if}
						<a
							class={buttonClass}
							href={audioUrl}
							aria-label={$i18n.t('Download')}
							title={$i18n.t('Download')}
							download={`${draft.name || 'recording'}.${voiceNoteExtension(draft.audio.type)}`}
							><Icon name="download" size={14} /></a
						>
					</div>
					<div class="ms-1 flex items-center gap-1.5">
						<button class={buttonClass} aria-disabled={busy} on:click={close}
							>{$i18n.t('Cancel')}</button
						>
						<button class={primaryButtonClass} disabled={busy || !draft.name.trim()} on:click={save}
							>{busy ? $i18n.t('Processing...') : $i18n.t('Save')}</button
						>
					</div>
				</div>
			{:else}
				<div class="flex justify-end gap-1.5">
					<button class={buttonClass} on:click={close}>{$i18n.t('Cancel')}</button>
					<button class={primaryButtonClass} on:click={start}>{$i18n.t('Record')}</button>
				</div>
			{/if}
			{#if error}<p role="alert" class="mt-3 text-xs text-red-500">{error}</p>{/if}
		</div>
	{/if}
</div>

<style>
	.voice-note-pill:hover .voice-note-wave,
	.voice-note-pill:focus-visible .voice-note-wave {
		opacity: 0.35;
	}
	.voice-note-pill:hover .voice-note-stop,
	.voice-note-pill:focus-visible .voice-note-stop {
		opacity: 1;
	}
	@media (prefers-reduced-motion: reduce) {
		.voice-note-panel :global(*) {
			transition: none;
		}
	}
</style>
