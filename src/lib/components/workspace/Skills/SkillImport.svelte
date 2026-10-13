<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { toast } from 'svelte-sonner';
	import { importSkillBundles, skillError } from '$lib/apis/skills';
	import { formatFileSize } from '$lib/utils';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	export let show = false;
	export let files: File[] = [];
	export let onImported: () => Promise<void> = async () => {};

	let loading = false;
	let error = '';
	let items: any[] = [];
	let results: any[] = [];
	let loadedFiles: File[] | null = null;
	$: selectedCount = items.filter((item) => item.action !== 'skip').length;
	$: if (show && files !== loadedFiles) {
		loadedFiles = files;
		preview();
	}

	const preview = async () => {
		const previewFiles = files;
		loading = true;
		error = '';
		results = [];
		items = [];
		try {
			const previewItems = await importSkillBundles(localStorage.token, previewFiles);
			if (files !== previewFiles) return;
			items = previewItems.map((item: any) => ({
				...item,
				originalId: item.id,
				action: item.id_taken || item.name_taken ? 'skip' : 'create'
			}));
		} catch (err) {
			if (files === previewFiles) error = skillError(err);
		} finally {
			if (files === previewFiles) loading = false;
		}
	};

	const save = async () => {
		if (loading || !selectedCount) return;
		const importFiles = files;
		loading = true;
		try {
			const importResults: any[] = await importSkillBundles(
				localStorage.token,
				importFiles,
				items.map(({ action, id, name, expected_version_id }) => ({
					action,
					id,
					name,
					expected_version_id
				}))
			);
			// A closed import can finish after a different bundle has opened.
			if (files === importFiles) {
				results = importResults.map((result, index) =>
					results[index]?.status === 'saved' ? results[index] : result
				);
				results.forEach((result, index) => {
					if (result.status === 'saved') items[index].action = 'skip';
				});
				items = [...items];
			}
			if (importResults.some((result) => result.status === 'saved')) await onImported();
		} catch (err) {
			toast.error(skillError(err));
		} finally {
			if (files === importFiles) loading = false;
		}
	};
</script>

<Modal bind:show size="md" className="rounded-2xl bg-white dark:bg-gray-900">
	<div class="flex max-h-[calc(100dvh-3rem)] flex-col text-gray-900 dark:text-gray-100">
		<div class="flex shrink-0 items-center justify-between gap-3 px-4 pt-3 pb-2">
			<h2 class="text-sm font-medium">{$i18n.t('Import skills')}</h2>
			<button
				type="button"
				class="rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => (show = false)}
			>
				<XMark className="size-4" />
			</button>
		</div>
		<p class="shrink-0 px-4 pb-3 text-xs leading-5 text-gray-500 dark:text-gray-400">
			{$i18n.t(
				'New skills and copies are private. Replace saves a new version and preserves existing sharing.'
			)}
		</p>
		<div class="min-h-0 overflow-y-auto overscroll-contain px-4" aria-busy={loading}>
			{#if loading && !items.length}
				<div
					class="flex items-center justify-center gap-2 py-10 text-xs text-gray-500 dark:text-gray-400"
					role="status"
				>
					<Spinner className="size-4" />
					{$i18n.t('Loading...')}
				</div>
			{:else if error}
				<div class="py-6 text-center">
					<p class="text-xs text-red-600 dark:text-red-400" role="alert">{error}</p>
					<button
						type="button"
						class="mt-3 rounded-lg px-2.5 py-1.5 text-xs transition hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={preview}
					>
						{$i18n.t('Retry')}
					</button>
				</div>
			{:else if !items.length}
				<p class="py-10 text-center text-xs text-gray-500 dark:text-gray-400" role="status">
					{$i18n.t('No skills found')}
				</p>
			{:else}
				<div class="divide-y divide-gray-100 dark:divide-gray-850">
					{#each items as item, index}
						<div class="py-3 first:pt-0">
							<div class="flex items-start gap-3">
								<div class="min-w-0 flex-1 space-y-1">
									<input
										aria-label={$i18n.t('Skill name')}
										class="w-full min-w-0 rounded-md bg-transparent px-1.5 py-1 text-sm font-medium outline-hidden transition hover:bg-gray-50 focus:bg-gray-50 focus:ring-1 focus:ring-gray-300 disabled:opacity-60 dark:hover:bg-gray-850 dark:focus:bg-gray-850 dark:focus:ring-gray-600"
										bind:value={item.name}
										disabled={loading || results[index]?.status === 'saved'}
									/>
									<label
										class="flex min-w-0 items-center gap-2 px-1.5 text-xs text-gray-500 dark:text-gray-400"
									>
										<span class="shrink-0">{$i18n.t('ID')}</span>
										<input
											aria-label={$i18n.t('Skill ID')}
											class="min-w-0 flex-1 rounded bg-transparent py-0.5 font-mono outline-hidden focus:ring-1 focus:ring-gray-300 disabled:opacity-60 dark:focus:ring-gray-600"
											bind:value={item.id}
											disabled={loading ||
												item.action === 'replace' ||
												results[index]?.status === 'saved'}
										/>
									</label>
								</div>
								<select
									aria-label={$i18n.t('Import action')}
									class="h-7 w-28 shrink-0 rounded-lg border border-gray-100 bg-gray-50 px-2 text-xs outline-hidden focus:ring-1 focus:ring-gray-300 disabled:opacity-60 dark:border-gray-800 dark:bg-gray-850 dark:focus:ring-gray-600"
									bind:value={item.action}
									on:change={(event) => {
										if (event.currentTarget.value === 'replace') item.id = item.originalId;
									}}
									disabled={loading || results[index]?.status === 'saved'}
								>
									<option value="create">{$i18n.t('Create')}</option>
									<option value="copy">{$i18n.t('Create copy')}</option>
									{#if item.can_replace}<option value="replace">{$i18n.t('Replace')}</option>{/if}
									<option value="skip">{$i18n.t('Skip')}</option>
								</select>
							</div>
							{#if (item.id_taken || item.name_taken) && item.action !== 'replace' && results[index]?.status !== 'saved'}
								<p class="mt-1.5 px-1.5 text-xs leading-5 text-amber-700 dark:text-amber-400">
									{$i18n.t('ID or name already exists. Choose a unique ID and name for a copy.')}
								</p>
							{/if}
							<details class="group mt-1.5 px-1.5 text-xs text-gray-500 dark:text-gray-400">
								<summary
									class="flex w-fit cursor-pointer list-none items-center gap-1 rounded py-0.5 hover:text-gray-900 dark:hover:text-gray-200 [&::-webkit-details-marker]:hidden"
								>
									{$i18n.t('{{count}} files', { count: item.files.length })}
									<ChevronDown className="size-3 transition-transform group-open:rotate-180" />
								</summary>
								<div
									class="mt-1 max-h-32 space-y-1 overflow-y-auto rounded-lg bg-gray-50 p-2 dark:bg-gray-850"
								>
									{#each item.files as file}
										<div class="flex items-start justify-between gap-3">
											<span class="min-w-0 break-all font-mono">{file.path}</span>
											<span class="shrink-0 tabular-nums">{formatFileSize(file.size)}</span>
										</div>
									{/each}
								</div>
							</details>
							{#if results[index]}
								<p
									class="mt-1.5 break-words px-1.5 text-xs leading-5"
									class:text-red-500={results[index].status === 'error'}
									role="status"
								>
									{results[index].status === 'saved'
										? $i18n.t('Saved')
										: results[index].status === 'skipped'
											? $i18n.t('Skipped')
											: $i18n.t('Error')}{results[index].error
										? `: ${skillError(results[index].error)}`
										: ''}
								</p>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
		<div class="flex shrink-0 items-center justify-between gap-3 px-4 py-3">
			<span class="text-xs text-gray-500 dark:text-gray-400" aria-live="polite"
				>{$i18n.t('{{count}} selected', { count: selectedCount })}</span
			>
			<button
				type="button"
				class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
				disabled={loading || !selectedCount}
				on:click={save}
			>
				{$i18n.t('Import selected')}
				{#if loading && items.length}<Spinner className="size-3" />{/if}
			</button>
		</div>
	</div>
</Modal>
