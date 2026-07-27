<script context="module" lang="ts">
	/**
	 * At most one user profile preview may be open across all ProfilePreview
	 * instances. bits-ui's safe-polygon close only re-evaluates on pointermove,
	 * so a preview can be left open when the pointer stops on a neighboring
	 * row while still inside the previous row's grace area; opening a preview
	 * therefore force-closes whichever one is still up.
	 */
	let closeActiveProfilePreview: (() => void) | null = null;
</script>

<script lang="ts">
	import { LinkPreview } from 'bits-ui';
	import { getContext, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	import UserStatus from './UserStatus.svelte';
	import UserStatusLinkPreview from './UserStatusLinkPreview.svelte';

	export let user = null;

	export let align = 'center';
	export let side = 'right';
	export let sideOffset = 8;

	let openPreview = false;

	const closeProfilePreview = () => {
		if (openPreview) {
			openPreview = false;
		}
	};

	$: if (openPreview && closeActiveProfilePreview !== closeProfilePreview) {
		closeActiveProfilePreview?.();
		closeActiveProfilePreview = closeProfilePreview;
	}

	onDestroy(() => {
		if (closeActiveProfilePreview === closeProfilePreview) {
			closeActiveProfilePreview = null;
		}
	});
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

	<UserStatusLinkPreview id={user?.id} {openPreview} {side} {align} {sideOffset} />
</LinkPreview.Root>
