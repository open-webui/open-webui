<script lang="ts">
	import { LinkPreview } from 'bits-ui';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');
	import UserStatus from './UserStatus.svelte';
	import UserStatusLinkPreview from './UserStatusLinkPreview.svelte';

	export let user = null;

	export let align = 'center';
	export let side = 'right';
	export let sideOffset = 8;
</script>

<LinkPreview.Root openDelay={0} closeDelay={0}>
	<LinkPreview.Trigger class=" cursor-pointer no-underline! font-normal! ">
		<slot />
	</LinkPreview.Trigger>

	<UserStatusLinkPreview id={user?.id} {side} {align} {sideOffset} />
</LinkPreview.Root>
