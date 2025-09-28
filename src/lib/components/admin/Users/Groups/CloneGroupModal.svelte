<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
    import Checkbox from '$lib/components/common/Checkbox.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	export let onSubmit: Function = () => {};
	export let show = false;
	export let group = null;
	let loading = false;
	export let name = '';
    export let clone_members = true;
    export let clone_settings = true;
	const submitHandler = async () => {
		loading = true;
		const clone_data = {
			name,
			clone_members,
			clone_settings
		};
		await onSubmit(clone_data);
		loading = false;
		show = false;
	};
    const init = () => {
		if (group && i18n?.t) {
			name = `${i18n.t('Copy of')} ${group.name}`;
		} else if (group) {
			// Fallback if i18n is not available yet
			name = `Copy of ${group.name}`;
		}
	};
	$: if (show && group) {
		init();
	}
	onMount(() => {
		if (group) {
			init();
		}
	});
    $: cloneDisabled = !clone_members && !clone_settings;
</script>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 mb-1.5">
			<div class=" text-lg font-medium self-center font-primary">
                {i18n?.t ? i18n.t('Clone User Group') : 'Clone User Group'}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
                    <div class="flex flex-col space-y-4">
                        <div class="flex flex-col">
                            <label for="group-name" class="text-sm font-medium">{i18n?.t ? i18n.t('Group Name') : 'Group Name'}</label>
                            <input
                                id="group-name"
                                type="text"
                                class="w-full mt-1 bg-transparent dark:text-white rounded-lg"
                                placeholder={i18n?.t ? i18n.t('Enter group name') : 'Enter group name'}
                                bind:value={name}
                                required
                            />
                        </div>

                        <div class="flex flex-col space-y-2">
                            <label class="text-sm font-medium">{i18n?.t ? i18n.t('Clone Options') : 'Clone Options'}</label>
                            <Checkbox bind:checked={clone_members} label={i18n?.t ? i18n.t('Clone group members') : 'Clone group members'} />
                            <Checkbox bind:checked={clone_settings} label={i18n?.t ? i18n.t('Clone group settings') : 'Clone group settings'} />
                        </div>
                    </div>


					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading || cloneDisabled
								? ' cursor-not-allowed opacity-50'
								: ''}"
							type="submit"
							disabled={loading || cloneDisabled}
						>
							{i18n?.t ? i18n.t('Clone') : 'Clone'}

							{#if loading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
