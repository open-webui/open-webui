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

<div class="w-full max-h-full overflow-y-auto">
	<div class="flex flex-col max-w-4xl mx-auto mt-6 mb-10">
		<div class="w-full flex flex-col justify-center">
			<div class="w-full mb-4">
				<div class="text-sm mb-2">{$i18n.t('Model')}</div>
				<div class="w-full mt-1">
					<div class="w-full">
						<Selector
							placeholder={$i18n.t('Select a model')}
							items={$models.map((model) => ({
								value: model.id,
								label: model.name,
								model: model
							}))}
							bind:value={selectedModelId}
							className="w-full"
							triggerClassName="w-full text-sm rounded-lg py-2 px-4 bg-gray-50 dark:text-gray-300 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 outline-hidden"
						/>
					</div>
				</div>
			</div>
		</div>

		<div class="w-full">
			<div class="text-sm mb-2">{$i18n.t('Input')}</div>
			<div class="w-full mt-1">
				<div class="w-full rounded-lg bg-gray-50 dark:bg-gray-850 h-[400px] overflow-hidden">
					<textarea
						id="text-completion-textarea"
						bind:this={textCompletionAreaElement}
						class="w-full h-full p-3 bg-transparent outline-hidden resize-none text-sm"
						bind:value={text}
						placeholder={$i18n.t("You're a helpful assistant.")}
					/>
				</div>
			</div>
		</div>

		<div class="flex justify-center mt-8 mb-12">
			{#if !loading}
				<button
					class="w-full bg-gray-800 dark:bg-gray-700 text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-900 dark:hover:bg-gray-600 transition-colors"
					on:click={() => {
						submitHandler();
					}}
				>
					{$i18n.t('Run')}
				</button>
			{:else}
				<button
					class="w-full bg-gray-300 text-black py-3 px-4 rounded-lg font-medium transition-colors"
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

<style>
	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
