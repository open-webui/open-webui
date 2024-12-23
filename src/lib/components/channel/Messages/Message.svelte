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

	export let message;
	export let showUserProfile = true;

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

{#if message}
	<div
		class="flex flex-col justify-between px-5 {showUserProfile
			? 'pt-1.5 pb-0.5'
			: ''} w-full {($settings?.widescreenMode ?? null)
			? 'max-w-full'
			: 'max-w-5xl'} mx-auto group hover:bg-gray-500/5 transition"
	>
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
						<span
							class=" text-xs self-center invisible group-hover:visible text-gray-500 font-medium first-letter:capitalize"
						>
							{dayjs(message.created_at / 1000000).format('HH:mm')}
						</span>
					{/if}
				{/if}
			</div>

			<div class="flex-auto w-0 pl-1">
				{#if showUserProfile}
					<Name>
						<span class="text-sm">
							{message?.user?.name}
						</span>

						{#if message.created_at}
							<span
								class=" self-center invisible group-hover:visible text-gray-400 text-xs font-medium first-letter:capitalize ml-0.5 -mt-0.5"
							>
								{formatDate(message.created_at / 1000000)}
							</span>
						{/if}
					</Name>
				{/if}

				<div class="markdown-prose">
					<Markdown id={message.id} content={message.content} />
				</div>
			</div>
		</div>
	</div>
{/if}
