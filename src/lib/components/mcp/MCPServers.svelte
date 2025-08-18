<script lang="ts">
	import { user } from '$lib/stores';
	import MCPServerManager from './MCPServerManager.svelte';
</script>

<div class="w-full">
	{#if $user}
		<MCPServerManager isAdmin={true} />
	{:else}
		<div class="flex items-center justify-center h-32">
			<div class="text-gray-500">Loading...</div>
		</div>
	{/if}
</div>