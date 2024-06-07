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

<div class="fixed w-full h-full flex z-[999]">
	<div
		class="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center"
	>
		<div class="m-auto pb-10 flex flex-col justify-center">
			<div class="max-w-md">
				<div class="text-center dark:text-white text-2xl font-medium z-50">
					账户待激活
				</div>

				<div class=" mt-4 text-center text-sm dark:text-gray-200 w-full">
					您的帐户当前处于待激活状态.<br /> 若要访问 ChatK,请联系管理员
				</div>

				{#if adminDetails}
					<div class="mt-4 text-sm font-medium text-center">
						<div>Admin: {adminDetails.name} (gkingt996@gmail.com)</div>
					</div>
				{/if}

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
