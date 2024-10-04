<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { renderSuiConnectButton } from '$lib/apis/atoma/SuiConnectButton';
	import { userSignIn, userSignUp } from '$lib/apis/auths';
	import { generateInitialsImage } from '$lib/utils';
	import { toast } from 'svelte-sonner';
	import { config, socket, user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { getBackendConfig } from '$lib/apis';

	const i18n = getContext('i18n');

	let suiCurrentWallet = null;
	let suiConnectionStatus = 'disconnected';
	let suiSignPersonalMessage = null;
	let suiSignAndExecuteTransaction = null;

	const setSessionUser = async (sessionUser: any) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			let backendConfig = await getBackendConfig();
			backendConfig['sui'] = {
				currentWallet: suiCurrentWallet,
				connectionStatus: suiConnectionStatus,
				signPersonalMessage: suiSignPersonalMessage,
				signAndExecuteTransaction: suiSignAndExecuteTransaction
			};
			await config.set(backendConfig);
			goto('/');
		}
	};

	const walletCallback = (
		currentWallet: import('@mysten/wallet-standard').WalletWithRequiredFeatures,
		connectionStatus: 'connecting' | 'disconnected' | 'connected',
		signPersonalMessage: any,
		signAndExecuteTransaction: any
	) => {
		suiCurrentWallet = currentWallet;
		suiConnectionStatus = connectionStatus;
		suiSignPersonalMessage = signPersonalMessage;
		suiSignAndExecuteTransaction = signAndExecuteTransaction;

		if (suiSignPersonalMessage) {
			suiSignPersonalMessage(
				{ message: new TextEncoder().encode('Welcome to Atoma') },
				{
					onSuccess: async (result: any) => {
						let name = 'Atoma User ' + currentWallet.accounts[0].address;
						console.log(name);
						let email = result.signature + '@atoma.user';
						let password = result.signature;
						let sessionUser: any;
						try {
							sessionUser = await userSignIn(email, password);
						} catch (error) {
							try {
								sessionUser = await userSignUp(name, email, password, generateInitialsImage(name));
							} catch (error) {
								console.error(error);
								return;
							}
						}
						console.log(sessionUser);
						setSessionUser(sessionUser);
					}
				}
			);
		}
	};

	onMount(() => {
		const target = document.getElementById('react-sui');
		renderSuiConnectButton(target, walletCallback);
	});
</script>

<!-- All these style are just copy pasted from the openwebui/+page.svelte so the style looks the same -->
<div class="bg-white dark:bg-gray-950 min-h-screen w-full flex justify-center font-primary gap-3">
	<div class="w-full sm:max-w-md px-10 min-h-screen flex flex-col text-center">
		<div class="my-auto pb-10 w-full flex flex-col">
			<button
				class="bg-gray-900 hover:bg-gray-800 w-full rounded-2xl text-white font-medium text-sm py-3 transition mb-3"
			>
				<a href="/auth/openwebui">OpenWebui eMail/password </a>
			</button>
			<!-- The py-3 is added to the ConnectModal in the nested react component -->
			<button
				class="bg-gray-900 hover:bg-gray-800 w-full rounded-2xl text-white font-medium text-sm transition mt-3"
				id="react-sui"
			/>
		</div>
	</div>
</div>
