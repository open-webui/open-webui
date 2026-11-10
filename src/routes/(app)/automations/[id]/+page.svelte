<script lang="ts">
	import Automation from '$lib/components/automations/Automation.svelte';
	import { page } from '$app/stores';
</script>

<Automation id={$page.params.id} />
