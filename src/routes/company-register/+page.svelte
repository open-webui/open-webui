<script lang="ts">
	import ProgressIndicator from '$lib/components/company-register/ProgressIndicator.svelte';
	import Step1Email from '$lib/components/company-register/Step1Email.svelte';
	import Step2Personal from '$lib/components/company-register/Step2Personal.svelte';
	import Step3Company from '$lib/components/company-register/Step3Company.svelte';
	import Step4Invite from '$lib/components/company-register/Step4Invite.svelte';

	let step = 1;

	const goNext = () => {
		if (step < 4) step += 1;
	};

	const goBack = () => {
		if (step > 1) step -= 1;
	};
</script>

<div
class="flex flex-col justify-between w-full h-screen max-h-[100dvh] text-white relative dark:bg-customGray-900"
>
<div></div>
	

	
		{#if step === 1}
			<Step1Email on:next={goNext} />
		{:else if step === 2}
			<Step2Personal on:next={goNext} on:back={goBack} />
		{:else if step === 3}
			<Step3Company on:next={goNext} on:back={goBack} />
		{:else if step === 4}
			<Step4Invite on:back={goBack} />
		{/if}
	
    <ProgressIndicator {step} />
</div>