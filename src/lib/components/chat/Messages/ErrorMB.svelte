<script lang="ts">
	import '$lib/styles/pill-button.css';
	const i18n = getContext('i18n');
	import PencilSquare from '$lib/components/icons/PencilSquare.svelte';
	import { getContext } from 'svelte'; // Import the shared styles
	export let initNewChat: Function;
	export let content = '';

</script>

<div class="flex justify-center items-center">
	<p class="italic text-[#EB8486]">{content}</p>
	<br>
	<br>
	<button id="error-new-chat-button"
		class="pill-button transition w-max rounded-full font-medium text-sm py-1 px-4"
		on:click={() => {
			initNewChat();
		}}
	>
		<div class="flex justify-center items-center">
			<PencilSquare className="size-7 text-white" strokeWidth="2" />
		</div>
	</button>
</div>