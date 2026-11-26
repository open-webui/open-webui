<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { machineRequest, type MachineTarget } from '$lib/apis/machines';
	import { getChatById } from '$lib/apis/chats';
	import { getFolderById } from '$lib/apis/folders';
	import { isFolderSessionId, isSavedChatId, isTemporaryChatId } from '$lib/utils/chatId';
	import Icon from './FileNav/Icon.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Stop from '$lib/components/icons/Stop.svelte';
	import { terminalIconName } from '$lib/utils/terminal';

	dayjs.extend(relativeTime);

	/** Lists the user's shells and running commands on a machine, from every chat. */
	export let target: MachineTarget;
	export let label: string;
	export let onClose: () => void;
	const i18n = getContext<any>('i18n');

	type Session = {
		kind: 'shell' | 'command';
		id: string;
		chat_id: string;
		command: string | null;
		pid: number;
		created_at: string;
	};
	type Place = { name: string; href: string | null };

	let sessions: Session[] = [];
	let places: Record<string, Place> = {};
	let error = '';
	let loading = true;
	let stopping: Session | null = null;
	let showConfirm = false;

	const folderIdOf = (id: string) => id.slice('folder:'.length, id.lastIndexOf(':'));

	const resolvePlace = async (id: string): Promise<Place> => {
		if (!id) return { name: $i18n.t('No chat'), href: null };
		if (isTemporaryChatId(id)) return { name: $i18n.t('Temporary chat'), href: null };
		if (isFolderSessionId(id)) {
			const folderId = folderIdOf(id);
			const folder = await getFolderById(localStorage.token, folderId).catch(() => null);
			return { name: folder?.name ?? $i18n.t('Folder'), href: `/folders/${folderId}` };
		}
		if (isSavedChatId(id)) {
			const chat = await getChatById(localStorage.token, id).catch(() => null);
			return chat
				? { name: chat.title || $i18n.t('Untitled'), href: `/c/${id}` }
				: { name: $i18n.t('Deleted chat'), href: null };
		}
		return { name: $i18n.t('Channel'), href: null };
	};

	const refresh = async () => {
		loading = true;
		try {
			sessions = await machineRequest<Session[]>(target, '/sessions');
			error = '';
			const missing = [...new Set(sessions.map((s) => s.chat_id))].filter((id) => !(id in places));
			const resolved = await Promise.all(missing.map(resolvePlace));
			places = { ...places, ...Object.fromEntries(missing.map((id, i) => [id, resolved[i]])) };
		} catch (reason) {
			error = reason instanceof Error ? reason.message : String(reason);
		} finally {
			loading = false;
		}
	};

	const stop = async (session: Session) => {
		try {
			await machineRequest(target, `/sessions/${session.kind}/${encodeURIComponent(session.id)}`, {
				method: 'DELETE'
			});
		} catch (reason) {
			error = reason instanceof Error ? reason.message : String(reason);
		}
		await refresh();
	};

	const open = async (href: string) => {
		onClose();
		await goto(href);
	};

	$: shells = sessions.filter((session) => session.kind === 'shell').length;
	$: commands = sessions.length - shells;

	// A shell shows its foreground program, as its terminal tab does.
	const nameOf = (session: Session) => session.command || $i18n.t('Shell');

	onMount(refresh);
</script>

<Modal
	size="sm"
	ariaLabel={$i18n.t('Sessions on {{name}}', { name: label })}
	onRequestClose={onClose}
>
	<section
		aria-label={$i18n.t('Sessions on {{name}}', { name: label })}
		class="text-xs text-base-600 dark:text-base-400"
	>
		<div class="flex items-center gap-2 px-3 pt-2.5 pb-1">
			<h2 class="min-w-0 truncate text-sm font-medium text-base-900 dark:text-base-0" title={label}>
				{label}
			</h2>
			<span class="min-w-0 flex-1 truncate text-base-500"
				>{[
					shells && $i18n.t('{{count}} shells', { count: shells }),
					commands && $i18n.t('{{count}} commands', { count: commands })
				]
					.filter(Boolean)
					.join(' · ')}</span
			>
			<button
				type="button"
				aria-label={$i18n.t('Refresh')}
				disabled={loading}
				on:click={refresh}
				class="flex size-6 shrink-0 items-center justify-center rounded-lg text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200 disabled:opacity-50"
			>
				<Icon name="refresh" size={12} />
			</button>
			<button
				type="button"
				aria-label={$i18n.t('Close')}
				on:click={onClose}
				class="flex size-6 shrink-0 items-center justify-center rounded-lg text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200"
			>
				<XMark className="size-3.5" />
			</button>
		</div>
		<div class="px-1.5 pb-2">
			{#if error}<div role="alert" class="px-1.5 py-1.5 break-words">
					{$i18n.t('Sessions unavailable')}
					<span class="text-base-500">· {error}</span>
				</div>{/if}
			{#if !sessions.length && loading}
				<div class="flex justify-center py-3"><Spinner className="size-3.5" /></div>
			{:else if !sessions.length && !error}
				<p class="px-1.5 py-1.5 text-base-500">{$i18n.t('Nothing running')}</p>
			{:else}
				<ul class="mx-1.5 flex flex-col">
					{#each sessions as session (`${session.kind}:${session.id}`)}
						{@const place = places[session.chat_id]}
						<li
							class="group flex h-[1.6875rem] items-center gap-2 rounded-lg pl-2.5 pr-1 hover:bg-base-50/40 dark:hover:bg-base-800/40"
						>
							<button
								type="button"
								disabled={!place?.href}
								class="flex h-full min-w-0 flex-1 items-center gap-2 text-left disabled:cursor-default"
								title={`${nameOf(session)} · PID ${session.pid} · ${new Date(session.created_at).toLocaleString()}`}
								on:click={() => place?.href && open(place.href)}
							>
								<span class="shrink-0 text-base-500"
									><Icon
										name={terminalIconName((session.command ?? '').trim().split(/\s+/)[0])}
										size={14}
									/></span
								>
								<span
									class="min-w-0 truncate text-base-800 dark:text-base-200 {session.kind ===
									'command'
										? 'font-mono'
										: ''}">{nameOf(session)}</span
								>
								<span class="ml-auto max-w-[50%] shrink-0 truncate text-base-500"
									>{place?.name ?? '…'} · {dayjs(session.created_at).fromNow(true)}</span
								>
							</button>
							<button
								type="button"
								aria-label={$i18n.t('Stop {{name}}', { name: nameOf(session) })}
								title={$i18n.t('Stop')}
								class="flex size-6 shrink-0 items-center justify-center rounded-lg text-base-400 opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100 hover:text-base-700 dark:hover:text-base-200"
								on:click={() => {
									stopping = session;
									showConfirm = true;
								}}><Stop className="size-3.5" /></button
							>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</section>
</Modal>

<ConfirmDialog
	bind:show={showConfirm}
	title={stopping?.kind === 'shell' ? $i18n.t('Stop this shell?') : $i18n.t('Stop this command?')}
	message={stopping?.kind === 'shell'
		? $i18n.t('The shell and everything running in it stop.')
		: $i18n.t('The command and everything it started stop.')}
	confirmLabel={$i18n.t('Stop')}
	onConfirm={() => stopping && stop(stopping)}
/>
