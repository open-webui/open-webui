<script>
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($config) {
			await goto('/');
		}

		loaded = true;
	});
</script>

{#if loaded}
	<div class="absolute w-full h-full flex z-50">
		<div class="absolute rounded-xl w-full h-full backdrop-blur-sm flex justify-center bg-gray-900/50 p-6">
			<div class="m-auto pb-20 flex flex-col justify-center items-center">
				<div class="max-w-lg text-center">
					<div class="text-4xl font-bold z-50 mb-6">
						🚧 {$i18n.t('Oops! Something’s Missing')}
					</div>

					<p class="text-md mb-4 leading-relaxed text-gray-300">
						{$i18n.t(
							"It seems that the WebUI doesn't have a connected backend. Don't worry! Double-check your setup, and we'll help you get up and running in no time."
						)}
					</p>

					<p class="text-sm mb-8 text-gray-300">
						{$i18n.t('If you need help, visit our documentation or contact support.')}
					</p>

					<div class="mt-6 flex justify-center gap-4">
						<button
							class="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 transition font-medium text-sm text-white shadow-lg"
							on:click={() => {
								location.href = '/';
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