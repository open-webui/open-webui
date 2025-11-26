<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';

	import UserPlusSolid from '$lib/components/icons/UserPlusSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Hashtag from '../icons/Hashtag.svelte';
	import Lock from '../icons/Lock.svelte';
	import UserList from './ChannelInfoModal/UserList.svelte';

	export let show = false;
	export let channel = null;

	const submitHandler = async () => {};

	const init = () => {};

	$: if (show) {
		init();
	}

	onMount(() => {
		init();
	});
</script>

{#if channel}
	<Modal size="sm" bind:show>
		<div>
			<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 mb-1.5">
				<div class="self-center text-base">
					<div class="flex items-center gap-0.5 shrink-0">
						<div class=" size-4 justify-center flex items-center">
							{#if channel?.access_control === null}
								<Hashtag className="size-3.5" strokeWidth="2.5" />
							{:else}
								<Lock className="size-5.5" strokeWidth="2" />
							{/if}
						</div>

						<div
							class=" text-left self-center overflow-hidden w-full line-clamp-1 capitalize flex-1"
						>
							{channel.name}
						</div>
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

			<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
				<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
					<form
						class="flex flex-col w-full"
						on:submit={(e) => {
							e.preventDefault();
							submitHandler();
						}}
					>
						<div class="flex flex-col w-full h-full pb-2">
							<UserList {channel} />
						</div>
					</form>
				</div>
			</div>
		</div>
	</Modal>
{/if}
