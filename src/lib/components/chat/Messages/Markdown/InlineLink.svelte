<script lang="ts">
	import type { Tokens } from 'marked';

	export let token: Tokens.Link | Tokens.Generic;
</script>

<a href={token.href} target="_blank" rel="nofollow" title={token.title}>{token.text}</a>
