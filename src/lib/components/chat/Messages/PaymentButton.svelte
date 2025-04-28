<script lang="ts">
	export let label = 'Charge your account';
	export let webPaymentUrl = 'https://www.aibrary.dev/chat/payment?chat=true';
	let loading = false;

	async function initiatePayment() {
		try {
			loading = true;

			// Check if Digital Goods API is available
			if (navigator.digitalGoods && navigator.digitalGoods.getService) {
				const digitalGoods = await navigator.digitalGoods.getService('play');
				const items = await digitalGoods.listPurchasableItems();
				const sku = items[0]?.itemId;

				if (!sku) {
					alert('No in-app products available.');
					return;
				}

				const paymentRequest = new PaymentRequest(
					[
						{
							supportedMethods: 'https://play.google.com/billing',
							data: { sku }
						}
					],
					{
						total: {
							label: 'Credit Pack',
							amount: { currency: 'USD', value: '4.99' }
						}
					}
				);

				const paymentResponse = await paymentRequest.show();
				await paymentResponse.complete('success');

				alert('Payment successful via Google Play! 🎉');
				location.reload();
			} else {
				// Fallback for regular web users
				window.location.href = webPaymentUrl;
			}
		} catch (err) {
			console.error('Payment failed:', err);
			alert('Payment failed. Please try again.');
		} finally {
			loading = false;
		}
	}
</script>

<button
	on:click={initiatePayment}
	class="text-blue-600 dark:text-blue-400 underline hover:text-blue-800 dark:hover:text-blue-500 text-sm text-left disabled:opacity-50"
	disabled={loading}
>
	{#if loading}
		Loading...
	{:else}
		{label}
	{/if}
</button>
