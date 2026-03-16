<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { LinkPreview } from 'bits-ui';

	const i18n = getContext('i18n');
	import { getUserInfoById } from '$lib/apis/users';

	import UserStatus from './UserStatus.svelte';

	export let id = null;

	export let side = 'top';
	export let align = 'start';
	export let sideOffset = 6;

	let user = null;
	onMount(async () => {
		if (id) {
			user = await getUserInfoById(localStorage.token, id).catch((error) => {
				console.error('Error fetching user by ID:', error);
				return null;
			});
		}
	});
</script>

{#if user}
	<LinkPreview.Content
		class="w-full max-w-[260px] rounded-2xl border border-gray-100  dark:border-gray-800 z-[9999] bg-white dark:bg-gray-850 dark:text-white shadow-lg transition"
		{side}
		{align}
		{sideOffset}
	>
		<UserStatus {user} />
	</LinkPreview.Content>
{/if}
