<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import dayjs, { getDayjsLocale } from '$lib/dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(relativeTime);

	import { config, showSettings, user as sessionUser } from '$lib/stores';
	import type { AppLayoutContext } from '$lib/types';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getDMChannelByUserId } from '$lib/apis/channels';
	import { getUserInfoById } from '$lib/apis/users';

	import Emoji from '$lib/components/common/Emoji.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	export let userId: string | null = null;

	let user: any = null;
	let failed = false;

	const loadUser = async (id: string) => {
		user = null;
		failed = false;
		const loadedUser = await getUserInfoById(localStorage.token, id).catch(() => null);
		if (userId !== id) return;
		user = loadedUser;
		failed = !loadedUser;
	};

	$: if (userId) loadUser(userId);

	$: isSelf = !!user && $sessionUser?.id === user.id;
	$: canMessage =
		!!user &&
		!isSelf &&
		$config?.features?.enable_channels &&
		($sessionUser?.role === 'admin' || ($sessionUser?.permissions?.features?.channels ?? true));
	$: groups = ((user?.groups ?? []) as { name: string }[]).map((group) => group.name).join(', ');
	$: localTime = getLocalTime(user?.timezone, $i18n.language);
	$: lastSeen =
		!user?.is_active && user?.last_active_at
			? dayjs(user.last_active_at * 1000)
					.locale(getDayjsLocale($i18n.language) ?? 'en')
					.fromNow()
			: '';

	const getLocalTime = (timeZone: string | null | undefined, language: string) => {
		if (!timeZone) return '';
		try {
			return new Date().toLocaleTimeString(language, {
				timeZone,
				hour: 'numeric',
				minute: '2-digit',
				timeZoneName: 'short'
			});
		} catch {
			// Older profiles may contain a timezone the browser cannot resolve.
			return '';
		}
	};

	const close = () => (userId = null);

	const sendMessage = async () => {
		const channel = await getDMChannelByUserId(localStorage.token, user.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!channel) return;

		const href = `/channels/${channel.id}`;
		close();
		showSettings.set(false);
		if (appLayout?.openPageTab) appLayout.openPageTab({ href, label: '' });
		else goto(href);
	};

	const rowClass =
		'grid grid-cols-[7rem_minmax(0,1fr)] items-start gap-2 text-base-900 dark:text-base-100';
	const labelClass = 'text-base-600 dark:text-base-400';
</script>

<Modal
	size="sm"
	className="bg-base-0 dark:bg-base-900 rounded-4xl overflow-hidden !border-0"
	show={!!userId}
	ariaLabel={$i18n.t('Profile')}
	onRequestClose={close}
>
	<div class="relative flex max-h-[calc(100dvh-3rem)] flex-col">
		<button
			type="button"
			aria-label={$i18n.t('Close')}
			class="absolute end-4 top-3 z-10 rounded-lg py-1 transition px-0 {user?.profile_banner_image_url
				? 'text-base-0 drop-shadow-sm hover:text-base-0/80'
				: 'text-base-500 hover:text-base-700 dark:text-base-400 dark:hover:text-base-200'}"
			on:click={close}
		>
			<XMark className="size-4" />
		</button>

		{#if user}
			<div class="min-h-0 overflow-y-auto scrollbar-hover pb-5">
				<!-- The model editor header, edge to edge. -->
				<div class="relative w-full {user.profile_banner_image_url ? 'h-36' : 'h-20'}">
					{#if user.profile_banner_image_url}
						<img
							src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/banner?v=${encodeURIComponent(user.profile_banner_image_url)}`}
							alt=""
							class="[mask-image:linear-gradient(to_bottom,black_15%,rgba(0,0,0,0.65)_40%,transparent_85%)] absolute inset-0 h-full w-full object-cover"
							on:error={() => (user = { ...user, profile_banner_image_url: null })}
						/>
					{:else}
						<div
							aria-hidden="true"
							class="[mask-image:linear-gradient(to_bottom,black_15%,rgba(0,0,0,0.65)_40%,transparent_85%)] absolute inset-0 h-full w-full bg-base-100 dark:bg-base-850"
						></div>
					{/if}
				</div>

				<div
					class="relative flex min-w-0 items-center gap-3.5 px-5 pb-1 {user.profile_banner_image_url
						? '-mt-14'
						: '-mt-9'}"
				>
					<img
						src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
						alt=""
						class="size-12 shrink-0 rounded-full bg-base-50 object-cover ring-1 ring-base-200/70 dark:bg-base-850 dark:ring-base-0/10"
					/>
					<div class="min-w-0 flex-1">
						<div
							class="break-words text-base leading-tight text-base-900 dark:text-base-0 md:text-lg"
						>
							{user.name}
						</div>
						<div class="flex items-center gap-1.5 py-0.5 text-xs text-base-500">
							<span
								class="size-1.5 shrink-0 rounded-full {user.is_active
									? 'bg-green-500'
									: 'bg-base-400'}"
								aria-hidden="true"
							></span>
							{user.is_active ? $i18n.t('Active') : $i18n.t('Away')}
						</div>
					</div>

					{#if canMessage}
						<button
							type="button"
							class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0"
							on:click={sendMessage}
						>
							{$i18n.t('Message')}
						</button>
					{:else if isSelf}
						<button
							type="button"
							class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-100 px-2.5 text-xs font-normal text-base-800 transition hover:bg-base-100/70 disabled:opacity-60 dark:bg-base-850 dark:text-base-0 dark:hover:bg-base-850/60"
							on:click={() => {
								close();
								showSettings.set('account');
							}}
						>
							{$i18n.t('Edit')}
						</button>
					{/if}
				</div>

				{#if user.bio}
					<div
						class="mt-3 whitespace-pre-line break-words px-5 text-[0.8125rem] font-normal text-base-900 dark:text-base-100"
					>
						{user.bio}
					</div>
				{/if}

				{#if user.status_emoji || user.status_message || localTime || lastSeen || groups}
					<dl class="mt-3 flex flex-col gap-2 px-5 text-xs font-normal">
						{#if user.status_emoji || user.status_message}
							<div class={rowClass}>
								<dt class={labelClass}>{$i18n.t('Status')}</dt>
								<dd class="flex min-w-0 items-start gap-1.5">
									{#if user.status_emoji}
										<span class="flex h-4 shrink-0 items-center">
											<Emoji className="size-3.5" shortCode={user.status_emoji} />
										</span>
									{/if}
									<span class="min-w-0 break-words">{user.status_message ?? ''}</span>
								</dd>
							</div>
						{/if}
						{#if localTime}
							<div class={rowClass}>
								<dt class={labelClass}>{$i18n.t('Local time')}</dt>
								<dd>{localTime}</dd>
							</div>
						{/if}
						{#if lastSeen}
							<div class={rowClass}>
								<dt class={labelClass}>{$i18n.t('Last seen')}</dt>
								<dd>{lastSeen}</dd>
							</div>
						{/if}
						{#if groups}
							<div class={rowClass}>
								<dt class={labelClass}>{$i18n.t('Groups')}</dt>
								<dd class="min-w-0 break-words">{groups}</dd>
							</div>
						{/if}
					</dl>
				{/if}
			</div>
		{:else if failed}
			<div class="py-12 text-center text-xs text-base-500">{$i18n.t('Unknown user')}</div>
		{:else}
			<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
		{/if}
	</div>
</Modal>
