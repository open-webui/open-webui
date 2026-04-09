<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';

	import { page } from '$app/stores';
	import { user, showSidebar } from '$lib/stores';
	import { getAutomationById } from '$lib/apis/automations';

	import AutomationEditor from '$lib/components/automations/AutomationEditor.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let automation = null;
	let loaded = false;

	$: automationId = $page.params.id;

	onMount(async () => {
		if ($user?.role !== 'admin' && !($user?.permissions?.features?.automations ?? false)) {
			goto('/');
			return;
		}

		if (automationId) {
			const res = await getAutomationById(localStorage.token, automationId).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				automation = res;
				loaded = true;
			} else {
				goto('/automations');
			}
		} else {
			goto('/automations');
		}
	});
</script>

{#if loaded && automation}
	<AutomationEditor {automation} />
{:else}
	<div
		class="w-full h-screen max-h-[100dvh] flex justify-center items-center transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''}"
	>
		<Spinner className="size-5" />
	</div>
{/if}
