<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { createSpace, updateSpaceById, deleteSpaceById, updateSpaceAccessLevel, SpaceAccessLevel } from '$lib/apis/spaces';
	import type { Space } from '$lib/apis/spaces';
	import { models, user } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let onSubmit: Function = () => {};
	export let onUpdate: Function = () => {};

	export let space: Space | null = null;
	export let edit = false;

	let name = '';
	let emoji = '';
	let description = '';
	let instructions = '';
	let modelId = '';
	let enableWebByDefault = false;
	let accessLevel = SpaceAccessLevel.PRIVATE;

	let loading = false;
	let showDeleteConfirmDialog = false;

	const submitHandler = async () => {
		loading = true;

		if (!name.trim()) {
			toast.error($i18n.t('Space name is required'));
			loading = false;
			return;
		}

		if (name.length > 128) {
			toast.error($i18n.t('Space name must be less than 128 characters'));
			loading = false;
			return;
		}

		try {
			if (edit && space) {
				const res = await updateSpaceById(localStorage.token, space.id, {
					name: name.trim(),
					emoji: emoji.trim() || null,
					description: description.trim() || null,
					instructions: instructions.trim() || null,
					model_id: modelId || null,
					enable_web_by_default: enableWebByDefault
				});

				// Update access level if it changed
				if (accessLevel !== (space.access_level ?? SpaceAccessLevel.PRIVATE)) {
					await updateSpaceAccessLevel(localStorage.token, space.id, accessLevel);
				}

				if (res) {
					toast.success($i18n.t('Space updated successfully'));
					onUpdate();
				}
			} else {
				const res = await createSpace(localStorage.token, {
					name: name.trim(),
					emoji: emoji.trim() || null,
					description: description.trim() || null,
					instructions: instructions.trim() || null,
					model_id: modelId || null,
					enable_web_by_default: enableWebByDefault
				});

				if (res) {
					toast.success($i18n.t('Space created successfully'));
					await onSubmit(res);
				}
			}
		} catch (error) {
			toast.error(String(error));
		}

		show = false;
		loading = false;
	};

	const deleteHandler = async () => {
		showDeleteConfirmDialog = false;

		if (!space) return;

		const res = await deleteSpaceById(localStorage.token, space.id).catch((error) => {
			toast.error(error.message);
		});

		if (res) {
			toast.success($i18n.t('Space deleted successfully'));
			onUpdate();

			if ($page.url.pathname.startsWith(`/spaces/${space.id}`)) {
				goto('/');
			}
		}

		show = false;
	};

	const init = () => {
		if (space) {
			name = space?.name ?? '';
			emoji = space?.emoji ?? '';
			description = space?.description ?? '';
			instructions = space?.instructions ?? '';
			modelId = space?.model_id ?? '';
			enableWebByDefault = space?.enable_web_by_default ?? false;
			accessLevel = space?.access_level ?? SpaceAccessLevel.PRIVATE;
		}
	};

	$: if (show) {
		init();
	} else {
		resetHandler();
	}

	const isCurrentUserOwner = (): boolean => {
		if (!space || !$user) return false;
		return space.user_id === $user.id;
	};

	const resetHandler = () => {
		name = '';
		emoji = '';
		description = '';
		instructions = '';
		modelId = '';
		enableWebByDefault = false;
		accessLevel = SpaceAccessLevel.PRIVATE;
		loading = false;
	};
</script>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">
				{#if edit}
					{$i18n.t('Edit Space')}
				{:else}
					{$i18n.t('Create Space')}
				{/if}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="flex gap-2 w-full mt-2">
						<div class="flex flex-col flex-1">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Space Name')}</div>
							<div class="flex-1 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 focus-within:border-gray-300 dark:focus-within:border-gray-600 transition">
								<input
									class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
									type="text"
									bind:value={name}
									placeholder={$i18n.t('My Space')}
									autocomplete="off"
									required
								/>
							</div>
						</div>

						<div class="flex flex-col w-20">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Emoji')}</div>
							<div class="flex-1 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 focus-within:border-gray-300 dark:focus-within:border-gray-600 transition">
								<input
									class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden text-center"
									type="text"
									bind:value={emoji}
									placeholder="🚀"
									autocomplete="off"
									maxlength="4"
								/>
							</div>
						</div>
					</div>

					<div class="flex flex-col w-full mt-3">
						<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Description')}</div>
						<div class="flex-1 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 focus-within:border-gray-300 dark:focus-within:border-gray-600 transition">
							<input
								class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
								type="text"
								bind:value={description}
								placeholder={$i18n.t('A brief description of this space')}
								autocomplete="off"
							/>
						</div>
					</div>

					<div class="flex flex-col w-full mt-3">
						<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Model')}</div>
						<div class="flex-1 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 focus-within:border-gray-300 dark:focus-within:border-gray-600 transition">
							<select
								class="w-full text-sm bg-transparent outline-hidden"
								bind:value={modelId}
							>
								<option value="" class="bg-gray-50 dark:bg-gray-700">
									{$i18n.t('Default')}
								</option>
								{#each $models.filter((model) => !(model?.info?.meta?.hidden ?? false)) as model}
									<option value={model.id} class="bg-gray-50 dark:bg-gray-700"
										>{model.name}</option
									>
								{/each}
							</select>
						</div>
					</div>

					<div class="flex flex-col w-full mt-3">
						<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Instructions')}</div>
						<div class="flex-1 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 focus-within:border-gray-300 dark:focus-within:border-gray-600 transition">
							<textarea
								class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden resize-none"
								bind:value={instructions}
								placeholder={$i18n.t(
									'Custom instructions for conversations in this space'
								)}
								rows="3"
							></textarea>
						</div>
					</div>

					<div class="flex w-full mt-3 items-center justify-between">
						<div class="text-xs text-gray-500">
							{$i18n.t('Enable Web Search by Default')}
						</div>
						<Switch bind:state={enableWebByDefault} />
					</div>

					{#if edit && isCurrentUserOwner()}
						<div class="flex flex-col w-full mt-3">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Access Level')}</div>
							<div class="flex-1 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 focus-within:border-gray-300 dark:focus-within:border-gray-600 transition">
								<select
									class="w-full text-sm bg-transparent outline-hidden"
									bind:value={accessLevel}
								>
									<option value={SpaceAccessLevel.PRIVATE} class="bg-gray-50 dark:bg-gray-700">
										{$i18n.t('Private — Only invited contributors')}
									</option>
									<option value={SpaceAccessLevel.ORG} class="bg-gray-50 dark:bg-gray-700">
										{$i18n.t('Organization — Anyone in your org')}
									</option>
									<option value={SpaceAccessLevel.PUBLIC} class="bg-gray-50 dark:bg-gray-700">
										{$i18n.t('Public — Anyone with the link')}
									</option>
								</select>
							</div>
						</div>
					{/if}

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if edit && isCurrentUserOwner()}
							<button
								class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-black/90 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{#if edit}
								{$i18n.t('Update')}
							{:else}
								{$i18n.t('Create')}
							{/if}

							{#if loading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<DeleteConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t('Are you sure you want to delete this space?')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		deleteHandler();
	}}
/>
