<script>
	import { goto } from '$app/navigation';
	import { getBackendConfig } from '$lib/apis';
	import { WEBUI_NAME, config } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let checkInProgress = false;
	const POLL_INTERVAL_MS = 2000;

	const checkBackendAvailability = async () => {
		if (checkInProgress) {
			return;
		}

		checkInProgress = true;
		try {
			const backendConfig = await getBackendConfig();
			if (backendConfig) {
				await config.set(backendConfig);
				await goto('/');
			}
		} catch {
			// Keep polling until backend is available.
		} finally {
			checkInProgress = false;
		}
	};

	onMount(() => {
		if ($config) {
			void goto('/');
			return;
		}

		void checkBackendAvailability();
		const pollId = setInterval(() => {
			void checkBackendAvailability();
		}, POLL_INTERVAL_MS);

		loaded = true;

		return () => {
			clearInterval(pollId);
		};
	});
</script>

{#if loaded}
	<div class="absolute w-full h-full flex z-50">
		<div class="absolute rounded-xl w-full h-full backdrop-blur-sm flex justify-center">
			<div class="m-auto pb-44 flex flex-col justify-center">
				<div class="max-w-md">
					<div class="text-center text-2xl font-medium z-50">
						{$i18n.t('{{webUIName}} Backend Required', { webUIName: $WEBUI_NAME })}
					</div>

					<div class=" mt-4 text-center text-sm w-full">
						{$i18n.t(
							"Oops! You're using an unsupported method (frontend only). Please serve the WebUI from the backend."
						)}

						<br class=" " />
						<br class=" " />
						<a
							class=" font-medium underline"
							href="https://github.com/open-webui/open-webui#how-to-install-"
							target="_blank">{$i18n.t('See readme.md for instructions')}</a
						>
						{$i18n.t('or')}
						<a class=" font-medium underline" href="https://discord.gg/5rJgQTnV4s" target="_blank"
							>{$i18n.t('join our Discord for help.')}</a
						>
					</div>

					<div class=" mt-6 mx-auto relative group w-fit">
						<button
							class="relative z-20 flex px-5 py-2 rounded-full bg-gray-100 hover:bg-gray-200 transition font-medium text-sm text-black"
							on:click={() => {
								void checkBackendAvailability();
							}}
						>
							{$i18n.t('Check Again')}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
