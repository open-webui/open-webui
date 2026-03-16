<script lang="ts">
	import { getContext } from 'svelte';
	import { saveAs } from 'file-saver';
	import { toast } from 'svelte-sonner';
	import Plus from '$lib/components/icons/Plus.svelte';
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

	$: if (promptSuggestions) {
		setPromptSuggestions();
	}
</script>

<div class=" space-y-3">
	<div class="flex w-full justify-between mb-1.5">
		<div class=" self-center text-xs flex-1 shrink-0 w-full">
			{$i18n.t('Default Prompt Suggestions')}
		</div>

		<div class="flex justify-end gap-2">
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
				class="flex text-xs items-center space-x-1 py-1 rounded-xl bg-transparent dark:text-gray-200 transition"
				type="button"
				on:click={() => {
					const input = document.getElementById('prompt-suggestions-import-input');
					if (input) {
						input.click();
					}
				}}
			>
				<div class=" self-center font-medium line-clamp-1">
					{$i18n.t('Import')}
				</div>
			</button>

			{#if promptSuggestions.length}
				<button
					class="flex text-xs items-center space-x-1 py-1 rounded-xl bg-transparent dark:text-gray-200 transition"
					type="button"
					on:click={async () => {
						let blob = new Blob([JSON.stringify(promptSuggestions)], {
							type: 'application/json'
						});
						saveAs(blob, `prompt-suggestions-export-${Date.now()}.json`);
					}}
				>
					<div class=" self-center font-medium line-clamp-1">
						{$i18n.t('Export')}
					</div>
				</button>
			{/if}

			<button
				class=" px-1.5 rounded-xl transition font-medium text-sm flex items-center"
				type="button"
				on:click={() => {
					if (promptSuggestions.length === 0 || promptSuggestions.at(-1).content !== '') {
						promptSuggestions = [...promptSuggestions, { content: '', title: ['', ''] }];
					}
				}}
			>
				<Plus className="size-3" strokeWidth="2.5" />
			</button>
		</div>
	</div>

	{#if _promptSuggestions.length > 0}
		<div class="flex flex-col gap-2">
			{#each _promptSuggestions as prompt, promptIdx}
				<div
					class=" flex border rounded-2xl border-gray-100/30 dark:border-gray-850/30 bg-transparent p-2"
				>
					<div class="flex flex-col md:flex-row w-full gap-1 md:gap-2 px-2">
						<div class="gap-0.5 min-w-60">
							<Tooltip content={$i18n.t('e.g. Tell me a fun fact')} placement="top-start">
								<input
									class="text-sm w-full bg-transparent outline-hidden"
									placeholder={$i18n.t('Title')}
									bind:value={prompt.title[0]}
								/>
							</Tooltip>

							<Tooltip content={$i18n.t('e.g. about the Roman Empire')} placement="top-start">
								<input
									class="text-sm w-full bg-transparent outline-hidden text-gray-600 dark:text-gray-400"
									placeholder={$i18n.t('Subtitle')}
									bind:value={prompt.title[1]}
								/>
							</Tooltip>
						</div>

						<Tooltip
							className="w-full self-center items-center flex"
							content={$i18n.t('e.g. Tell me a fun fact about the Roman Empire')}
							placement="top-start"
						>
							<textarea
								class="text-sm w-full bg-transparent outline-hidden resize-none"
								placeholder={$i18n.t('Prompt')}
								rows="2"
								bind:value={prompt.content}
							/>
						</Tooltip>
					</div>

					<button
						class="p-1 self-start"
						type="button"
						on:click={() => {
							promptSuggestions.splice(promptIdx, 1);
							promptSuggestions = promptSuggestions;
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
							/>
						</svg>
					</button>
				</div>
			{/each}
		</div>
	{:else}
		<div class="text-xs text-center w-full text-gray-500 mb-1.5">
			{$i18n.t('No suggestion prompts')}
		</div>
	{/if}
</div>
