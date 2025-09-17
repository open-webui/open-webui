<script lang="ts">
	import { LinkPreview } from 'bits-ui';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');
	import UserStatus from './UserStatus.svelte';

	export let user = null;
</script>

<LinkPreview.Root openDelay={0} closeDelay={0}>
	<LinkPreview.Trigger class=" cursor-pointer no-underline! font-normal! ">
		<slot />
	</LinkPreview.Trigger>

	<LinkPreview.Content
		class="w-full max-w-[260px] rounded-2xl border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg transition"
		side="right"
		align="center"
		sideOffset={8}
	>
		<UserStatus id={user.id} />
	</LinkPreview.Content>
</LinkPreview.Root>
