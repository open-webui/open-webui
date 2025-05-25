<script lang="ts">
	import ProgressIndicator from '$lib/components/company-register/ProgressIndicator.svelte';
	import Step1Email from '$lib/components/company-register/Step1Email.svelte';
	import Step2Verify from '$lib/components/company-register/Step2Verify.svelte';
	import Step3Personal from '$lib/components/company-register/Step3Personal.svelte';
	import Step4Company from '$lib/components/company-register/Step4Company.svelte';
	import Step5Invite from '$lib/components/company-register/Step5Invite.svelte';
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
		showToast,
		company,
		companyConfig
	} from '$lib/stores';
	import { getSessionUser, userSignIn } from '$lib/apis/auths';
	import { getBackendConfig } from '$lib/apis';
	import { generateInitialsImage } from '$lib/utils';
	import CustomToast from '$lib/components/common/CustomToast.svelte';
	import { toast } from 'svelte-sonner';
	import { getCompanyDetails, getCompanyConfig } from '$lib/apis/auths';

	let step = 1;

	let email = '';
	let first_name = '';
	let last_name = '';
	let registration_code = '';
	let password = '';
	let profile_image_url = '';
	let company_name = '';
	let company_size = '';
	let company_industry = '';
	let company_team_function = '';
	let company_profile_image_url = '';

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

	async function goNext(event) {
		if (step === 1) {
			email = event.detail.email;
		}
		
		if (step === 4) {
			if(!company_name || !company_size || !company_industry || !company_team_function) {
				showToast('error', "To continue, please provide full information about your company and team.")
				return;
			}
			const user = await completeRegistration(
				first_name,
				last_name,
				registration_code?.trim(),
				password,
				profile_image_url ? profile_image_url : generateInitialsImage(first_name),
				company_name,
				company_size,
				company_industry,
				company_team_function,
				company_profile_image_url ? company_profile_image_url : generateInitialsImage(company_name)
			).catch(error => showToast('error', error));
			console.log(user)
			if(user) {
				await setSessionUser(user);
				step = step + 1;
				const [companyInfo, companyConfigInfo] = await Promise.all([
					getCompanyDetails(user.token).catch((error) => {
						toast.error(`${error}`);
						return null;
					}),
					getCompanyConfig(user.token).catch((error) => {
						toast.error(`${error}`);
						return null;
					})
				]);

				if (companyInfo) {
					company.set(companyInfo);
				}

				if (companyConfigInfo) {
					console.log(companyConfigInfo);
					companyConfig.set(companyConfigInfo);
				}
			}
		}
		if (step < 4) step += 1;	
	}

	const goBack = () => {
		if (step > 1) step -= 1;
	};
</script>

<CustomToast message={$toastMessage} type={$toastType} visible={$toastVisible} />
<div
	class="flex flex-col justify-between w-full h-screen max-h-[100dvh]  px-4 text-white relative bg-lightGray-300 dark:bg-customGray-900"
>
	<div></div>
	{#if step === 1}
		<Step1Email on:next={goNext} bind:email />
	{:else if step === 2}
		<Step2Verify {email} on:next={goNext} on:back={goBack} bind:registration_code/>
	{:else if step === 3}
		<Step3Personal
			on:next={goNext}
			on:back={goBack}
			bind:profile_image_url
			bind:first_name
			bind:last_name
			bind:password
		/>
	{:else if step === 4}
		<Step4Company
			on:next={goNext}
			on:back={goBack}
			bind:company_profile_image_url
			bind:company_name
			bind:company_size
			bind:company_industry
			bind:company_team_function
		/>
	{:else if step === 5}
		<Step5Invite on:back={goBack} />
	{/if}

	<ProgressIndicator {step} />
</div>
