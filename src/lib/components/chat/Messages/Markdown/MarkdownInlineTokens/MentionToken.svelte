<script lang="ts">
	import type { Token } from 'marked';
	import { LinkPreview } from 'bits-ui';

	import { getContext } from 'svelte';

	import { goto } from '$app/navigation';
	import { channels, models } from '$lib/stores';
	import UserStatus from '$lib/components/channel/Messages/Message/UserStatus.svelte';
	import UserStatusLinkPreview from '$lib/components/channel/Messages/Message/UserStatusLinkPreview.svelte';

	const i18n = getContext('i18n');

	export let token: Token;

	let triggerChar = '';
	let label = '';

	let idType = null;
	let id = '';

	$: if (token) {
		init();
	}

	const init = () => {
		const _id = token?.id;
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
		triggerChar = token?.triggerChar ?? '@';

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
				// User
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
	};
</script>

<LinkPreview.Root openDelay={0} closeDelay={0}>
	<LinkPreview.Trigger class=" cursor-pointer no-underline! font-normal! ">
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->

		<span
			class="mention"
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
	</LinkPreview.Trigger>

	{#if triggerChar === '@' && idType === 'U'}
		<UserStatusLinkPreview {id} />
	{/if}
</LinkPreview.Root>
