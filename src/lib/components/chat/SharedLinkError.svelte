<script lang="ts">
	import { goto } from '$app/navigation';

	export let error = {
		code: '',
		message: "We could not find what you're looking for :/"
	};

	let title = 'Link Error';

	$: switch (error.code) {
		case 'SHARE_LINK_NOT_FOUND':
			title = 'Link Not Found';
			break;
		case 'SHARE_LINK_REVOKED':
			title = 'Link Revoked';
			break;
		case 'SHARE_LINK_EXPIRED':
			title = 'Link Expired';
			break;
	}
</script>

<div class="h-screen max-h-[100dvh] w-full flex justify-center items-center">
	<div
		class="w-full max-w-sm p-8 space-y-4 bg-white dark:bg-gray-800 rounded-xl shadow-lg text-center"
	>
		<div class="text-2xl font-medium text-center">{title}</div>
		<p class="text-sm text-center text-gray-500">
			{error.message}
		</p>

		<button
			class="w-full px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={() => {
				goto('/');
			}}
		>
			Go back Home
		</button>
	</div>
</div>
