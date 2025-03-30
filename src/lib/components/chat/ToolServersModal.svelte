<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config, toolServers } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import Collapsible from '../common/Collapsible.svelte';

	export let show = false;

	const i18n = getContext('i18n');
</script>

<Modal bind:show size="md">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class=" text-lg font-medium self-center">{$i18n.t('Available Tool Servers')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="px-5 pb-5 w-full flex flex-col justify-center">
			<div class=" text-sm dark:text-gray-300 mb-2">
				Open WebUI can use tools provided by any OpenAPI server. <br /><a
					class="underline"
					href="https://github.com/open-webui/openapi-servers"
					target="_blank">Learn more about OpenAPI tool servers.</a
				>
			</div>
			<div class=" text-sm dark:text-gray-300 mb-1">
				{#each $toolServers as toolServer}
					<Collapsible buttonClassName="w-full" chevron>
						<div>
							<div class="text-base font-medium dark:text-gray-100 text-gray-800">
								{toolServer?.openapi?.info?.title} - v{toolServer?.openapi?.info?.version}
							</div>

							<div class="text-sm text-gray-500">
								{toolServer?.openapi?.info?.description}
							</div>

							<div class="text-sm text-gray-500">
								{toolServer?.url}
							</div>
						</div>

						<div slot="content">
							{#each toolServer?.specs ?? [] as tool_spec}
								<div class="my-1">
									<div class="font-medium text-gray-800 dark:text-gray-100">
										{tool_spec?.name}
									</div>

									<div>
										{tool_spec?.description}
									</div>
								</div>
							{/each}
						</div>
					</Collapsible>
				{/each}
			</div>
		</div>
	</div>
</Modal>
