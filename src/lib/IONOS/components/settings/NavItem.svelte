<script lang="ts">
	export let value;
	export let group;
</script>

<label class="block p-2 rounded hover:bg-gray-50 has-[:checked]:bg-gray-200 cursor-pointer">
	<input type="radio" bind:group={group} {value} class="hidden" />
	<slot name="icon" />
	<span class="ml-2">
		<slot />
	</span>
</label>
