<!-- Company custom: Team Workspaces V1 -->
<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { createWorkspace, updateWorkspace } from '$lib/apis/workspaces';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let workspace: any = null; // null = create mode
	export let onSubmit: (ws: any) => void = () => {};

	let name = '';
	let description = '';
	let loading = false;

	// Reset fields whenever modal opens
	$: if (show) {
		name = workspace?.name ?? '';
		description = workspace?.description ?? '';
	}

	const submit = async () => {
		name = name.trim();
		if (!name) {
			toast.error($i18n.t('Workspace name cannot be empty.'));
			return;
		}

		loading = true;
		try {
			let res;
			if (workspace) {
				res = await updateWorkspace(localStorage.token, workspace.id, {
					name,
					description: description || null
				});
			} else {
				res = await createWorkspace(localStorage.token, { name, description: description || null });
			}

			if (res) {
				toast.success(workspace ? $i18n.t('Workspace updated') : $i18n.t('Workspace created'));
				onSubmit(res);
				show = false;
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	};
</script>

<Modal bind:show size="sm">
	<div class="px-5 py-4">
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-semibold dark:text-white">
				{workspace ? $i18n.t('Edit Workspace') : $i18n.t('New Workspace')}
			</h3>
			<button
				type="button"
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
				on:click={() => (show = false)}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<form on:submit|preventDefault={submit} class="flex flex-col gap-3">
			<div>
				<label class="block text-sm font-medium dark:text-gray-300 mb-1">
					{$i18n.t('Name')}
				</label>
				<input
					bind:value={name}
					class="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
					placeholder={$i18n.t('e.g. AM Team')}
					required
					autofocus
				/>
			</div>

			<div>
				<label class="block text-sm font-medium dark:text-gray-300 mb-1">
					{$i18n.t('Description')}
					<span class="font-normal text-gray-400">({$i18n.t('optional')})</span>
				</label>
				<input
					bind:value={description}
					class="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
					placeholder={$i18n.t('Short description…')}
				/>
			</div>

			<div class="flex justify-end gap-2 mt-2">
				<button
					type="button"
					class="px-4 py-2 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
					on:click={() => (show = false)}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					type="submit"
					disabled={loading}
					class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm bg-black text-white dark:bg-white dark:text-black hover:opacity-80 disabled:opacity-50"
				>
					{#if loading}
						<Spinner className="size-4" />
					{/if}
					{workspace ? $i18n.t('Save') : $i18n.t('Create')}
				</button>
			</div>
		</form>
	</div>
</Modal>
