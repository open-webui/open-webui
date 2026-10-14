<script context="module" lang="ts">
	import { getUserInfoById } from '$lib/apis/users';

	const pendingUsers = new Map<string, ReturnType<typeof getUserInfoById>>();
	function loadMentionUser(token: string, id: string) {
		const key = `${token}:${id}`;
		if (!pendingUsers.has(key)) {
			pendingUsers.set(
				key,
				getUserInfoById(token, id).finally(() => pendingUsers.delete(key))
			);
		}
		return pendingUsers.get(key)!;
	}
</script>

<script lang="ts">
	import type { Tokens } from 'marked';
	import { LinkPreview } from 'bits-ui';

	import { getContext } from 'svelte';
	import { browser } from '$app/environment';

	import { goto } from '$app/navigation';
	import { channels, models } from '$lib/stores';
	import UserStatusLinkPreview from '$lib/components/channel/Messages/Message/UserStatusLinkPreview.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let token: Tokens.Generic;

	let triggerChar = '';
	let label = '';

	let idType = null;
	let id = '';
	let openPreview = false;
	let resolvedUser = null;
	let requestedUserId: string | null = null;
	let userUnavailable = false;

	$: if (token && $i18n && $models && $channels) {
		init(resolvedUser, userUnavailable);
	}

	const init = (user, unavailable) => {
		const _id = token?.id;
		triggerChar = token?.triggerChar ?? '@';

		if (triggerChar === '$') {
			// Skill mention: id format is "skillId|label"
			const pipeIdx = _id?.indexOf('|') ?? -1;
			if (pipeIdx > 0) {
				id = _id.substring(0, pipeIdx);
				label = _id.substring(pipeIdx + 1);
			} else {
				id = _id;
				label = _id;
			}
			idType = null;
			return;
		}

		// split by : and take first part as idType and second part as id
		const parts = _id?.split(':');
		if (parts) {
			idType = parts[0];
			id = parts.slice(1).join(':'); // in case id contains ':'
		} else {
			idType = null;
			id = _id;
		}

		label = token?.label ?? id;

		if (triggerChar === '#') {
			if (idType === 'C') {
				// Channel
				const channel = $channels.find((c) => c.id === id);
				if (channel) {
					label = channel.name;
				} else {
					label = $i18n.t('Unknown');
				}
			} else if (idType === 'T') {
				// Thread
			}
		} else if (triggerChar === '@') {
			if (idType === 'U') {
				label =
					user?.id === id
						? user.name
						: unavailable && requestedUserId === id
							? $i18n.t('Unknown')
							: label;
			} else if (idType === 'M') {
				// Model
				const model = $models.find((m) => m.id === id);
				if (model) {
					label = model.name;
				} else {
					label = $i18n.t('Unknown');
				}
			}
		}
		if (
			browser &&
			idType === 'U' &&
			requestedUserId !== id &&
			(!token?.label ||
				token.label === _id ||
				token.label === id ||
				/^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(token.label))
		) {
			requestedUserId = id;
			resolvedUser = null;
			userUnavailable = false;
			resolveUser(id);
		}
	};

	async function resolveUser(userId: string) {
		try {
			const user = await loadMentionUser(localStorage.token, userId);
			if (requestedUserId === userId) {
				resolvedUser = user;
				userUnavailable = !user;
			}
		} catch {
			if (requestedUserId === userId) userUnavailable = true;
		}
	}
</script>

<LinkPreview.Root openDelay={0} closeDelay={0} bind:open={openPreview}>
	<LinkPreview.Trigger class=" cursor-pointer no-underline! font-normal! ">
		{#snippet child({ props })}
			<span {...props}>
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<!-- svelte-ignore a11y-no-static-element-interactions -->

				<span
					class="mention"
					data-type="mention"
					data-id={`${token.id.split('|')[0]}|${label}`}
					data-label={label}
					data-mention-suggestion-char={triggerChar}
					on:click={async () => {
						if (triggerChar === '@') {
							if (idType === 'U') {
								// Open user profile
								console.log('Clicked user mention', id);
							} else if (idType === 'M') {
								console.log('Clicked model mention', id);
								await goto(`/?model=${id}`);
							}
						} else if (triggerChar === '#') {
							if (idType === 'C') {
								// Open channel
								if ($channels.find((c) => c.id === id)) {
									await goto(`/channels/${id}`);
								}
							} else if (idType === 'T') {
								// Open thread
							}
						} else {
							// Unknown trigger char, just log
							console.log('Clicked mention', id);
						}
					}}
				>
					{triggerChar}{label}
				</span>
			</span>
		{/snippet}
	</LinkPreview.Trigger>

	{#if triggerChar === '@' && idType === 'U'}
		<UserStatusLinkPreview
			{id}
			{openPreview}
			resolvedUser={resolvedUser?.id === id ? resolvedUser : null}
			loadingUser={requestedUserId === id && !resolvedUser && !userUnavailable}
		/>
	{/if}
</LinkPreview.Root>
