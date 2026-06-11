<script lang="ts">
	import { getContext } from 'svelte';
	import { LinkPreview } from 'bits-ui';

	const i18n = getContext('i18n');
	import { getUserInfoById } from '$lib/apis/users';

	import UserStatus from './UserStatus.svelte';

	export let id = null;
	export let open = false;

	export let side = 'top';
	export let align = 'start';
	export let sideOffset = 6;

	let user = null;
	let fetched = false;

	$: if (open && id && !fetched) {
		fetched = true;
		getUserInfoById(localStorage.token, id)
			.then((res) => {
				user = res;
			})
			.catch((error) => {
				console.error('Error fetching user by ID:', error);
			});
	}
</script>

{#if user}
	<LinkPreview.Portal>
		<LinkPreview.Content
			class="w-[260px] rounded-2xl border border-gray-100  dark:border-gray-800 z-[9999] bg-white dark:bg-gray-850 dark:text-white shadow-lg transition"
			{side}
			{align}
			{sideOffset}
		>
			<UserStatus {user} />
		</LinkPreview.Content>
	</LinkPreview.Portal>
{/if}
