<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { i18n as i18nType } from 'i18next';
	import type { Writable } from 'svelte/store';

	import type { UploadTenant } from '$lib/apis/uploads';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let tenants: UploadTenant[] = [];
	export let selectedTenantId: string | null = null;
	export let loading: boolean = false;
	export let error: string | null = null;

	const dispatch = createEventDispatcher<{ change: string | null }>();

	const handleChange = (event: Event) => {
		const nextValue = (event.currentTarget as HTMLSelectElement).value;
		dispatch('change', nextValue ? nextValue : null);
	};
</script>

<div class="mt-2 md:mt-0 flex flex-col w-full">
	<label class="text-[0.65rem] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
		{$i18n.t('Tenant Scope')}
	</label>

	<div class="mt-1">
		<select
			class="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-900 transition focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
			on:change={handleChange}
			disabled={loading}
			value={selectedTenantId ?? ''}
		>
			<option value="">
				{loading ? $i18n.t('Loading tenants...') : $i18n.t('Use assigned tenant')}
			</option>
			{#each tenants as tenant}
				<option value={tenant.id} title={tenant.s3_bucket}>
					{tenant.name}
				</option>
			{/each}
		</select>
	</div>

	{#if error}
		<p class="mt-1 text-xs text-red-500">{error}</p>
	{:else if !loading && tenants.length === 0}
		<p class="mt-1 text-xs text-gray-500">{$i18n.t('No tenants available.')}</p>
	{/if}
</div>
