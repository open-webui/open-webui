<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	onMount(() => {
		if (!$page.params.id) {
			goto('/');
		}
	});
</script>

<svelte:head>
	<title>UOH-AI</title>
</svelte:head>

<div class="container mx-auto">
	<h1 class="text-3xl font-bold mb-4">{$i18n.t('Page ID')}: {$page.params.id}</h1>
	<p>{$i18n.t('This is the page for ID')}: {$page.params.id}</p>
</div>
