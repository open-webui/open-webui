<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import VersionMenuItem from '../common/VersionMenuItem.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import LanguageModeSelect from '$lib/components/common/LanguageModeSelect.svelte';
	import LocalizedField from '$lib/components/common/LocalizedField.svelte';
	let locale = '';
	let meta: { i18n?: Record<string, Record<string, string>>; [key: string]: any } = {};
	import { user } from '$lib/stores';
	import { slugify } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { updateSkillAccessGrants } from '$lib/apis/skills';
	import { goto, beforeNavigate } from '$app/navigation';
	import SkillFiles from './SkillFiles.svelte';
	import VersionDiff from '../common/VersionDiff.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import {
		getSkillHistory,
		deleteSkillHistoryVersion,
		getSkillVersion,
		setProductionSkillVersion,
		getSkillById,
		createNewSkill,
		exportSkillBundle,
		skillRequest,
		skillError
	} from '$lib/apis/skills';
	import { downloadSkillBlob as saveAs } from '$lib/apis/skills';

	export let onSubmit: Function;
	export let edit = false;
	export let skill: any = null;
	export let clone = false;
	export let disabled = false;

	const i18n = getContext<any>('i18n');

	let loading = false;
	let ready = false;

	let name = '';
	let id = '';
	let description = '';
	let content = '';
	let fileEditor: SkillFiles;
	let fileDirty = false;
	let reloadKey = 0;
	let versionId: string | null = null;
	let currentVersionId: string | null = null;
	let history: any[] = [];
	let currentHistoryEntry: any = null;
	let historyPage = 1;
	let showHistory = false;
	let historyLoading = false;
	let historyError = false;
	let commitMessage = '';
	let conflict = false;
	let baseline = '';
	let historyDiff: any = null;
	let comparing = false;
	let discard = false;
	let showDeleteVersion = false;
	let deleteVersionId: string | null = null;
	let discardAction = () => {};
	$: historical = edit && versionId !== currentVersionId;
	$: readOnly = disabled || historical;
	$: dirty = fileDirty || (!!baseline && baseline !== JSON.stringify({ name, description, meta }));
	const remember = () => {
		baseline = JSON.stringify({ name, description, meta });
		fileDirty = false;
	};
	const confirmDiscard = (action: () => void) => {
		if (dirty) {
			discardAction = action;
			discard = true;
		} else action();
	};
	beforeNavigate(({ cancel }) => {
		if (dirty && !window.confirm('Discard unsaved skill changes?')) cancel();
	});
	const loadHistory = async () => {
		historyLoading = true;
		historyError = false;
		try {
			history = await getSkillHistory(localStorage.token, id, historyPage);
			currentHistoryEntry =
				history.find((entry) => entry.id === currentVersionId) ||
				(currentHistoryEntry?.id === currentVersionId
					? currentHistoryEntry
					: await getSkillVersion(localStorage.token, id, currentVersionId!));
		} catch (error) {
			historyError = true;
			toast.error(skillError(error));
		} finally {
			historyLoading = false;
		}
	};
	const chooseVersion = (selected: string) => {
		showHistory = false;
		if (selected !== versionId) confirmDiscard(() => selectVersion(selected));
	};
	const deleteVersion = async () => {
		if (disabled || loading || !deleteVersionId || deleteVersionId === currentVersionId) return;
		loading = true;
		try {
			await deleteSkillHistoryVersion(localStorage.token, id, deleteVersionId);
			if (versionId === deleteVersionId) await reload();
			historyPage = 1;
			await loadHistory();
			toast.success($i18n.t('Version deleted'));
		} catch (error) {
			toast.error(skillError(error));
		} finally {
			loading = false;
		}
	};
	const compareToCurrent = async () => {
		if (comparing || historyDiff) return;
		const fromId = versionId!;
		const toId = currentVersionId!;
		comparing = true;
		try {
			const result = await (
				await skillRequest(
					localStorage.token,
					`/id/${id}/history/diff?${new URLSearchParams({ from_id: fromId, to_id: toId })}`
				)
			).json();
			if (versionId === fromId && currentVersionId === toId)
				historyDiff = { ...result, fromId, toId };
		} catch (error) {
			toast.error(skillError(error));
		} finally {
			comparing = false;
		}
	};
	const selectVersion = async (selected: string) => {
		try {
			const entry = await getSkillVersion(localStorage.token, id, selected);
			name = entry.snapshot.name;
			description = entry.snapshot.description || '';
			meta = entry.snapshot.meta || {};
			versionId = selected;
			reloadKey++;
			remember();
			historyDiff = null;
		} catch (error) {
			toast.error(skillError(error));
		}
	};
	const reload = async () => {
		try {
			const latest = await getSkillById(localStorage.token, id);
			currentVersionId = latest.version_id;
			await selectVersion(latest.version_id);
			conflict = false;
		} catch (error) {
			toast.error(skillError(error));
		}
	};
	const setProductionVersion = async () => {
		if (disabled || !historical || loading) return;
		loading = true;
		try {
			const updated = await setProductionSkillVersion(
				localStorage.token,
				id,
				versionId!,
				currentVersionId!
			);
			currentVersionId = updated.version_id;
			versionId = updated.version_id;
			historyDiff = null;
			remember();
			await loadHistory();
			toast.success($i18n.t('Production version updated'));
		} catch (error) {
			if ((error as any)?.code === 'version_conflict') conflict = true;
			toast.error(skillError(error));
		} finally {
			loading = false;
		}
	};
	const exportVersion = async (format: 'json' | 'zip') => {
		try {
			saveAs(
				await exportSkillBundle(localStorage.token, format, [id], versionId!),
				`${id}-${versionId?.slice(0, 7)}.${format}`
			);
		} catch (error) {
			toast.error(skillError(error));
		}
	};
	const saveCopy = async () => {
		try {
			const suffix = crypto.randomUUID().slice(0, 7);
			const result = await createNewSkill(localStorage.token, {
				id: `${id}-${suffix}`,
				name: `${name} (${suffix})`,
				description,
				meta,
				files: await fileEditor.getFiles(),
				access_grants: []
			});
			remember();
			await goto(`/workspace/skills/edit?id=${result.id}`);
			window.location.reload();
		} catch (error) {
			toast.error(skillError(error));
		}
	};

	let accessGrants: any[] = [];
	let showAccessControlModal = false;
	$: if (!edit && !clone && name) {
		id = slugify(name);
	}

	const submitHandler = async () => {
		if (loading) return;
		if (readOnly) {
			toast.error($i18n.t('You do not have permission to edit this skill.'));
			return;
		}
		loading = true;
		if (!name.trim()) {
			locale = '';
			loading = false;
			return;
		}
		if (!edit) id = slugify(id);

		try {
			const result = await onSubmit({
				id,
				name,
				description,
				...(edit
					? { operations: await fileEditor.getOperations(), expected_version_id: currentVersionId }
					: { files: await fileEditor.getFiles() }),
				commit_message: commitMessage,
				is_active: skill?.is_active ?? true,
				meta,
				...(!edit ? { access_grants: accessGrants } : {})
			});
			if (result) {
				currentVersionId = result.version_id;
				versionId = result.version_id;
				commitMessage = '';
				conflict = false;
				remember();
				if (showHistory) await loadHistory();
				if (!edit) await goto(`/workspace/skills/edit?id=${result.id}`);
			}
		} catch (error) {
			if ((error as any)?.code === 'version_conflict') conflict = true;
			toast.error(skillError(error));
		} finally {
			loading = false;
		}
	};

	onMount(async () => {
		if (skill) {
			meta = structuredClone(skill.meta ?? {});
			name = skill.name || '';
			await tick();
			id = skill.id || '';
			description = skill.description || '';
			content = skill.content || '';
			currentVersionId = skill.version_id || null;
			versionId = currentVersionId;
			accessGrants = skill?.access_grants === undefined ? [] : skill?.access_grants;
		}
		remember();
		ready = true;
		const requestedVersion = new URLSearchParams(location.search).get('version_id');
		if (edit && requestedVersion && requestedVersion !== versionId)
			await selectVersion(requestedVersion);
	});
</script>

<ConfirmDialog
	bind:show={discard}
	title="Discard unsaved changes?"
	on:confirm={() => {
		remember();
		discardAction();
	}}
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

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.skills || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_skills || $user?.role === 'admin'}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	allowGroups={($user?.permissions?.access_grants?.allow_groups ?? true) || $user?.role === 'admin'}
	onChange={async () => {
		if (edit && skill?.id) {
			try {
				await updateSkillAccessGrants(localStorage.token, skill.id, accessGrants);
				toast.success($i18n.t('Saved'));
			} catch (error) {
				toast.error(`${error}`);
			}
		}
	}}
/>

<div class="flex h-full w-full min-w-0 flex-col overflow-hidden">
	<form
		inert={loading}
		class="flex h-full min-h-0 min-w-0 flex-col"
		on:submit|preventDefault={submitHandler}
	>
		<div class="flex shrink-0 items-center justify-between gap-2">
			<button
				class="flex h-6 w-fit shrink-0 items-center gap-1 whitespace-nowrap rounded-md text-xs text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
				type="button"
				on:click={() => {
					goto('/workspace/skills');
				}}
			>
				<ChevronLeft className="size-3" strokeWidth="2" />
				<span>{$i18n.t('Back')}</span>
			</button>
			<div class="flex shrink-0 items-center gap-1 pr-0.5">
				<LanguageModeSelect bind:value={locale} translatedLocales={Object.keys(meta.i18n ?? {})} />
				{#if !disabled}
					<AccessButton on:click={() => (showAccessControlModal = true)} />
				{:else}
					<span class="rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-500 dark:bg-gray-850">
						{$i18n.t('Read Only')}
					</span>
				{/if}
			</div>
		</div>

		<div class="shrink-0 pb-2 px-1">
			<Tooltip content={$i18n.t('e.g. Code Review Guidelines')} placement="top-start">
				<LocalizedField
					placeholder={$i18n.t('Skill Name')}
					showControls={false}
					bind:value={name}
					bind:translations={meta.i18n}
					{locale}
					required
					disabled={readOnly}
				/>
			</Tooltip>

			<div class="mt-0.5 flex min-w-0 items-center gap-2 text-xs text-gray-500">
				<Tooltip
					className="flex min-w-0 flex-1 items-center"
					content={$i18n.t('e.g. Step-by-step instructions for code reviews')}
					placement="top-start"
				>
					<LocalizedField
						placeholder={$i18n.t('Skill Description')}
						showControls={false}
						bind:value={description}
						bind:translations={meta.i18n}
						{locale}
						field="description"
						disabled={readOnly}
					/>
				</Tooltip>

				{#if edit}
					<div class="shrink-0 truncate font-mono" title={id}>
						{id}
					</div>
				{:else}
					<Tooltip
						className="min-w-[8rem] flex-1"
						content={$i18n.t('e.g. code-review-guidelines')}
						placement="top-start"
					>
						<input
							class="w-full bg-transparent font-mono outline-hidden disabled:text-gray-500"
							type="text"
							placeholder={$i18n.t('Skill ID')}
							aria-label={$i18n.t('Skill ID')}
							bind:value={id}
							required
							disabled={edit}
						/>
					</Tooltip>
				{/if}
			</div>
		</div>

		{#if conflict}<div
				role="alert"
				class="flex flex-wrap gap-3 bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-100"
			>
				<span>This skill has a newer version. Your draft is preserved.</span><button
					type="button"
					on:click={() => confirmDiscard(reload)}>Reload latest</button
				><button type="button" on:click={saveCopy}>Save draft as copy</button><button
					type="button"
					on:click={() => (conflict = false)}>Keep editing</button
				>
			</div>{/if}
		<div
			class="min-h-0 flex-1 overflow-hidden rounded-2xl border border-gray-100 bg-gray-50/60 dark:border-white/5 dark:bg-white/[0.03]"
		>
			{#if historyDiff}
				<VersionDiff
					diff={historyDiff}
					onClose={() => (historyDiff = null)}
					loadFileDiff={async (path) => {
						try {
							return await (
								await skillRequest(
									localStorage.token,
									`/id/${id}/history/diff/file?${new URLSearchParams({ from_id: historyDiff.fromId, to_id: historyDiff.toId, path })}`
								)
							).json();
						} catch (error) {
							throw new Error(skillError(error));
						}
					}}
				/>
			{:else if ready}<SkillFiles
					bind:this={fileEditor}
					skillId={id}
					{versionId}
					{reloadKey}
					initialContent={content}
					initialFiles={skill?.files || null}
					{readOnly}
					bind:dirty={fileDirty}
					initialPath={new URLSearchParams(location.search).get('path') || 'SKILL.md'}
					onSave={submitHandler}
					canExport={edit &&
						($user?.role === 'admin' || $user?.permissions?.workspace?.skills_export)}
				>
					{#snippet version()}
						{#if edit}
							<div class="min-w-0">
								<Dropdown
									bind:show={showHistory}
									onOpenChange={(open) => {
										if (open) {
											historyPage = 1;
											history = [];
											loadHistory();
										}
									}}
								>
									<button
										type="button"
										aria-label="Select version"
										class="flex h-7 max-w-full items-center gap-2 rounded-lg bg-transparent px-2 text-xs text-gray-500 transition hover:text-gray-900 dark:hover:text-gray-100"
									>
										<span class="truncate"
											>{name} · {historical ? versionId?.slice(0, 7) : $i18n.t('Current')}</span
										>
										<ChevronDown className="size-3 shrink-0" />
									</button>
									<div slot="content">
										<DropdownMenu
											className="w-56 max-w-[calc(100vw-2rem)] max-h-80 overflow-y-auto"
										>
											<VersionMenuItem
												entry={currentHistoryEntry?.id === currentVersionId
													? currentHistoryEntry
													: null}
												status={$i18n.t('Current')}
												selected={versionId === currentVersionId}
												onSelect={() => chooseVersion(currentVersionId!)}
											/>
											{#if historyLoading || historyError || history.some((entry) => entry.id !== currentVersionId)}
												<hr class="border-gray-100 dark:border-gray-800" />
											{/if}
											{#if historyLoading}
												<div class="flex items-center gap-2 px-2 py-2 text-xs text-gray-500">
													<Spinner className="size-3" />{$i18n.t('Loading...')}
												</div>
											{:else if historyError}
												<button type="button" on:click={loadHistory}>{$i18n.t('Retry')}</button>
											{:else}
												{#each history.filter((entry) => entry.id !== currentVersionId) as entry}
													<VersionMenuItem
														{entry}
														selected={entry.id === versionId}
														onSelect={() => chooseVersion(entry.id)}
														onDelete={disabled
															? undefined
															: () => {
																	deleteVersionId = entry.id;
																	showHistory = false;
																	showDeleteVersion = true;
																}}
													/>
												{:else}
													{#if historyPage > 1}
														<div class="px-2 py-2 text-xs text-gray-500">
															{$i18n.t('No more versions')}
														</div>
													{/if}
												{/each}
											{/if}
											{#if historyPage > 1 || history.length === 20}
												<hr class="border-gray-100 dark:border-gray-800" />
												<div class="flex justify-between px-2 py-1 text-xs">
													<button
														type="button"
														disabled={historyLoading || historyPage === 1}
														class="disabled:opacity-40"
														on:click={() => {
															historyPage--;
															loadHistory();
														}}>{$i18n.t('Previous')}</button
													>
													<button
														type="button"
														disabled={historyLoading || history.length < 20}
														class="disabled:opacity-40"
														on:click={() => {
															historyPage++;
															loadHistory();
														}}>{$i18n.t('Next')}</button
													>
												</div>
											{/if}
										</DropdownMenu>
									</div>
								</Dropdown>
							</div>
						{/if}
					{/snippet}
					{#snippet exports()}
						<button type="button" on:click={() => exportVersion('json')}
							><Download className="size-3.5" />{$i18n.t('Export JSON')}</button
						>
						<button type="button" on:click={() => exportVersion('zip')}
							><Download className="size-3.5" />{$i18n.t('Export ZIP')}</button
						>
					{/snippet}
				</SkillFiles>{/if}
		</div>

		{#if historical}
			<div
				class="flex w-full shrink-0 flex-wrap items-center gap-2 px-1 py-2 text-xs text-gray-500"
			>
				<span class="mr-auto">{$i18n.t('Read Only')}</span>
				<div class="ml-auto flex flex-wrap justify-end gap-2">
					<button
						type="button"
						class="flex h-7 items-center rounded-lg bg-gray-100 px-2.5 text-xs text-gray-700 disabled:opacity-60 dark:bg-gray-850 dark:text-gray-200"
						disabled={comparing || !!historyDiff}
						on:click={compareToCurrent}
						>{#if comparing}<Spinner className="mr-1.5 size-3" />{/if}{$i18n.t(
							'Compare to current'
						)}</button
					>
					{#if !disabled}<button
							type="button"
							class="flex h-7 items-center rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
							on:click={setProductionVersion}>{$i18n.t('Set as Production')}</button
						>{/if}
				</div>
			</div>
		{/if}

		{#if !readOnly}
			<div class="flex shrink-0 justify-end gap-3 py-2">
				<input
					class="min-w-0 flex-1 bg-transparent px-2 text-xs outline-hidden"
					placeholder="Describe this change"
					aria-label="Commit message"
					bind:value={commitMessage}
				/>
				<button
					class="flex h-7 items-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
					type="submit"
					disabled={loading || !fileEditor}
				>
					{$i18n.t(edit ? 'Save' : 'Save & Create')}
					{#if loading}
						<Spinner className="size-3" />
					{/if}
				</button>
			</div>
		{/if}
	</form>
</div>
