<script>
	import { goto } from '$app/navigation';
	import { userSignIn, userSignUp } from '$lib/apis/auths';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { config, user } from '$lib/stores';
	import { onMount } from 'svelte';
	import toast from 'svelte-french-toast';
	import Typewriter from 'svelte-typewriter'
	

	let loaded = false;
	let mode = 'signin';

	let name = '';
	let email = '';
	let password = '';

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success(`Du bist nun eingeloggt`);
			localStorage.token = sessionUser.token;
			await user.set(sessionUser);
			goto('/');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(error);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password).catch((error) => {
			toast.error(error);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	onMount(async () => {
		if ($user !== undefined) {
			await goto('/');
		}
		loaded = true;
		toast(
	"Seit dem letzten Update muss ein neuer Account erstellt werden. \n\n In Zukunft ist das nicht mehr notwendig.",
	{
		duration: 5000,
		icon: '⚠️'
	}
);
  });

</script>

{#if loaded}
	<div class="fixed m-10 z-50">
		<div class="flex space-x-2">
			<div class=" self-center">
				<img src="/fi-ts_log2.png" class=" w-40" />
			</div>
		</div>
	</div>

	<div class=" bg-white min-h-screen w-full flex justify-center font-mona">
	<div class="hidden 2xl:block absolute top-60 left-40 w-72 h-72 bg-fits-blue rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob"></div>
	<div class="hidden 2xl:block absolute bottom-80 right-60 w-72 h-72 bg-red-500 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-2000"></div>
	<!-- <div class="hidden 2xl:block absolute top-20 right-40 w-72 h-72 bg-gray-500 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-4000"></div>
		<div class="hidden lg:flex lg:flex-1 px-10 md:px-16 w-full bg-yellow-50 justify-center">
			<div class=" my-auto pb-16 text-left">
				<div>
					<div class=" font-bold text-yellow-600 text-4xl">
						Get up and running with <br />large language models, locally.
					</div>

					<div class="mt-2 text-yellow-600 text-xl">
						Run Llama 2, Code Llama, and other models. Customize and create your own.
					</div>
				</div>
			</div>
		</div> -->

		<div class="w-full max-w-lg px-10 md:px-16 bg-white min-h-screen flex flex-col">

			<div class=" my-auto pb-10 w-full">
				<form
					class=" flex flex-col justify-center"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class=" text-xl md:text-2xl font-bold">
						{mode === 'signin' ? 'Anmelden' : 'Registrieren'} <Typewriter interval={50}>für die FI-TS AI</Typewriter>
					</div>

					<div class="flex flex-col mt-4">
						{#if mode === 'signup'}
							<div>
								<div class=" text-sm font-semibold text-left mb-1">Name</div>
								<input
									bind:value={name}
									type="text"
									class=" border px-4 py-2.5 rounded-2xl w-full text-sm"
									autocomplete="name"
									placeholder="Gib deinen vollständigen Namen ein"
									required
								/>
							</div>

							<hr class=" my-3" />
						{/if}

						<div class="mb-2">
							<div class=" text-sm font-semibold text-left mb-1">Email</div>
							<input
								bind:value={email}
								type="email"
								class=" border px-4 py-2.5 rounded-2xl w-full text-sm"
								autocomplete="email"
								placeholder="Gib deine E-Mail ein"
								required
							/>
						</div>

						<div>
							<div class=" text-sm font-semibold text-left mb-1">Passwort</div>
							<input
								bind:value={password}
								type="password"
								class=" border px-4 py-2.5 rounded-2xl w-full text-sm"
								placeholder="Gib dein Passwort ein"
								autocomplete="current-password"
								required
							/>
						</div>
					</div>

					<div class="mt-5">
						<button
						class="relative inline-flex items-center px-12 py-3 text-lg font-medium text-gray-900 bg-gray-900 hover:bg-gray-800 w-full rounded-full text-white font-semibold text-sm transition group"
						type="submit"
					>
						<span class="relative z-10 mx-auto">{mode === 'signin' ? 'Anmelden' : 'Account erstellen'}</span>
						<span class="absolute right-0 flex items-center justify-end w-10 h-full transition-transform transform translate-x-full group-hover:translate-x-0 duration-300 ease">
							<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
						</span>
					</button>

						<div class=" mt-4 text-sm text-center">
							{mode === 'signin' ? `Noch keinen Account?` : `Du hast schon einen Account?`}

							<button
								class=" font-medium underline"
								type="button"
								on:click={() => {
									if (mode === 'signin') {
										mode = 'signup';
									} else {
										mode = 'signin';
									}
								}}
							>
								{mode === 'signin' ? `Account erstellen` : `Anmelden`}
							</button>
					</div>
				</form>
			</div>
		</div>
	</div>
{/if}

<style>
	.font-mona {
		font-family: 'Mona Sans';
	}
</style>
