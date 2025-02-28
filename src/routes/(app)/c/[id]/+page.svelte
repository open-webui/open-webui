<script lang="ts">
  import { page } from '$app/state';

  import Chat from '$lib/components/chat/Chat.svelte';
  import Help from '$lib/components/layout/Help.svelte';
</script>

<Help />
<Chat chatIdProp={page.params.id} />
