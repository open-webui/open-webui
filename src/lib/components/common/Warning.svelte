<script lang="ts">
	import ExclamationTriangle from '$lib/components/icons/ExclamationTriangle.svelte';
	export let text = '';
</script>

<div class="flex items-center text-xs text-yellow-600 dark:text-yellow-500">
	<ExclamationTriangle className="w-4 h-4 mr-1.5" />
	<p>{text}</p>
</div>