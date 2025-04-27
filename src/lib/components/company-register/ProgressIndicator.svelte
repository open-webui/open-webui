<script lang="ts">
	export let step = 1;

	const steps = [
		{ label: 'Email', icon: '📧' },
		{ label: 'Personal', icon: '👤' },
		{ label: 'Company', icon: '🏢' },
		{ label: 'Invite', icon: '📨' }
	];
</script>

<div class="flex justify-between items-center text-sm font-medium">
	{#each steps as s, index}
		<div class="flex-1 flex items-center gap-2">
			<div class={`rounded-full w-6 h-6 flex items-center justify-center 
				${index + 1 <= step ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-700'}`}>
				{s.icon}
			</div>
			<span class={index + 1 <= step ? 'text-black dark:text-white' : 'text-gray-400'}>
				{s.label}
			</span>
			{#if index < steps.length - 1}
				<hr class="flex-1 border-t border-gray-300 mx-2" />
			{/if}
		</div>
	{/each}
</div>