<script lang="ts">
	let { src, title }: { src: string; title: string } = $props();
</script>

<iframe
	frameborder="0"
	onload={(e) => {
		const el = e.currentTarget as HTMLIFrameElement;
		if (el.contentWindow) {
			el.style.height = el.contentWindow.document.body.scrollHeight + 20 + 'px';
		}
	}}
	{src}
	{title}
	width="100%"
>
	<!-- Loading iframe -->
</iframe>
