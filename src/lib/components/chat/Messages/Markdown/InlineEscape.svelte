<script lang="ts">
	import type { Tokens } from 'marked';
	import { unescapeHtml } from '$lib/utils';

	export let token: Tokens.Escape | Tokens.Generic;
</script>

{unescapeHtml(token.text)}
