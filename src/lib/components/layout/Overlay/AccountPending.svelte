<script lang="ts">
	import { getAdminDetails } from '$lib/apis/auths';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	let adminDetails = null;

	onMount(async () => {
		adminDetails = await getAdminDetails(localStorage.token).catch((err) => {
			console.error(err);
			return null;
		});
	});
</script>

<div class="fixed w-full h-full flex z-999">
	<div
		class="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center"
	>
		<div class="m-auto pb-10 flex flex-col justify-center">
			<div class="max-w-md">
				<div class="text-center dark:text-white text-2xl font-medium z-50">
					{$i18n.t('Account Activation Pending')}<br />					
				</div>

				<div class=" mt-4 text-center text-sm dark:text-gray-200 w-full">
					{$i18n.t('Your account status is currently pending activation.')}<br />
					 To access the ContextOps AI Platform, please reach out to the 
					 <a href="https://discord.gg/RNa7nds8" class="inline-flex items-center justify-center px-2 py-1 text-base font-medium text-center text-black border border-black rounded-lg bg-white hover:bg-gray-100 focus:ring-4 focus:ring-gray-300 lg:ml-2">
						Discord channel
						<svg class="w-4 h-4 ml-1 text-blue-500" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M20.317 4.369a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.211.375-.444.864-.608 1.249a18.365 18.365 0 00-5.487 0 12.64 12.64 0 00-.617-1.249.077.077 0 00-.079-.037 19.736 19.736 0 00-4.885 1.515.069.069 0 00-.032.027C2.99 9.045 2.213 13.579 2.513 18.057a.082.082 0 00.031.056 19.9 19.9 0 005.993 3.03.077.077 0 00.084-.027c.462-.63.873-1.295 1.226-1.994a.076.076 0 00-.041-.105 13.19 13.19 0 01-1.872-.885.077.077 0 01-.008-.13c.126-.094.252-.192.373-.291a.075.075 0 01.077-.01c3.927 1.793 8.18 1.793 12.061 0a.075.075 0 01.078.009c.121.099.247.197.373.291a.077.077 0 01-.007.13 12.64 12.64 0 01-1.873.884.076.076 0 00-.04.106c.36.698.772 1.362 1.226 1.993a.076.076 0 00.084.028 19.876 19.876 0 005.994-3.03.082.082 0 00.031-.056c.334-4.479-.444-9.012-3.742-13.661a.06.06 0 00-.032-.027zM8.02 15.331c-1.182 0-2.156-1.085-2.156-2.419 0-1.333.955-2.418 2.156-2.418 1.21 0 2.175 1.095 2.156 2.418 0 1.334-.955 2.419-2.156 2.419zm7.974 0c-1.182 0-2.156-1.085-2.156-2.419 0-1.333.955-2.418 2.156-2.418 1.21 0 2.175 1.095 2.156 2.418 0 1.334-.946 2.419-2.156 2.419z"></path></svg>
					</a>  to say hello or send a mail to 
  					<a href="mailto:support@rnd-solutions.net" class="text-blue-500 underline">support@rnd-solutions.net</a>
				</div>

					<div class="mt-4 text-sm font-medium text-center">
						<img/>
					</div>

				<div class=" mt-6 mx-auto relative group w-fit">
					<button
						class="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 text-gray-700 transition font-medium text-sm"
						on:click={async () => {
							location.href = '/';
						}}
					>
						{$i18n.t('Check Again')}
					</button>

					<button
						class="text-xs text-center w-full mt-2 text-gray-400 underline"
						on:click={async () => {
							localStorage.removeItem('token');
							location.href = '/auth';
						}}>{$i18n.t('Sign Out')}</button
					>
				</div>
			</div>
		</div>
	</div>
</div>
