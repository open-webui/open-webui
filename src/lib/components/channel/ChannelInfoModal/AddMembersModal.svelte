<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { addMembersById } from '$lib/apis/channels';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import MemberSelector from '$lib/components/workspace/common/MemberSelector.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let show = false;
	export let channel = null;

	export let onUpdate = () => {};

	let groupIds = [];
	let userIds = [];

	let loading = false;

	const submitHandler = async () => {
		const res = await addMembersById(localStorage.token, channel.id, {
			user_ids: userIds,
			group_ids: groupIds
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Members added successfully'));
			onUpdate();
			show = false;
		} else {
			toast.error($i18n.t('Failed to add members'));
		}
	};

	const reset = () => {
		userIds = [];
		groupIds = [];
		loading = false;
	};

	$: if (!show) {
		reset();
	}
</script>

{#if channel}
	<Modal size="sm" bind:show>
		<div>
			<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 mb-1.5">
				<div class="self-center text-base">
					<div class="flex items-center gap-0.5 shrink-0">
						{$i18n.t('Add Members')}
					</div>
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

			<div class="flex flex-col md:flex-row w-full px-3 pb-4 md:space-x-4 dark:text-gray-200">
				<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
					<form
						class="flex flex-col w-full"
						on:submit={(e) => {
							e.preventDefault();
							submitHandler();
						}}
					>
						<div class="flex flex-col w-full h-full pb-2">
							<MemberSelector bind:userIds bind:groupIds includeGroups={true} />
						</div>

						<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
									? ' cursor-not-allowed'
									: ''}"
								type="submit"
								disabled={loading}
							>
								{$i18n.t('Add')}

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
{/if}
