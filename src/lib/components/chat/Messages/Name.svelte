<!--
	Rendered as a heading, not a div, so screen-reader users get a jump target at
	the start of every turn. The conversation itself is an <h2> (the sr-only
	#chat-conversation label in Messages.svelte), so each message name nests under
	it as an <h3>.

	Tailwind's preflight resets heading font-size, font-weight and margin to
	inherit, and the sizing here is set by the classes below, so this renders
	identically to the <div> it replaces.
-->
<h3 class=" self-center text-[0.9375rem] font-normal line-clamp-1 flex gap-1 items-center">
	<slot />
</h3>
