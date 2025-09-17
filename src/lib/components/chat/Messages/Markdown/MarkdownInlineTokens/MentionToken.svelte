<script lang="ts">
	import type { Token } from 'marked';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { goto } from '$app/navigation';
	import { channels, models } from '$lib/stores';
	import i18n from '$lib/i18n';

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

<Tooltip
	as="span"
	className="mention cursor-pointer"
	onClick={async () => {
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
	content={id}
	placement="top"
>
	{triggerChar}{label}
</Tooltip>
