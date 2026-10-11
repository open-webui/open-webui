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
	import { user as sessionUser } from '$lib/stores';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	import UserStatusLinkPreview from './UserStatusLinkPreview.svelte';

	export let user: { id?: string | null; name?: string | null } | null = null;

	export let align = 'center';
	export let side = 'right';
	export let sideOffset = 8;

	export let openPreview = false;

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

{#if user?.id && $sessionUser}
	<LinkPreview.Root openDelay={0} closeDelay={200} bind:open={openPreview}>
		<LinkPreview.Trigger
			class="flex shrink-0 items-center cursor-pointer no-underline! font-normal!"
		>
			{#snippet child({ props })}
				<button
					{...props}
					type="button"
					aria-label={user.name || $i18n.t('User')}
					onclick={() => (openPreview = !openPreview)}
				>
					<slot />
				</button>
			{/snippet}
		</LinkPreview.Trigger>

		<UserStatusLinkPreview id={user.id} {openPreview} {side} {align} {sideOffset} />
	</LinkPreview.Root>
{:else}
	<slot />
{/if}
