<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings, showSidebar } from '$lib/stores';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';


	import Selector from '$lib/components/chat/ModelSelector/Selector.svelte';

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

		try {
			const res = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					model: model.id,
					stream: false, // Use non-streaming for playground to avoid socket issues
					messages: [
						{
							role: 'assistant',
							content: text
						}
					],
					model_item: {
						...model,
						direct: model.direct || model.owned_by === 'openai' // Ensure direct flag is set for OpenAI models
					}
				},
				`http://localhost:8080/api`
			);

			if (res && res.choices && res.choices[0] && res.choices[0].message) {
				const content = res.choices[0].message.content || '';
				text += content;
				await tick();
				scrollToBottom();
			}
		} catch (error) {
			console.error('Text completion error:', error);
			toast.error(`Error: ${error.message || error}`);
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
		<div class=" flex flex-col h-full px-4">
			<div class="flex flex-col justify-between mb-1 gap-1">
				<div class="flex flex-col gap-1 w-full">
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
				class=" pt-0.5 pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
				id="messages-container"
			>
				<div class=" h-full w-full flex flex-col">
					<div class="flex-1">
						<textarea
							id="text-completion-textarea"
							bind:this={textCompletionAreaElement}
							class="w-full h-full p-3 bg-transparent border border-gray-100 dark:border-gray-850 outline-hidden resize-none rounded-lg text-sm"
							bind:value={text}
							placeholder={$i18n.t("You're a helpful assistant.")}
						/>
					</div>
				</div>
			</div>

			<div class="pb-3 flex justify-end">
				{#if !loading}
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						on:click={() => {
							submitHandler();
						}}
					>
						{$i18n.t('Run')}
					</button>
				{:else}
					<button
						class="px-3 py-1.5 text-sm font-medium bg-gray-300 text-black transition rounded-full"
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
