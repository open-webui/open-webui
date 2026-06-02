<script lang="ts">
	import { getContext } from 'svelte';
	import { skills } from '$lib/stores';

	import Modal from '../common/Modal.svelte';
	import Collapsible from '../common/Collapsible.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let selectedSkillIds = [];

	let selectedSkills = [];

	$: selectedSkills = ($skills ?? []).filter((skill) => selectedSkillIds.includes(skill.id));

	const i18n = getContext('i18n');
</script>

<Modal bind:show size="md">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class=" text-lg font-medium self-center">{$i18n.t('Available Skills')}</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if selectedSkills.length > 0}
			<div class=" flex justify-between dark:text-gray-300 px-5 pb-1">
				<div class=" text-base font-medium self-center">{$i18n.t('Skills')}</div>
			</div>

			<div class="px-5 pb-5 w-full flex flex-col justify-center">
				<div class=" text-sm dark:text-gray-300 mb-1">
					{#each selectedSkills as skill}
						<Collapsible buttonClassName="w-full mb-0.5">
							<div class="truncate">
								<div class="text-sm font-medium dark:text-gray-100 text-gray-800 truncate">
									{skill?.name}
								</div>

								{#if skill?.description}
									<div class="text-xs text-gray-500">
										{skill?.description}
									</div>
								{/if}
							</div>
						</Collapsible>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</Modal>
