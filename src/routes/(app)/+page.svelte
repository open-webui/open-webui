<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import OnboardingWizard from '$lib/components/onboarding/OnboardingWizard.svelte';
	import { isOnboardingCompleted } from '$lib/stores/onboarding';
	import { page } from '$app/stores';

	let showOnboarding = false;

	onMount(() => {
		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || 'An unknown error occurred.');
		}
		showOnboarding = !$isOnboardingCompleted;
	});
</script>

{#if showOnboarding}
	<OnboardingWizard
		onComplete={() => {
			showOnboarding = false;
		}}
	/>
{/if}

<Chat />
