<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
import { createTenant } from '$lib/apis/tenants';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let loading = false;
	let name = '';

	$: if (show) {
		name = '';
	}

	const submitHandler = async () => {
		const trimmed = name.trim();
		if (!trimmed) {
			toast.error($i18n.t('Tenant name is required'));
			return;
		}

		if (typeof localStorage === 'undefined' || !localStorage.token) {
			toast.error($i18n.t('You must be signed in to add tenants.'));
			return;
		}

		loading = true;
		try {
			await createTenant(localStorage.token, trimmed);
			toast.success($i18n.t('Tenant created'));
			dispatch('save');
			show = false;
		} catch (error) {
			const message = typeof error === 'string' ? error : (error?.detail ?? 'Failed to create tenant.');
			toast.error(message);
		} finally {
			loading = false;
		}
	};
</script>

<Modal size="sm" bind:show>
	<div class="px-5 pt-4 pb-4">
		<div class="mb-4 flex items-center justify-between">
			<h2 class="text-lg font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Add Tenant')}</h2>
			<button
				class="text-sm text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
				on:click={() => {
					show = false;
				}}
			>
				{$i18n.t('Close')}
			</button>
		</div>

		<form
			class="space-y-4"
			on:submit|preventDefault={() => {
				submitHandler();
			}}
		>
			<div class="flex flex-col space-y-1">
				<label class="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
					{$i18n.t('Tenant Name')}
				</label>
				<input
					class="rounded-xl border border-gray-200 bg-transparent px-3 py-2 text-sm text-gray-900 outline-hidden focus:border-blue-500 dark:border-gray-700 dark:text-gray-100"
					type="text"
					placeholder={$i18n.t('Enter tenant name')}
					bind:value={name}
					required
				/>
			</div>

			<div class="flex justify-end">
				<button
					class="inline-flex items-center rounded-full bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-900 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-gray-100"
					type="submit"
					disabled={loading}
				>
					{$i18n.t('Save')}
					{#if loading}
						<span class="ml-2">
							<Spinner className="size-4" />
						</span>
					{/if}
				</button>
			</div>
		</form>
	</div>
</Modal>
