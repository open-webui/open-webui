<script>
	export let exchangeRateInfo = null;
	export let plnConversionAvailable = true;
</script>

{#if exchangeRateInfo}
	<div class="mb-4 text-xs text-gray-600 dark:text-gray-400 flex items-center justify-between bg-gray-50 dark:bg-gray-800 p-2 rounded">
		<span>
			Exchange rate: 1 USD = {exchangeRateInfo.usd_pln.toFixed(4)} PLN 
			(NBP rate from {exchangeRateInfo.effective_date})
		</span>
	</div>
{:else if plnConversionAvailable === false}
	<div class="mb-4 text-xs text-orange-600 dark:text-orange-400 flex items-center bg-orange-50 dark:bg-orange-900/20 p-2 rounded">
		<svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
			<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
		</svg>
		<span>PLN conversion temporarily unavailable - showing USD only</span>
	</div>
{/if}