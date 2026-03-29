<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, onDestroy, getContext, tick } from 'svelte';

	import { settings, config } from '$lib/stores';
	import { getRealtimeClientConfig } from '$lib/apis/audio';

	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	export let searchTarget: string | null = null;

	// --- Realtime voice state ---
	let showAdvancedRealtimeSettings = false;
	let realtimeAutoUnmuteWhenReady = false;
	let realtimeVoice = 'marin';
	let realtimeSpeed = 1;
	let realtimeVadType: 'semantic_vad' | 'server_vad' | 'push_to_talk' = 'server_vad';
	let realtimeSemanticVadEagerness: 'low' | 'medium' | 'high' | 'auto' = 'auto';
	let realtimeServerVadThreshold = 0.5;
	let realtimeServerVadSilenceDurationMs = 500;
	let realtimeServerVadPrefixPaddingMs = 300;
	let realtimeNoiseReduction: 'near_field' | 'far_field' | '' = 'near_field';
	let realtimeVadCreateResponse = true;
	let realtimeVadInterruptResponse = true;
	let realtimeClientConfig = null;
	let realtimeVoiceOptions: { id: string; name: string }[] = [];

	// --- Search / highlight infrastructure ---
	let highlightedSection: string | null = null;
	let lastAppliedSearchTarget: string | null = null;
	let clearHighlightTimeout: ReturnType<typeof setTimeout> | null = null;
	const sectionNodes: Record<string, HTMLDivElement | null> = {};
	const advancedSearchTargets = new Set([
		'realtime-noise-reduction',
		'realtime-response-eagerness'
	]);
	const resolveSearchTarget = (target: string) =>
		target === 'realtime-response-eagerness' && realtimeVadType !== 'semantic_vad'
			? 'realtime-vad'
			: target;

	const registerSection = (node: HTMLDivElement, sectionId: string) => {
		sectionNodes[sectionId] = node;

		return {
			update(nextSectionId: string) {
				if (nextSectionId === sectionId) {
					return;
				}

				if (sectionNodes[sectionId] === node) {
					sectionNodes[sectionId] = null;
				}

				sectionId = nextSectionId;
				sectionNodes[sectionId] = node;
			},
			destroy() {
				if (sectionNodes[sectionId] === node) {
					sectionNodes[sectionId] = null;
				}
			}
		};
	};

	const getSectionClasses = (sectionId: string) =>
		highlightedSection === sectionId
			? 'rounded-xl bg-blue-50/60 ring-1 ring-blue-300 dark:bg-blue-500/10 dark:ring-blue-700 px-3 py-2 -mx-3'
			: '';

	const focusSearchTarget = async (target: string) => {
		await tick();

		const node = sectionNodes[target];
		if (!node) {
			return;
		}

		node.scrollIntoView({ behavior: 'smooth', block: 'start' });
		highlightedSection = target;

		if (clearHighlightTimeout) {
			clearTimeout(clearHighlightTimeout);
		}

		clearHighlightTimeout = setTimeout(() => {
			if (highlightedSection === target) {
				highlightedSection = null;
			}
		}, 1800);
	};

	// --- Public API: expose current settings to parent ---
	export function getRealtimeSettings() {
		return {
			autoUnmuteWhenReady: realtimeAutoUnmuteWhenReady,
			voice: realtimeVoice,
			speed: realtimeSpeed,
			vadType: realtimeVadType,
			semanticVadEagerness: realtimeSemanticVadEagerness,
			serverVadThreshold: realtimeServerVadThreshold,
			serverVadSilenceDurationMs: realtimeServerVadSilenceDurationMs,
			serverVadPrefixPaddingMs: realtimeServerVadPrefixPaddingMs,
			noiseReduction: realtimeNoiseReduction,
			vadCreateResponse: realtimeVadCreateResponse,
			vadInterruptResponse: realtimeVadInterruptResponse
		};
	}

	// --- Lifecycle ---
	onMount(async () => {
		if ($config?.audio?.realtime?.enabled) {
			realtimeClientConfig = await getRealtimeClientConfig(localStorage.token).catch((e) => {
				toast.error(`${e}`);
				return null;
			});
			realtimeVoiceOptions = realtimeClientConfig?.capabilities?.voices ?? [];
		}

		const realtimeDefaults = realtimeClientConfig?.defaults ?? {};
		const realtimeSettings = $settings?.audio?.realtime ?? {};

		realtimeAutoUnmuteWhenReady = realtimeSettings.autoUnmuteWhenReady ?? false;
		realtimeVoice = realtimeSettings.voice ?? realtimeDefaults.voice ?? 'marin';
		realtimeSpeed = realtimeSettings.speed ?? realtimeDefaults.speed ?? 1;
		realtimeVadType = realtimeSettings.vadType ?? realtimeDefaults.vad_type ?? 'server_vad';
		realtimeSemanticVadEagerness =
			realtimeSettings.semanticVadEagerness ?? realtimeDefaults.semantic_vad_eagerness ?? 'auto';
		realtimeServerVadThreshold =
			realtimeSettings.serverVadThreshold ?? realtimeDefaults.server_vad_threshold ?? 0.5;
		realtimeServerVadSilenceDurationMs =
			realtimeSettings.serverVadSilenceDurationMs ??
			realtimeDefaults.server_vad_silence_duration_ms ??
			500;
		realtimeServerVadPrefixPaddingMs =
			realtimeSettings.serverVadPrefixPaddingMs ??
			realtimeDefaults.server_vad_prefix_padding_ms ??
			300;
		realtimeNoiseReduction =
			realtimeSettings.noiseReduction ?? realtimeDefaults.noise_reduction ?? 'near_field';
		realtimeVadCreateResponse =
			realtimeSettings.vadCreateResponse ?? realtimeDefaults.vad_create_response ?? true;
		realtimeVadInterruptResponse =
			realtimeSettings.vadInterruptResponse ?? realtimeDefaults.vad_interrupt_response ?? true;
		if (realtimeVoice && !realtimeVoiceOptions.some((option) => option.id === realtimeVoice)) {
			realtimeVoiceOptions = [{ id: realtimeVoice, name: realtimeVoice }, ...realtimeVoiceOptions];
		}
	});

	// --- Reactive: searchTarget highlight ---
	$: if (searchTarget && searchTarget !== lastAppliedSearchTarget) {
		if (advancedSearchTargets.has(searchTarget)) {
			showAdvancedRealtimeSettings = true;
		}

		lastAppliedSearchTarget = searchTarget;
		void focusSearchTarget(resolveSearchTarget(searchTarget));
	} else if (!searchTarget && lastAppliedSearchTarget !== null) {
		lastAppliedSearchTarget = null;
		highlightedSection = null;
		if (clearHighlightTimeout) {
			clearTimeout(clearHighlightTimeout);
			clearHighlightTimeout = null;
		}
	}

	onDestroy(() => {
		if (clearHighlightTimeout) {
			clearTimeout(clearHighlightTimeout);
		}
	});
</script>

<hr class=" border-gray-100/30 dark:border-gray-850/30" />

<div class="space-y-3">
	<div use:registerSection={'realtime-voice'} class={getSectionClasses('realtime-voice')}>
		<div class=" mb-1 text-sm font-medium">{$i18n.t('Realtime Voice')}</div>
		<div class="text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t('Used for realtime voice calls.')}
		</div>
	</div>

	<div
		use:registerSection={'realtime-auto-unmute'}
		class={getSectionClasses('realtime-auto-unmute')}
	>
		<div class="py-0.5 flex w-full justify-between">
			<div class="self-center text-xs font-medium">
				{$i18n.t('Auto-unmute microphone when call is ready')}
			</div>
			<div class="mt-1">
				<Switch bind:state={realtimeAutoUnmuteWhenReady} />
			</div>
		</div>
		<div class="text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t('Automatically unmutes the microphone once the realtime call is ready.')}
		</div>
	</div>

	<div
		use:registerSection={'realtime-voice-choice'}
		class={getSectionClasses('realtime-voice-choice')}
	>
		<div class=" py-0.5 flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Voice')}</div>
			<div class="flex items-center relative">
				<select
					class="cursor-pointer w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
					bind:value={realtimeVoice}
				>
					{#each realtimeVoiceOptions as realtimeVoiceOption}
						<option value={realtimeVoiceOption.id}>{realtimeVoiceOption.name}</option>
					{/each}
				</select>
			</div>
		</div>
		<div class="text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t('Recommended voices include marin and cedar.')}
		</div>
	</div>

	<div
		use:registerSection={'realtime-speech-speed'}
		class={getSectionClasses('realtime-speech-speed')}
	>
		<div class="py-0.5 flex w-full justify-between gap-3">
			<div class="self-center text-xs font-medium">{$i18n.t('Speech Speed')}</div>
			<input
				type="number"
				step="0.05"
				min="0.25"
				max="1.5"
				class="w-24 rounded-lg py-1 px-2 text-right text-xs bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
				bind:value={realtimeSpeed}
			/>
		</div>
		<div class="text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t('Adjusts how quickly the assistant speaks in realtime calls.')}
		</div>
	</div>

	<div use:registerSection={'realtime-vad'} class={getSectionClasses('realtime-vad')}>
		<div class=" py-0.5 flex w-full justify-between">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Voice Activity Detection (VAD)')}
			</div>
			<div class="flex items-center relative">
				<select
					class="cursor-pointer w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
					bind:value={realtimeVadType}
				>
					<option value="semantic_vad">{$i18n.t('Smart (AI-powered)')}</option>
					<option value="server_vad">{$i18n.t('Standard (volume-based)')}</option>
					<option value="push_to_talk">{$i18n.t('Push to Talk')}</option>
				</select>
			</div>
		</div>
		<div class="text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t(
				'Controls how the call decides when you have finished speaking: AI-powered detection, volume-based detection, or push-to-talk.'
			)}
		</div>
	</div>

	<div class="flex justify-between items-center text-sm">
		<div class="font-medium">{$i18n.t('Advanced Settings')}</div>
		<button
			class=" text-xs font-medium {($settings?.highContrastMode ?? false)
				? 'text-gray-800 dark:text-gray-100'
				: 'text-gray-400 dark:text-gray-500'}"
			type="button"
			aria-expanded={showAdvancedRealtimeSettings}
			on:click={() => {
				showAdvancedRealtimeSettings = !showAdvancedRealtimeSettings;
			}}
		>
			{showAdvancedRealtimeSettings ? $i18n.t('Hide') : $i18n.t('Show')}
		</button>
	</div>

	{#if showAdvancedRealtimeSettings}
		<div class="space-y-3">
			<div
				use:registerSection={'realtime-noise-reduction'}
				class={getSectionClasses('realtime-noise-reduction')}
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Noise Reduction')}
					</div>
					<div class="flex items-center relative">
						<select
							class="cursor-pointer w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
							bind:value={realtimeNoiseReduction}
						>
							<option value="near_field">
								{$i18n.t('Close range (headset/laptop)')}
							</option>
							<option value="far_field">
								{$i18n.t('Far range (room mic/speaker)')}
							</option>
							<option value="">{$i18n.t('None')}</option>
						</select>
					</div>
				</div>
				<div class="text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t('Preprocesses microphone audio before turn detection and transcription.')}
				</div>
			</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Auto-respond after speech')}
				</div>
				<div class="mt-1">
					<Switch bind:state={realtimeVadCreateResponse} />
				</div>
			</div>
			<div class="text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Automatically creates a model response when you finish speaking.')}
			</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow speech interruption')}
				</div>
				<div class="mt-1">
					<Switch bind:state={realtimeVadInterruptResponse} />
				</div>
			</div>
			<div class="text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Lets a new user turn interrupt the assistant while it is still speaking.')}
			</div>

			{#if realtimeVadType === 'semantic_vad'}
				<div
					use:registerSection={'realtime-response-eagerness'}
					class={getSectionClasses('realtime-response-eagerness')}
				>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Response Eagerness')}
						</div>
						<div class="flex items-center relative">
							<select
								class="cursor-pointer w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
								bind:value={realtimeSemanticVadEagerness}
							>
								<option value="auto">{$i18n.t('Auto')}</option>
								<option value="low">{$i18n.t('Low')}</option>
								<option value="medium">{$i18n.t('Medium')}</option>
								<option value="high">{$i18n.t('High')}</option>
							</select>
						</div>
					</div>
					<div class="text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t(
							'Higher eagerness makes the assistant respond sooner after speech ends.'
						)}
					</div>
				</div>
			{:else if realtimeVadType === 'server_vad'}
				<div class="space-y-3">
					<div>
						<div class="py-0.5 flex w-full justify-between gap-3">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Volume Threshold')}
							</div>
							<input
								type="number"
								step="0.1"
								min="0"
								max="1"
								class="w-24 rounded-lg py-1 px-2 text-right text-xs bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								bind:value={realtimeServerVadThreshold}
							/>
						</div>
						<div class="text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t(
								'Minimum audio level required before speech is treated as a user turn.'
							)}
						</div>
					</div>

					<div>
						<div class="py-0.5 flex w-full justify-between gap-3">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Silence Duration (ms)')}
							</div>
							<input
								type="number"
								min="0"
								class="w-24 rounded-lg py-1 px-2 text-right text-xs bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								bind:value={realtimeServerVadSilenceDurationMs}
							/>
						</div>
						<div class="text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('How long silence must last before the turn is considered finished.')}
						</div>
					</div>

					<div>
						<div class="py-0.5 flex w-full justify-between gap-3">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Prefix Padding (ms)')}
							</div>
							<input
								type="number"
								min="0"
								class="w-24 rounded-lg py-1 px-2 text-right text-xs bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								bind:value={realtimeServerVadPrefixPaddingMs}
							/>
						</div>
						<div class="text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t(
								'Keeps a small amount of audio before speech starts so the beginning is not clipped.'
							)}
						</div>
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>
