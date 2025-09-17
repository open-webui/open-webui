<script lang="ts">
	import type { Token } from 'marked';
	import { LinkPreview } from 'bits-ui';

	import { getContext } from 'svelte';

	import { goto } from '$app/navigation';
	import { channels, models } from '$lib/stores';
	import UserStatus from '$lib/components/channel/Messages/Message/UserStatus.svelte';

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
			} else if (idType === 'A') {
				// Agent/assistant/ai model
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
	<LinkPreview.Trigger class="mention cursor-pointer no-underline! font-normal! ">
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->

		<span
			on:click={async () => {
				if (triggerChar === '@') {
					if (idType === 'U') {
						// Open user profile
						console.log('Clicked user mention', id);
					} else if (idType === 'A') {
						// Open agent/assistant/ai model profile
						console.log('Clicked agent mention', id);
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

	<LinkPreview.Content
		class="w-full max-w-[260px] rounded-2xl border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg transition"
		side="top"
		align="start"
		sideOffset={6}
	>
		{#if triggerChar === '@' && idType === 'U'}
			<UserStatus {id} />
		{/if}
		<!-- <div class="flex space-x-4">HI</div> -->
	</LinkPreview.Content>
</LinkPreview.Root>
