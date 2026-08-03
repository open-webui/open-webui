<script>
	import { toast } from 'svelte-sonner';

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	let loaded = false;
	let passwordVisible = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let name = '';
	let email = '';
	let password = '';

	let ldapUsername = '';

	const showAuthError = (error, message) => {
		console.error(error);
		toast.error(message);
	};

	const querystringValue = (key) => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success('Connexion réussie.');
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			showAuthError(
				error,
				'Connexion impossible. Vérifiez votre adresse e-mail et votre mot de passe.'
			);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				showAuthError(
					error,
					'Création du compte impossible. Vérifiez les informations saisies.'
				);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			showAuthError(
				error,
				'Connexion LDAP impossible. Vérifiez votre identifiant et votre mot de passe.'
			);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const forgotPasswordHandler = () => {
		toast.info(
			`Pour réinitialiser votre mot de passe, contactez l'administrateur de votre espace.`
		);
	};

	const checkOauthCallback = async () => {
		if (!$page.url.hash) {
			return;
		}
		const hash = $page.url.hash.substring(1);
		if (!hash) {
			return;
		}
		const params = new URLSearchParams(hash);
		const token = params.get('token');
		if (!token) {
			return;
		}
		const sessionUser = await getSessionUser(token).catch((error) => {
			showAuthError(error, 'Connexion impossible. Veuillez réessayer.');
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	let onboarding = false;

	onMount(async () => {
		if ($user !== undefined) {
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
		await checkOauthCallback();

		loaded = true;

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="auth-page" lang="fr">
	<div class="auth-drag-region drag-region" aria-hidden="true"></div>

	{#if loaded}
		<header class="auth-header">
			<img
				src="{WEBUI_BASE_URL}/assets/oreegami/oreegami-logo.png"
				alt="Oreegami"
				class="oreegami-logo"
			/>
		</header>

		<main class="auth-main">
			<section class="auth-card" aria-labelledby="auth-title">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class="auto-signin">
						<img
							src="{WEBUI_BASE_URL}/assets/oreegami/suricate.jpeg"
							alt=""
							class="auto-signin-mascot"
						/>
						<div class="auto-signin-status" role="status">
							<span id="auth-title">Connexion à {$WEBUI_NAME} en cours…</span>
							<Spinner />
						</div>
					</div>
				{:else}
					<div class="auth-heading">
						<h1 id="auth-title">
							{#if $config?.onboarding ?? false}
								Configurez votre espace
							{:else if mode === 'ldap'}
								Connectez-vous avec LDAP
							{:else if mode === 'signin'}
								Connectez-vous à IA Compagnon
							{:else}
								Créez un compte IA Compagnon
							{/if}
						</h1>
						<p>Votre compagnon d'apprentissage propulsé par l'IA.</p>

						{#if $config?.onboarding ?? false}
							<div class="onboarding-notice">
								ⓘ {$WEBUI_NAME} ne se connecte à aucun service externe et vos données
								restent en sécurité sur votre serveur local.
							</div>
						{/if}
					</div>

					<div class="auth-body">
						<img
							src="{WEBUI_BASE_URL}/assets/oreegami/suricate.jpeg"
							alt="Suricate, la mascotte d'Oreegami"
							class="auth-mascot"
						/>

						<div class="auth-actions">
							<form
								class="auth-form"
								on:submit={(event) => {
									event.preventDefault();
									submitHandler();
								}}
							>
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
									{#if mode === 'signup'}
										<div class="auth-field">
											<label for="auth-name">Nom complet</label>
											<input
												id="auth-name"
												bind:value={name}
												type="text"
												class="auth-input"
												autocomplete="name"
												placeholder="Saisissez votre nom complet"
												required
											/>
										</div>
									{/if}

									{#if mode === 'ldap'}
										<div class="auth-field">
											<label for="auth-username">Identifiant</label>
											<input
												id="auth-username"
												bind:value={ldapUsername}
												type="text"
												class="auth-input"
												autocomplete="username"
												name="username"
												placeholder="Saisissez votre identifiant"
												required
											/>
										</div>
									{:else}
										<div class="auth-field">
											<label for="auth-email">Adresse e-mail</label>
											<input
												id="auth-email"
												bind:value={email}
												type="email"
												class="auth-input"
												autocomplete="email"
												name="email"
												placeholder="Saisissez votre adresse e-mail"
												required
											/>
										</div>
									{/if}

									<div class="auth-field">
										<label for="auth-password">Mot de passe</label>
										<div class="password-input">
											<input
												id="auth-password"
												value={password}
												type={passwordVisible ? 'text' : 'password'}
												class="auth-input"
												placeholder="Saisissez votre mot de passe"
												autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
												name="password"
												on:input={(event) => {
													password = event.currentTarget.value;
												}}
												required
											/>
											<button
												type="button"
												class="password-toggle"
												aria-label={passwordVisible
													? 'Masquer le mot de passe'
													: 'Afficher le mot de passe'}
												aria-pressed={passwordVisible}
												on:click={() => {
													passwordVisible = !passwordVisible;
												}}
											>
												{#if passwordVisible}
													<svg
														width="20"
														height="20"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.75"
														stroke-linecap="round"
														stroke-linejoin="round"
														aria-hidden="true"
													>
														<path
															d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
														/>
														<line x1="1" y1="1" x2="23" y2="23" />
													</svg>
												{:else}
													<svg
														width="20"
														height="20"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.75"
														stroke-linecap="round"
														stroke-linejoin="round"
														aria-hidden="true"
													>
														<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
														<circle cx="12" cy="12" r="3" />
													</svg>
												{/if}
											</button>
										</div>

										{#if mode === 'signin'}
											<button
												type="button"
												class="forgot-password"
												on:click={forgotPasswordHandler}
											>
												Mot de passe oublié&nbsp;?
											</button>
										{/if}
									</div>

									<button class="primary-button" type="submit">
										{#if mode === 'ldap'}
											Se connecter
										{:else if mode === 'signin'}
											Se connecter
										{:else if $config?.onboarding ?? false}
											Créer le compte administrateur IA Compagnon
										{:else}
											Créer mon compte IA Compagnon
										{/if}
									</button>
								{/if}
							</form>

							{#if $config?.features.enable_signup && !($config?.onboarding ?? false) && mode !== 'ldap'}
								<div class="mode-switch">
									<span>
										{mode === 'signin'
											? "Vous n'avez pas encore de compte ?"
											: 'Vous avez déjà un compte ?'}
									</span>
									<button
										type="button"
										on:click={() => {
											mode = mode === 'signin' ? 'signup' : 'signin';
										}}
									>
										{mode === 'signin' ? 'Créer un compte' : 'Se connecter'}
									</button>
								</div>
							{/if}

							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div class="oauth-separator" aria-hidden="true">
									<span></span>
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
										<strong>ou</strong>
									{/if}
									<span></span>
								</div>

								<div class="oauth-options">
									{#if $config?.oauth?.providers?.google}
										<button
											type="button"
											class="oauth-button"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 48 48"
												aria-hidden="true"
											>
												<path
													fill="#EA4335"
													d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
												/>
												<path
													fill="#4285F4"
													d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
												/>
												<path
													fill="#FBBC05"
													d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
												/>
												<path
													fill="#34A853"
													d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
												/>
											</svg>
											<span>Continuer avec Google</span>
										</button>
									{/if}

									{#if $config?.oauth?.providers?.microsoft}
										<button
											type="button"
											class="oauth-button"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 21 21"
												aria-hidden="true"
											>
												<rect x="1" y="1" width="9" height="9" fill="#f25022" />
												<rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
												<rect x="11" y="1" width="9" height="9" fill="#7fba00" />
												<rect x="11" y="11" width="9" height="9" fill="#ffb900" />
											</svg>
											<span>Continuer avec Microsoft</span>
										</button>
									{/if}

									{#if $config?.oauth?.providers?.github}
										<button
											type="button"
											class="oauth-button"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												aria-hidden="true"
											>
												<path
													fill="currentColor"
													d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
												/>
											</svg>
											<span>Continuer avec GitHub</span>
										</button>
									{/if}

									{#if $config?.oauth?.providers?.oidc}
										<button
											type="button"
											class="oauth-button"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												aria-hidden="true"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
												/>
											</svg>
											<span>
												Continuer avec {$config?.oauth?.providers?.oidc ?? 'SSO'}
											</span>
										</button>
									{/if}
								</div>
							{/if}

							{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
								<button
									class="ldap-switch"
									type="button"
									on:click={() => {
										if (mode === 'ldap') {
											mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
										} else {
											mode = 'ldap';
										}
									}}
								>
									{mode === 'ldap' ? "Continuer avec l'adresse e-mail" : 'Continuer avec LDAP'}
								</button>
							{/if}
						</div>
					</div>

					<div class="supporters">
						<span>Un projet soutenu par</span>
						<div class="supporter-logos">
							<img
								src="{WEBUI_BASE_URL}/assets/oreegami/logo-cfa.jpg"
								alt="Lauréat du programme Atlas — Inventer les CFA de demain"
								class="cfa-logo"
							/>
							<img
								src="{WEBUI_BASE_URL}/assets/oreegami/logo-afdas.png"
								alt="Afdas — Demain sera formation"
								class="afdas-logo"
							/>
						</div>
					</div>
				{/if}
			</section>
		</main>
	{/if}
</div>

<style>
	.auth-page {
		--oreegami-blue: #0000e6;
		--oreegami-ink: #0a0a1e;
		--oreegami-ink-50: #6b6b80;
		--oreegami-ink-30: #b5b5c2;
		--oreegami-ink-10: #e6e6ed;

		position: relative;
		display: flex;
		min-height: 100vh;
		min-height: 100dvh;
		flex-direction: column;
		overflow-x: hidden;
		background: #fff;
		color: var(--oreegami-ink);
		font-family:
			'Inter',
			ui-sans-serif,
			system-ui,
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			sans-serif;
	}

	.auth-drag-region {
		position: fixed;
		z-index: 60;
		top: 0;
		right: 0;
		left: 0;
		height: 2rem;
		pointer-events: none;
	}

	.auth-header {
		z-index: 10;
		display: flex;
		align-items: center;
		padding: 20px 24px;
	}

	.oreegami-logo {
		width: auto;
		height: 30px;
		object-fit: contain;
	}

	.auth-main {
		display: flex;
		flex: 1;
		align-items: center;
		justify-content: center;
		padding: 8px 20px 40px;
	}

	.auth-card {
		display: flex;
		width: 100%;
		max-width: 400px;
		flex-direction: column;
		align-items: stretch;
	}

	.auth-heading {
		margin-bottom: 28px;
		text-align: center;
	}

	.auth-heading h1 {
		margin: 0;
		font-size: 26px;
		font-weight: 800;
		letter-spacing: -0.02em;
		line-height: 1.15;
	}

	.auth-heading p {
		margin: 10px 0 0;
		color: var(--oreegami-ink-50);
		font-size: 15px;
		line-height: 1.5;
	}

	.onboarding-notice {
		max-width: 540px;
		margin: 12px auto 0;
		color: var(--oreegami-ink-50);
		font-size: 12px;
		font-weight: 500;
		line-height: 1.5;
	}

	.auth-body {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24px;
	}

	.auth-mascot {
		width: auto;
		height: 132px;
		flex: 0 0 auto;
		object-fit: contain;
	}

	.auth-actions {
		width: 100%;
	}

	.auth-form {
		display: flex;
		width: 100%;
		flex-direction: column;
		gap: 18px;
	}

	.auth-field {
		display: flex;
		flex-direction: column;
		gap: 7px;
	}

	.auth-field label {
		color: var(--oreegami-ink);
		font-size: 14px;
		font-weight: 600;
		line-height: 1.4;
		text-align: left;
	}

	.auth-input {
		box-sizing: border-box;
		width: 100%;
		height: 48px;
		padding: 0 16px;
		border: 1px solid var(--oreegami-ink-10);
		border-radius: 10px;
		outline: none;
		background: #fff;
		color: var(--oreegami-ink);
		font-family: inherit;
		font-size: 15px;
		transition:
			border-color 180ms ease,
			box-shadow 180ms ease;
	}

	.auth-input::placeholder {
		color: var(--oreegami-ink-30);
	}

	.auth-input:focus {
		border-color: var(--oreegami-blue);
		box-shadow: 0 0 0 3px rgba(0, 0, 230, 0.1);
	}

	.password-input {
		position: relative;
		display: flex;
		align-items: center;
	}

	.password-input .auth-input {
		padding-right: 48px;
	}

	.password-toggle {
		position: absolute;
		right: 6px;
		display: flex;
		width: 36px;
		height: 36px;
		align-items: center;
		justify-content: center;
		border: 0;
		border-radius: 8px;
		background: transparent;
		color: var(--oreegami-ink-50);
		transition:
			background-color 180ms ease,
			color 180ms ease;
	}

	.password-toggle:hover {
		background: #f3f3fa;
		color: var(--oreegami-ink);
	}

	.forgot-password {
		align-self: flex-end;
		margin-top: 1px;
		padding: 0;
		border: 0;
		background: transparent;
		color: var(--oreegami-blue);
		font-family: inherit;
		font-size: 13px;
		line-height: 1.4;
	}

	.forgot-password:hover,
	.mode-switch button:hover,
	.ldap-switch:hover {
		text-decoration: underline;
	}

	.primary-button {
		display: flex;
		width: 100%;
		height: 50px;
		align-items: center;
		justify-content: center;
		margin-top: 4px;
		border: 0;
		border-radius: 999px;
		background: var(--oreegami-blue);
		box-shadow: 0 8px 24px rgba(0, 0, 230, 0.18);
		color: #fff;
		font-family: inherit;
		font-size: 16px;
		font-weight: 600;
		transition:
			transform 180ms ease,
			box-shadow 180ms ease,
			background-color 180ms ease;
	}

	.primary-button:hover {
		transform: translateY(-1px);
		box-shadow: 0 12px 30px rgba(0, 0, 230, 0.26);
	}

	.primary-button:active {
		transform: translateY(0);
	}

	.mode-switch {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 5px;
		margin-top: 16px;
		color: var(--oreegami-ink-50);
		font-size: 13px;
	}

	.mode-switch button,
	.ldap-switch {
		padding: 0;
		border: 0;
		background: transparent;
		color: var(--oreegami-blue);
		font-family: inherit;
		font-size: inherit;
		font-weight: 600;
	}

	.oauth-separator {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		align-items: center;
		gap: 12px;
		margin: 20px 0 14px;
		color: var(--oreegami-ink-50);
	}

	.oauth-separator span {
		height: 1px;
		background: var(--oreegami-ink-10);
	}

	.oauth-separator strong {
		font-size: 13px;
		font-weight: 500;
	}

	.oauth-options {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.oauth-button {
		display: flex;
		width: 100%;
		min-height: 46px;
		align-items: center;
		justify-content: center;
		padding: 9px 16px;
		border: 1px solid var(--oreegami-ink-10);
		border-radius: 999px;
		background: #fff;
		color: var(--oreegami-ink);
		font-family: inherit;
		font-size: 14px;
		font-weight: 600;
		transition:
			border-color 180ms ease,
			background-color 180ms ease,
			transform 180ms ease;
	}

	.oauth-button:hover {
		transform: translateY(-1px);
		border-color: var(--oreegami-ink-30);
		background: #f9f9fc;
	}

	.oauth-button svg {
		width: 22px;
		height: 22px;
		flex: 0 0 auto;
		margin-right: 10px;
	}

	.ldap-switch {
		display: block;
		width: 100%;
		margin-top: 14px;
		font-size: 12px;
		text-align: center;
	}

	.supporters {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 18px;
		margin-top: 40px;
		padding-top: 28px;
		border-top: 1px solid var(--oreegami-ink-10);
	}

	.supporters > span {
		color: var(--oreegami-ink-50);
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.14em;
		line-height: 1.4;
		text-transform: uppercase;
	}

	.supporter-logos {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 36px;
		flex-wrap: wrap;
	}

	.supporter-logos img {
		width: auto;
		object-fit: contain;
	}

	.cfa-logo {
		height: 88px;
	}

	.afdas-logo {
		height: 56px;
	}

	.auto-signin {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24px;
		padding: 40px 0;
	}

	.auto-signin-mascot {
		width: auto;
		height: 180px;
		object-fit: contain;
	}

	.auto-signin-status {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12px;
		font-size: 21px;
		font-weight: 700;
		text-align: center;
	}

	button:focus-visible {
		outline: 3px solid rgba(0, 0, 230, 0.22);
		outline-offset: 3px;
	}

	@media (min-width: 768px) {
		.auth-card {
			max-width: 720px;
		}

		.auth-body {
			flex-direction: row;
			justify-content: center;
			gap: 52px;
		}

		.auth-mascot {
			height: 220px;
		}

		.auth-actions {
			flex: 0 1 360px;
		}
	}

	@media (max-width: 767px) {
		.auth-header {
			padding: 18px 20px;
		}

		.auth-main {
			align-items: flex-start;
			padding-top: 18px;
		}

		.auth-heading h1 {
			font-size: 24px;
		}

		.supporter-logos {
			gap: 24px;
		}

		.cfa-logo {
			height: 76px;
		}

		.afdas-logo {
			height: 48px;
		}
	}

	@media (min-width: 768px) and (max-height: 720px) {
		.auth-header {
			padding-top: 16px;
			padding-bottom: 12px;
		}

		.auth-main {
			padding-bottom: 24px;
		}

		.auth-heading {
			margin-bottom: 20px;
		}

		.auth-mascot {
			height: 180px;
		}

		.supporters {
			gap: 12px;
			margin-top: 28px;
			padding-top: 20px;
		}

		.cfa-logo {
			height: 72px;
		}

		.afdas-logo {
			height: 46px;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.auth-input,
		.password-toggle,
		.primary-button,
		.oauth-button {
			transition: none;
		}

		.primary-button:hover,
		.oauth-button:hover {
			transform: none;
		}
	}
</style>
