<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { user } from '$lib/stores';
	import { slugify, parseFrontmatter, formatSkillName } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { updateSkillAccessGrants } from '$lib/apis/skills';
	import { goto } from '$app/navigation';

	export let onSubmit: Function;
	export let edit = false;
	export let skill = null;
	export let clone = false;
	export let disabled = false;

	const i18n = getContext('i18n');

	let loading = false;

	let name = '';
	let id = '';
	let description = '';
	let content = '';

	let accessGrants = [];
	let showAccessControlModal = false;
	let hasManualEdit = false;
	let hasManualName = false;
	let hasManualDescription = false;
	let isFrontmatterDetected = false;

	// Auto-detect frontmatter and fill name/description in create mode
	$: if (!edit && content) {
		const fm = parseFrontmatter(content);
		if (fm.name) {
			isFrontmatterDetected = true;
			if (!hasManualName) {
				name = formatSkillName(fm.name);
			}
			if (!hasManualEdit) {
				id = fm.name;
			}
		} else {
			isFrontmatterDetected = false;
		}
		if (fm.description && !hasManualDescription) {
			description = fm.description;
		}
	} else if (!edit && !content) {
		isFrontmatterDetected = false;
	}

	$: if (!edit && !hasManualEdit && !isFrontmatterDetected) {
		id = name !== '' ? slugify(name) : '';
	}

	function handleIdInput(e: Event) {
		hasManualEdit = true;
	}

	function handleNameInput(e: Event) {
		hasManualName = true;
	}

	function handleDescriptionInput(e: Event) {
		hasManualDescription = true;
	}

	const submitHandler = async () => {
		if (disabled) {
			toast.error($i18n.t('You do not have permission to edit this skill.'));
			return;
		}
		loading = true;

		await onSubmit({
			id,
			name,
			description,
			content,
			is_active: true,
			meta: { tags: [] },
			access_grants: accessGrants
		});

		loading = false;
	};

	onMount(async () => {
		if (skill) {
			name = skill.name || '';
			await tick();
			id = skill.id || '';
			description = skill.description || '';
			content = skill.content || '';
			accessGrants = skill?.access_grants === undefined ? [] : skill?.access_grants;

			if (name) hasManualName = true;
			if (description) hasManualDescription = true;
			if (id) hasManualEdit = true;
		}
	});
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.skills || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_skills || $user?.role === 'admin' || edit}
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

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<form class=" flex flex-col max-h-[100dvh] h-full" on:submit|preventDefault={submitHandler}>
			<div class="flex flex-col flex-1 overflow-auto h-0 rounded-lg">
				<div class="w-full mb-2 flex flex-col gap-0.5">
					<div class="flex w-full items-center">
						<div class=" shrink-0 mr-2">
							<Tooltip content={$i18n.t('Back')}>
								<button
									class="w-full text-left text-sm py-1.5 px-1 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850"
									on:click={() => {
										goto('/workspace/skills');
									}}
									type="button"
								>
									<ChevronLeft strokeWidth="2.5" />
								</button>
							</Tooltip>
						</div>

						<div class="flex-1">
							<Tooltip content={$i18n.t('e.g. Code Review Guidelines')} placement="top-start">
								<input
									class="w-full text-2xl font-medium bg-transparent outline-hidden font-primary"
									type="text"
									placeholder={$i18n.t('Skill Name')}
									bind:value={name}
									on:input={handleNameInput}
									required
									{disabled}
								/>
							</Tooltip>
						</div>

						<div class="self-center shrink-0">
							{#if !disabled}
								<button
									class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
									type="button"
									on:click={() => (showAccessControlModal = true)}
								>
									<LockClosed strokeWidth="2.5" className="size-3.5" />

									<div class="text-sm font-medium shrink-0">
										{$i18n.t('Access')}
									</div>
								</button>
							{:else}
								<span
									class="text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full"
									>{$i18n.t('Read Only')}</span
								>
							{/if}
						</div>
					</div>

					<div class=" flex gap-2 px-1 items-center">
						{#if edit}
							<div class="text-sm text-gray-500 shrink-0">
								{id}
							</div>
						{:else}
							<Tooltip
								className="w-full"
								content={$i18n.t('e.g. code-review-guidelines')}
								placement="top-start"
							>
								<input
									class="w-full text-sm disabled:text-gray-500 bg-transparent outline-hidden"
									type="text"
									placeholder={$i18n.t('Skill ID')}
									bind:value={id}
									on:input={handleIdInput}
									required
									disabled={edit}
								/>
							</Tooltip>
						{/if}

						<Tooltip
							className="w-full self-center items-center flex"
							content={$i18n.t('e.g. Step-by-step instructions for code reviews')}
							placement="top-start"
						>
							<input
								class="w-full text-sm bg-transparent outline-hidden"
								type="text"
								placeholder={$i18n.t('Skill Description')}
								bind:value={description}
								on:input={handleDescriptionInput}
								{disabled}
							/>
						</Tooltip>
					</div>
				</div>

				<div class="mb-2 flex-1 overflow-auto h-0 rounded-lg">
					<div class="h-full flex flex-col">
						<div
							class="bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-100/50 dark:border-gray-850/50 flex-1 min-h-0 overflow-hidden flex flex-col"
						>
							{#if disabled}
								<div class="px-4 py-3 overflow-y-auto flex-1">
									<pre class="text-xs whitespace-pre-wrap font-mono">{content}</pre>
								</div>
							{:else}
								<textarea
									class="w-full flex-1 text-xs bg-transparent outline-hidden resize-none font-mono px-4 py-3"
									bind:value={content}
									placeholder={$i18n.t('Enter skill instructions in markdown...')}
									required
								/>
							{/if}
						</div>
					</div>
				</div>

				<div class="pb-3 flex justify-end">
					{#if !disabled}
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center"
							type="submit"
							disabled={loading}
						>
							{$i18n.t(edit ? 'Save' : 'Save & Create')}
							{#if loading}
								<div class="ml-1.5">
									<Spinner />
								</div>
							{/if}
						</button>
					{/if}
				</div>
			</div>
		</form>
	</div>
</div>
