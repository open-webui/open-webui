<script lang="ts">
	import { LinkPreview } from 'bits-ui';

	import { getUserInfoById } from '$lib/apis/users';

	import UserStatus from './UserStatus.svelte';

	export let id: string | null = null;
	export let openPreview = false;
	export let resolvedUser = null;
	export let loadingUser = false;

	export let side = 'top';
	export let align = 'start';
	export let sideOffset = 6;

	let user = null;
	let requestedUserId: string | null = null;

	const loadUser = async (userId: string) => {
		requestedUserId = userId;
		user = null;

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

	$: if (resolvedUser?.id === id) {
		user = resolvedUser;
		requestedUserId = id;
	} else if (!loadingUser && openPreview && id && id !== requestedUserId) {
		loadUser(id);
	} else if (!openPreview) {
		requestedUserId = null;
	}
</script>

{#if user}
	<LinkPreview.Portal>
		<LinkPreview.Content
			class="z-[9999] w-64 max-w-[calc(100vw-1.5rem)] max-h-[calc(100dvh-1.5rem)] overflow-y-auto rounded-xl bg-white font-sans text-gray-900 shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-black/5 dark:bg-gray-850 dark:text-gray-100 dark:ring-white/10"
			{side}
			{align}
			{sideOffset}
		>
			<UserStatus {user} />
		</LinkPreview.Content>
	</LinkPreview.Portal>
{/if}
