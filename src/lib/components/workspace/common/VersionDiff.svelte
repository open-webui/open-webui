<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import VersionDiffContent from './VersionDiffContent.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let currentLabel = 'Current';
	export let showFileHeaders = true;
	let mode: 'split' | 'unified' = 'split';
	let showMode = false;
	export let loadFileDiff: (
		path: string
	) => Promise<{ binary?: boolean; diff?: string; line_endings_only?: boolean }>;
	export let diff: {
		fromId: string;
		toId: string;
		metadata: Record<string, { before: unknown; after: unknown }>;
		files: { path: string; status: 'added' | 'deleted' | 'modified'; binary: boolean }[];
	};
	export let onClose: () => void;
	const i18n = getContext<any>('i18n');
	let selectedPath: string | null = null;
	let results: Record<
		string,
		{
			loading?: boolean;
			error?: string;
			binary?: boolean;
			diff?: string;
			line_endings_only?: boolean;
		}
	> = {};

	const isObject = (value: unknown): value is Record<string, unknown> =>
		!!value && typeof value === 'object' && !Array.isArray(value);
	const displayValue = (value: unknown): string => {
		if (value == null) return '';
		if (Array.isArray(value)) return value.map(displayValue).join(', ');
		if (isObject(value))
			return Object.entries(value)
				.map(([key, item]) => `${key}: ${displayValue(item)}`)
				.join(', ');
		return String(value);
	};
	function changes(
		path: string[],
		before: unknown,
		after: unknown
	): { path: string[]; before: string; after: string }[] {
		if (
			(isObject(before) || isObject(after)) &&
			(before == null || isObject(before)) &&
			(after == null || isObject(after))
		) {
			const a = isObject(before) ? before : {};
			const b = isObject(after) ? after : {};
			return [...new Set([...Object.keys(a), ...Object.keys(b)])].flatMap((key) =>
				changes([...path, key], a[key], b[key])
			);
		}
		const a = displayValue(before);
		const b = displayValue(after);
		return a === b ? [] : [{ path, before: a, after: b }];
	}
	$: metadata = Object.entries(diff.metadata).flatMap(([key, value]) =>
		changes(key === 'meta' ? [] : [key], value.before, value.after)
	);
	const labels: Record<string, string> = {
		name: 'Name',
		description: 'Description',
		tags: 'Tags',
		i18n: 'Translations'
	};
	const statuses = { added: 'Added', deleted: 'Deleted', modified: 'Modified' };

	async function loadFile(path: string) {
		if (results[path]?.loading || results[path]?.diff !== undefined || results[path]?.binary)
			return;
		results = { ...results, [path]: { loading: true } };
		try {
			results = { ...results, [path]: await loadFileDiff(path) };
		} catch (error) {
			results = {
				...results,
				[path]: { error: error instanceof Error ? error.message : String(error) }
			};
		}
	}
	function selectFile(path: string) {
		selectedPath = selectedPath === path ? null : path;
		if (selectedPath) loadFile(path);
	}
	onMount(() => {
		try {
			mode = localStorage.getItem('versionDiff:mode') === 'unified' ? 'unified' : 'split';
		} catch {
			/* Use the default when storage is unavailable. */
		}
		if (diff.files.length) selectFile(diff.files[0].path);
	});
</script>

<section
	class="flex h-full min-h-0 flex-col bg-white text-xs dark:bg-gray-900"
	aria-label={$i18n.t('Compare to current')}
>
	<div class="flex shrink-0 items-center gap-2 bg-gray-50/60 px-3 py-1.5 dark:bg-black">
		<span class="min-w-0 flex-1 font-medium">{$i18n.t('Compare to current')}</span>
		<Dropdown bind:show={showMode} align="end">
			<button
				type="button"
				aria-label={$i18n.t('Diff layout')}
				class="flex items-center gap-1 px-1 text-gray-500"
				><Icon
					name={mode === 'split' ? 'split-horizontal' : 'list'}
					size={13}
					class="shrink-0"
				/>{$i18n.t(mode === 'split' ? 'Split' : 'Unified')}<ChevronDown
					className="size-3"
				/></button
			>
			<div slot="content">
				<DropdownMenu className="w-32">
					{#each ['split', 'unified'] as option}<button
							type="button"
							aria-pressed={mode === option}
							on:click={() => {
								mode = option as 'split' | 'unified';
								showMode = false;
								try {
									localStorage.setItem('versionDiff:mode', mode);
								} catch {
									/* Keep the current selection in memory. */
								}
							}}
							><Icon
								name={option === 'split' ? 'split-horizontal' : 'list'}
								size={13}
								class="shrink-0 text-gray-500"
							/><span class="flex-1 text-left"
								>{$i18n.t(option === 'split' ? 'Split' : 'Unified')}</span
							>{#if mode === option}<Check className="size-3" />{/if}</button
						>{/each}
				</DropdownMenu>
			</div>
		</Dropdown>
		<button
			type="button"
			class="p-1 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
			aria-label={$i18n.t('Close')}
			on:click={onClose}><XMark className="size-3.5" /></button
		>
	</div>
	<div class="grid shrink-0 grid-cols-2 border-b border-gray-100 dark:border-white/5">
		<div class="min-w-0 px-3 py-2 text-gray-500">
			{$i18n.t('Selected version')} <span class="font-mono">{diff.fromId.slice(0, 7)}</span>
		</div>
		<div class="min-w-0 px-3 py-2 text-gray-500">
			{$i18n.t(currentLabel)} <span class="font-mono">{diff.toId.slice(0, 7)}</span>
		</div>
	</div>
	<div class="min-h-0 flex-1 overflow-auto">
		{#each metadata as change}
			<div class="border-b border-gray-100 dark:border-white/5">
				<div class="px-3 py-1.5 font-medium text-gray-600 dark:text-gray-300">
					{change.path.map((key) => $i18n.t(labels[key] || key)).join(' / ')}
				</div>
				<div class="grid grid-cols-2">
					<div
						class="min-w-0 whitespace-pre-wrap break-words bg-red-50 px-3 py-2 text-red-800 dark:bg-red-950/30 dark:text-red-200"
					>
						{change.before || '—'}
					</div>
					<div
						class="min-w-0 whitespace-pre-wrap break-words bg-green-50 px-3 py-2 text-green-800 dark:bg-green-950/30 dark:text-green-200"
					>
						{change.after || '—'}
					</div>
				</div>
			</div>
		{/each}
		{#each diff.files as file, index}
			<div class="border-b border-gray-100 dark:border-white/5">
				{#if showFileHeaders}<button
						type="button"
						class="flex w-full items-center gap-2 px-3 py-2 text-left"
						aria-expanded={selectedPath === file.path}
						aria-controls={`version-diff-file-${index}`}
						on:click={() => selectFile(file.path)}
					>
						<span class:rotate-[-90deg]={selectedPath !== file.path}
							><ChevronDown className="size-3 shrink-0 text-gray-400" /></span
						>
						<span class="min-w-0 flex-1 truncate font-mono" title={file.path}>{file.path}</span>
						<span
							class="shrink-0 rounded px-1.5 py-0.5 text-[0.625rem] {file.status === 'added'
								? 'bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-400'
								: file.status === 'deleted'
									? 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400'
									: 'bg-gray-100 text-gray-500 dark:bg-gray-850 dark:text-gray-400'}"
							>{$i18n.t(statuses[file.status])}</span
						>
					</button>
				{/if}
				{#if selectedPath === file.path}
					<div id={`version-diff-file-${index}`} class="min-w-0">
						{#if results[file.path]?.loading}
							<div class="flex items-center gap-2 px-3 py-3 text-gray-500" role="status">
								<Spinner className="size-3" />{$i18n.t('Loading...')}
							</div>
						{:else if results[file.path]?.error}
							<div class="px-3 py-3 text-gray-500" role="alert">
								{results[file.path].error}<button
									type="button"
									class="ml-2 underline"
									on:click={() => loadFile(file.path)}>{$i18n.t('Retry')}</button
								>
							</div>
						{:else if results[file.path]?.binary}
							<p class="px-3 py-3 text-gray-500">
								{$i18n.t('Binary file — text comparison is unavailable.')}
							</p>
						{:else if results[file.path]?.diff}
							<VersionDiffContent code={results[file.path].diff ?? ''} {mode} />
						{:else}
							<p class="px-3 py-3 text-gray-500">
								{$i18n.t(
									results[file.path]?.line_endings_only
										? 'Only line endings changed'
										: 'No text differences'
								)}
							</p>
						{/if}
					</div>
				{/if}
			</div>
		{/each}
		{#if !metadata.length && !diff.files.length}
			<p class="px-3 py-4 text-gray-500">{$i18n.t('No differences')}</p>
		{/if}
	</div>
</section>
