<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { channels, config, user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { canUseEncryption, enter } from '$lib/encryption/client';
	import { updateChannelMemberMuteStatusById } from '$lib/apis/channels';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import AppNotification from '$lib/components/icons/AppNotification.svelte';
	import BellSlash from '$lib/components/icons/BellSlash.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';

	const i18n = getContext<any>('i18n');
	// Keep the dynamic menu labels visible to i18next-parser.
	// $i18n.t('Conversation options');
	// $i18n.t('Channel options');
	export let channel: {
		id: string;
		type?: string | null;
		is_channel_muted?: boolean;
		is_private?: boolean | null;
	};
	export let sidebar = false;
	export let onEdit: (() => void) | undefined = undefined;
	export let onHide: (() => Promise<void>) | undefined = undefined;
	let show = false;
	let saving = false;
	$: isMuted =
		$channels.find((item) => item.id === channel.id)?.is_channel_muted ??
		channel.is_channel_muted ??
		false;

	const setMuted = async (muted: boolean) => {
		if (saving) return;
		if (muted === isMuted) {
			show = false;
			return;
		}
		saving = true;
		const channelId = channel.id;
		try {
			const result = await updateChannelMemberMuteStatusById(localStorage.token, channelId, muted);
			channels.update((items) =>
				items.map((item) => (item.id === channelId ? { ...item, ...result } : item))
			);
			if (channel.id === channelId) channel = { ...channel, ...result };
			show = false;
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};
</script>

<div class:sidebar class:open={show} class="channel-menu self-center shrink-0">
	<Dropdown bind:show align={sidebar ? 'start' : 'end'}>
		<button
			type="button"
			class="flex {sidebar
				? 'size-4.5'
				: 'size-7'} items-center justify-center rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 touch-auto"
			aria-label={$i18n.t(channel.type === 'dm' ? 'Conversation options' : 'Channel options')}
			aria-haspopup="menu"
			aria-expanded={show}
		>
			<EllipsisHorizontal className="size-3.5" />
		</button>
		<div slot="content">
			<DropdownMenu className="w-44 border-gray-200/30! dark:border-gray-700/30!">
				{#if canUseEncryption($user, $config?.features) && (channel.type === 'dm' || (channel.type === 'group' && channel.is_private === true))}
					<button
						type="button"
						role="menuitem"
						on:click={() => {
							if (!canUseEncryption($user, $config?.features)) return;
							show = false;
							enter(channel.id, { action: 'start' });
							void goto(`/channels/${encodeURIComponent(channel.id)}/encrypted`);
						}}
					>
						<LockClosed className="size-3.5 shrink-0" />
						<span>{$i18n.t('Encrypted Chat')}</span>
					</button>
					<hr class="border-gray-200/30 dark:border-gray-700/30" />
				{/if}
				<div class="px-2 pt-1 pb-0.5 text-[0.6875rem] text-gray-500 dark:text-gray-400">
					{$i18n.t('Notifications')}
				</div>
				<button
					type="button"
					role="menuitemradio"
					aria-checked={!isMuted}
					disabled={saving}
					class="disabled:opacity-50"
					on:click={() => setMuted(false)}
				>
					<AppNotification className="size-3.5 shrink-0" />
					<span class="flex-1 text-left">{$i18n.t('All messages')}</span>
					<span class="size-3.5"
						>{#if !isMuted}<Check className="size-3.5" />{/if}</span
					>
				</button>
				<button
					type="button"
					role="menuitemradio"
					aria-checked={isMuted}
					disabled={saving}
					class="disabled:opacity-50"
					on:click={() => setMuted(true)}
				>
					<BellSlash className="size-3.5 shrink-0" />
					<span class="flex-1 text-left">{$i18n.t('Mentions only')}</span>
					<span class="size-3.5"
						>{#if isMuted}<Check className="size-3.5" />{/if}</span
					>
				</button>
				{#if onEdit || onHide}<hr class="border-gray-200/30 dark:border-gray-700/30" />{/if}
				{#if onEdit}
					<button
						type="button"
						role="menuitem"
						on:click={() => {
							onEdit?.();
							show = false;
						}}
					>
						<Settings className="size-3.5 shrink-0" />
						<span>{$i18n.t('Edit channel')}</span>
					</button>
				{/if}
				{#if onHide}
					<button
						type="button"
						role="menuitem"
						on:click={async () => {
							await onHide?.();
							show = false;
						}}
					>
						<EyeSlash className="size-3.5 shrink-0" />
						<span>{$i18n.t('Hide conversation')}</span>
					</button>
				{/if}
			</DropdownMenu>
		</div>
	</Dropdown>
</div>

<style>
	@media (hover: hover) and (pointer: fine) {
		.sidebar:not(.open) {
			opacity: 0;
		}
		:global(.group:hover) .sidebar,
		:global(.group:focus-within) .sidebar {
			opacity: 1;
		}
	}
</style>
