<script lang="ts">
	import { getFilterConfig, updateFilterConfig } from '$lib/apis/filter';
	import { user, settings, config } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getBackendConfig } from '$lib/apis';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	// Filter

	// app.state.config.ENABLE_MESSAGE_FILTER = ENABLE_MESSAGE_FILTER
	// app.state.config.CHAT_FILTER_WORDS_FILE = CHAT_FILTER_WORDS_FILE
	// app.state.config.CHAT_FILTER_WORDS = CHAT_FILTER_WORDS
	// app.state.config.ENABLE_REPLACE_FILTER_WORDS = ENABLE_REPLACE_FILTER_WORDS
	// app.state.config.REPLACE_FILTER_WORDS = REPLACE_FILTER_WORDS

	let ENABLE_MESSAGE_FILTER = false;
	let CHAT_FILTER_WORDS_FILE = '';
	let CHAT_FILTER_WORDS = '';
	let ENABLE_REPLACE_FILTER_WORDS = false;
	let REPLACE_FILTER_WORDS = '';
	let ENABLE_WECHAT_NOTICE = true;
	let WECHAT_APP_SECRET = '';
	let ENABLE_DAILY_USAGES_NOTICE = true;
	let SEND_FILTER_MESSAGE_TYPE = 'text';
	let WECHAT_NOTICE_SUFFIX = '';

	const updateConfigHandler = async () => {
		const res = await updateFilterConfig(localStorage.token, {
			ENABLE_MESSAGE_FILTER: ENABLE_MESSAGE_FILTER,
			CHAT_FILTER_WORDS: CHAT_FILTER_WORDS,
			CHAT_FILTER_WORDS_FILE: CHAT_FILTER_WORDS_FILE,
			ENABLE_REPLACE_FILTER_WORDS: ENABLE_REPLACE_FILTER_WORDS,
			REPLACE_FILTER_WORDS: REPLACE_FILTER_WORDS,
			ENABLE_WECHAT_NOTICE: ENABLE_WECHAT_NOTICE,
			WECHAT_APP_SECRET: WECHAT_APP_SECRET,
			ENABLE_DAILY_USAGES_NOTICE: ENABLE_DAILY_USAGES_NOTICE,
			SEND_FILTER_MESSAGE_TYPE: SEND_FILTER_MESSAGE_TYPE,
			WECHAT_NOTICE_SUFFIX: WECHAT_NOTICE_SUFFIX
		});

		if (res) {
			toast.success($i18n.t('Bad words filter settings updated successfully'));
			config.set(await getBackendConfig());
		}
	};

	onMount(async () => {
		const res = await getFilterConfig(localStorage.token);

		if (res) {
			console.log(res);
			ENABLE_MESSAGE_FILTER = res.ENABLE_MESSAGE_FILTER;
			CHAT_FILTER_WORDS_FILE = res.CHAT_FILTER_WORDS_FILE;
			CHAT_FILTER_WORDS = res.CHAT_FILTER_WORDS;
			ENABLE_REPLACE_FILTER_WORDS = res.ENABLE_REPLACE_FILTER_WORDS;
			REPLACE_FILTER_WORDS = res.REPLACE_FILTER_WORDS;
			ENABLE_WECHAT_NOTICE = res.ENABLE_WECHAT_NOTICE;
			WECHAT_APP_SECRET = res.WECHAT_APP_SECRET;
			ENABLE_DAILY_USAGES_NOTICE = res.ENABLE_DAILY_USAGES_NOTICE;
			SEND_FILTER_MESSAGE_TYPE = res.SEND_FILTER_MESSAGE_TYPE;
			WECHAT_NOTICE_SUFFIX = res.WECHAT_NOTICE_SUFFIX;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		await updateConfigHandler();
		dispatch('save');
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div class="flex flex-col gap-3">
			<div>
				<div class=" mb-1.5 text-sm font-medium">{$i18n.t('Message Filter Settings')}</div>

				<div class=" mb-1.5 py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enable Message Filter')}
					</div>

					<button
						class=" text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							ENABLE_MESSAGE_FILTER = !ENABLE_MESSAGE_FILTER;
						}}
						>{ENABLE_MESSAGE_FILTER ? $i18n.t('On') : $i18n.t('Off')}
					</button>
				</div>

				<div class=" mb-1.5 py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enable Message Bad Words Replacement')}
					</div>

					<button
						class=" text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							ENABLE_REPLACE_FILTER_WORDS = !ENABLE_REPLACE_FILTER_WORDS;
						}}
						>{ENABLE_REPLACE_FILTER_WORDS ? $i18n.t('On') : $i18n.t('Off')}
					</button>
				</div>

				<div class=" mb-1.5 py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enable Daily Usages Notice')}
					</div>

					<button
						class=" text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							ENABLE_DAILY_USAGES_NOTICE = !ENABLE_DAILY_USAGES_NOTICE;
						}}
						>{ENABLE_DAILY_USAGES_NOTICE ? $i18n.t('On') : $i18n.t('Off')}
					</button>
				</div>

				<div class=" mb-1.5 py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enable Message Bad Words wechat Notice')}
					</div>

					<button
						class=" text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							ENABLE_WECHAT_NOTICE = !ENABLE_WECHAT_NOTICE;
						}}
						>{ENABLE_WECHAT_NOTICE ? $i18n.t('On') : $i18n.t('Off')}
					</button>
				</div>

				<div class=" mb-1.5 py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Select restricted message warning acceptance type')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
							bind:value={SEND_FILTER_MESSAGE_TYPE}
							placeholder="Select restricted message warning acceptance type"
						>
							<option value="Text">{'Text'}</option>
							<option value="Markdown">{'Markdown'}</option>
						</select>
					</div>
				</div>

				<div class=" py-1 flex w-full justify-between" />

				<div class=" flex gap-2">
					<div class="w-full">
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('Bad words File')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
									bind:value={CHAT_FILTER_WORDS_FILE}
								/>
							</div>
						</div>
					</div>
					<div class="w-full">
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('Replace bad words')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
									bind:value={REPLACE_FILTER_WORDS}
								/>
							</div>
						</div>
					</div>
				</div>

				<div class=" mb-1.5 py-0.5 flex w-full justify-between" />

				<div>
					<div class=" mb-1.5 text-sm font-medium">{$i18n.t('Wechat App Secret')}</div>
					<SensitiveInput
						placeholder={$i18n.t('Wechat App Secret')}
						bind:value={WECHAT_APP_SECRET}
					/>
				</div>

				<div class=" mb-1.5 py-0.5 flex w-full justify-between" />

				<div>
					<div class=" mb-1.5 text-sm font-medium">{$i18n.t('Wechat Notice Suffix')}</div>
					<input
						class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
						type="text"
						placeholder={$i18n.t('Wechat Notice Suffix')}
						bind:value={WECHAT_NOTICE_SUFFIX}
					/>
				</div>

				<div class=" mb-1.5 py-0.5 flex w-full justify-between" />

				<div>
					<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Bad words Template')}</div>
					<textarea
						bind:value={CHAT_FILTER_WORDS}
						class="w-full rounded-lg px-4 py-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none resize-none"
						rows="16"
					/>
				</div>
			</div>
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
