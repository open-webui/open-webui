<script lang="ts">
	import { onMount } from 'svelte';
	import WorkflowEditor from '$lib/components/workspace/Workflows/WorkflowEditor.svelte';

	let workflow = null;

	onMount(() => {
		// Check if we're cloning a workflow
		if (sessionStorage.workflow) {
			try {
				workflow = JSON.parse(sessionStorage.workflow);
				// Clear session storage
				sessionStorage.removeItem('workflow');
			} catch (error) {
				console.error('Error parsing workflow from session storage:', error);
			}
		}
	});
</script>

<WorkflowEditor {workflow} />
