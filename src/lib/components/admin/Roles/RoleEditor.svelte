<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import CapabilitySelector from './CapabilitySelector.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let show = false;
	export let edit = false;
	export let role: any = null;
	export let availableCapabilities: string[] = [];

	export let onSubmit: (role: object) => Promise<void> = async () => {};
	export let onDelete: () => Promise<void> = async () => {};

	// System roles that cannot be deleted or fundamentally modified
	const SYSTEM_ROLES = ['admin', 'user', 'pending'];

	let loading = false;
	let showDeleteConfirmDialog = false;

	// Form state
	let name = '';
	let description = '';
	let selectedCapabilities: string[] = [];

	$: isSystemRole = SYSTEM_ROLES.includes(role?.name ?? '');
	$: isDeletable = edit && !isSystemRole;

	const init = () => {
		if (role) {
			name = role.name ?? '';
			description = role.description ?? '';
			selectedCapabilities = [...(role.capabilities ?? [])];
		} else {
			name = '';
			description = '';
			selectedCapabilities = [];
		}
	};

	$: if (show) {
		init();
	}

	const submitHandler = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('Role name is required'));
			return;
		}

		loading = true;
		try {
			await onSubmit({
				name: name.trim(),
				description: description.trim(),
				capabilities: selectedCapabilities
			});
			show = false;
		} catch {
			// error handled by parent
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		init();
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={async () => {
		await onDelete();
		show = false;
	}}
/>

<Modal size="md" bind:show>
	<div>
		<!-- Header -->
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 mb-3">
			<div class="text-lg font-medium self-center font-primary">
				{#if edit}
					{#if isSystemRole}
						{$i18n.t('View Role')} —
						<span class="text-gray-400 dark:text-gray-500 text-base">{$i18n.t('System role')}</span>
					{:else}
						{$i18n.t('Edit Role')}
					{/if}
				{:else}
					{$i18n.t('Create Role')}
				{/if}
			</div>
			<button
				class="self-center text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
				on:click={() => (show = false)}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<!-- Body -->
		<form class="flex flex-col px-5 pb-5" on:submit|preventDefault={submitHandler}>
			<!-- Name field -->
			<div class="mb-4">
				<div
					class="mb-1 text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide"
				>
					{$i18n.t('Name')}
				</div>
				<input
					class="w-full text-sm bg-transparent border-b border-gray-200 dark:border-gray-700 pb-1 outline-none focus:border-gray-400 dark:focus:border-gray-500 transition placeholder:text-gray-300 dark:placeholder:text-gray-700 {isSystemRole
						? 'opacity-60 cursor-not-allowed'
						: ''}"
					type="text"
					bind:value={name}
					placeholder={$i18n.t('Role name (e.g. moderator)')}
					autocomplete="off"
					disabled={isSystemRole}
					required
				/>
			</div>

			<!-- Description field -->
			<div class="mb-5">
				<div
					class="mb-1 text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide"
				>
					{$i18n.t('Description')}
				</div>
			<textarea
				class="w-full text-sm bg-transparent border-b border-gray-200 dark:border-gray-700 pb-1 outline-none focus:border-gray-400 dark:focus:border-gray-500 transition resize-none placeholder:text-gray-300 dark:placeholder:text-gray-700 {isSystemRole
					? 'opacity-60 cursor-not-allowed'
					: ''}"
				rows="2"
				bind:value={description}
				placeholder={$i18n.t('Describe what this role can do...')}
				disabled={isSystemRole}
			></textarea>
			</div>

			<hr class="border-gray-100/50 dark:border-gray-850/50 mb-4" />

			<!-- Capabilities section -->
			<div class="mb-5">
				<div class="flex items-center gap-2 mb-3">
					<WrenchSolid className="size-4 text-gray-400" />
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Capabilities')}
					</span>
					{#if selectedCapabilities.length > 0}
						<span
							class="text-xs bg-black/5 dark:bg-white/10 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full font-medium"
						>
							{selectedCapabilities.length}
						</span>
					{/if}
				</div>

				{#if isSystemRole}
					<div
						class="text-xs text-gray-400 dark:text-gray-500 italic mb-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg px-3 py-2"
					>
						{$i18n.t('System role capabilities cannot be modified.')}
					</div>

					{#if selectedCapabilities.length > 0}
						<div class="flex flex-wrap gap-1.5">
							{#each selectedCapabilities as cap}
								<span
									class="text-xs px-2 py-1 rounded-full bg-black/5 dark:bg-white/10 text-gray-600 dark:text-gray-400"
								>
									{cap.replace(/_/g, ' ')}
								</span>
							{/each}
						</div>
					{:else}
						<div class="text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('No capabilities assigned to this role.')}
						</div>
					{/if}
				{:else}
					<div class="max-h-80 overflow-y-auto scrollbar-hidden pr-1">
						<CapabilitySelector capabilities={availableCapabilities} bind:selectedCapabilities />
					</div>
				{/if}
			</div>

			<!-- Footer actions -->
			<div class="flex items-center justify-between pt-2">
				<div>
					{#if isDeletable}
						<button
							type="button"
							class="text-xs text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 transition hover:underline"
							on:click={() => (showDeleteConfirmDialog = true)}
						>
							{$i18n.t('Delete role')}
						</button>
					{/if}
				</div>

				{#if !isSystemRole}
					<button
						type="submit"
						class="px-4 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 {loading
							? 'opacity-70 cursor-not-allowed'
							: ''}"
						disabled={loading}
					>
						{#if loading}
							<Spinner className="size-3.5" />
						{/if}
						{edit ? $i18n.t('Save') : $i18n.t('Create')}
					</button>
				{:else}
					<button
						type="button"
						class="px-4 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition rounded-full"
						on:click={() => (show = false)}
					>
						{$i18n.t('Close')}
					</button>
				{/if}
			</div>
		</form>
	</div>
</Modal>
