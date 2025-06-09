<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import CloseIcon from '$lib/components/icons/CloseIcon.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import PublicIcon from '$lib/components/icons/PublicIcon.svelte';
	import PrivateIcon from '$lib/components/icons/PrivateIcon.svelte';
	import GroupIcon from '$lib/components/icons/GroupIcon.svelte';
	import dayjs from 'dayjs';
	import { capitalizeFirstLetter } from '$lib/utils';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let selectedKnowledge = [];
	export let collections = [];

	export let show = false;

	function hasGroupAccess(model) {
		if (!model.access_control) return [];

		const readGroups = model.access_control.read?.group_ids || [];
		const writeGroups = model.access_control.write?.group_ids || [];

		return readGroups.length > 0 || writeGroups.length > 0;
	}
</script>

<Modal size="md-plus" containerClassName="bg-lightGray-250/50 dark:bg-[#1D1A1A]/50 backdrop-blur-[6px]" bind:show>
	<div class="px-8 py-6 bg-lightGray-550 dark:bg-customGray-800 rounded-2xl">
		<div class="flex justify-between border-b border-lightGray-400 dark:border-customGray-700 pb-7">
			<div class="text-lightGray-100 dark:text-white">{$i18n.t('Knowledge')}</div>
			<button type="button" class="dark:text-white" on:click={() => {
                selectedKnowledge = [];
                show = false;
                }}>
				<CloseIcon />
			</button>
		</div>
		<div>
			<ul>
				{#each collections as knowledge}
					<li class="grid grid-cols-[40px_100px_300px_150px_1fr] gap-4 py-2.5 border-b border-lightGray-400 dark:border-customGray-700">
						<div class="flex items-start justify-center">
							<Checkbox
								state={selectedKnowledge.find((k) => k.id === knowledge.id)
									? 'checked'
									: 'unchecked'}
								on:change={(e) => {
									if (e.detail === 'checked') {
										if (!selectedKnowledge.find((k) => k.id === knowledge.id)) {
											selectedKnowledge = [...selectedKnowledge, knowledge];
										}
									} else {
										selectedKnowledge = selectedKnowledge.filter((k) => k.id !== knowledge.id);
									}
								}}
							/>
						</div>

						<div class="">
							{#if knowledge.access_control == null}
								<div
									class="w-fit flex gap-1 items-center bg-lightGray-400 text-lightGray-100 font-medium dark:text-white text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
								>
									<PublicIcon />
									<span>{$i18n.t('Public')}</span>
								</div>
							{:else if hasGroupAccess(knowledge)}
								<div
									class="w-fit flex items-center bg-lightGray-400 text-lightGray-100 font-medium dark:text-white text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
								>
									<GroupIcon />
									<span class="ml-1">{$i18n.t('Group')}</span>
								</div>
							{:else}
								<div
									class="w-fit flex gap-1 items-center bg-lightGray-400 text-lightGray-100 font-medium dark:text-white text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
								>
									<PrivateIcon />
									<span>{$i18n.t('Private')}</span>
								</div>
							{/if}
						</div>

						<div class="truncate">
							<div
								class="text-left line-clamp-2 h-fit text-base text-lightGray-100 dark:text-customGray-100 leading-[1.2] mb-1"
							>
								{knowledge.name}
							</div>
							<div
								class="text-left overflow-hidden text-ellipsis line-clamp-1 text-xs text-lightGray-1200 dark:text-customGray-100/50"
							>
								{knowledge.description}
							</div>
						</div>

						<div class="flex items-center">
							<div class="whitespace-nowrap text-xs text-lightGray-1200 dark:text-customGray-100 flex items-center">
								{#if knowledge?.user?.profile_image_url}
									<img
										class="w-3 h-3 rounded-full mr-1"
										src={knowledge?.user?.profile_image_url}
										alt={knowledge?.user?.first_name ?? knowledge?.user?.email ?? $i18n.t('Deleted User')}
									/>
								{/if}

								{$i18n.t('{{name}}', {
									name: capitalizeFirstLetter(
										(knowledge?.user?.first_name && knowledge?.user?.last_name) ? `${knowledge?.user?.first_name} ${knowledge?.user?.last_name}` : knowledge?.user?.email ?  knowledge?.user?.email : $i18n.t('Deleted User')
									)
								})}
							</div>
						</div>

						<div class="flex items-center text-xs text-lightGray-1200 line-clamp-1 dark:text-customGray-100">
							{dayjs(knowledge.updated_at * 1000).format('DD.MM.YYYY')}
						</div>
					</li>
				{/each}
			</ul>
		</div>
        <div class="mt-3 flex justify-end">
            <button
                class=" text-xs w-[168px] h-10 px-3 py-2 transition rounded-lg hover:bg-lightGray-500 text-lightGray-100 bg-lightGray-300 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700 flex justify-center"
                type="button"
                on:click={() => (show = false)}
            >
                <div class=" self-center">   
                    {$i18n.t('Done')}
                </div>
            </button>
        </div>
	</div>
</Modal>
