<script lang="ts">
	export let integrations: { provider: string; connected: boolean }[] = [];

	const providerIcons: Record<string, string> = {
		google: 'G',
		slack: 'S',
		notion: 'N'
	};
</script>

<div class="p-5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Integraciones</h3>

	<div class="space-y-2">
		{#each integrations as integration}
			<div class="flex items-center justify-between py-1.5">
				<div class="flex items-center gap-2">
					<span class="text-lg">{providerIcons[integration.provider] || '?'}</span>
					<span class="text-sm text-gray-900 dark:text-white capitalize">
						{integration.provider}
					</span>
				</div>
				<span
					class="text-xs px-2 py-0.5 rounded-full {integration.connected
						? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
						: 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'}"
				>
					{integration.connected ? 'Conectado' : 'Desconectado'}
				</span>
			</div>
		{/each}
		{#if integrations.length === 0}
			<p class="text-sm text-gray-400">Sin integraciones configuradas.</p>
		{/if}
	</div>
</div>
