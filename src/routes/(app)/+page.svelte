<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { getUserType } from '$lib/utils';
	import { getWorkflowState } from '$lib/apis/workflow';

	onMount(async () => {
		if (!$user) {
			goto('/auth');
			return;
		}

		const userType = await getUserType($user);

		// Route based on user type
		if (userType === 'parent') {
			goto('/parent');
			return;
		}

		if (userType === 'child') {
			goto('/');
			return;
		}

		if (userType === 'admin') {
			goto('/');
			return;
		}

		// For interviewees, use workflow state
		if (userType === 'interviewee') {
			const assignmentCompleted = localStorage.getItem('assignmentCompleted') === 'true';
			if (assignmentCompleted) {
				goto('/completion');
				return;
			}

			// Get workflow state from backend
			try {
				const workflowState = await getWorkflowState(localStorage.token);
				goto(workflowState.next_route || '/assignment-instructions');
			} catch (error) {
				goto('/assignment-instructions');
			}
			return;
		}

		// Default fallback
		goto('/assignment-instructions');
	});
</script>
