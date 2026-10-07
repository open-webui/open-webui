<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import { models, showCallOverlay } from '$lib/stores';
	import type { RealtimeCall } from '$lib/utils/realtime';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import VoiceOrb from './VoiceOrb.svelte';
	import VoiceAvatar from './VoiceAvatar.svelte';

	export let bridge: RealtimeCall;
	export let modelId = '';
	let failedAvatar = '';
	let avatarView: VoiceAvatar;
	$: bridge.animationPlayer = (name) =>
		showAvatar ? (avatarView?.playAnimation(name) ?? 'unavailable') : 'unavailable';
	let readyAvatar = '';
	$: avatar = $models.find((model) => model.id === modelId)?.info?.meta?.voice_avatar;
	$: showAvatar = avatar?.file_id && failedAvatar !== avatar.file_id;

	const i18n = getContext<any>('i18n');
	const dispatch = createEventDispatcher();
	$: unavailable = !bridge.connected;
	$: status = bridge.error
		? $i18n.t('Call disconnected')
		: bridge.connecting
			? $i18n.t('Connecting...')
			: bridge.speaking
				? $i18n.t('Speaking')
				: bridge.muted
					? $i18n.t('Microphone off')
					: $i18n.t('Listening');

	const endCall = () => {
		bridge.end();
		showCallOverlay.set(false);
		dispatch('close');
	};

	onMount(() => {
		const handleKeydown = (event: KeyboardEvent) => {
			const target = event.target as HTMLElement;
			if (
				event.key.toLowerCase() === 'm' &&
				!event.repeat &&
				!event.metaKey &&
				!event.ctrlKey &&
				!event.altKey &&
				!target.closest('input, textarea, select, [contenteditable="true"], [role="textbox"]') &&
				bridge.connected
			) {
				event.preventDefault();
				bridge.mute();
			}
		};
		document.addEventListener('keydown', handleKeydown);
		return () => {
			document.removeEventListener('keydown', handleKeydown);
			bridge.animationPlayer = undefined;
		};
	});
</script>

<section class="bridge-call" class:avatar-call={showAvatar} aria-label={$i18n.t('Voice call')}>
	<div class="call-stage">
		<button
			type="button"
			class="orb-button"
			class:avatar-button={showAvatar}
			disabled={!bridge.speaking}
			aria-label={$i18n.t('Stop speaking')}
			on:click={() => bridge.stopSpeaking()}
		>
			{#if showAvatar && avatar}
				{@const selectedAvatar = avatar}
				{#key selectedAvatar.file_id}
					<div
						class="avatar-content"
						class:unavailable-avatar={unavailable}
						class:loading-avatar={readyAvatar !== selectedAvatar.file_id || !bridge.connected}
					>
						<VoiceAvatar
							bind:this={avatarView}
							interruption={bridge.animationInterruption}
							config={selectedAvatar}
							speaking={bridge.playbackActive && !unavailable}
							listening={bridge.userSpeaking && !bridge.muted && !unavailable}
							level={bridge.outputLevel}
							active={!unavailable}
							on:ready={() => {
								readyAvatar = selectedAvatar.file_id;
							}}
							on:error={() => {
								failedAvatar = selectedAvatar.file_id;
							}}
						/>
					</div>
				{/key}
				{#if readyAvatar !== selectedAvatar.file_id || !bridge.connected}
					<div class="avatar-loading" role="status">
						{#if !bridge.error}
							<Spinner className="size-6 text-gray-400 dark:text-gray-500" />
							<span class="sr-only">
								{bridge.connected ? $i18n.t('Loading avatar...') : $i18n.t('Connecting...')}
							</span>
						{/if}
					</div>
				{/if}
			{:else}
				<VoiceOrb
					speaking={bridge.speaking && !unavailable}
					level={unavailable
						? 0
						: bridge.speaking
							? bridge.outputLevel
							: bridge.muted
								? 0
								: bridge.inputLevel}
					muted={unavailable || (bridge.muted && !bridge.speaking)}
				/>
			{/if}
		</button>

		<div class="call-status" role="status" aria-live="polite" aria-atomic="true">
			<p class="status-label">
				{#if bridge.connecting}<span class="connecting-dot" aria-hidden="true"></span>{/if}
				{status}
			</p>
			<p class="status-hint">
				{#if bridge.speaking}
					{bridge.muted ? $i18n.t('Microphone off') : $i18n.t('Tap to interrupt')}
				{:else if bridge.muted && bridge.connected}
					{$i18n.t('Unmute to continue')}
				{/if}
			</p>
		</div>

		{#if bridge.error}
			<div class="call-error">
				<p role="alert">{bridge.error}</p>
				<button
					type="button"
					class="text-action"
					on:click={() => bridge.connect(localStorage.token)}
				>
					{$i18n.t('Retry')}
				</button>
			</div>
		{/if}
	</div>

	<footer>
		<div class="call-controls">
			<button
				type="button"
				class="call-control mute-control"
				class:is-muted={bridge.muted}
				aria-label={bridge.muted ? $i18n.t('Unmute') : $i18n.t('Mute')}
				aria-pressed={bridge.muted}
				title={`${bridge.muted ? $i18n.t('Unmute') : $i18n.t('Mute')} (M)`}
				disabled={unavailable}
				on:click={() => bridge.mute()}
			>
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					aria-hidden="true"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M12 15.75a3 3 0 0 0 3-3V4.5a3 3 0 0 0-6 0v8.25a3 3 0 0 0 3 3Zm-6-4.5v1.5a6 6 0 0 0 12 0v-1.5M12 18.75v3M9 21.75h6"
					/>
					{#if bridge.muted}<path stroke-linecap="round" d="m3 3 18 18" />{/if}
				</svg>
				<span>{bridge.muted ? $i18n.t('Unmute') : $i18n.t('Mute')}</span>
			</button>
			<button type="button" class="call-control end-control" on:click={endCall}>
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					aria-hidden="true"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M3.3 15.4c-.8.3-1.7-.3-1.7-1.2v-2.1c0-.8.3-1.5 1-1.9 5.5-3.5 13.3-3.5 18.8 0 .7.4 1 1.1 1 1.9v2.1c0 .9-.9 1.5-1.7 1.2l-4-1.4a1.3 1.3 0 0 1-.9-1.2v-1.3a15 15 0 0 0-7.6 0v1.3c0 .5-.4 1-.9 1.2Z"
					/>
				</svg>
				<span>{$i18n.t('End call')}</span>
			</button>
		</div>
	</footer>
</section>

<style>
	.bridge-call {
		display: flex;
		flex-direction: column;
		width: 100%;
		min-height: 100%;
		padding: 24px 16px max(24px, env(safe-area-inset-bottom));
		color: var(--color-gray-900);
	}
	:global(.dark) .bridge-call {
		color: var(--color-gray-100);
	}
	.call-stage {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 260px;
		padding: 40px 16px;
	}
	.orb-button {
		flex-shrink: 0;
		padding: 12px;
		border-radius: 50%;
	}
	.avatar-call {
		height: 100%;
		padding-inline: 0;
	}
	.avatar-call .call-stage {
		min-height: 0;
		padding: 0;
	}
	.avatar-call .call-status {
		margin-bottom: 24px;
	}
	.avatar-call footer {
		padding-inline: 16px;
	}
	.avatar-button {
		flex: 1;
		width: 100%;
		min-height: 160px;
		position: relative;
		padding: 0;
		border-radius: 16px;
		overflow: hidden;
	}
	.avatar-content {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		transition: opacity 240ms ease;
	}
	.unavailable-avatar {
		opacity: 0.55;
	}
	.loading-avatar {
		opacity: 0;
	}
	.avatar-loading {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
	}
	.orb-button:disabled {
		cursor: default;
	}
	.call-status {
		margin-top: 16px;
		text-align: center;
	}
	.status-label {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		font-size: 14px;
		line-height: 20px;
		font-weight: 400;
	}
	.status-hint {
		min-height: 18px;
		margin-top: 8px;
		color: var(--color-gray-600);
		font-size: 12px;
		line-height: 18px;
	}
	:global(.dark) .status-hint {
		color: var(--color-gray-400);
	}
	.connecting-dot {
		flex-shrink: 0;
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: currentColor;
	}
	.connecting-dot {
		animation: pulse 1.4s ease-in-out infinite;
	}
	.call-error {
		max-width: 260px;
		margin-top: 12px;
		text-align: center;
		font-size: 12px;
		line-height: 18px;
	}
	.call-error .text-action {
		margin-top: 8px;
	}
	footer {
		flex-shrink: 0;
	}
	.text-action {
		min-height: 44px;
		text-align: start;
		font-size: 12px;
		font-weight: 500;
		text-underline-offset: 3px;
	}
	.text-action:hover {
		text-decoration: underline;
	}
	.call-controls {
		display: flex;
		align-items: center;
		justify-content: center;
		flex-wrap: wrap;
		gap: 12px;
	}
	.call-control {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		min-width: 104px;
		min-height: 44px;
		padding: 10px 16px;
		border-radius: 999px;
		font-size: 12px;
		line-height: 20px;
		font-weight: 500;
		transition:
			background 160ms ease,
			color 160ms ease;
	}
	.call-control svg {
		width: 18px;
		height: 18px;
		flex-shrink: 0;
	}
	.mute-control {
		background: var(--color-gray-100);
	}
	.mute-control:hover {
		background: var(--color-gray-200);
	}
	:global(.dark) .mute-control {
		background: var(--color-gray-800);
	}
	:global(.dark) .mute-control:hover {
		background: var(--color-gray-700);
	}
	.mute-control.is-muted {
		background: var(--color-gray-900);
		color: white;
	}
	:global(.dark) .mute-control.is-muted {
		background: var(--color-gray-100);
		color: var(--color-gray-900);
	}
	.end-control {
		background: #fff0ef;
		color: #b42324;
	}
	.end-control:hover {
		background: #ffe1df;
	}
	:global(.dark) .end-control {
		background: #392526;
		color: #f2a3a3;
	}
	:global(.dark) .end-control:hover {
		background: #482a2c;
	}
	button:focus-visible {
		outline: 2px solid currentColor;
		outline-offset: 4px;
	}
	.call-control:disabled,
	.text-action:disabled {
		opacity: 0.45;
		cursor: default;
	}
	@keyframes pulse {
		50% {
			opacity: 0.3;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.connecting-dot {
			animation: none;
		}
		.call-control,
		.avatar-content {
			transition: none;
		}
	}
</style>
