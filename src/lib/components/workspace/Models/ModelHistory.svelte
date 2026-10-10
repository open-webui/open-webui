<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import VersionMenuItem from '../common/VersionMenuItem.svelte';
	import {
		getModelHistory,
		deleteModelHistoryVersion,
		getModelHistoryEntry,
		setProductionModelVersion,
		type ModelHistoryEntry,
		type ModelSnapshot
	} from '$lib/apis/models';

	export let model: any;
	export let dirty = false;
	export let onProduction: (model: any) => Promise<void>;
	const i18n = getContext<any>('i18n');
	let show = false;
	let page = 1;
	let history: ModelHistoryEntry[] = [];
	let production: ModelHistoryEntry | null = null;
	export let selected: (ModelHistoryEntry & { snapshot: ModelSnapshot }) | null = null;
	let loading = false;
	export let selecting = false;
	export let promoting = false;
	let error = '';
	let confirmPromotion = false;
	let showDeleteVersion = false;
	let deleteVersionId = '';
	let deleting = false;
	let selection = 0;
	const message = (error: any) =>
		typeof error?.detail === 'string'
			? error.detail
			: error?.message || $i18n.t('Failed to load model version');

	async function loadHistory() {
		loading = true;
		error = '';
		try {
			history = await getModelHistory(localStorage.token, model.id, page);
			production =
				history.find((entry) => entry.id === model.version_id) ||
				(await getModelHistoryEntry(localStorage.token, model.id, model.version_id));
		} catch (e) {
			error = message(e);
		} finally {
			loading = false;
		}
	}

	async function selectVersion(id: string) {
		show = false;
		const request = ++selection;
		if (id === model.version_id) {
			selected = null;
			selecting = false;
			return;
		}
		selecting = true;
		try {
			const entry = await getModelHistoryEntry(localStorage.token, model.id, id);
			if (request === selection) {
				selected = entry;
			}
		} catch (e) {
			if (request === selection) toast.error(message(e));
		} finally {
			if (request === selection) selecting = false;
		}
	}

	async function deleteVersion() {
		if (deleting || promoting || !deleteVersionId || deleteVersionId === model.version_id) return;
		deleting = true;
		try {
			await deleteModelHistoryVersion(localStorage.token, model.id, deleteVersionId);
			// Invalidate an in-flight preview response for the deleted version.
			selection++;
			selecting = false;
			if (selected?.id === deleteVersionId) selected = null;
			page = 1;
			await loadHistory();
			toast.success($i18n.t('Version deleted'));
		} catch (e) {
			toast.error(message(e));
		} finally {
			deleting = false;
		}
	}

	export function requestPromotion() {
		if (dirty) confirmPromotion = true;
		else promote();
	}

	async function promote() {
		if (!selected || promoting || deleting) return;
		promoting = true;
		try {
			const result = await setProductionModelVersion(localStorage.token, model.id, selected.id);
			await onProduction(result);
			selected = null;
			production = null;
			history = [];
			toast.success($i18n.t('Production version updated'));
		} catch (e) {
			toast.error(message(e));
		} finally {
			promoting = false;
		}
	}
</script>

<ConfirmDialog
	bind:show={confirmPromotion}
	title={$i18n.t('Discard unsaved changes?')}
	message={$i18n.t('Setting this version as Production will discard your unsaved changes.')}
	confirmLabel={$i18n.t('Set as Production')}
	on:confirm={promote}
/>

<ConfirmDialog
	bind:show={showDeleteVersion}
	title={$i18n.t('Delete Version')}
	message={$i18n.t(
		"Are you sure you want to delete this version? Child versions will be relinked to this version's parent."
	)}
	confirmLabel={$i18n.t('Delete')}
	onConfirm={deleteVersion}
/>

<div class="flex shrink-0 items-center">
	<Dropdown bind:show align="start">
		<button
			type="button"
			aria-label={$i18n.t('Select version')}
			class="flex min-w-0 items-center gap-1.5 text-xs text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
			disabled={promoting || deleting}
			on:click={() => {
				page = 1;
				loadHistory();
			}}
		>
			<span>{selected ? selected.id.slice(0, 7) : $i18n.t('Production')}</span>
			<ChevronDown className="size-3" />
		</button>
		<div slot="content">
			<DropdownMenu className="w-56">
				<VersionMenuItem
					entry={production}
					status={$i18n.t('Production')}
					selected={!selected}
					onSelect={() => selectVersion(model.version_id)}
				/>
				{#if loading}
					<div class="flex justify-center py-2"><Spinner className="size-4" /></div>
				{:else if error}
					<button type="button" on:click={loadHistory}>{$i18n.t('Retry')}</button>
				{:else}
					{#if history.some((entry) => entry.id !== model.version_id)}<hr
							class="my-1 border-gray-100 dark:border-gray-850"
						/>{/if}
					{#each history.filter((entry) => entry.id !== model.version_id) as entry (entry.id)}
						<VersionMenuItem
							{entry}
							selected={entry.id === selected?.id}
							onSelect={() => selectVersion(entry.id)}
							onDelete={() => {
								deleteVersionId = entry.id;
								show = false;
								showDeleteVersion = true;
							}}
						/>
					{/each}
					{#if page > 1 || history.length === 20}
						<div class="flex justify-between gap-2 pt-1">
							<button
								type="button"
								disabled={page === 1}
								on:click={() => {
									page--;
									loadHistory();
								}}>{$i18n.t('Previous')}</button
							>
							<button
								type="button"
								disabled={history.length < 20}
								on:click={() => {
									page++;
									loadHistory();
								}}>{$i18n.t('Next')}</button
							>
						</div>
					{/if}
				{/if}
			</DropdownMenu>
		</div>
	</Dropdown>
</div>
