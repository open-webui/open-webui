<script lang="ts">
	import { getContext } from 'svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { settings, mobile, commentDrafts } from '$lib/stores';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import MentionList from '$lib/components/channel/MessageInput/MentionList.svelte';
	import { getSuggestionRenderer } from '$lib/components/common/RichTextInput/suggestions';
	import { commentsRequest, resourceQuery, type CommentResource } from '$lib/apis/comments';
	export let resource: CommentResource;
	export let draftKey: string;
	export let contextLabel = '';
	export let quote = '';
	export let onClearContext: (() => void) | null = null;
	export let initialContent = '';
	export let submitLabel = 'Comment';
	export let onSubmitted: () => void = () => {};
	export function focus() {
		editor?.commands.focus();
	}
	export let onSubmit: (content: string, tempId: string) => Promise<void>;
	export let onCancel: (() => void) | null = null;
	const i18n = getContext<any>('i18n');
	let content = commentDrafts.get(draftKey)?.content ?? initialContent;
	let tempId = commentDrafts.get(draftKey)?.temp_id ?? crypto.randomUUID();
	let editor: import('@tiptap/core').Editor | null = null;
	let saving = false;
	let submitted = false;
	let error = '';
	const suggestions = [
		{
			char: '@',
			render: getSuggestionRenderer(MentionList, {
				i18n,
				userSuggestions: true,
				modelSuggestions: false,
				loadUsers: (query: string, signal: AbortSignal) =>
					commentsRequest(
						`/mentions?${resourceQuery(resource)}&query=${encodeURIComponent(query)}`,
						'GET',
						undefined,
						signal
					)
			})
		}
	];
	const remember = () => {
		if (submitted) return;
		if (content.trim()) commentDrafts.set(draftKey, { content, temp_id: tempId });
		else commentDrafts.delete(draftKey);
	};
	const submit = async () => {
		if (saving || !content.trim()) return;
		saving = true;
		error = '';
		remember();
		try {
			await onSubmit(content, tempId);
			submitted = true;
			content = '';
			commentDrafts.delete(draftKey);
			tempId = crypto.randomUUID();
			editor?.commands.clearContent();
			onSubmitted();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			saving = false;
		}
	};
</script>

<div
	class="w-full"
	on:focusout={(event) => {
		if (
			onCancel &&
			!saving &&
			!content.trim() &&
			!event.currentTarget.contains(event.relatedTarget as Node | null)
		)
			onCancel();
	}}
>
	<div class="min-w-0 flex-1">
		<div
			dir={$settings?.chatDirection === 'RTL'
				? 'rtl'
				: $settings?.chatDirection === 'LTR'
					? 'ltr'
					: 'auto'}
			class="relative rounded-2xl border border-gray-100/50 dark:border-gray-850/50 hover:border-gray-200 focus-within:border-gray-100 hover:dark:border-gray-800 focus-within:dark:border-gray-800 transition bg-white/5 dark:bg-gray-500/5 ps-3 pb-2.5 {contextLabel ||
			quote
				? 'pt-1'
				: 'pt-2.5'} {($settings?.highContrastMode ?? false)
				? 'focus-within:outline focus-within:outline-2 focus-within:-outline-offset-2 focus-within:outline-blue-500'
				: ''}"
		>
			{#if contextLabel || quote}
				<div class="pb-2 pe-3 text-left w-full flex flex-col">
					<div
						class="flex items-center justify-between gap-2 text-xs text-gray-500 dark:text-gray-400"
					>
						<span class="truncate">{contextLabel}</span>{#if onClearContext}<button
								type="button"
								class="flex h-6 shrink-0 items-center justify-center p-0 hover:text-gray-700 dark:hover:text-gray-200"
								aria-label={$i18n.t('Remove context')}
								on:click={onClearContext}><XMark className="size-3.5" /></button
							>{/if}
					</div>
					{#if quote}<div
							class="mb-1 mt-1 max-h-20 overflow-auto border-l-2 border-gray-200 dark:border-gray-700 ps-2 text-xs text-gray-500 whitespace-pre-wrap"
						>
							{quote}
						</div>{/if}
				</div>
			{/if}
			<div class={submitLabel === 'Save' ? 'pe-16' : 'pe-12'}>
				<div
					class="scrollbar-hidden rtl:text-right ltr:text-left bg-transparent dark:text-gray-100 outline-hidden w-full resize-none h-fit max-h-96 overflow-auto"
				>
					<RichTextInput
						id={`comment-input-${tempId}`}
						bind:editor
						value={content}
						{suggestions}
						placeholder={$i18n.t('Add a comment…')}
						className="input-prose min-h-5 h-full text-[0.8125rem]! leading-5! [&_.tiptap>p:first-child]:mt-0! [&_.tiptap>p:last-child]:mb-0!"
						editable={!saving}
						showFormattingToolbar={false}
						onChange={(value) => {
							if (submitted) return;
							content = value.md;
							remember();
						}}
						on:keydown={(event) => {
							const e = event.detail.event;
							if (
								e.isComposing ||
								e.keyCode === 229 ||
								editor?.view.composing ||
								document.getElementById('suggestions-container')
							)
								return;
							if (
								e.key === 'Enter' &&
								!e.shiftKey &&
								(($settings?.ctrlEnterToSend ?? false) ? e.metaKey || e.ctrlKey : !$mobile)
							) {
								e.preventDefault();
								submit();
							}
						}}
					/>
				</div>
			</div>
			{#if error}<p role="alert" class="py-1 text-xs text-red-500">{error}</p>{/if}
			<div class="absolute bottom-2 end-2.5 flex items-center">
				<div class="flex items-center gap-2">
					<button
						type="button"
						aria-label={$i18n.t(submitLabel)}
						title={$i18n.t(submitLabel)}
						class="flex h-6 shrink-0 items-center justify-center bg-black text-white transition hover:bg-gray-900 disabled:bg-gray-200 disabled:text-gray-500 dark:bg-white dark:text-black dark:hover:bg-gray-100 dark:disabled:bg-gray-600 dark:disabled:text-gray-850 {submitLabel ===
						'Save'
							? 'rounded-md px-2 text-xs'
							: 'size-6 rounded-full'}"
						disabled={saving || !content.trim() || content.length > 20000}
						on:click={submit}
					>
						{#if submitLabel === 'Save'}
							{$i18n.t(submitLabel)}
						{:else}
							<svg aria-hidden="true" viewBox="0 0 16 16" fill="currentColor" class="size-4">
								<path
									fill-rule="evenodd"
									d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
									clip-rule="evenodd"
								/>
							</svg>
						{/if}
					</button>
				</div>
			</div>
		</div>
	</div>
</div>
