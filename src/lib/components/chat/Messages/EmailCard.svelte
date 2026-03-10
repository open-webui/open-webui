<script lang="ts">
	import { getContext } from 'svelte';
	import { tick, afterUpdate, onDestroy } from 'svelte';
	import { copyToClipboard } from '$lib/utils';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Envelope from '$lib/components/icons/Envelope.svelte';
	import PaperPlane from '$lib/components/icons/PaperPlane.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	const i18n = getContext('i18n');

	export let token: { raw: string; subject: string; to: string; body: string };
	export let edit = true;
	export let done = true;
	export let stickyButtonsClassName = 'top-0';

	export let onSave: Function = () => {};

	let copied = false;
	let sentinelEl: HTMLElement;
	let isStuck = false;
	let observer: IntersectionObserver;

	let isEditing = false;
	let editBody = '';
	let editSubject = '';
	let textareaEl: HTMLTextAreaElement;

	let saveStatus = '';
	let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;

	// Email block is complete when the closing tag is present or the full message is done
	$: emailDone = done || (token?.raw ?? '').includes('</email>');

	// Start editing automatically when email block finishes
	$: if (emailDone && edit && !isEditing) {
		startEditing();
	}

	const resizeTextarea = () => {
		if (!textareaEl) return;
		textareaEl.style.height = 'auto';
		textareaEl.style.height = textareaEl.scrollHeight + 'px';
	};

	const saveEmail = () => {
		saveStatus = 'saving';
		const oldBody = token.body;
		const oldSubject = token.subject;

		// Rebuild the raw token with updated values
		let newRaw = '<email>\n';
		if (editSubject) newRaw += `<subject>${editSubject}</subject>\n`;
		if (token.to) newRaw += `<to>${token.to}</to>\n`;
		newRaw += `\n${editBody}\n</email>`;

		onSave({
			raw: token.raw,
			oldContent: oldBody,
			newContent: editBody,
			newRaw
		});

		// Update token in place so the card reflects changes
		token.body = editBody;
		token.subject = editSubject;
		token.raw = newRaw;

		setTimeout(() => {
			saveStatus = 'saved';
			setTimeout(() => {
				saveStatus = '';
			}, 1500);
		}, 300);
	};

	const debouncedSave = () => {
		if (autoSaveTimer) clearTimeout(autoSaveTimer);
		saveStatus = '';
		autoSaveTimer = setTimeout(() => {
			saveEmail();
		}, 800);
	};

	const startEditing = async () => {
		editBody = token.body;
		editSubject = token.subject;
		isEditing = true;
		await tick();
		resizeTextarea();
	};

	const mailtoHref = () => {
		const params = new URLSearchParams();
		const subject = isEditing ? editSubject : token.subject;
		const body = isEditing ? editBody : token.body;
		if (subject) params.set('subject', subject);
		if (body) params.set('body', body);
		const paramStr = params.toString();
		const to = token.to || '';
		return `mailto:${to}${paramStr ? '?' + paramStr : ''}`;
	};

	const handleCopy = () => {
		const body = isEditing ? editBody : token.body;
		copyToClipboard(body);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	};

	afterUpdate(() => {
		if (sentinelEl && !observer) {
			observer = new IntersectionObserver(
				([entry]) => {
					isStuck = !entry.isIntersecting;
				},
				{ threshold: 0 }
			);
			observer.observe(sentinelEl);
		}
	});

	onDestroy(() => {
		if (autoSaveTimer) clearTimeout(autoSaveTimer);
		if (observer) observer.disconnect();
	});
</script>

<div>
	<div
		class="relative flex flex-col rounded-2xl border border-gray-200 dark:border-gray-800 my-0.5 bg-neutral-50 dark:bg-gray-850 overflow-clip"
	>
		<div bind:this={sentinelEl} class="h-0 w-full shrink-0" aria-hidden="true"></div>

		<div
			class="email-card-header sticky {stickyButtonsClassName} left-0 right-0 z-10 py-2 px-3 gap-2 flex items-center justify-between w-full text-sm text-gray-600 dark:text-gray-300 bg-neutral-50 dark:bg-gray-850 {isStuck
				? 'border-b border-gray-200/60 dark:border-gray-700/40'
				: 'rounded-t-2xl'}"
		>
			<div class="flex items-center gap-2 truncate">
				{#if !emailDone}
					<Spinner className="size-3.5 shrink-0" />
				{:else}
					<Envelope className="size-3.5 shrink-0" />
				{/if}
				<span class="font-semibold truncate">{$i18n.t('Email')}</span>
			</div>

			{#if emailDone}
				<div class="flex items-center gap-0.5 shrink-0">
					{#if isEditing && saveStatus}
						<span class="px-2 py-0.5 text-xs text-gray-400 dark:text-gray-500 select-none">
							{#if saveStatus === 'saving'}
								{$i18n.t('Saving...')}
							{:else if saveStatus === 'saved'}
								{$i18n.t('Saved')}
							{/if}
						</span>
					{/if}

					<Tooltip content={$i18n.t('Copy')}>
						<button
							class="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition"
							on:click={handleCopy}
						>
							{#if copied}
								<Check className="size-4" strokeWidth="2" />
							{:else}
								<Clipboard className="size-4" strokeWidth="1.5" />
							{/if}
						</button>
					</Tooltip>

					<Tooltip content={$i18n.t('Open in mail app')}>
						<a
							href={mailtoHref()}
							class="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition"
						>
							<PaperPlane className="size-4" strokeWidth="1.5" />
						</a>
					</Tooltip>
				</div>
			{/if}
		</div>

		<div class="px-5 pb-4">
			{#if token.to}
				<div class="flex gap-2 text-sm py-2 text-gray-500 dark:text-gray-400">
					<span class="font-medium shrink-0">{$i18n.t('To')}:</span>
					<span class="text-gray-700 dark:text-gray-200">{token.to}</span>
				</div>
			{/if}

			{#if isEditing}
				<div class="flex gap-2 text-sm py-2 border-b border-gray-200 dark:border-gray-700">
					<span class="font-medium text-gray-500 dark:text-gray-400 shrink-0"
						>{$i18n.t('Subject')}:</span
					>
					<input
						type="text"
						class="flex-1 bg-transparent font-semibold text-gray-800 dark:text-gray-100 outline-none border-none p-0"
						bind:value={editSubject}
						on:input={debouncedSave}
					/>
				</div>

				<textarea
					bind:this={textareaEl}
					class="w-full bg-transparent whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 pt-3 outline-none border-none resize-none"
					bind:value={editBody}
					on:input={() => {
						resizeTextarea();
						debouncedSave();
					}}
				></textarea>
			{:else}
				{#if token.subject}
					<div class="flex gap-2 text-sm py-2 border-b border-gray-200 dark:border-gray-700">
						<span class="font-medium text-gray-500 dark:text-gray-400 shrink-0"
							>{$i18n.t('Subject')}:</span
						>
						<span class="font-semibold text-gray-800 dark:text-gray-100">{token.subject}</span>
					</div>
				{/if}

				<div class="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 pt-3">
					{token.body}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.email-card-header::before {
		content: '';
		position: absolute;
		bottom: 100%;
		left: 0;
		right: 0;
		height: 2.5rem;
		background: inherit;
	}
</style>
