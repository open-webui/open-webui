<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { LanguageDescription } from '@codemirror/language';
	import { languages } from '@codemirror/language-data';
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<any>('i18n');

	export let files: { path: string; content: string }[] = [];
	export let selectedPath = '';
	export let mainPath: string;
	export let readOnly = false;
	export let onSave = () => {};

	let creating = false;
	let newName = '';
	let newNameInput: HTMLInputElement;

	$: selectedFile = files.find((file) => file.path === selectedPath);

	const startCreate = async () => {
		creating = true;
		newName = '';
		await tick();
		newNameInput?.focus();
	};

	const submitCreate = () => {
		if (!creating) return;
		const path = newName.trim();
		creating = false;
		if (!path) return;
		if (
			path === mainPath ||
			/[\\\x00:]/.test(path) ||
			path.split('/').some((part) => !part || part === '.' || part === '..') ||
			files.some(
				(file) =>
					file.path === path || file.path.startsWith(`${path}/`) || path.startsWith(`${file.path}/`)
			)
		) {
			toast.error($i18n.t('Invalid or conflicting file path'));
			return;
		}
		files = [...files, { path, content: '' }];
		selectedPath = path;
	};

	const removeFile = (path: string) => {
		files = files.filter((file) => file.path !== path);
		if (selectedPath === path) selectedPath = '';
	};

	const tabClass = (active: boolean) =>
		`flex h-7 shrink-0 items-center gap-1 rounded-lg px-2 font-mono text-xs transition ${
			active
				? 'bg-base-100 text-base-900 dark:bg-base-850 dark:text-base-100'
				: 'text-base-500 hover:text-base-900 dark:hover:text-base-100'
		}`;
</script>

<div class={selectedFile ? 'flex min-h-0 flex-1 flex-col' : 'shrink-0'}>
	<div class="flex shrink-0 items-center gap-1 overflow-x-auto pb-1">
		<button
			type="button"
			class={tabClass(selectedPath === '')}
			on:click={() => (selectedPath = '')}
		>
			{mainPath}
		</button>

		{#each files as file (file.path)}
			<div class={tabClass(selectedPath === file.path)}>
				<button type="button" on:click={() => (selectedPath = file.path)}>{file.path}</button>
				{#if !readOnly}
					<Tooltip content={$i18n.t('Delete File')}>
						<button
							type="button"
							aria-label={$i18n.t('Delete File')}
							class="text-base-400 hover:text-base-900 dark:hover:text-base-100"
							on:click={() => removeFile(file.path)}
						>
							<XMark className="size-3" />
						</button>
					</Tooltip>
				{/if}
			</div>
		{/each}

		{#if !readOnly}
			{#if creating}
				<input
					bind:this={newNameInput}
					bind:value={newName}
					class="h-7 w-40 shrink-0 bg-transparent px-2 font-mono text-xs outline-hidden"
					placeholder={$i18n.t('File name')}
					aria-label={$i18n.t('File name')}
					on:keydown={(event) => {
						if (event.key === 'Enter') {
							event.preventDefault();
							submitCreate();
						}
						if (event.key === 'Escape') {
							event.preventDefault();
							creating = false;
						}
					}}
					on:blur={submitCreate}
				/>
			{:else}
				<Tooltip content={$i18n.t('New File')}>
					<button
						type="button"
						aria-label={$i18n.t('New File')}
						class="flex h-7 shrink-0 items-center px-1.5 text-base-500 hover:text-base-900 dark:hover:text-base-100"
						on:click={startCreate}
					>
						<Plus className="size-3.5" />
					</button>
				</Tooltip>
			{/if}
		{/if}
	</div>

	{#if selectedFile}
		{#key selectedPath}
			<div class="min-h-0 flex-1">
				<CodeEditor
					value={selectedFile.content}
					lang={LanguageDescription.matchFilename(languages, selectedPath)?.alias[0] ?? ''}
					{readOnly}
					ariaLabel={selectedPath}
					className="text-[0.6875rem]"
					onChange={(value) => {
						files = files.map((file) =>
							file.path === selectedPath ? { ...file, content: value } : file
						);
					}}
					{onSave}
				/>
			</div>
		{/key}
	{/if}
</div>
