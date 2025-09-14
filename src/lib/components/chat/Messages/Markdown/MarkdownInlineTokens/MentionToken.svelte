<script lang="ts">
	import type { Token } from 'marked';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let token: Token;
</script>

<Tooltip as="span" className="mention" content={token.id} placement="top">
	{token?.triggerChar ?? '@'}{token?.label ?? token?.id}
</Tooltip>
