<script lang="ts">
	const translations = {
		'en-GB': {
			welcome: 'Welcome to CANChat',
			message: 'Your account is pending activation.',
			action: 'For access, please reach out to our team here:',
			team: 'Intake Team',
			button: 'Check Again',
			signout: 'Sign Out'
		},
		'fr-CA': {
			welcome: 'Bienvenue sur CANChat',
			message: "Votre compte est en attente d'activation.",
			action: 'Pour accéder, veuillez contacter notre équipe ici :',
			team: "Équipe d'intégration",
			button: 'Vérifiez à nouveau',
			signout: 'Déconnexion'
		}
	};

	let currentLang = 'en-GB';
	$: currentLangDisplay = currentLang === 'en-GB' ? 'Français' : 'English';
	$: currentTranslation = translations[currentLang];

	const toggleLanguage = () => {
		currentLang = currentLang === 'en-GB' ? 'fr-CA' : 'en-GB';
	};
</script>

<div class="fixed w-full h-full flex z-[999]">
	<div
		class="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center"
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
					{currentTranslation.action}
					<br />
					<a
						href="mailto:dsaiclientengagement.sdiaclientmobilisation@ssc-spc.gc.ca"
						class="underline"
					>
						{currentTranslation.team}
					</a>
				</div>
				<div class="mt-6 mx-auto relative group w-fit">
					<button
						class="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 text-gray-700 transition font-medium text-md"
						on:click={async () => {
							location.href = '/';
						}}
					>
						{currentTranslation.button}
					</button>
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
			</div>
		</div>
	</div>
</div>
