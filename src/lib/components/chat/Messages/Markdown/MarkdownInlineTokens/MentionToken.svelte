<script lang="ts">
	import type { Token } from 'marked';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let token: Token;

	let triggerChar = '';
	let label = '';

	let idType = '';
	let id = '';

	$: if (token) {
		init();
	}

	const init = () => {
		const _id = token?.id;
		if (_id?.includes(':')) {
			idType = _id.split(':')[0];
			id = _id.split(':')[1];
		} else {
			id = _id;
		}

		label = token?.label ?? id;
		triggerChar = token?.triggerChar ?? '@';
	};
</script>

<Tooltip as="span" className="mention" content={id} placement="top">
	{triggerChar}{label}
</Tooltip>
