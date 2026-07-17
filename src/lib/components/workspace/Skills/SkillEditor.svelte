<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
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
	$: if (!edit && !clone && name) {
		id = slugify(name);
	}

	const handleContentInput = () => {
		if (edit) return;
		const fm = parseFrontmatter(content);
		if (fm.name && !name) {
			name = formatSkillName(fm.name);
			id = fm.name;
		}
		if (fm.description && !description) {
			description = fm.description;
		}
	};

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
		}
	});
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.skills || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_skills || $user?.role === 'admin'}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
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
	<form class="flex h-full min-h-0 min-w-0 flex-col" on:submit|preventDefault={submitHandler}>
		<button
			class="mb-1 flex h-6 w-fit items-center gap-1 rounded-md text-xs text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
			type="button"
			on:click={() => {
				goto('/workspace/skills');
			}}
		>
			<ChevronLeft className="size-3" strokeWidth="2" />
			<span>{$i18n.t('Back')}</span>
		</button>

		<div class="flex shrink-0 items-start gap-2 pb-2 px-1">
			<div class="min-w-0 flex-1">
				<Tooltip content={$i18n.t('e.g. Code Review Guidelines')} placement="top-start">
					<input
						class="w-full bg-transparent text-sm outline-hidden"
						type="text"
						placeholder={$i18n.t('Skill Name')}
						aria-label={$i18n.t('Skill Name')}
						bind:value={name}
						required
						{disabled}
					/>
				</Tooltip>

				<div class="mt-0.5 flex min-w-0 items-center gap-2 text-xs text-gray-500">
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

					<Tooltip
						className="flex min-w-0 flex-1 items-center"
						content={$i18n.t('e.g. Step-by-step instructions for code reviews')}
						placement="top-start"
					>
						<input
							class="w-full bg-transparent outline-hidden"
							type="text"
							placeholder={$i18n.t('Skill Description')}
							aria-label={$i18n.t('Skill Description')}
							bind:value={description}
							{disabled}
						/>
					</Tooltip>
				</div>
			</div>

			<div class="flex shrink-0 items-center gap-1 pr-0.5">
				{#if !disabled}
					<AccessButton on:click={() => (showAccessControlModal = true)} />
				{:else}
					<span class="rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-500 dark:bg-gray-850">
						{$i18n.t('Read Only')}
					</span>
				{/if}
			</div>
		</div>

		<div class="min-h-0 flex-1 overflow-hidden rounded-lg bg-gray-50/60 dark:bg-white/[0.03]">
			{#if disabled}
				<div class="h-full overflow-y-auto px-3 py-2">
					<pre class="whitespace-pre-wrap font-mono text-[11px] leading-relaxed">{content}</pre>
				</div>
			{:else}
				<textarea
					class="h-full w-full resize-none bg-transparent px-3 py-2 font-mono text-[11px] leading-relaxed outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-600"
					bind:value={content}
					on:input={handleContentInput}
					placeholder={$i18n.t('Enter skill instructions in markdown...')}
					aria-label={$i18n.t('Skill Instructions')}
					required
				></textarea>
			{/if}
		</div>

		{#if !disabled}
			<div class="flex shrink-0 justify-end py-2">
				<button
					class="flex h-7 items-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
					type="submit"
					disabled={loading}
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
