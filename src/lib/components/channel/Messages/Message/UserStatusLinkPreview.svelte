<script lang="ts">
	import { getContext } from 'svelte';
	import { LinkPreview } from 'bits-ui';

	const i18n = getContext('i18n');
	import { getUserInfoById } from '$lib/apis/users';

	import UserStatus from './UserStatus.svelte';

	export let id: string | null = null;
	export let openPreview = false;

	export let side = 'top';
	export let align = 'start';
	export let sideOffset = 6;

	let user = null;
	let requestedUserId: string | null = null;

	const loadUser = async (userId: string) => {
		requestedUserId = userId;

		const loadedUser = await getUserInfoById(localStorage.token, userId).catch((error) => {
			if (requestedUserId === userId) {
				console.error('Error fetching user by ID:', error);
			}

			return null;
		});

		if (requestedUserId === userId) {
			user = loadedUser;
		}
	};

	$: if (openPreview && id && id !== requestedUserId) {
		loadUser(id);
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
