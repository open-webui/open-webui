<script lang="ts">
	import { getContext } from 'svelte';
	import { getGroupPreview } from '$lib/apis/groups';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let groupId: string = '';

	let loading = true;
	let preview: any = null;
	let error: string = '';

	$: if (groupId) {
		loadPreview();
	}

	const loadPreview = async () => {
		loading = true;
		error = '';
		try {
			preview = await getGroupPreview(localStorage.token, groupId);
		} catch (e) {
			error = String(e);
		} finally {
			loading = false;
		}
	};
</script>

<div class="space-y-2">
	{#if loading}
		<div class="flex justify-center items-center py-8">
			<Spinner className="size-5" />
		</div>
	{:else if error}
		<div class="text-red-500 text-xs text-center py-4">{error}</div>
	{:else if preview}
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('Models')}</div>

			<div class="flex flex-col w-full">
				{#if preview.models.items.length === 0}
					<div class="flex w-full justify-between my-1">
						<div class=" self-center text-xs text-gray-500">
							{$i18n.t('No models accessible')}
						</div>
					</div>
				{:else}
					{#each preview.models.items as model}
						<div class="flex w-full justify-between my-1">
							<div class=" self-center text-xs font-medium">{model.name}</div>
						</div>
					{/each}

					{#if preview.models.total > preview.models.items.length}
						<div class="flex w-full justify-between my-1">
							<div class=" self-center text-xs text-gray-500">
								{$i18n.t('{{count}} of {{total}} accessible', {
									count: preview.models.items.length,
									total: preview.models.total
								})}
							</div>
						</div>
					{/if}
				{/if}
			</div>
		</div>

		<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('Knowledge')}</div>

			<div class="flex flex-col w-full">
				{#if preview.knowledge.items.length === 0}
					<div class="flex w-full justify-between my-1">
						<div class=" self-center text-xs text-gray-500">
							{$i18n.t('No knowledge bases accessible')}
						</div>
					</div>
				{:else}
					{#each preview.knowledge.items as kb}
						<div class="flex w-full justify-between my-1">
							<div class=" self-center text-xs font-medium">{kb.name}</div>
						</div>
					{/each}

					{#if preview.knowledge.total > preview.knowledge.items.length}
						<div class="flex w-full justify-between my-1">
							<div class=" self-center text-xs text-gray-500">
								{$i18n.t('{{count}} of {{total}} accessible', {
									count: preview.knowledge.items.length,
									total: preview.knowledge.total
								})}
							</div>
						</div>
					{/if}
				{/if}
			</div>
		</div>

		<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('Tools')}</div>

			<div class="flex flex-col w-full">
				{#if preview.tools.items.length === 0}
					<div class="flex w-full justify-between my-1">
						<div class=" self-center text-xs text-gray-500">
							{$i18n.t('No tools accessible')}
						</div>
					</div>
				{:else}
					{#each preview.tools.items as tool}
						<div class="flex w-full justify-between my-1">
							<div class=" self-center text-xs font-medium">{tool.name}</div>
						</div>
					{/each}

					{#if preview.tools.total > preview.tools.items.length}
						<div class="flex w-full justify-between my-1">
							<div class=" self-center text-xs text-gray-500">
								{$i18n.t('{{count}} of {{total}} accessible', {
									count: preview.tools.items.length,
									total: preview.tools.total
								})}
							</div>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	{/if}
</div>
