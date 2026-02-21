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

	let openPreview = false;
</script>

<LinkPreview.Root openDelay={0} closeDelay={200} bind:open={openPreview}>
	<LinkPreview.Trigger class="flex items-center">
		<button
			type="button"
			class=" cursor-pointer no-underline! font-normal!"
			on:click={() => {
				openPreview = !openPreview;
			}}
		>
			<slot />
		</button>
	</LinkPreview.Trigger>

	<UserStatusLinkPreview id={user?.id} {side} {align} {sideOffset} />
</LinkPreview.Root>
