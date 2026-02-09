<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { toast } from 'svelte-sonner';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	export let onSubmit: (skill: Record<string, unknown>) => Promise<void> | void;
	export let edit = false;
	export let skill: any = null;
	export let disabled = false;

	const i18n = getContext('i18n');

	let loading = false;
	let showAccessControlModal = false;

	let id = '';
	let name = '';
	let content = '';
	let isActive = true;
	let priority = 0;
	let activationMode = 'manual';
	let activationKeywords = '';
	let activationAllKeywords = '';
	let activationRegex = '';

	let accessControl: Record<string, unknown> | null = {};

	const submitHandler = async () => {
		if (disabled) {
			toast.error($i18n.t('You do not have permission to edit this skill.'));
			return;
		}

		if (!/^[a-zA-Z0-9-_]+$/.test(id)) {
			toast.error(
				$i18n.t('Only alphanumeric characters and hyphens are allowed in the identifier.')
			);
			return;
		}

		loading = true;

		const keywords = activationKeywords
			.split(',')
			.map((item) => item.trim())
			.filter(Boolean);
		const allKeywords = activationAllKeywords
			.split(',')
			.map((item) => item.trim())
			.filter(Boolean);
		const regexPatterns = activationRegex
			.split('\n')
			.map((item) => item.trim())
			.filter(Boolean);

		await onSubmit({
			id,
			name,
			content,
			meta: {},
			activation: {
				mode: activationMode,
				keywords,
				all_keywords: allKeywords,
				regex: regexPatterns,
				combine: 'and'
			},
			effects: {},
			is_active: isActive,
			priority: Number.isFinite(Number(priority)) ? Number(priority) : 0,
			access_control: accessControl
		});

		loading = false;
	};

	onMount(() => {
		if (skill) {
			id = skill.id;
			name = skill.name;
			content = skill.content;
			isActive = Boolean(skill.is_active);
			priority = Number(skill.priority ?? 0);
			accessControl = skill?.access_control === undefined ? {} : skill?.access_control;

			const activation =
				skill?.activation && typeof skill.activation === 'object' ? skill.activation : {};

			activationMode =
				activation?.mode === 'semantic'
					? 'semantic'
					: activation?.mode === 'auto' || activation?.mode === 'always'
						? 'auto'
						: 'manual';
			activationKeywords = Array.isArray(activation?.keywords)
				? activation.keywords.join(', ')
				: '';
			activationAllKeywords = Array.isArray(activation?.all_keywords)
				? activation.all_keywords.join(', ')
				: '';
			activationRegex = Array.isArray(activation?.regex) ? activation.regex.join('\n') : '';
		}
	});
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessControl
	accessRoles={['read', 'write']}
	share={false}
	sharePublic={false}
/>

<div class="w-full max-h-full flex justify-center">
	<form
		class="flex flex-col w-full mb-10"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div class="my-2 flex items-center gap-2">
			<input
				class="text-2xl font-medium w-full bg-transparent outline-hidden"
				placeholder={$i18n.t('Name')}
				bind:value={name}
				required
				{disabled}
			/>

			{#if disabled}
				<div class="text-xs shrink-0 text-gray-500">{$i18n.t('Read Only')}</div>
			{:else}
				<button
					class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
					type="button"
					on:click={() => {
						showAccessControlModal = true;
					}}
				>
					<LockClosed strokeWidth="2.5" className="size-3.5" />
					<div class="text-sm font-medium shrink-0">{$i18n.t('Access')}</div>
				</button>
			{/if}
		</div>

		<div class="my-2 flex flex-col gap-2">
			<div class="text-xs text-gray-500">{$i18n.t('Identifier')}</div>
			<input
				class="w-full text-sm bg-transparent outline-hidden border border-gray-200 dark:border-gray-800 rounded-xl px-3 py-2"
				placeholder={$i18n.t('skill_id')}
				bind:value={id}
				required
				disabled={edit || disabled}
			/>
			<div class="text-xs text-gray-500">
				{$i18n.t('Use only letters, numbers, underscore, and hyphen.')}
			</div>
		</div>

		<div class="my-2 grid grid-cols-1 md:grid-cols-2 gap-3">
			<div class="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-800 px-3 py-2">
				<div class="text-sm">{$i18n.t('Active')}</div>
				<Switch bind:state={isActive} />
			</div>

			<div class="flex items-center gap-2 rounded-xl border border-gray-200 dark:border-gray-800 px-3 py-2">
				<div class="text-sm shrink-0">{$i18n.t('Priority')}</div>
				<input
					type="number"
					class="w-full text-sm bg-transparent outline-hidden"
					bind:value={priority}
					disabled={disabled}
				/>
			</div>
		</div>

		<div class="my-2 rounded-xl border border-gray-200 dark:border-gray-800 px-3 py-3">
			<div class="text-sm font-medium mb-2">{$i18n.t('Activation')}</div>

			<div class="flex items-center gap-4 text-sm">
				<label class="flex items-center gap-1.5">
					<input
						type="radio"
						bind:group={activationMode}
						value="manual"
						disabled={disabled}
					/>
					<span>{$i18n.t('Manual')}</span>
				</label>

				<label class="flex items-center gap-1.5">
					<input
						type="radio"
						bind:group={activationMode}
						value="auto"
						disabled={disabled}
					/>
					<span>{$i18n.t('Auto')}</span>
				</label>

				<label class="flex items-center gap-1.5">
					<input
						type="radio"
						bind:group={activationMode}
						value="semantic"
						disabled={disabled}
					/>
					<span>{$i18n.t('Semantic')}</span>
				</label>
			</div>

			{#if activationMode === 'auto'}
				<div class="mt-3 grid grid-cols-1 gap-2">
					<input
						class="w-full text-sm bg-transparent outline-hidden border border-gray-200 dark:border-gray-800 rounded-xl px-3 py-2"
						placeholder={$i18n.t('Any keyword (comma separated)')}
						bind:value={activationKeywords}
						disabled={disabled}
					/>

					<input
						class="w-full text-sm bg-transparent outline-hidden border border-gray-200 dark:border-gray-800 rounded-xl px-3 py-2"
						placeholder={$i18n.t('All keywords required (comma separated)')}
						bind:value={activationAllKeywords}
						disabled={disabled}
					/>

					<Textarea
						className="text-sm w-full bg-transparent outline-hidden overflow-y-hidden resize-none border border-gray-200 dark:border-gray-800 rounded-xl px-3 py-2"
						placeholder={$i18n.t('Regex patterns (one per line)')}
						bind:value={activationRegex}
						rows={3}
						readonly={disabled}
					/>

					<div class="text-xs text-gray-500">
						{$i18n.t('Auto mode triggers only when activation rules match user message.')}
					</div>
				</div>
			{:else if activationMode === 'semantic'}
				<div class="mt-3 text-xs text-gray-500">
					{$i18n.t(
						'Semantic mode uses model-based intent matching. No keyword patterns are required.'
					)}
				</div>
			{/if}
		</div>

		<div class="my-2">
			<div class="flex w-full justify-between">
				<div class=" self-center text-sm font-medium">{$i18n.t('Skill Content')}</div>
			</div>

			<div class="mt-2">
				<Textarea
					className="text-sm w-full bg-transparent outline-hidden overflow-y-hidden resize-none"
					placeholder={$i18n.t('Describe behavior and constraints for this skill...')}
					bind:value={content}
					rows={10}
					required
					readonly={disabled}
				/>
			</div>
		</div>

		<div class="my-4 flex justify-end pb-20">
			<button
				class="text-sm w-full lg:w-fit px-4 py-2 transition rounded-xl {loading || disabled
					? ' cursor-not-allowed bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
					: 'bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'} flex justify-center"
				type="submit"
				disabled={loading || disabled}
			>
				<div class=" self-center font-medium">{$i18n.t('Save')}</div>
				{#if loading}
					<div class="ml-1.5 self-center">
						<Spinner />
					</div>
				{/if}
			</button>
		</div>
	</form>
</div>
