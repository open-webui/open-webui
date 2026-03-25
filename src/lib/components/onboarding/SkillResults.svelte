<script lang="ts">
	import type { SkillRecommendation } from '$lib/stores/onboarding';

	export let skills: SkillRecommendation[] = [];
</script>

<div class="space-y-3">
	<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
		Skills recomendadas para ti
	</h3>
	<div class="grid gap-3">
		{#each skills as skill}
			<div
				class="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700"
			>
				<span class="text-2xl">{skill.icon}</span>
				<div class="flex-1">
					<div class="font-medium text-gray-900 dark:text-white text-sm">{skill.name}</div>
					<div class="text-xs text-gray-500 dark:text-gray-400">{skill.description}</div>
				</div>
			</div>
		{/each}
	</div>
</div>
