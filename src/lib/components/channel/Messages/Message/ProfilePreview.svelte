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
		class="max-w-full w-[240px] rounded-2xl z-9999 bg-white dark:bg-black dark:text-white shadow-lg"
		side="left"
		align="center"
		sideOffset={8}
	>
		<UserStatus id={user.id} />
	</LinkPreview.Content>
</LinkPreview.Root>
