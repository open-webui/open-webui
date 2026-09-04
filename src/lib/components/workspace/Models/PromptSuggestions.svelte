<script lang="ts">
	import { getContext } from 'svelte';
	import { saveAs } from 'file-saver';
	import { toast } from 'svelte-sonner';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const i18n = getContext('i18n');

	export let promptSuggestions = [];
	export let onChange = (suggestions) => {};
	export let inherited = false;

	let _promptSuggestions = [];
	let importInput: HTMLInputElement;
	const toolClass =
		'flex size-7 shrink-0 items-center justify-center rounded-lg text-gray-500 transition hover:bg-black/5 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-white/5 dark:hover:text-gray-200 disabled:opacity-40';
	const updateSuggestions = (suggestions) => {
		promptSuggestions = suggestions;
		onChange(suggestions);
	};

	const setPromptSuggestions = () => {
		_promptSuggestions = promptSuggestions.map((s) => ({
			...s,
			title: typeof s.title === 'string' ? [s.title, ''] : [...(s.title ?? ['', ''])]
		}));
	};

	const autosize = (node: HTMLTextAreaElement) => {
		const resize = () => {
			node.style.height = 'auto';
			node.style.height = `${node.scrollHeight}px`;
		};

		resize();
		node.addEventListener('input', resize);

		return {
			update: resize,
			destroy() {
				node.removeEventListener('input', resize);
			}
		};
	};

	$: if (promptSuggestions) {
		setPromptSuggestions();
	}
</script>

<div class="space-y-2">
	<div class="mb-1 flex min-h-7 w-full flex-wrap items-center justify-between gap-x-2 gap-y-1">
		<div class="min-w-fit flex-1 self-center text-xs text-gray-500 dark:text-gray-400">
			<slot name="label">{$i18n.t('Default Prompt Suggestions')}</slot>
		</div>

		<div class="ms-auto flex max-w-full shrink-0 items-center justify-end gap-1">
			<slot name="actions" />
			<input
				bind:this={importInput}
				type="file"
				accept=".json"
				hidden
				on:change={(e) => {
					const files = e.target.files;
					if (!files || files.length === 0) {
						return;
					}

					let reader = new FileReader();
					reader.onload = async (event) => {
						try {
							let suggestions = JSON.parse(event.target.result);
							if (
								!Array.isArray(suggestions) ||
								suggestions.some(
									(s) =>
										!s ||
										typeof s.content !== 'string' ||
										(s.title != null &&
											typeof s.title !== 'string' &&
											(!Array.isArray(s.title) || s.title.some((part) => typeof part !== 'string')))
								)
							)
								throw new Error('Invalid prompt suggestions');

							suggestions = suggestions.map((s) => {
								if (typeof s.title === 'string') {
									s.title = [s.title, ''];
								} else if (!Array.isArray(s.title)) {
									s.title = ['', ''];
								}

								return s;
							});

							updateSuggestions([...promptSuggestions, ...suggestions]);
						} catch (error) {
							toast.error($i18n.t('Invalid JSON file'));
							return;
						}
					};

					reader.readAsText(files[0]);

					e.target.value = ''; // Reset the input value
				}}
			/>

			<button
				class="shrink-0 px-1 py-0.5 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				type="button"
				aria-label={$i18n.t('Import')}
				on:click={() => importInput.click()}
			>
				{$i18n.t('Import')}
			</button>

			{#if promptSuggestions.length}
				<button
					class="shrink-0 px-1 py-0.5 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
					type="button"
					aria-label={$i18n.t('Export')}
					disabled={!promptSuggestions.length}
					on:click={async () => {
						let blob = new Blob([JSON.stringify(promptSuggestions)], {
							type: 'application/json'
						});
						saveAs(blob, `prompt-suggestions-export-${Date.now()}.json`);
					}}
				>
					{$i18n.t('Export')}
				</button>
			{/if}

			<Tooltip content={$i18n.t('Add prompt suggestion')}>
				<button
					class={toolClass}
					type="button"
					aria-label={$i18n.t('Add prompt suggestion')}
					on:click={() => {
						if (promptSuggestions.length === 0 || promptSuggestions.at(-1).content !== '') {
							updateSuggestions([...promptSuggestions, { content: '', title: ['', ''] }]);
						}
					}}
				>
					<Plus className="size-3.5" strokeWidth="2.25" />
				</button>
			</Tooltip>
		</div>
	</div>

	{#if _promptSuggestions.length > 0}
		<div class="flex flex-col gap-1.5">
			{#each _promptSuggestions as prompt, promptIdx}
				<div
					class="flex gap-1 rounded-lg border border-gray-100/40 bg-transparent px-2 py-1 transition focus-within:border-gray-300 dark:border-gray-850/50 dark:focus-within:border-gray-600 {inherited
						? 'opacity-60 focus-within:opacity-100'
						: ''}"
				>
					<div class="flex min-w-0 flex-1 flex-col gap-0.5">
						<div class="grid min-w-0 gap-1 md:grid-cols-2 md:gap-1.5">
							<Tooltip content={$i18n.t('e.g. Tell me a fun fact')} placement="top-start">
								<input
									class="w-full bg-transparent text-[0.8125rem] leading-5 text-gray-700 outline-hidden placeholder:text-gray-300 dark:text-gray-200 dark:placeholder:text-gray-700"
									placeholder={$i18n.t('Title')}
									aria-label={$i18n.t('Title')}
									value={prompt.title[0]}
									on:input={(e) => {
										prompt.title[0] = e.currentTarget.value;
										updateSuggestions(_promptSuggestions);
									}}
								/>
							</Tooltip>

							<Tooltip content={$i18n.t('e.g. about the Roman Empire')} placement="top-start">
								<input
									class="w-full bg-transparent text-[0.8125rem] leading-5 text-gray-500 outline-hidden placeholder:text-gray-300 dark:text-gray-500 dark:placeholder:text-gray-700"
									placeholder={$i18n.t('Subtitle')}
									aria-label={$i18n.t('Subtitle')}
									value={prompt.title[1]}
									on:input={(e) => {
										prompt.title[1] = e.currentTarget.value;
										updateSuggestions(_promptSuggestions);
									}}
								/>
							</Tooltip>
						</div>

						<Tooltip
							className="flex min-w-0"
							content={$i18n.t('e.g. Tell me a fun fact about the Roman Empire')}
							placement="top-start"
						>
							<textarea
								class="min-h-5 w-full resize-none overflow-hidden bg-transparent text-[0.8125rem] leading-5 text-gray-700 outline-hidden placeholder:text-gray-300 dark:text-gray-200 dark:placeholder:text-gray-700"
								placeholder={$i18n.t('Content')}
								aria-label={$i18n.t('Content')}
								rows="1"
								use:autosize={prompt.content}
								value={prompt.content}
								on:input={(e) => {
									prompt.content = e.currentTarget.value;
									updateSuggestions(_promptSuggestions);
								}}
							></textarea>
						</Tooltip>
					</div>

					<button
						class="flex size-6 shrink-0 items-center justify-center text-gray-400 opacity-70 transition hover:text-gray-700 hover:opacity-100 dark:text-gray-600 dark:hover:text-gray-300"
						type="button"
						aria-label={$i18n.t('Remove prompt suggestion')}
						on:click={() => {
							updateSuggestions(promptSuggestions.filter((_, index) => index !== promptIdx));
						}}
					>
						<XMark className="size-3.5" />
					</button>
				</div>
			{/each}
		</div>
	{:else}
		<div class="mb-1.5 w-full text-center text-xs text-gray-500 dark:text-gray-600">
			{$i18n.t('No suggestion prompts')}
		</div>
	{/if}
</div>
