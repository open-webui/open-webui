<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import type { Token } from 'marked';

	export let token: Token;
</script>

<Tooltip as="span" className="mention" content={token.id} placement="top">
	{token.triggerChar}{token.label}
</Tooltip>
