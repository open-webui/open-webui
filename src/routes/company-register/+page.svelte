<script lang="ts">
	import ProgressIndicator from '$lib/components/company-register/ProgressIndicator.svelte';
	import Step1Email from '$lib/components/company-register/Step1Email.svelte';
	import Step2Personal from '$lib/components/company-register/Step2Personal.svelte';
	import Step3Company from '$lib/components/company-register/Step3Company.svelte';
	import Step4Invite from '$lib/components/company-register/Step4Invite.svelte';
	import { completeRegistration } from '$lib/apis/auths';
	import { COMPANY_SIZE_OPTIONS, INDUSTRY_OPTIONS, TEAM_FUNCTION_OPTIONS } from '$lib/constants';
	import {
		WEBUI_NAME,
		config,
		user,
		socket,
		toastVisible,
		toastMessage,
		toastType,
		showToast
	} from '$lib/stores';
	import { getSessionUser, userSignIn } from '$lib/apis/auths';
	import { getBackendConfig } from '$lib/apis';

	let step = 1;

	let email = '';
	let first_name = '';
	let last_name = '';
	let registration_code = '';
	let password = '';
	let profile_image_url = '';
	let company_name = '';
	let company_size = COMPANY_SIZE_OPTIONS[0];
	let company_industry = INDUSTRY_OPTIONS[0];
	let company_team_function = TEAM_FUNCTION_OPTIONS[0];

	$:console.log(first_name, last_name, registration_code, password, profile_image_url, company_name, company_size, company_industry, company_team_function)

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
		}
	};

	async function goNext (event) {
		if (step === 1) {
			email = event.detail.email;
		}
		if (step === 3) {
			const user = await completeRegistration(
				first_name,
				last_name,
				registration_code,
				password,
				profile_image_url,
				company_name,
				company_size,
				company_industry,
				company_team_function
			);
			await setSessionUser(user);
		}
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
		<Step1Email on:next={goNext} {email} />
	{:else if step === 2}
		<Step2Personal
			on:next={goNext}
			on:back={goBack}
			{email}
			bind:first_name
			bind:last_name
			bind:registration_code
			bind:password
		/>
	{:else if step === 3}
		<Step3Company
			on:next={goNext}
			on:back={goBack}
			bind:profile_image_url
			bind:company_name
			bind:company_size
			bind:company_industry
			bind:company_team_function
		/>
	{:else if step === 4}
		<Step4Invite on:back={goBack} />
	{/if}

	<ProgressIndicator {step} />
</div>
