<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import isToday from 'dayjs/plugin/isToday';
	import isYesterday from 'dayjs/plugin/isYesterday';

	dayjs.extend(relativeTime);
	dayjs.extend(isToday);
	dayjs.extend(isYesterday);

	import { getContext } from 'svelte';
	const i18n = getContext<Writable<i18nType>>('i18n');

	import { settings } from '$lib/stores';

	import { WEBUI_BASE_URL } from '$lib/constants';

	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import Name from '$lib/components/chat/Messages/Name.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	export let message;
	export let showUserProfile = true;

	export let onDelete: Function = () => {};
	export let onEdit: Function = () => {};

	let edit = false;
	let editedContent = null;
	let showDeleteConfirmDialog = false;

	const formatDate = (inputDate) => {
		const date = dayjs(inputDate);
		const now = dayjs();

		if (date.isToday()) {
			return `Today at ${date.format('HH:mm')}`;
		} else if (date.isYesterday()) {
			return `Yesterday at ${date.format('HH:mm')}`;
		} else {
			return `${date.format('DD/MM/YYYY')} at ${date.format('HH:mm')}`;
		}
	};
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	title={$i18n.t('Delete Message')}
	message={$i18n.t('Are you sure you want to delete this message?')}
	onConfirm={async () => {
		await onDelete(message.id);
	}}
/>

{#if message}
	<div
		class="flex flex-col justify-between px-5 {showUserProfile
			? 'pt-1.5 pb-0.5'
			: ''} w-full {($settings?.widescreenMode ?? null)
			? 'max-w-full'
			: 'max-w-5xl'} mx-auto group hover:bg-gray-500/5 transition relative"
	>
		{#if !edit}
			<div class=" absolute invisible group-hover:visible right-1 -top-2 z-30">
				<div
					class="flex gap-1 rounded-lg bg-white dark:bg-gray-850 shadow-md p-0.5 border border-gray-100 dark:border-gray-800"
				>
					<button
						class="hover:bg-gray-100 dark:hover:bg-gray-800 transition rounded-lg p-1"
						on:click={() => {
							edit = true;
							editedContent = message.content;
						}}
					>
						<Pencil />
					</button>

					<button
						class="hover:bg-gray-100 dark:hover:bg-gray-800 transition rounded-lg p-1"
						on:click={() => (showDeleteConfirmDialog = true)}
					>
						<GarbageBin />
					</button>
				</div>
			</div>
		{/if}

		<div
			class=" flex w-full message-{message.id}"
			id="message-{message.id}"
			dir={$settings.chatDirection}
		>
			<div
				class={`flex-shrink-0 ${($settings?.chatDirection ?? 'LTR') === 'LTR' ? 'mr-3' : 'ml-3'}`}
			>
				{#if showUserProfile}
					<ProfileImage
						src={message.user?.profile_image_url ??
							($i18n.language === 'dg-DG' ? `/doge.png` : `${WEBUI_BASE_URL}/static/favicon.png`)}
						className={'size-8 translate-y-1 mr-0.5'}
					/>
				{:else}
					<!-- <div class="w-7 h-7 rounded-full bg-transparent" /> -->

					{#if message.created_at}
						<div
							class="mt-1.5 flex items-center text-xs self-center invisible group-hover:visible text-gray-500 font-medium first-letter:capitalize"
						>
							<Tooltip
								content={dayjs(message.created_at / 1000000).format('dddd, DD MMMM YYYY HH:mm')}
							>
								{dayjs(message.created_at / 1000000).format('HH:mm')}
							</Tooltip>
						</div>
					{/if}
				{/if}
			</div>

			<div class="flex-auto w-0 pl-1">
				{#if showUserProfile}
					<Name>
						<div class="text-sm">
							{message?.user?.name}
						</div>

						{#if message.created_at}
							<div
								class=" self-center text-xs invisible group-hover:visible text-gray-400 font-medium first-letter:capitalize ml-0.5 -mt-0.5"
							>
								<Tooltip
									content={dayjs(message.created_at / 1000000).format('dddd, DD MMMM YYYY HH:mm')}
								>
									{formatDate(message.created_at / 1000000)}
								</Tooltip>
							</div>
						{/if}
					</Name>
				{/if}

				{#if edit}
					<div class="py-2">
						<Textarea
							class=" bg-transparent outline-none w-full resize-none"
							bind:value={editedContent}
							onKeydown={(e) => {
								if (e.key === 'Escape') {
									document.getElementById('close-edit-message-button')?.click();
								}

								const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
								const isEnterPressed = e.key === 'Enter';

								if (isCmdOrCtrlPressed && isEnterPressed) {
									document.getElementById('confirm-edit-message-button')?.click();
								}
							}}
						/>
						<div class=" mt-2 mb-1 flex justify-end text-sm font-medium">
							<div class="flex space-x-1.5">
								<button
									id="close-edit-message-button"
									class="px-4 py-2 bg-white dark:bg-gray-900 hover:bg-gray-100 text-gray-800 dark:text-gray-100 transition rounded-3xl"
									on:click={() => {
										edit = false;
										editedContent = null;
									}}
								>
									{$i18n.t('Cancel')}
								</button>

								<button
									id="confirm-edit-message-button"
									class=" px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
									on:click={async () => {
										onEdit(message.id, editedContent);
										edit = false;
										editedContent = null;
									}}
								>
									{$i18n.t('Save')}
								</button>
							</div>
						</div>
					</div>
				{:else}
					<div class=" min-w-full markdown-prose">
						<Markdown id={message.id} content={message.content} />
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
