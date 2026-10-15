<script lang="ts">
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';

	export let id: string;
	export let content: string;
</script>

<div
	class="markdown-prose !text-xs !leading-snug font-normal [&_p]:!text-xs [&_p]:!leading-snug [&_h1]:!text-xs [&_h2]:!text-xs [&_h3]:!text-xs [&_h4]:!text-xs [&_h5]:!text-xs [&_h6]:!text-xs [&_h1]:!font-normal [&_h2]:!font-normal [&_h3]:!font-normal [&_h4]:!font-normal [&_h5]:!font-normal [&_h6]:!font-normal [&_strong]:!font-normal [&_a]:!font-normal [&_th]:!font-normal [&_pre]:!text-[0.6875rem] [&_ul]:!my-1 [&_ol]:!my-1 [&_li]:!leading-snug"
>
	<Markdown
		{id}
		{content}
		compactPreview={true}
		preview={true}
		editCodeBlock={false}
		allowHtml={false}
	/>
</div>
