<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { getChannelPinnedMessages, pinMessage } from '$lib/apis/channels';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';

	export let show = false;
	export let channel = null;
	export let onPin = (messageId, pinned) => {};

	let page = 1;
	let pinnedMessages = null;

	let allItemsLoaded = false;
	let loading = false;

	const getPinnedMessages = async () => {
		if (!channel) return;
		if (allItemsLoaded) return;

		loading = true;
		try {
			const res = await getChannelPinnedMessages(localStorage.token, channel.id, page).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				pinnedMessages = [...(pinnedMessages ?? []), ...res];
			}

			if (res.length === 0) {
				allItemsLoaded = true;
			}
		} catch (error) {
			console.error('Error fetching pinned messages:', error);
		} finally {
			loading = false;
		}
	};

	const init = () => {
		page = 1;
		pinnedMessages = null;
		allItemsLoaded = false;

		getPinnedMessages();
	};

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
						{$i18n.t('Pinned Messages')}
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
					<div class="flex flex-col w-full h-full pb-2 gap-1">
						{#if pinnedMessages === null}
							<div class="my-10">
								<Spinner className="size-5" />
							</div>
						{:else}
							<div
								class="flex flex-col gap-2 max-h-[60vh] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-700 scrollbar-track-transparent py-2"
							>
								{#if pinnedMessages.length === 0}
									<div class=" text-center text-xs text-gray-500 dark:text-gray-400 py-6">
										{$i18n.t('No pinned messages')}
									</div>
								{:else}
									{#each pinnedMessages as message, messageIdx (message.id)}
										<Message
											className="rounded-xl px-2"
											{message}
											{channel}
											onPin={async (message) => {
												pinnedMessages = pinnedMessages.filter((m) => m.id !== message.id);
												onPin(message.id, !message.is_pinned);

												const updatedMessage = await pinMessage(
													localStorage.token,
													message.channel_id,
													message.id,
													!message.is_pinned
												).catch((error) => {
													toast.error(`${error}`);
													return null;
												});

												init();
											}}
											onReaction={false}
											onThread={false}
											onReply={false}
											onEdit={false}
											onDelete={false}
										/>

										{#if messageIdx === pinnedMessages.length - 1 && !allItemsLoaded}
											<Loader
												on:visible={(e) => {
													console.log('visible');
													if (!loading) {
														page += 1;
														getPinnedMessages();
													}
												}}
											>
												<div
													class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
												>
													<Spinner className=" size-4" />
													<div class=" ">{$i18n.t('Loading...')}</div>
												</div>
											</Loader>
										{/if}
									{/each}
								{/if}
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</Modal>
{/if}
