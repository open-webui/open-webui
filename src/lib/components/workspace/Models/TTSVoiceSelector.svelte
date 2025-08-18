<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { config, settings } from '$lib/stores';
	import { getVoices as _getVoices } from '$lib/apis/audio';

	const i18n = getContext('i18n');

	export let selectedVoice = '';

	let loading = false;
	let voices = [];

	const getVoicesFromAdminSettings = async () => {
		loading = true;
		voices = [];
		
		try {
			// Get the admin-configured TTS engine
			const adminEngine = $config?.audio?.tts?.engine || '';
			
			if (adminEngine === 'browser-kokoro') {
				// Kokoro voices
				voices = [
					{ id: 'af', name: 'AF (Female)' },
					{ id: 'af_bella', name: 'AF Bella (Female)' },
					{ id: 'af_sarah', name: 'AF Sarah (Female)' },
					{ id: 'am_adam', name: 'AM Adam (Male)' },
					{ id: 'am_michael', name: 'AM Michael (Male)' },
					{ id: 'bf_emma', name: 'BF Emma (Female)' },
					{ id: 'bf_isabella', name: 'BF Isabella (Female)' },
					{ id: 'bm_george', name: 'BM George (Male)' },
					{ id: 'bm_lewis', name: 'BM Lewis (Male)' }
				];
			} else if (adminEngine && adminEngine !== '') {
				// External TTS service - get voices from API
				try {
					const res = await _getVoices(localStorage.token);
					if (res && res.voices) {
						voices = res.voices.map(voice => ({
							id: voice.id || voice.name,
							name: voice.name || voice.id
						}));
					}
				} catch (e) {
					console.warn('Failed to fetch voices from admin TTS service:', e);
					voices = [];
				}
			} else {
				// Browser TTS (default)
				const browserVoices = speechSynthesis.getVoices();
				voices = browserVoices.map(voice => ({
					id: voice.name,
					name: voice.name
				}));
			}
		} catch (error) {
			console.error('Error loading voices from admin settings:', error);
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		getVoicesFromAdminSettings();
		
		// Listen for voice changes (browser voices load asynchronously)
		if (typeof speechSynthesis !== 'undefined') {
			speechSynthesis.onvoiceschanged = () => {
				const adminEngine = $config?.audio?.tts?.engine || '';
				if (!adminEngine) {
					getVoicesFromAdminSettings();
				}
			};
		}
	});
</script>

<div class="py-0.5 flex w-full justify-between">
	<div class="self-center text-xs font-medium">{$i18n.t('Voice')}</div>
	<div class="flex items-center relative">
		{#if loading}
			<div class="text-xs text-gray-500">Loading voices...</div>
		{:else}
			<select
				class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
				bind:value={selectedVoice}
				disabled={loading || voices.length === 0}
			>
				<option value="">{$i18n.t('Use default voice')}</option>
				{#each voices as voice}
					<option value={voice.id}>
						{voice.name}
					</option>
				{/each}
			</select>
		{/if}
	</div>
</div>