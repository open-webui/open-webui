<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getWorkflowById } from '$lib/apis/workflows';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import WorkflowEditor from '$lib/components/workspace/Workflows/WorkflowEditor.svelte';

	const i18n = getContext('i18n');

	let workflow = null;
	let mounted = false;

	onMount(async () => {
		// Get workflow ID from URL params
		const id = $page.url.searchParams.get('id');
		
		if (id) {
			try {
				workflow = await getWorkflowById(localStorage.token, id);
			} catch (error) {
				toast.error($i18n.t('Failed to load workflow'));
				console.error('Error loading workflow:', error);
			}
		}
		
		mounted = true;
	});
</script>

{#if mounted}
	<WorkflowEditor {workflow} />
{:else}
	<div class="flex items-center justify-center py-12">
		<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
	</div>
{/if}