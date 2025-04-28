<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';
	import PaymentButton from './PaymentButton.svelte';

	export let content = '';
	const isPaymentError = typeof content === 'string' && content.includes('402');
</script>

<div class="flex flex-col my-2 gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-lg">
	<div class="flex items-start gap-2">
		<Info className="size-5 text-red-700 dark:text-red-400" />
		<div class="text-sm">{typeof content === 'string' ? content : JSON.stringify(content)}</div>
	</div>

	{#if isPaymentError}
		<PaymentButton />
	{/if}
</div>
