<script lang="ts">
	import {
		getSystemSettings,
		updateSystemSettings
	} from '$lib/apis/rag';

	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	let systemSettings = {
		bypassSSLVerify: false
	};

	const toggleBypassSSLVerification = async () => {
		systemSettings.bypassSSLVerify = !systemSettings.bypassSSLVerify;

		systemSettings = await updateSystemSettings(localStorage.token, systemSettings);
	};

	onMount(async () => {
		systemSettings = await getSystemSettings(localStorage.token);
	});
</script>

<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-[22rem]">
	<div>
		<div class=" mb-1 text-sm font-medium">{$i18n.t('Retrieval Augmented Generation Settings')}</div>

		<div>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Bypass SSL verification for Websites')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
							toggleBypassSSLVerification();
						}}
					type="button"
				>
					{#if systemSettings.bypassSSLVerify === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
</div>
