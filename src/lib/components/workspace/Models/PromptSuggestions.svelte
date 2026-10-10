<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { saveAs } from 'file-saver';
	import { toast } from 'svelte-sonner';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	const i18n = getContext<any>('i18n');

	export let promptSuggestions = [];
	export let onChange = (suggestions) => {};
	export let inherited = false;
	export let disabled = false;
	let promptInputs: HTMLTextAreaElement[] = [];

	let _promptSuggestions = [];
	let importInput: HTMLInputElement;
	const updateSuggestions = (suggestions) => {
		if (disabled) return;
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

<div class="space-y-0">
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

	{#each _promptSuggestions as prompt, promptIdx}
		<div
			class="rounded-xl px-2 py-1.5 focus-within:bg-gray-50 dark:focus-within:bg-gray-850 {inherited
				? 'opacity-60 focus-within:opacity-100'
				: ''}"
		>
			<div class="flex items-start gap-2">
				<textarea
					bind:this={promptInputs[promptIdx]}
					class="min-h-5 min-w-0 flex-1 resize-none overflow-hidden bg-transparent text-[0.8125rem] font-normal leading-5 text-gray-900 outline-hidden placeholder:text-gray-500 dark:text-gray-100 dark:placeholder:text-gray-400"
					placeholder={$i18n.t('Write a prompt…')}
					aria-label={$i18n.t('Prompt')}
					rows="1"
					{disabled}
					use:autosize={prompt.content}
					value={prompt.content}
					on:input={(e) => {
						prompt.content = e.currentTarget.value;
						updateSuggestions(_promptSuggestions);
					}}
				></textarea>
				<Tooltip content={$i18n.t('Remove prompt suggestion')}>
					<button
						type="button"
						{disabled}
						aria-label={$i18n.t('Remove prompt suggestion')}
						class="flex size-5 shrink-0 items-center justify-center text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
						on:click={() =>
							updateSuggestions(promptSuggestions.filter((_, index) => index !== promptIdx))}
					>
						<XMark className="size-3" />
					</button>
				</Tooltip>
			</div>
			<details class="group/prompt mt-0.5">
				<summary
					class="flex w-fit max-w-full cursor-pointer list-none items-center gap-1 text-xs text-gray-500 dark:text-gray-400 [&::-webkit-details-marker]:hidden"
				>
					<ChevronRight
						className="size-3 shrink-0 transition-transform group-open/prompt:rotate-90"
					/>
					<span class="shrink-0">{$i18n.t('Display text')}</span>
					{#if prompt.title.some((part) => part.trim())}
						<span class="truncate text-gray-600 dark:text-gray-300">
							{prompt.title.filter((part) => part.trim()).join(' · ')}
						</span>
					{/if}
				</summary>
				<div class="grid gap-2 py-1.5 sm:grid-cols-2">
					{#each ['Title', 'Subtitle'] as label, index}
						<label class="flex min-w-0 flex-col gap-0.5 text-xs text-gray-500 dark:text-gray-400">
							<span>{$i18n.t(label)}</span>
							<input
								{disabled}
								class="min-w-0 w-full bg-transparent text-[0.8125rem] font-normal leading-5 text-gray-900 outline-hidden placeholder:text-gray-400 dark:text-gray-100 dark:placeholder:text-gray-500"
								aria-label={$i18n.t(label)}
								placeholder={index === 0
									? $i18n.t('e.g. Tell me a fun fact')
									: $i18n.t('e.g. about the Roman Empire')}
								value={prompt.title[index]}
								on:input={(e) => {
									prompt.title[index] = e.currentTarget.value;
									updateSuggestions(_promptSuggestions);
								}}
							/>
						</label>
					{/each}
				</div>
			</details>
		</div>
	{:else}
		<p class="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('No suggestion prompts')}
		</p>
	{/each}
	<div
		class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 pt-1 text-xs text-gray-500 dark:text-gray-400"
	>
		<button
			type="button"
			{disabled}
			aria-label={$i18n.t('Add prompt suggestion')}
			class="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 disabled:opacity-40 dark:text-gray-400 dark:hover:text-gray-300"
			on:click={async () => {
				if (promptSuggestions.length === 0 || promptSuggestions.at(-1).content.trim() !== '') {
					updateSuggestions([...promptSuggestions, { content: '', title: ['', ''] }]);
				}
				await tick();
				promptInputs[promptSuggestions.length - 1]?.focus();
			}}
		>
			<Plus className="size-3" strokeWidth="1.5" />
			{$i18n.t('Add prompt')}
		</button>
		<div class="ml-auto flex max-w-full flex-wrap items-center justify-end gap-3 px-2 py-1">
			<slot name="label" />
			<slot name="actions" />
			<button
				type="button"
				{disabled}
				class="hover:text-gray-900 disabled:opacity-40 dark:hover:text-gray-100"
				on:click={() => importInput.click()}>{$i18n.t('Import')}</button
			>
			<button
				type="button"
				disabled={disabled || !promptSuggestions.length}
				class="hover:text-gray-900 disabled:opacity-40 dark:hover:text-gray-100"
				on:click={() => {
					saveAs(
						new Blob([JSON.stringify(promptSuggestions)], { type: 'application/json' }),
						`prompt-suggestions-export-${Date.now()}.json`
					);
				}}>{$i18n.t('Export')}</button
			>
		</div>
	</div>
</div>
