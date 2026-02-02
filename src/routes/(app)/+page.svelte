<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { getUserType } from '$lib/utils';
	import { getWorkflowState } from '$lib/apis/workflow';
	import { getChildProfiles } from '$lib/apis/child-profiles';
	import Chat from '$lib/components/chat/Chat.svelte';

	let showChat = false;

	onMount(async () => {
		if (!$user) {
			goto('/auth');
			return;
		}

		const userType = await getUserType($user, [], {
			mayFetchWhitelist: $user?.role === 'admin'
		});

		// Route based on user type
		if (userType === 'parent') {
			try {
				const profiles = await getChildProfiles(localStorage.token);
				if (profiles && profiles.length > 0) {
					showChat = true;
					return;
				}
			} catch (e) {
				// On error, send to /parent to add children
			}
			goto('/parent');
			return;
		}

		if (userType === 'child') {
			showChat = true;
			return;
		}

		if (userType === 'admin') {
			showChat = true;
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

{#if showChat}
	<Chat />
{/if}
