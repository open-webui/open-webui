<script lang="ts">
	import SuccessIcon from '../icons/SuccessIcon.svelte';
	export let step = 1;

	const steps = [
		'Account creation',
		'Verify mail',
		'Personal information',
		'Create company profile',
		'Invite team members'
	];
	let container;
	$: scrollToStep(step); // reactive call when step changes

	function scrollToStep(step) {
		if (!container) return;

		const items = container.querySelectorAll('.step-item');
		const current = items[step - 1];
		if (current) {
			// Scroll smoothly to the current step
			container.scrollTo({
				left: current.offsetLeft - 16, // Optional padding
				behavior: 'smooth'
			});
		}
	}
</script>

<div bind:this={container} class="flex mb-7 md:mx-auto overflow-x-auto">
	{#each steps as s, index}
		<div class="step-item pb-2.5 border-b font-medium {index + 1 <= step ? 'border-customBlue-500' : 'border-customGray-700'}">
			<div
				class="whitespace-nowrap w-fit {index + 1 < steps.length
					? 'border-r'
					: ''}  border-customGray-700 flex items-center text-xs px-2.5 {index + 1 <= step
					? 'text-lightGray-100 dark:text-customGray-300'
					: 'text-lightGray-100/50 dark:text-customGray-300/50'}"
			>	
				{#if index + 1 < step}
					<SuccessIcon className="size-3 mr-1"/>
				{:else}
					{index + 1}
				{/if}
				{s}
			</div>
		</div>
	{/each}
</div>
