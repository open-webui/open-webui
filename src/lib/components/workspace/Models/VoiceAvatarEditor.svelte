<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import {
		AVATAR_MAX_BYTES,
		type AnimationFiles,
		type AvatarState,
		type VoiceAvatarConfig
	} from '$lib/utils/voice-avatar';
	import VoiceAvatar from '$lib/components/chat/MessageInput/CallOverlay/VoiceAvatar.svelte';

	export let value: VoiceAvatarConfig | null = null;
	export let file: File | null = null;
	export let valid = true;
	export let animationFiles: AnimationFiles = {};
	let avatarValid = true;
	let animationsLoading = false;
	let animationErrors: Record<string, string> = {};
	let avatarPreview: VoiceAvatar;
	let previewContainer: HTMLDivElement;
	let animationInput: HTMLInputElement;
	let animationTarget: AvatarState | number = 'idle';
	$: gestures = value?.gestures ?? [];
	$: namesValid =
		gestures.every(
			(g) => /^[a-z][a-z0-9_]{0,47}$/.test(g.name) && g.description.trim().length > 0 && g.file_id
		) && new Set(gestures.map((g) => g.name)).size === gestures.length;
	$: valid =
		avatarValid && !animationsLoading && !Object.keys(animationErrors).length && namesValid;
	const uploadAnimation = (target: AvatarState | number) => {
		animationTarget = target;
		animationInput.click();
	};
	const chooseAnimation = () => {
		const selected = animationInput.files?.[0];
		animationInput.value = '';
		if (!selected || !value) return;
		if (!/\.vrma$/i.test(selected.name) || selected.size > 10 * 1024 * 1024) {
			error = $i18n.t('Choose a VRMA file, up to 10 MiB.');
			return;
		}
		const id = crypto.randomUUID();
		animationFiles = { ...animationFiles, [id]: selected };
		if (typeof animationTarget === 'number') {
			value = {
				...value,
				gestures: gestures.map((g, i) => (i === animationTarget ? { ...g, file_id: id } : g))
			};
		} else value = { ...value, states: { ...value.states, [animationTarget]: { file_id: id } } };
		error = '';
	};
	const removeState = (mode: AvatarState) => {
		if (!value) return;
		const states = { ...value.states };
		delete states[mode];
		value = { ...value, states };
	};
	const addGesture = () => {
		if (!value) return;
		let n = 1;
		while (gestures.some((g) => g.name === `gesture_${n}`)) n++;
		value = {
			...value,
			gestures: [...gestures, { name: `gesture_${n}`, description: '', file_id: '' }]
		};
	};
	const previewGesture = (name: string) => {
		previewContainer?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
		const result = avatarPreview?.playAnimation(name);
		if (result !== 'started')
			error = $i18n.t(
				result === 'busy'
					? 'Wait for the current gesture to finish.'
					: 'Animation is unavailable or reduced motion is enabled.'
			);
		else error = '';
	};
	export let disabled = false;
	const i18n = getContext<any>('i18n');
	let input: HTMLInputElement;
	let error = '';
	let ready = false;
	let capabilities = { mouth: true, blink: true };
	let state: 'idle' | 'listening' | 'speaking' = 'idle';
	let level = 0;
	let previewTimer: ReturnType<typeof setInterval> | undefined;
	const stopPreview = () => {
		clearInterval(previewTimer);
		state = 'idle';
		level = 0;
	};
	onDestroy(stopPreview);
	const preview = (next: typeof state) => {
		previewContainer?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
		stopPreview();
		avatarPreview?.cancelAnimation();
		state = next;
		if (next === 'speaking') {
			let step = 0;
			previewTimer = setInterval(() => {
				step++;
				level = step % 17 < 3 ? 0 : 0.04 + Math.abs(Math.sin(step * 0.9)) * 0.13;
			}, 60);
		}
	};
	const choose = () => {
		const selected = input.files?.[0];
		input.value = '';
		if (!selected) return;
		if (selected.size > AVATAR_MAX_BYTES || !/\.(vrm|glb)$/i.test(selected.name)) {
			error = $i18n.t('Choose a VRM file, up to 25 MiB.');
			return;
		}
		stopPreview();
		error = '';
		ready = false;
		avatarValid = false;
		file = selected;
		value = { ...value, file_id: '' };
	};
	const remove = () => {
		stopPreview();
		file = null;
		animationFiles = {};
		animationErrors = {};
		animationsLoading = false;
		value = null;
		error = '';
		ready = false;
		avatarValid = true;
	};
</script>

<fieldset {disabled} class="avatar-editor my-4 min-w-0 w-full">
	<legend class="text-xs text-gray-500">{$i18n.t('Voice avatar')}</legend>
	<p class="text-xs text-gray-500 mt-1 mb-3">
		{$i18n.t('A character for bridge voice calls. The orb is used by default.')}
	</p>
	<input
		bind:this={input}
		type="file"
		accept=".vrm,.glb"
		class="hidden"
		on:change={choose}
		aria-label={$i18n.t('Upload voice avatar')}
	/>
	{#if value}
		<div
			bind:this={previewContainer}
			class="preview rounded-xl bg-gray-50 dark:bg-gray-900"
			aria-label={$i18n.t('Avatar preview')}
		>
			{#key file ?? value.file_id}
				<VoiceAvatar
					bind:this={avatarPreview}
					{animationFiles}
					on:animations={(event) => {
						animationsLoading = event.detail.loading;
						animationErrors = event.detail.errors;
					}}
					config={value}
					{file}
					speaking={state === 'speaking'}
					listening={state === 'listening'}
					{level}
					on:ready={(event) => {
						capabilities = event.detail;
						ready = true;
						avatarValid = true;
						error = '';
					}}
					on:error={(event) => {
						error = event.detail?.message ?? $i18n.t('Could not load avatar.');
						ready = false;
						avatarValid = !file;
						stopPreview();
					}}
				/>
			{/key}
			{#if !ready && !error}<span class="preview-message text-xs text-gray-500" role="status"
					>{$i18n.t('Loading avatar…')}</span
				>{/if}
		</div>
		<div
			class="flex gap-1 justify-center my-2"
			role="group"
			aria-label={$i18n.t('Preview behavior')}
		>
			{#each ['idle', 'listening', 'speaking'] as mode}
				<button
					type="button"
					class="preview-state text-xs px-3 py-1.5 rounded-lg"
					class:selected={state === mode}
					disabled={!ready || disabled}
					aria-pressed={state === mode}
					on:click={() => preview(mode as typeof state)}
				>
					{$i18n.t(mode === 'idle' ? 'Idle' : mode === 'listening' ? 'Listening' : 'Speaking')}
				</button>
			{/each}
		</div>
		<p class="text-xs text-gray-500 text-center mb-3">
			{$i18n.t('Silent motion preview. During calls, the mouth follows assistant audio.')}
		</p>
		{#if ready && (!capabilities.mouth || !capabilities.blink)}
			<p class="text-xs text-amber-700 dark:text-amber-400 mb-3" role="status">
				{#if !capabilities.mouth}{$i18n.t(
						'This avatar has no mouth expression; speech will use body motion only.'
					)}{/if}
				{#if !capabilities.blink}
					{$i18n.t('This avatar has no blink expressions.')}{/if}
			</p>
		{/if}
		<input
			bind:this={animationInput}
			type="file"
			accept=".vrma"
			class="hidden"
			on:change={chooseAnimation}
			aria-label={$i18n.t('Upload animation')}
		/>
		<section class="my-4 text-xs" aria-label={$i18n.t('State animations')}>
			<div class="font-medium mb-1">{$i18n.t('State animations')}</div>
			<p class="text-gray-500 mb-2">
				{$i18n.t('Optional clips replace the built-in movement for each state.')}
			</p>
			{#each ['idle', 'listening', 'speaking'] as mode}
				{@const asset = value.states?.[mode as AvatarState]}
				<div class="flex items-center justify-between gap-3 py-2">
					<div class="min-w-0">
						<div>
							{$i18n.t(mode === 'idle' ? 'Idle' : mode === 'listening' ? 'Listening' : 'Speaking')}
						</div>
						<div class="text-gray-500 truncate max-w-44">
							{asset
								? (animationFiles[asset.file_id]?.name ?? $i18n.t('Custom animation'))
								: $i18n.t('Built-in')}
						</div>
					</div>
					<div class="flex shrink-0 gap-3 text-gray-500">
						{#if asset}<button
								type="button"
								disabled={!ready || animationsLoading || !!animationErrors[asset.file_id]}
								on:click={() => preview(mode as AvatarState)}>{$i18n.t('Preview')}</button
							>{/if}
						<button
							type="button"
							aria-label={`${$i18n.t('Upload')} ${mode} VRMA`}
							on:click={() => uploadAnimation(mode as AvatarState)}
							>{$i18n.t(asset ? 'Replace' : 'Upload')}</button
						>
						{#if asset}<button
								type="button"
								aria-label={`${$i18n.t('Remove')} ${mode} VRMA`}
								on:click={() => removeState(mode as AvatarState)}>{$i18n.t('Remove')}</button
							>{/if}
					</div>
				</div>
				{#if asset && animationErrors[asset.file_id]}<p
						class="text-red-600 dark:text-red-400"
						role="alert"
					>
						{animationErrors[asset.file_id]}
					</p>{/if}
			{/each}
		</section>
		<section class="my-4 text-xs" aria-label={$i18n.t('Named gestures')}>
			<div class="flex items-center justify-between">
				<div class="font-medium">{$i18n.t('Named gestures')}</div>
				<button
					type="button"
					class="text-gray-500"
					disabled={gestures.length >= 16}
					on:click={addGesture}>{$i18n.t('Add gesture')}</button
				>
			</div>
			<p class="text-gray-500 mt-1">
				{$i18n.t('The voice model chooses when to play a gesture using its name and description.')}
			</p>
			{#each gestures as gesture, i}
				<div class="mt-3 space-y-2">
					<div class="flex items-center gap-3">
						<input
							aria-label={$i18n.t('Gesture name')}
							class="setting-input min-w-0 flex-1"
							placeholder="wave"
							maxlength="48"
							bind:value={gesture.name}
							on:input={() => {
								if (value) value = { ...value, gestures };
							}}
						/><button
							type="button"
							class="text-gray-500"
							aria-label={`${$i18n.t('Remove gesture')} ${i + 1}`}
							on:click={() => {
								if (value)
									value = { ...value, gestures: gestures.filter((_, index) => index !== i) };
							}}>{$i18n.t('Remove')}</button
						>
					</div>
					<input
						aria-label={$i18n.t('Gesture description')}
						class="setting-input"
						placeholder={$i18n.t('When should the model use this gesture?')}
						maxlength="500"
						bind:value={gesture.description}
						on:input={() => {
							if (value) value = { ...value, gestures };
						}}
					/>
					<div class="flex items-center gap-3 text-gray-500">
						<button
							type="button"
							aria-label={`${$i18n.t('Upload gesture')} ${i + 1} VRMA`}
							on:click={() => uploadAnimation(i)}
							>{$i18n.t(gesture.file_id ? 'Replace clip' : 'Upload VRMA')}</button
						>{#if gesture.file_id}<button
								type="button"
								aria-label={`${$i18n.t('Preview gesture')} ${i + 1}`}
								disabled={!ready || animationsLoading || !!animationErrors[gesture.file_id]}
								on:click={() => previewGesture(gesture.name)}>{$i18n.t('Preview')}</button
							><span class="truncate"
								>{animationFiles[gesture.file_id]?.name ?? $i18n.t('Custom animation')}</span
							>{/if}
					</div>
					{#if animationErrors[gesture.file_id]}<p
							class="text-red-600 dark:text-red-400"
							role="alert"
						>
							{animationErrors[gesture.file_id]}
						</p>{/if}
				</div>
			{/each}
			{#if !namesValid}<p class="mt-2 text-gray-500">
					{$i18n.t(
						'Each gesture needs a clip, a description, and a unique lowercase name using letters, numbers or underscores.'
					)}
				</p>{/if}
		</section>
		<p class="text-xs text-gray-500 mb-4">
			{$i18n.t(
				'VRMA 1.0 · 10 MiB max · 60 seconds max. Body motion only, played in place. Mouth, blinking and gaze remain automatic.'
			)}
		</p>
		{#if animationsLoading}<p class="text-xs text-gray-500" role="status">
				{$i18n.t('Loading animations…')}
			</p>{/if}
	{/if}
	{#if error}<p class="text-xs text-red-600 dark:text-red-400 my-2" role="alert">{error}</p>{/if}
	<div class="flex gap-3 items-center mt-3 text-xs">
		<button
			type="button"
			class="px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-850"
			on:click={() => input.click()}>{$i18n.t(value ? 'Replace avatar' : 'Upload VRM')}</button
		>
		{#if value}<button type="button" class="text-gray-500" on:click={remove}
				>{$i18n.t('Use orb')}</button
			>{/if}
		{#if file}<span class="text-gray-500 truncate">{file.name}</span>{/if}
	</div>
	<p class="text-xs text-gray-500 mt-2">
		{$i18n.t(
			'VRM 0.x or 1.0 · 25 MiB max · Embedded textures. Upload a character you have permission to use.'
		)}
	</p>
</fieldset>

<style>
	.preview {
		height: 320px;
		position: relative;
		overflow: hidden;
	}
	.preview-message {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
	}
	.preview-state.selected {
		background: rgb(127 127 127 / 0.15);
	}
	.setting-input {
		padding: 7px 8px;
		background: rgb(127 127 127 / 0.08);
		border-radius: 7px;
		width: 100%;
	}
</style>
