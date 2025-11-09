<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getMCPPromptContent, type MCPPrompt } from '$lib/apis/mcp-prompts';
	import { user } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let prompt: MCPPrompt;

	const i18n = getContext('i18n');

	let promptContent: any = null;
	let loadingContent = false;
	let promptArguments: Record<string, any> = {};

	const loadPromptContent = async (args = {}) => {
		loadingContent = true;
		promptArguments = {};

		if ((prompt.arguments || []).length === 0 || Object.keys(args).length != 0) {
			try {
				promptContent = await getMCPPromptContent($user.token, prompt.server_id, prompt.name, args);
			} catch (error) {
				console.error('Error loading prompt content:', error);
				toast.error('Failed to load prompt content');
				promptContent = null;
			} finally {
				loadingContent = false;
			}
		} else {
			promptContent = null;
			loadingContent = false;
		}
	};

	const loadPromptWithArgs = async () => {
		await loadPromptContent(promptArguments);
	};

	const useRenderedPrompt = () => {
		if (!promptContent?.messages) return;

		let promptText = promptContent.messages
			.map((m) => {
				if (typeof m.content === 'string') {
					return m.content;
				} else if (m.content?.text) {
					return m.content.text;
				} else if (m.content?.type === 'text') {
					return m.content.text || '';
				}
				return '';
			})
			.filter(Boolean)
			.join('\n\n');

		window.location.href = `/?q=${encodeURIComponent(promptText)}`;
	};

	onMount(() => {
		loadPromptContent();
	});
</script>

<div class="w-full max-h-full flex justify-center">
	<div class="flex flex-col w-full mb-10">
		<div class="my-2">
			<div class="flex flex-col w-full">
				<div class="text-2xl font-medium w-full bg-transparent">
					{prompt.name}
				</div>

				{#if prompt.description}
					<div class="text-gray-600 dark:text-gray-300 mt-2">
						{prompt.description}
					</div>
				{/if}

				<div class="text-sm text-gray-500 dark:text-gray-400 mt-2">
					Server: {prompt.server_id}
				</div>
			</div>
		</div>

		{#if prompt.arguments && prompt.arguments.length > 0}
			<div class="my-4">
				<div class="text-sm font-semibold mb-3">{$i18n.t('Parameters')}</div>

				<div class="space-y-3">
					{#each prompt.arguments as arg}
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								{arg.name}
								{#if arg.required}<span class="text-red-500">*</span>{/if}
							</label>
							<input
								type="text"
								bind:value={promptArguments[arg.name]}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
								placeholder={arg.description || `Enter ${arg.name}`}
							/>
						</div>
					{/each}

					<button
						class="text-sm px-4 py-2 transition rounded-xl bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black"
						type="button"
						on:click={loadPromptWithArgs}
						disabled={loadingContent}
					>
						<div class="font-medium">{$i18n.t('Load Prompt')}</div>
					</button>
				</div>
			</div>
		{/if}

		{#if loadingContent}
			<div class="flex justify-center items-center h-32">
				<Spinner />
			</div>
		{:else if promptContent}
			<div class="my-4">
				<div class="flex w-full justify-between items-center mb-3">
					<div class="text-sm font-semibold">{$i18n.t('Messages')}</div>
					<button
						class="text-sm px-4 py-2 transition rounded-xl bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black"
						type="button"
						on:click={useRenderedPrompt}
					>
						<div class="font-medium">{$i18n.t('Use Prompt')}</div>
					</button>
				</div>

				<div class="space-y-3">
					{#each promptContent.messages as message}
						<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
							<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 capitalize">
								{message.role}
							</div>
							<div class="text-gray-900 dark:text-white whitespace-pre-wrap text-sm">
								{typeof message.content === 'string'
									? message.content
									: message.content?.text || JSON.stringify(message.content)}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>
