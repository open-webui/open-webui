<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	export let saveSettings: Function;

	// Voice
	let engines = ['', 'openai'];
	let engine = '';

	let voices = [];
	let speaker = '';

	const getOpenAIVoices = () => {
		voices = [
			{ name: 'alloy' },
			{ name: 'echo' },
			{ name: 'fable' },
			{ name: 'onyx' },
			{ name: 'nova' },
			{ name: 'shimmer' }
		];
	};

	const getWebAPIVoices = () => {
		const getVoicesLoop = setInterval(async () => {
			voices = await speechSynthesis.getVoices();

			// do your loop
			if (voices.length > 0) {
				clearInterval(getVoicesLoop);
			}
		}, 100);
	};

	onMount(async () => {
		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');

		engine = settings?.speech?.engine ?? '';
		speaker = settings?.speech?.speaker ?? '';

		if (engine === 'openai') {
			getOpenAIVoices();
		} else {
			getWebAPIVoices();
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		saveSettings({
			speech: {
				engine: engine !== '' ? engine : undefined,
				speaker: speaker !== '' ? speaker : undefined
			}
		});
		dispatch('save');
	}}
>
	<div class=" space-y-3">
		<div class=" py-0.5 flex w-full justify-between">
			<div class=" self-center text-sm font-medium">Speech Engine</div>
			<div class="flex items-center relative">
				<select
					class="w-fit pr-8 rounded py-2 px-2 text-xs bg-transparent outline-none text-right"
					bind:value={engine}
					placeholder="Select a mode"
					on:change={(e) => {
						if (e.target.value === 'openai') {
							getOpenAIVoices();
							speaker = 'alloy';
						} else {
							getWebAPIVoices();
							speaker = '';
						}
					}}
				>
					<option value="">Default (Web API)</option>
					<option value="openai">Open AI</option>
				</select>
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		{#if engine === ''}
			<div>
				<div class=" mb-2.5 text-sm font-medium">Set Voice</div>
				<div class="flex w-full">
					<div class="flex-1">
						<select
							class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
							bind:value={speaker}
							placeholder="Select a voice"
						>
							<option value="" selected>Default</option>
							{#each voices.filter((v) => v.localService === true) as voice}
								<option value={voice.name} class="bg-gray-100 dark:bg-gray-700">{voice.name}</option
								>
							{/each}
						</select>
					</div>
				</div>
			</div>
		{:else if engine === 'openai'}
			<div>
				<div class=" mb-2.5 text-sm font-medium">Set Voice</div>
				<div class="flex w-full">
					<div class="flex-1">
						<select
							class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
							bind:value={speaker}
							placeholder="Select a voice"
						>
							{#each voices as voice}
								<option value={voice.name} class="bg-gray-100 dark:bg-gray-700">{voice.name}</option
								>
							{/each}
						</select>
					</div>
				</div>
			</div>
		{/if}
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
