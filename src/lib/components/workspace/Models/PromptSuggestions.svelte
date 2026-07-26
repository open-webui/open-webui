<script lang="ts">
	import { getContext } from 'svelte';
	import { saveAs } from 'file-saver';
	import { toast } from 'svelte-sonner';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const i18n = getContext('i18n');

	export let promptSuggestions = [];

	let _promptSuggestions = [];

	const setPromptSuggestions = () => {
		_promptSuggestions = promptSuggestions.map((s) => {
			if (typeof s.title === 'string') {
				s.title = [s.title, ''];
			} else if (!Array.isArray(s.title)) {
				s.title = ['', ''];
			}
			return s;
		});
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
	<div class="mb-1 flex h-6 w-full items-center justify-between">
		<div class="min-w-0 flex-1 self-center text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Default Prompt Suggestions')}
		</div>

		<div class="flex shrink-0 items-center justify-end gap-1.5">
			<input
				id="prompt-suggestions-import-input"
				type="file"
				accept=".json"
				hidden
				on:change={(e) => {
					const files = e.target.files;
					if (!files || files.length === 0) {
						return;
					}

					console.log(files);

					let reader = new FileReader();
					reader.onload = async (event) => {
						try {
							let suggestions = JSON.parse(event.target.result);

							suggestions = suggestions.map((s) => {
								if (typeof s.title === 'string') {
									s.title = [s.title, ''];
								} else if (!Array.isArray(s.title)) {
									s.title = ['', ''];
								}

								return s;
							});

							promptSuggestions = [...promptSuggestions, ...suggestions];
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
				class="flex items-center rounded-xl bg-transparent px-1 py-0.5 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				type="button"
				on:click={() => {
					const input = document.getElementById('prompt-suggestions-import-input');
					if (input) {
						input.click();
					}
				}}
			>
				<div class="line-clamp-1 self-center font-normal">
					{$i18n.t('Import')}
				</div>
			</button>

			{#if promptSuggestions.length}
				<button
					class="flex items-center rounded-xl bg-transparent px-1 py-0.5 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
					type="button"
					on:click={async () => {
						let blob = new Blob([JSON.stringify(promptSuggestions)], {
							type: 'application/json'
						});
						saveAs(blob, `prompt-suggestions-export-${Date.now()}.json`);
					}}
				>
					<div class="line-clamp-1 self-center font-normal">
						{$i18n.t('Export')}
					</div>
				</button>
			{/if}

			<button
				class="flex size-6 items-center justify-center text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				type="button"
				aria-label={$i18n.t('Add prompt suggestion')}
				on:click={() => {
					if (promptSuggestions.length === 0 || promptSuggestions.at(-1).content !== '') {
						promptSuggestions = [...promptSuggestions, { content: '', title: ['', ''] }];
					}
				}}
			>
				<Plus className="size-3.5" strokeWidth="2.25" />
			</button>
		</div>
	</div>

	{#if _promptSuggestions.length > 0}
		<div class="flex flex-col gap-1.5">
			{#each _promptSuggestions as prompt, promptIdx}
				<div
					class="flex gap-1 rounded-lg border border-gray-100/40 bg-transparent px-2 py-1 dark:border-gray-850/50"
				>
					<div class="flex min-w-0 flex-1 flex-col gap-0.5">
						<div class="grid min-w-0 gap-1 md:grid-cols-2 md:gap-1.5">
							<Tooltip content={$i18n.t('e.g. Tell me a fun fact')} placement="top-start">
								<input
									class="w-full bg-transparent text-[13px] leading-5 text-gray-700 outline-hidden placeholder:text-gray-300 dark:text-gray-200 dark:placeholder:text-gray-700"
									placeholder={$i18n.t('Title')}
									aria-label={$i18n.t('Title')}
									bind:value={prompt.title[0]}
								/>
							</Tooltip>

							<Tooltip content={$i18n.t('e.g. about the Roman Empire')} placement="top-start">
								<input
									class="w-full bg-transparent text-[13px] leading-5 text-gray-500 outline-hidden placeholder:text-gray-300 dark:text-gray-500 dark:placeholder:text-gray-700"
									placeholder={$i18n.t('Subtitle')}
									aria-label={$i18n.t('Subtitle')}
									bind:value={prompt.title[1]}
								/>
							</Tooltip>
						</div>

						<Tooltip
							className="flex min-w-0"
							content={$i18n.t('e.g. Tell me a fun fact about the Roman Empire')}
							placement="top-start"
						>
							<textarea
								class="min-h-5 w-full resize-none overflow-hidden bg-transparent text-[13px] leading-5 text-gray-700 outline-hidden placeholder:text-gray-300 dark:text-gray-200 dark:placeholder:text-gray-700"
								placeholder={$i18n.t('Content')}
								aria-label={$i18n.t('Content')}
								rows="1"
								use:autosize={prompt.content}
								bind:value={prompt.content}
							/>
						</Tooltip>
					</div>

					<button
						class="flex size-6 shrink-0 items-center justify-center text-gray-400 opacity-70 transition hover:text-gray-700 hover:opacity-100 dark:text-gray-600 dark:hover:text-gray-300"
						type="button"
						aria-label={$i18n.t('Remove prompt suggestion')}
						on:click={() => {
							promptSuggestions.splice(promptIdx, 1);
							promptSuggestions = promptSuggestions;
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
