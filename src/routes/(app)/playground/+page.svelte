<script>
	import { goto } from '$app/navigation';

	import { onMount } from 'svelte';

	import { toast } from 'svelte-sonner';

	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models } from '$lib/stores';

	import { cancelChatCompletion, generateTextCompletion } from '$lib/apis/ollama';
	import { splitStream } from '$lib/utils';

	let mode = 'complete';
	let loaded = false;

	let text = '';

	let selectedModel = '';

	let loading = false;
	let currentRequestId;
	let stopResponseFlag = false;

	const scrollToBottom = () => {
		const element = document.getElementById('text-completion-textarea');
		element.scrollTop = element.scrollHeight;
	};

	// const cancelHandler = async () => {
	// 	if (currentRequestId) {
	// 		const res = await cancelChatCompletion(localStorage.token, currentRequestId);
	// 		currentRequestId = null;
	// 		loading = false;
	// 	}
	// };

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const submitHandler = async () => {
		if (selectedModel) {
			loading = true;

			const res = await generateTextCompletion(localStorage.token, selectedModel, text);

			if (res && res.ok) {
				const reader = res.body
					.pipeThrough(new TextDecoderStream())
					.pipeThrough(splitStream('\n'))
					.getReader();

				while (true) {
					const { value, done } = await reader.read();
					if (done || stopResponseFlag) {
						if (stopResponseFlag) {
							await cancelChatCompletion(localStorage.token, currentRequestId);
						}

						currentRequestId = null;
						break;
					}

					try {
						let lines = value.split('\n');

						for (const line of lines) {
							if (line !== '') {
								console.log(line);
								let data = JSON.parse(line);

								if ('detail' in data) {
									throw data;
								}

								if ('id' in data) {
									console.log(data);
									currentRequestId = data.id;
								} else {
									if (data.done == false) {
										text += data.response;
									} else {
										console.log('done');
									}
								}
							}
						}
					} catch (error) {
						console.log(error);
					}

					scrollToBottom();
				}
			}

			loading = false;
			stopResponseFlag = false;
			currentRequestId = null;
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{`Playground | ${$WEBUI_NAME}`}
	</title>
</svelte:head>

<div class="min-h-screen max-h-[100dvh] w-full flex justify-center dark:text-white">
	<div class=" flex flex-col justify-between w-full overflow-y-auto h-[100dvh]">
		<div class="max-w-2xl mx-auto w-full px-3 p-3 md:px-0 h-full">
			<div class=" flex flex-col h-full">
				<div class="flex flex-col sm:flex-row justify-between mb-2.5 gap-1">
					<div class="flex items-center gap-2">
						<div class=" text-2xl font-semibold self-center">Playground</div>

						<div>
							<button
								class=" flex items-center gap-2 text-xs px-3 py-0.5 rounded-lg {mode === 'chat' &&
									'text-sky-600 dark:text-sky-200 bg-sky-200/30'} {mode === 'complete' &&
									'text-green-600 dark:text-green-200 bg-green-200/30'} "
								on:click={() => {
									if (mode === 'complete') {
										mode = 'chat';
									} else {
										mode = 'complete';
									}
								}}
							>
								<div
									class="w-1 h-1 rounded-full {mode === 'chat' &&
										'bg-sky-600 dark:bg-sky-300'} {mode === 'complete' &&
										'bg-green-600 dark:bg-green-300'} "
								/>
								{mode}</button
							>
						</div>
					</div>

					<div class=" sm:self-center flex gap-1">
						<select
							id="models"
							class="outline-none bg-transparent text-xs font-medium rounded-lg w-full placeholder-gray-400"
							bind:value={selectedModel}
						>
							<option class=" text-gray-700" value="" selected disabled>Select a model</option>

							{#each $models as model}
								{#if model.name === 'hr'}
									<hr />
								{:else if !(model?.external ?? false)}
									<option value={model.id} class="text-gray-700 text-lg"
										>{model.name +
											`${model.size ? ` (${(model.size / 1024 ** 3).toFixed(1)}GB)` : ''}`}</option
									>
								{/if}
							{/each}
						</select>

						<button
							class=" self-center dark:hover:text-gray-300"
							id="open-settings-button"
							on:click={async () => {}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
								/>
							</svg>
						</button>
					</div>
				</div>

				<div class="flex-1 flex flex-col space-y-2.5">
					<div class="flex-1">
						<textarea
							id="text-completion-textarea"
							class="w-full h-full p-3 bg-transparent outline outline-1 outline-gray-200 dark:outline-gray-700 resize-none rounded-lg"
							bind:value={text}
						/>
					</div>

					<div>
						{#if !loading}
							<button
								class="px-3 py-1.5 text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-gray-50 transition rounded-lg"
								on:click={() => {
									submitHandler();
								}}
							>
								Submit
							</button>
						{:else}
							<button
								class="px-3 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-900 transition rounded-lg"
								on:click={() => {
									stopResponse();
								}}
							>
								Cancel
							</button>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<!-- <div class="min-h-screen max-h-[100dvh] w-full flex justify-center dark:text-white">
	{#if loaded}
		<div class=" flex flex-col justify-between w-full overflow-y-auto">
			<div class="max-w-2xl mx-auto w-full px-3 md:px-0 my-10">
				<div class="w-full">
					<div class=" flex flex-col justify-center">
						<div class=" text-2xl font-semibold self-center">My Documents</div>

						<div>test</div>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div> -->

<style>
	.font-mona {
		font-family: 'Mona Sans';
	}

	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
