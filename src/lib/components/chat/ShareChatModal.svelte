<script lang="ts">
	import { getContext } from 'svelte';
	import { models, config, user } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import {
		deleteSharedChatById,
		getChatById,
		shareChatById,
		getChatAccessGrants,
		updateChatAccessGrants
	} from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';

	export let chatId;

	let chat = null;
	let shareUrl = null;
	let copied = false;
	let accessGrants: any[] = [];
	const i18n = getContext('i18n');

	const shareLocalChat = async () => {
		try {
			const sharedChat = await shareChatById(localStorage.token, chatId);
			if (sharedChat?.share_id) {
				shareUrl = `${window.location.origin}/s/${sharedChat.share_id}`;
				chat = await getChatById(localStorage.token, chatId);
				await handleCopy(shareUrl);
				return shareUrl;
			}
		} catch (e) {
			console.error('Failed to share chat:', e);
			toast.error(`${e}`);
		}
		return null;
	};

	const handleCopy = async (urlToCopy?: string) => {
		const targetUrl = urlToCopy || shareUrl;
		if (!targetUrl) return;

		const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
		if (isSafari) {
			try {
				await navigator.clipboard.write([
					new ClipboardItem({
						'text/plain': new Blob([targetUrl], { type: 'text/plain' })
					})
				]);
			} catch {
				await copyToClipboard(targetUrl);
			}
		} else {
			await copyToClipboard(targetUrl);
		}

		copied = true;
		toast.success($i18n.t('Share URL copied to clipboard!'));
		setTimeout(() => {
			copied = false;
		}, 2000);
	};

	const loadAccessGrants = async () => {
		if (!chatId) return;
		try {
			accessGrants = (await getChatAccessGrants(localStorage.token, chatId)) ?? [];
		} catch (e) {
			console.error('Failed to load access grants', e);
			accessGrants = [];
		}
	};

	const saveAccessGrants = async () => {
		try {
			await updateChatAccessGrants(localStorage.token, chatId, accessGrants);
			toast.success($i18n.t('Access updated'));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	export let show = false;

	const isDifferentChat = (_chat) => {
		if (!chat) return true;
		if (!_chat) return false;
		return chat.id !== _chat.id || chat.share_id !== _chat.share_id;
	};

	$: if (show) {
		(async () => {
			if (chatId) {
				const _chat = await getChatById(localStorage.token, chatId);
				if (isDifferentChat(_chat)) {
					chat = _chat;
				}
				if (chat?.share_id) {
					shareUrl = `${window.location.origin}/s/${chat.share_id}`;
				} else {
					shareUrl = null;
				}
				await loadAccessGrants();
			} else {
				chat = null;
				shareUrl = null;
				accessGrants = [];
			}
		})();
	}
</script>

<Modal bind:show size="md">
	<div>
		<div class="flex justify-between items-center dark:text-gray-200 px-5 pt-4 pb-2 border-b border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold flex items-center gap-2">
				<Link className="size-4 text-sky-500" />
				{$i18n.t('Share Conversation')}
			</div>
			<button
				class="rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		{#if chat}
			<div class="px-5 pt-4 pb-5 w-full flex flex-col gap-3">
				<!-- Warning / Context Info -->
				<div class="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-900 dark:text-amber-200 leading-relaxed">
					<div class="font-semibold mb-1 flex items-center gap-1.5">
						<span>ℹ️</span> Snapshot Notice
					</div>
					{$i18n.t(
						"Only messages up to this point will be included in the shared link. Any new messages you send after creating this link will remain private and won't appear. Users with authorized access can view this conversation snapshot."
					)}
				</div>

				<!-- Share URL Box (if generated) -->
				{#if shareUrl}
					<div class="flex flex-col gap-1.5">
						<div class="text-xs font-medium text-gray-600 dark:text-gray-400">
							{$i18n.t('Shareable Link')}
						</div>
						<div class="flex items-center gap-2 p-1.5 bg-gray-50 dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-gray-750">
							<input
								type="text"
								readonly
								class="bg-transparent text-xs w-full px-2.5 py-1 outline-hidden select-all font-mono text-gray-800 dark:text-gray-200 truncate"
								value={shareUrl}
								on:focus={(e) => e.currentTarget.select()}
							/>
							<button
								type="button"
								class="px-3.5 py-1.5 bg-slate-900 text-white dark:bg-sky-600 dark:hover:bg-sky-500 hover:bg-black text-xs font-semibold rounded-lg transition shrink-0 flex items-center gap-1 cursor-pointer shadow-xs"
								on:click={() => handleCopy()}
							>
								{#if copied}
									<span class="text-emerald-400 font-bold">✓ Copied</span>
								{:else}
									<span>Copy URL</span>
								{/if}
							</button>
						</div>
					</div>

					<!-- Access Control -->
					<div class="mt-1">
						<AccessControl
							bind:accessGrants
							accessRoles={['read']}
							sharePublic={$user?.permissions?.sharing?.public_chats || $user?.role === 'admin'}
							shareOpen={$user?.permissions?.sharing?.open_chats || $user?.role === 'admin'}
							shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) ||
								$user?.role === 'admin'}
							onChange={saveAccessGrants}
						/>
					</div>
				{/if}

				<!-- Actions -->
				<div class="flex justify-between items-center mt-2 pt-2 border-t border-gray-100 dark:border-gray-800">
					{#if chat.share_id}
						<button
							class="text-xs text-rose-500 hover:text-rose-600 dark:hover:text-rose-400 font-medium transition cursor-pointer hover:underline"
							type="button"
							on:click={async () => {
								const res = await deleteSharedChatById(localStorage.token, chatId);
								if (res) {
									chat = await getChatById(localStorage.token, chatId);
									shareUrl = null;
									toast.success($i18n.t('Shared link deleted'));
								}
							}}
						>
							{$i18n.t('Revoke Link')}
						</button>
					{:else}
						<div></div>
					{/if}

					<div class="flex items-center gap-2">
						<button
							class="px-3.5 py-1.5 text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 transition rounded-lg cursor-pointer"
							type="button"
							on:click={() => {
								show = false;
							}}
						>
							{$i18n.t('Close')}
						</button>

						<button
							class="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition rounded-lg cursor-pointer shadow-sm"
							type="button"
							id="generate-share-link-button"
							on:click={async () => {
								await shareLocalChat();
							}}
						>
							<Link className="size-3.5" />
							{#if chat.share_id}
								{$i18n.t('Update & Copy Link')}
							{:else}
								{$i18n.t('Generate & Copy Link')}
							{/if}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
</Modal>
