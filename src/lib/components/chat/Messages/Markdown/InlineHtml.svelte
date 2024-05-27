<script lang="ts">
	import type { Tokens } from 'marked';

	export let token: Tokens.HTML | Tokens.Tag | Tokens.Generic;
</script>

{@html token.text}
