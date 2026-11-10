<script lang="ts">
	import { getPageContext } from '$lib/utils/page';
	const { goto } = getPageContext();

	import { toast } from 'svelte-sonner';

	import { onMount, onDestroy } from 'svelte';

	export let id = '';
	import { user, config } from '$lib/stores';
	import { getAutomationById, type AutomationResponse } from '$lib/apis/automations';

	import AutomationEditor from '$lib/components/automations/AutomationEditor.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let automation: AutomationResponse | null = null;
	let loaded = false;
	let ready = false;
	let loadingId = '';

	$: automationId = id ?? '';
	$: if (ready && automationId !== loadingId) {
		loadingId = automationId;
		void loadAutomation(automationId);
	}

	onMount(async () => {
		if (
			!($config?.features as any)?.enable_automations ||
			($user?.role !== 'admin' && !($user?.permissions?.features?.automations ?? false))
		) {
			goto('/');
			return;
		}

		ready = true;
	});
	onDestroy(() => {
		ready = false;
	});
	async function loadAutomation(id: string) {
		loaded = false;
		if (id) {
			const res = await getAutomationById(localStorage.token, id).catch((error) => {
				if (ready && loadingId === id) toast.error(`${error}`);
				return null;
			});
			if (!ready || loadingId !== id) return;

			if (res) {
				automation = res;
				loaded = true;
			} else {
				goto('/automations');
			}
		} else {
			goto('/automations');
		}
	}
</script>

{#if loaded && automation}
	{#key automation.id}<AutomationEditor {automation} />{/key}
{:else}
	<div class="flex h-full w-full items-center justify-center">
		<Spinner className="size-5" />
	</div>
{/if}
