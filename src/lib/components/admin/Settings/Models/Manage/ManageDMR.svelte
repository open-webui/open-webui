<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, models, user, config, settings } from '$lib/stores';

	import {
		getDMRVersion,
		getDMRModels
	} from '$lib/apis/dmr';
	import { getModels } from '$lib/apis';

	import Spinner from '$lib/components/common/Spinner.svelte';

	let loading = true;
	let dmrModels = [];
	let dmrVersion = '';

	const getModelsAsync = async () => {
		const models = await getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
		);
		return models;
	};

	const getDMRModelsAsync = async () => {
		dmrModels = await getDMRModels(localStorage.token);
	};

	const getDMRVersionAsync = async () => {
		dmrVersion = await getDMRVersion(localStorage.token);
	};

	onMount(async () => {
		loading = true;
		
		await Promise.all([
			getDMRModelsAsync(),
			getDMRVersionAsync()
		]);
		
		loading = false;
	});
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<div class="space-y-3 pr-1.5 overflow-y-scroll scrollbar-hidden h-fit max-h-80">
		{#if loading}
			<div class="flex justify-center">
				<div class="py-5">
					<Spinner />
				</div>
			</div>
		{:else}
			<!-- DMR Version -->
			<div class="space-y-2">
				<div class="flex items-center space-x-2">
					<div class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
						{$i18n.t('Version')}
					</div>
				</div>
				<div class="text-sm text-gray-700 dark:text-gray-300">
					{dmrVersion || $i18n.t('Unknown')}
				</div>
			</div>

			<!-- Available Models -->
			<div class="space-y-2">
				<div class="flex items-center space-x-2">
					<div class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
						{$i18n.t('Models')} ({dmrModels.length})
					</div>
				</div>

				{#if dmrModels.length === 0}
					<div class="text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('No models found')}
					</div>
				{:else}
					<div class="space-y-1">
						{#each dmrModels as model}
							<div class="flex items-center justify-between p-2 rounded-lg border border-gray-200 dark:border-gray-700">
								<div class="flex flex-col">
									<div class="text-sm font-medium text-gray-800 dark:text-gray-200">
										{model.name || model.id}
									</div>
									{#if model.description}
										<div class="text-xs text-gray-500 dark:text-gray-400">
											{model.description}
										</div>
									{/if}
								</div>
								{#if model.size}
									<div class="text-xs text-gray-500 dark:text-gray-400">
										{model.size}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Info Note -->
			<div class="text-xs text-gray-500 dark:text-gray-400 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
				<div class="font-medium mb-1">{$i18n.t('Note')}</div>
				<div>
					{$i18n.t('DMR does not support model management operations. Models are managed by the Docker Model Runner service directly.')}
				</div>
			</div>
		{/if}
	</div>
</div> 