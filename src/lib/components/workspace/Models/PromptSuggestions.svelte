<script lang="ts">
	import { getContext } from 'svelte';
	import { saveAs } from 'file-saver';
	import { toast } from 'svelte-sonner';
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
	<div class="flex w-full justify-between mb-2">
		<div class=" self-center text-xs">
			{$i18n.t('Default Prompt Suggestions')}
		</div>

		<button
			class="p-1 px-3 text-xs flex rounded-sm transition"
			type="button"
			on:click={() => {
				if (promptSuggestions.length === 0 || promptSuggestions.at(-1).content !== '') {
					promptSuggestions = [...promptSuggestions, { content: '', title: ['', ''] }];
				}
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
				/>
			</svg>
		</button>
	</div>

	{#if _promptSuggestions.length > 0}
		<div class="grid lg:grid-cols-2 flex-col gap-2">
			{#each _promptSuggestions as prompt, promptIdx}
				<div
					class=" flex border rounded-3xl border-gray-100 dark:border-gray-800 dark:bg-gray-850 py-1.5"
				>
					<div class="flex flex-col flex-1 pl-1">
						<div class="py-1 gap-1">
							<input
								class="px-3 text-sm font-medium w-full bg-transparent outline-hidden"
								placeholder={$i18n.t('Title (e.g. Tell me a fun fact)')}
								bind:value={prompt.title[0]}
							/>

							<input
								class="px-3 text-xs w-full bg-transparent outline-hidden text-gray-600 dark:text-gray-400"
								placeholder={$i18n.t('Subtitle (e.g. about the Roman Empire)')}
								bind:value={prompt.title[1]}
							/>
						</div>

						<hr class="border-gray-50 dark:border-gray-850 my-0.5" />

						<textarea
							class="px-3 py-1.5 text-xs w-full bg-transparent outline-hidden resize-none"
							placeholder={$i18n.t('Prompt (e.g. Tell me a fun fact about the Roman Empire)')}
							rows="4"
							bind:value={prompt.content}
						/>
					</div>

					<div class="">
						<button
							class="p-3"
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
				</div>
			{/each}
		</div>
	{:else}
		<div class="text-xs text-center w-full py-2">{$i18n.t('No suggestion prompts')}</div>
	{/if}

	<div class="flex items-center justify-end space-x-2 mt-2">
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
			class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
			type="button"
			on:click={() => {
				const input = document.getElementById('prompt-suggestions-import-input');
				if (input) {
					input.click();
				}
			}}
		>
			<div class=" self-center mr-2 font-medium line-clamp-1">
				{$i18n.t('Import Prompt Suggestions')}
			</div>

			<div class=" self-center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					class="w-3.5 h-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
		</button>

		{#if promptSuggestions.length}
			<button
				class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
				type="button"
				on:click={async () => {
					let blob = new Blob([JSON.stringify(promptSuggestions)], {
						type: 'application/json'
					});
					saveAs(blob, `prompt-suggestions-export-${Date.now()}.json`);
				}}
			>
				<div class=" self-center mr-2 font-medium line-clamp-1">
					{$i18n.t('Export Prompt Suggestions')} ({promptSuggestions.length})
				</div>

				<div class=" self-center">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-3.5 h-3.5"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			</button>
		{/if}
	</div>
</div>
