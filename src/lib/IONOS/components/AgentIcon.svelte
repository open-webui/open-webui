<script lang="ts">
	import Pencil from '$lib/IONOS/components/icons/Pencil.svelte';
	import Image from '$lib/IONOS/components/icons/Image.svelte';
	import Code from '$lib/IONOS/components/icons/Code.svelte';
	import Comment from '$lib/IONOS/components/icons/Comment.svelte';

	export let iconName = '';
</script>

{#if iconName == 'talk'}
	<Comment className="inline-block size-4" />
{:else if iconName == 'code'}
	<Code className="inline-block size-4" />
{:else if iconName == 'image'}
	<Image className="inline-block size-4" />
{:else if iconName == 'pencil'}
	<Pencil className="inline-block size-4" />
{:else}
	<Pencil className="inline-block size-4" />
{/if}
