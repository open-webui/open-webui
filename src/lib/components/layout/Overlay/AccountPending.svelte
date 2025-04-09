<script lang="ts">
	import { getUserRole } from '$lib/apis/users';
	import { onMount } from 'svelte';

	const translations = {
		'en-GB': {
			welcome: 'Welcome to CANChat',
			message: 'Please wait while we activate your account.',
			message2: '(approx. 10 minutes)',
			message3: 'Issues with your activation?',
			action: 'Please reach out to our team here',
			signout: 'Sign Out'
		},
		'fr-CA': {
			welcome: 'Bienvenue sur CANChat',
			message: 'Veuillez patienter pendant que nous activons votre compte.',
			message2: '(environ 10 minutes)',
			message3: 'Des problèmes avec votre activation?',
			action: 'Veuillez contacter notre équipe ici',
			signout: 'Déconnexion'
		}
	};

	let currentLang = 'en-GB';
	$: currentLangDisplay = currentLang === 'en-GB' ? 'Français' : 'English';
	$: currentTranslation = translations[currentLang];

	const toggleLanguage = () => {
		currentLang = currentLang === 'en-GB' ? 'fr-CA' : 'en-GB';
	};

	onMount(() => {
		const checkUserRole = async () => {
			try {
				const role = await getUserRole(localStorage.token);
				if (role !== 'pending') {
					location.href = '/';
				}
			} catch (error) {
				console.error('Error checking user role:', error);
			}
		};

		const interval = setInterval(checkUserRole, 60000);
		checkUserRole();

		return () => clearInterval(interval);
	});
</script>

<div class="fixed w-full h-full flex z-[999]">
	<div
		class="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center"
		style="-webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);"
	>
		<div class="m-auto pb-10 flex flex-col justify-center">
			<div class="max-w-lg">
				<button
					class="text-sm text-center w-full mb-5 text-gray-700 dark:text-gray-200 underline"
					on:click={toggleLanguage}
				>
					{currentLangDisplay}
				</button>
				<div class="text-center dark:text-white text-2xl font-medium z-50">
					{currentTranslation.welcome}
				</div>
				<div class="mt-6 text-center text-lg dark:text-gray-200 w-full">
					{currentTranslation.message}
					<br />
					{currentTranslation.message2}
					<br />
					<br />
					{currentTranslation.message3}
					<br />
					<a
						href="mailto:dsaiclientengagement.sdiaclientmobilisation@ssc-spc.gc.ca"
						class="underline"
					>
						{currentTranslation.action}
					</a>
				</div>
				{#if location.hostname === 'localhost'}
					<div class="mt-6 mx-auto relative group w-fit">
						<button
							class="text-xs text-center w-full mt-3 text-gray-700 dark:text-gray-200 underline"
							on:click={async () => {
								localStorage.removeItem('token');
								location.href = '/auth';
							}}
						>
							{currentTranslation.signout}
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
