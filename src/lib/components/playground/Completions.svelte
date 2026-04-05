<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings, showSidebar } from '$lib/stores';
	import { chatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';
	import Selector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import MenuLines from '../icons/MenuLines.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let text = '';

	let selectedModelId = '';

	let loading = false;
	let stopResponseFlag = false;

	let textCompletionAreaElement: HTMLTextAreaElement;

	const scrollToBottom = () => {
		const element = textCompletionAreaElement;

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const textCompletionHandler = async () => {
		const model = $models.find((model) => model.id === selectedModelId);

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					{
						role: 'assistant',
						content: text
					}
				]
			},
			`${WEBUI_BASE_URL}/api`
		);

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						controller.abort('User: Stop Response');
					}
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							if (line.includes('[DONE]')) {
								console.log('done');
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								text += data.choices[0].delta.content ?? '';
							}
						}
					}
				} catch (error) {
					console.log(error);
				}

				scrollToBottom();
			}
		}
	};

	const submitHandler = async () => {
		if (selectedModelId) {
			loading = true;
			await textCompletionHandler();

			loading = false;
			stopResponseFlag = false;
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		if ($settings?.models) {
			selectedModelId = $settings?.models[0];
		} else if ($config?.default_models) {
			selectedModelId = $config?.default_models.split(',')[0];
		} else {
			selectedModelId = '';
		}
		loaded = true;
	});
</script>

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
<div class="flex flex-col h-full px-6 py-4">
		<div class="flex flex-col justify-between mb-4 gap-3">
			<div class="flex flex-col gap-2 w-full">
				<label class="text-sm font-semibold text-gray-700 dark:text-gray-300">Model Selection</label>
					<div class="flex w-full">
						<div class="overflow-hidden w-full">
							<div class="max-w-full">
								<Selector
									placeholder={$i18n.t('Select a model')}
									items={$models.map((model) => ({
										value: model.id,
										label: model.name,
										model: model
									}))}
									bind:value={selectedModelId}
								/>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div
			class="pt-0 pb-4 flex flex-col justify-between w-full flex-auto overflow-auto h-0 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm"
			id="messages-container"
		>
			<div class="h-full w-full flex flex-col">
				<div class="flex-1">
					<textarea
						id="text-completion-textarea"
						bind:this={textCompletionAreaElement}
						class="w-full h-full p-4 bg-transparent outline-none resize-none text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
						bind:value={text}
						placeholder={$i18n.t("Enter your prompt here...")}
					/>
				</div>
			</div>
		</div>

		<div class="pt-4 flex justify-end gap-2">
			{#if !loading}
				<button
					class="px-6 py-2.5 text-sm font-semibold bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white transition-all rounded-lg shadow-sm hover:shadow-md"
					on:click={() => {
						submitHandler();
					}}
				>
					{$i18n.t('Run')}
				</button>
			{:else}
				<button
					class="px-6 py-2.5 text-sm font-semibold bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-900/30 dark:hover:bg-red-900/50 dark:text-red-400 transition-all rounded-lg"
					on:click={() => {
						stopResponse();
					}}
				>
					{$i18n.t('Cancel')}
				</button>
			{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
