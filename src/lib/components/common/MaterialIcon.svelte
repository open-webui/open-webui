<script lang="ts">
	export let name: string;
	export let className: string = '';
	export let size: string = '1.1rem';
	export let color: string = '';
</script>

<span
	class="material-icons {className}"
	style="font-size: {size}; width: {size}; height: {size}; display: inline-flex; align-items: center; justify-content: center;{color
		? ` color: ${color};`
		: ''}"
>
	{name}
</span>
