<script lang="ts">
    export let name;
    export let onClick: () => void = () => {};
</script>

<button class="hover:bg-gray-100 text-gray-800 py-2 px-4 rounded-full inline-flex items-center mx-2" on:click={onClick}>
    {name}
</button>