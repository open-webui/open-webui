<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount, onDestroy, tick, getContext } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings, showSidebar } from '$lib/stores';
	import { chatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';
	import { Shortcut, shortcuts } from '$lib/shortcuts';
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

	// Helper function to check if the pressed keys match the shortcut definition
	const isShortcutMatch = (event: KeyboardEvent, shortcut): boolean => {
		const keys = shortcut?.keys || [];

		const normalized = keys.map((k) => k.toLowerCase());
		const needCtrl = normalized.includes('ctrl') || normalized.includes('mod');
		const needShift = normalized.includes('shift');
		const needAlt = normalized.includes('alt');

		const mainKeys = normalized.filter((k) => !['ctrl', 'shift', 'alt', 'mod'].includes(k));

		// Get the main key pressed
		const keyPressed = event.key.toLowerCase();

		// Check modifiers
		if (needShift && !event.shiftKey) return false;

		if (needCtrl && !(event.ctrlKey || event.metaKey)) return false;
		if (!needCtrl && (event.ctrlKey || event.metaKey)) return false;
		if (needAlt && !event.altKey) return false;
		if (!needAlt && event.altKey) return false;

		if (mainKeys.length && !mainKeys.includes(keyPressed)) return false;

		return true;
	};

	const handleKeyboardShortcuts = (event: KeyboardEvent) => {
		// Only handle shortcuts when on playground completions route
		if (!$page.url.pathname.startsWith('/playground')) {
			return;
		}

		const isInputFocused = document.activeElement === textCompletionAreaElement;

		// Handle playground-specific shortcuts
		if (isShortcutMatch(event, shortcuts[Shortcut.PLAYGROUND_FOCUS_INPUT])) {
			event.preventDefault();
			event.stopPropagation();
			textCompletionAreaElement?.focus();
		} else if (isShortcutMatch(event, shortcuts[Shortcut.PLAYGROUND_RUN])) {
			if (isInputFocused && !loading && selectedModelId) {
				event.preventDefault();
				event.stopPropagation();
				submitHandler();
			}
		} else if (isShortcutMatch(event, shortcuts[Shortcut.PLAYGROUND_CANCEL])) {
			if (loading) {
				event.preventDefault();
				event.stopPropagation();
				stopResponse();
			}
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

		document.addEventListener('keydown', handleKeyboardShortcuts);
	});

	onDestroy(() => {
		document.removeEventListener('keydown', handleKeyboardShortcuts);
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
							class="w-full h-full p-3 bg-transparent border border-gray-100/30 dark:border-gray-850/30 outline-hidden resize-none rounded-lg text-sm"
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
