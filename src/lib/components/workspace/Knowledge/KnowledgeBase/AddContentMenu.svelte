<script lang="ts">
    import { DropdownMenu } from 'bits-ui';
    import { flyAndScale } from '$lib/utils/transitions';
    import { getContext, createEventDispatcher } from 'svelte';
    import { onMount } from 'svelte';
    const dispatch = createEventDispatcher();

    // Components
    import Dropdown from '$lib/components/common/Dropdown.svelte';
    import Tooltip from '$lib/components/common/Tooltip.svelte';
    // Icons
    import ArrowUpCircle from '$lib/components/icons/ArrowUpCircle.svelte';
    import BarsArrowUp from '$lib/components/icons/BarsArrowUp.svelte';
    import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
    import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
    import LinkIcon from '$lib/components/icons/LinkIcon.svelte'; 

    const i18n = getContext('i18n');
    export let onClose: Function = () => {};

    // State
    let show = false;
    let showDriveLinkModal = false;
    let googleDriveLink = '';
    let driveLinkInput: HTMLInputElement;

    // Drive link modal functions
    function closeDriveLinkModal() {
        showDriveLinkModal = false;
        googleDriveLink = '';
    }

    function saveDriveLink() {
        if (googleDriveLink) {
			 console.log(googleDriveLink, 'Google Drive link saved')
            dispatch('addDriveLink', { link: googleDriveLink });
            closeDriveLinkModal();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            closeDriveLinkModal();
        }
    }

    // Focus input when modal opens
    onMount(() => {
        if (showDriveLinkModal && driveLinkInput) {
            driveLinkInput.focus();
        }
    });
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
	align="end"
>
	<Tooltip content={$i18n.t('Add Content')}>
		<button
			class=" p-1.5 rounded-xl hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition font-medium text-sm flex items-center space-x-1"
			on:click={(e) => {
				e.stopPropagation();
				show = true;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
				/>
			</svg>
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-44 rounded-xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white shadow"
			sideOffset={4}
			side="bottom"
			align="end"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					dispatch('upload', { type: 'files' });
				}}
			>
				<ArrowUpCircle strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Upload files')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					dispatch('upload', { type: 'directory' });
				}}
			>
				<FolderOpen strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Upload directory')}</div>
			</DropdownMenu.Item>

			<Tooltip
				content={$i18n.t(
					'This option will delete all existing files in the collection and replace them with newly uploaded files.'
				)}
				className="w-full"
			>
				<DropdownMenu.Item
					class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					on:click={() => {
						dispatch('sync', { type: 'directory' });
					}}
				>
					<ArrowPath strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Sync directory')}</div>
				</DropdownMenu.Item>
			</Tooltip>

			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					dispatch('upload', { type: 'text' });
				}}
			>
				<BarsArrowUp strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Add text content')}</div>
			</DropdownMenu.Item>
			<!-- Add the Drive Link option to the dropdown menu -->
			<DropdownMenu.Item
				
				class="flex gap-2 items-center px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => (showDriveLinkModal = true)}
			>
				<LinkIcon strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Add Drive Link')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>

{#if showDriveLinkModal}
    <div
        class="fixed inset-0 bg-black/50 z-50 backdrop-blur-sm transition-all"
        on:click={closeDriveLinkModal}
        on:keydown={handleKeydown}
    >
        <div
            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-white dark:bg-gray-850 rounded-xl p-6 shadow-xl"
            on:click|stopPropagation
        >
            <h3 class="text-lg font-semibold mb-4 dark:text-white">
                {$i18n.t('Add Google Drive Link')}
            </h3>

            <input
                bind:this={driveLinkInput}
                type="text"
                class="w-full px-4 py-2 rounded-lg border dark:border-gray-700 dark:bg-gray-900 dark:text-white mb-4"
                placeholder="https://drive.google.com/..."
                bind:value={googleDriveLink}
            />

            <div class="flex justify-end gap-2">
                <button
                    class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                    on:click={closeDriveLinkModal}
                >
                    {$i18n.t('Cancel')}
                </button>
                <button
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                    on:click={saveDriveLink}
                >
                    {$i18n.t('Save Link')}
                </button>
            </div>
        </div>
    </div>
{/if}