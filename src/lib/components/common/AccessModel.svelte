<script lang="ts">
	// import { onClickOutside } from '$lib/utils/onClickOutside'; // optional if you have a helper
	import { getContext, onMount } from 'svelte';
	import { getGroups } from '$lib/apis/groups';
    import { onClickOutside } from '$lib/utils';

	const i18n = getContext('i18n');

	import PrivateIcon from '../icons/PrivateIcon.svelte';
	import PublicIcon from '../icons/PublicIcon.svelte';
	import GroupIcon from '../icons/GroupIcon.svelte';
	import { AllSelection } from 'prosemirror-state';
	import CheckmarkIcon from '../icons/CheckmarkIcon.svelte';
    import ChevronDown from '../icons/ChevronDown.svelte';
	import { mobile } from '$lib/stores';

	export let onChange: Function = () => {};
	export let updateModel: Function = () => {};

	export let accessRoles = ['read'];
	export let accessControl = null;

	export let openAccessDropdownId = null;

	// let selectedGroupId = '';
	export let groups = [];

	onMount(async () => {

		if (accessControl === null) {
			accessControl = null;
		} else {
			accessControl = {
				read: {
					group_ids: accessControl?.read?.group_ids ?? [],
					user_ids: accessControl?.read?.user_ids ?? []
				},
				write: {
					group_ids: accessControl?.write?.group_ids ?? [],
					user_ids: accessControl?.write?.user_ids ?? []
				}
			};
		}
	});

	$: onChange(accessControl);

	// $: if (selectedGroupId) {
	// 	onSelectGroup();
	// }

	const toggleGroup = (groupId) => {
		if (accessControl === null || !accessControl.read) {
			accessControl = {
				read: { group_ids: [], user_ids: [] },
				write: { group_ids: [], user_ids: [] }
			};
		}
		const current = accessControl.read.group_ids;
		const updated = current.includes(groupId)
			? current.filter((id) => id !== groupId)
			: [...current, groupId];

		accessControl = {
			...accessControl,
			read: {
				...accessControl.read,
				group_ids: updated
			}
		};
		updateModel(openAccessDropdownId, accessControl);
		// openAccessDropdownId = null;
	};

	$: activeGroupIds = [
		...(accessControl?.read?.group_ids ?? []),
		...(accessControl?.write?.group_ids ?? [])
	];

	function isGroupActive(groupId) {
		if (accessControl !== null && accessControl.read) {
			const isInRead = accessControl.read.group_ids.includes(groupId);
			const isInWrite = accessControl.write.group_ids.includes(groupId);
			return isInRead || isInWrite;
		}
		return false;
	}

	let hoveringGroup = false;
	let hoveringSubmenu = false;

	$: showSubmenu = hoveringGroup || hoveringSubmenu;
	let root;

	let showMobileSubmenu = false;

	let submenuX = 0;
	let submenuY = 0;
	let groupTriggerEl: HTMLElement;

</script>

<div bind:this={root} class="relative w-[1px]" use:onClickOutside={() => (openAccessDropdownId = null)}>
		<div
			class="flex flex-col w-[9rem] absolute right-0 md:-left-20 top-4 bg-lightGray-300 border-lightGray-400 dark:bg-customGray-900 px-1 py-2 border-l border-b border-r dark:border-customGray-700 rounded-lg shadow z-10"
		>
			<button
				type="button"
				class="flex justify-between items-center px-3 py-2 rounded-lg hover:bg-lightGray-700 dark:hover:bg-customGray-950 cursor-pointer"
				on:click={() => {
					accessControl = {
						read: {
							group_ids: []
						},
						write: {
							group_ids: []
						}
					};
					updateModel(openAccessDropdownId, accessControl);
					openAccessDropdownId = null;
				}}
			>
				<div>
					<div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100">
						<PrivateIcon className="size-3" />{$i18n.t('Private')}
						{#if accessControl !== null && activeGroupIds.length < 1}
							<CheckmarkIcon className="size-4" />
						{/if}
					</div>
				</div>
			</button>

			<button
				type="button"
				class="flex justify-start items-center px-3 py-2 rounded-lg hover:bg-lightGray-700 dark:hover:bg-customGray-950 cursor-pointer"
				on:click={() => {
					accessControl = null;
					updateModel(openAccessDropdownId, accessControl);
					openAccessDropdownId = null;
				}}
			>
				<div>
					<div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100">
						<PublicIcon className="size-3" />{$i18n.t('Public')}
						{#if accessControl === null}
							<CheckmarkIcon className="size-4" />
						{/if}
					</div>
				</div>
			</button>
			{#if groups.length > 0}
				<button
					type="button"
					class="relative"
					bind:this={groupTriggerEl}
					on:mouseenter={() => {
						hoveringGroup = true;
						if (groupTriggerEl) {
							const rect = groupTriggerEl.getBoundingClientRect();
							submenuX = rect.right + 8;
							submenuY = rect.top - ((groups.length - 1) * 30);
							showSubmenu = true;
						}
					}}
					on:mouseleave={() => {
						hoveringGroup = false;
						setTimeout(() => {
							if (!hoveringSubmenu) showSubmenu = false;
						}, 100);
					}}
				>
					<button
						on:click={() => {
							if($mobile){
								showMobileSubmenu = true;
							}else{
								openAccessDropdownId = null;
							}
							
						}}
						class="flex w-full justify-start items-center rounded-lg px-3 py-2 hover:bg-gray-100 dark:hover:bg-customGray-950 cursor-pointer"
					>
						<div>
							<div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100">
								<GroupIcon className="size-3" />{$i18n.t('Group')}
								{#if activeGroupIds.length > 0}
									<CheckmarkIcon className="size-4" />
								{/if}
							</div>
						</div>
					</button>
					<div
						class="absolute left-full top-0 w-4 h-full z-10"
						on:mouseenter={() => (hoveringSubmenu = true)}
						on:mouseleave={() => (hoveringSubmenu = false)}
					></div>

					<!-- Submenu -->
					{#if (showSubmenu || showMobileSubmenu)}
						<button
							type="button"
							class="min-w-[8rem] absolute left-[-136px] md:left-[8.8rem] -bottom-2 bg-lightGray-300 dark:bg-customGray-900 border px-1 py-2 border-gray-300 dark:border-customGray-700 rounded-xl shadow z-20 min-w-30"
							
							on:mouseenter={() => (hoveringSubmenu = true)}
							on:mouseleave={() => {
								hoveringSubmenu = false;
								showSubmenu = false;
							}}
						>
							{#each groups as group}
								<button
									type="button"
									on:click={() => toggleGroup(group.id)}
									class="grid grid-cols-[16px_1fr] text-xs w-full gap-1 justify-center px-2 py-2 hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-xl"
								>
									<div>
										{#if activeGroupIds.includes(group.id)}
											<CheckmarkIcon className="size-4" />
										{/if}
									</div>
									<div class="text-left">
										{group.name}
									</div>
								</button>
							{/each}
						</button>
					{/if}
				</button>
			{/if}
		</div>
</div>

