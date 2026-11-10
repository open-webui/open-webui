<script lang="ts">
	import { getPageContext } from '$lib/utils/page';
	export let title: string;
	const { tab } = getPageContext();
	$: tab?.setTitle(title);
</script>

<svelte:head
	>{#if !tab}<title>{title}</title>{/if}</svelte:head
>
