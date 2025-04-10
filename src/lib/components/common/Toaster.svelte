<script lang="ts">
	import { Toaster } from 'svelte-sonner';
	import { onDestroy } from 'svelte';
	import { ariaMessage, theme } from '$lib/stores';

	let message = '';

	const unsubscribe = ariaMessage.subscribe((value) => {
		message = value;
	});

	onDestroy(() => {
		unsubscribe();
	});
</script>

<Toaster
	theme={$theme.includes('dark')
		? 'dark'
		: $theme === 'system'
			? window.matchMedia('(prefers-color-scheme: dark)').matches
				? 'dark'
				: 'light'
			: 'light'}
	richColors
	position="top-right"
	toastOptions={{
		classes: {
			error: '!bg-white !text-red-600 !border-red-600',
			success: '!bg-white !text-green-700 !border-green-700',
			warning: '!bg-white !text-yellow-700 !border-yellow-700',
			info: '!bg-white !text-blue-700 !border-blue-700'
		}
	}}
/>
<div aria-live="assertive" class="sr-only">{message}</div>
