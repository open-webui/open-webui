<script lang="ts">
	import { dismissedBanners } from '$lib/stores';

	export let dismissable = true;
	export let content = '';
	export let type = 'info';
	export let dismissed = false;

	const classNames: Record<string, string> = {
		info: 'bg-blue-500',
		success: 'bg-green-500',
		warning: 'bg-yellow-500',
		error: 'bg-red-500'
	};

	const dismiss = () => {
		dismissed = true;
		dismissedBanners.update((banners) => banners.concat(content));
		localStorage.setItem('dismissedBanners', JSON.stringify($dismissedBanners));
	};
</script>

{#if !dismissed}
	<div
		class=" top-0 left-0 right-0 p-2 flex justify-center items-center relative {classNames[type] ??
			classNames['info']}"
	>
		<span class="mx-auto text-center">{content}</span>
		{#if dismissable}
			<button on:click={dismiss} class="absolute right-2 text-white">&times;</button>
		{/if}
	</div>
{/if}
