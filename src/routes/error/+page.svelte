<script>
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';
	import { onMount } from 'svelte';

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
		<div class="absolute rounded-xl w-full h-full backdrop-blur flex justify-center">
			<div class="m-auto pb-44 flex flex-col justify-center">
				<div class="max-w-md">
					<div class="text-center text-2xl font-medium z-50">Ollama Backend nicht erreichbar.</div>

					<div class=" mt-4 text-center text-sm w-full">
						Das Frontend kann derzeit keine Verbindug zum Backend herstellen. Versuche es später erneut. Eventuell werden Wartungsarbeiten vorgenommen.

						<br class=" " />
						<br class=" " />

						<a class=" font-semibold underline" href="mailto:jannik.streidl@f-i-ts.de;christian.koenig@f-i-ts.de;patrick.wilhelm@f-i-ts.de;claus.jordan@f-i-ts.de" target="_blank"
							>Falls dies länger besteht kontaktiere bitte einen Admin aus 55021 AI Services. Vielen Dank!</a
						>
					</div>

					<div class=" mt-6 mx-auto relative group w-fit">
						<button
							class="relative z-20 flex px-5 py-2 rounded-full bg-gray-100 hover:bg-gray-200 transition font-medium text-sm"
							on:click={() => {
								location.href = '/';
							}}
						>
							Erneut prüfen
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
