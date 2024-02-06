<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { voices } from '$lib/stores';
	const dispatch = createEventDispatcher();

	export let saveSettings: Function;

	// Voice
	let speakVoice = '';

	onMount(async () => {
		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');

		speakVoice = settings.speakVoice ?? '';

		const getVoicesLoop = setInterval(async () => {
			const _voices = await speechSynthesis.getVoices();
			await voices.set(_voices);

			// do your loop
			if (_voices.length > 0) {
				clearInterval(getVoicesLoop);
			}
		}, 100);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		saveSettings({
			speakVoice: speakVoice !== '' ? speakVoice : undefined
		});
		dispatch('save');
	}}
>
	<div class=" space-y-3">
		<div class=" space-y-3">
			<div>
				<div class=" mb-2.5 text-sm font-medium">Set Default Voice</div>
				<div class="flex w-full">
					<div class="flex-1">
						<select
							class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
							bind:value={speakVoice}
							placeholder="Select a voice"
						>
							<option value="" selected>Default</option>
							{#each $voices.filter((v) => v.localService === true) as voice}
								<option value={voice.name} class="bg-gray-100 dark:bg-gray-700">{voice.name}</option
								>
							{/each}
						</select>
					</div>
				</div>
			</div>
		</div>

		<!--
							<div>
								<div class=" mb-2.5 text-sm font-medium">
									Gravatar Email <span class=" text-gray-400 text-sm">(optional)</span>
								</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
											placeholder="Enter Your Email"
											bind:value={gravatarEmail}
											autocomplete="off"
											type="email"
										/>
									</div>
								</div>
								<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
									Changes user profile image to match your <a
										class=" text-gray-500 dark:text-gray-300 font-medium"
										href="https://gravatar.com/"
										target="_blank">Gravatar.</a
									>
								</div>
							</div> -->
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
