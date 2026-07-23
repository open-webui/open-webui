<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import { page } from '$app/stores';
	import { user, config } from '$lib/stores';
	import { getAutomationById, type AutomationResponse } from '$lib/apis/automations';

	import AutomationEditor from '$lib/components/automations/AutomationEditor.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let automation: AutomationResponse | null = null;
	let loaded = false;

	$: automationId = $page.params.id;

	onMount(async () => {
		if (
			!($config?.features as any)?.enable_automations ||
			($user?.role !== 'admin' && !($user?.permissions?.features?.automations ?? false))
		) {
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
	<div class="flex h-full w-full items-center justify-center">
		<Spinner className="size-5" />
	</div>
{/if}
