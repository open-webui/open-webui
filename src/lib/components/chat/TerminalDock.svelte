<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import type { Readable } from 'svelte/store';
	import { settings, terminalServers, selectedTerminalId } from '$lib/stores';
	import {
		resolveTerminalConnection,
		terminalRequest,
		type TerminalConnection,
		type TerminalProcess,
		type TerminalProcessOutput
	} from '$lib/apis/terminal';
	import XTerminal from './XTerminal.svelte';
	import Icon from './FileNav/Icon.svelte';

	export let chatId: string | null = null;
	export let expanded = false;
	export let height = 200;
	export let overlay = false;
	export let connected = false;
	export let connecting = false;
	export let running = 0;

	const i18n = getContext<Readable<{ t: (key: string) => string }>>('i18n');
	type Tab = TerminalProcess & {
		offset: number;
		loaded: boolean;
		available: boolean;
		finished: boolean;
	};
	let connection: TerminalConnection | null = null;
	let tabs: Tab[] = [];
	let activeId = 'shell';
	let shellOpened = false;
	let shellDismissed = false;
	let error = '';
	let panes: Record<string, XTerminal> = {};
	const dismissed = new Set<string>();
	const controller = new AbortController();
	let polling = false;
	let disposed = false;

	$: if (expanded && activeId === 'shell') shellOpened = true;
	$: running = tabs.filter((tab) => tab.status === 'running' && tab.available).length;

	async function poll() {
		if (!connection || polling || disposed || document.hidden) return;
		polling = true;
		try {
			const processes = await terminalRequest<TerminalProcess[]>(connection, chatId, '/execute', {
				signal: controller.signal
			});
			if (disposed) return;
			error = '';
			const live = new Map(processes.map((process) => [process.id, process]));
			tabs = tabs.map((tab) => ({ ...tab, ...live.get(tab.id), available: live.has(tab.id) }));
			const known = new Set(tabs.map((tab) => tab.id));
			for (const process of processes) {
				if (!known.has(process.id) && !dismissed.has(process.id)) {
					tabs = [
						...tabs,
						{ ...process, offset: 0, loaded: false, available: true, finished: false }
					];
				}
			}
			const tab = tabs.find((tab) => tab.id === activeId);
			if (expanded && tab?.available && !tab.finished) {
				await tick();
				if (!panes[tab.id]) return;
				const result = await terminalRequest<TerminalProcessOutput>(
					connection,
					chatId,
					`/execute/${encodeURIComponent(tab.id)}/status?wait=0&offset=${tab.offset}&tail=1000`,
					{ signal: controller.signal }
				);
				if (disposed || !panes[tab.id]) return;
				if (!tab.loaded) {
					panes[tab.id].write(`$ ${tab.command.replace(/\r?\n/g, '\r\n')}\r\n`);
				}
				if (result.truncated) panes[tab.id].write('\r\n[Earlier output omitted]\r\n');
				panes[tab.id].write(result.output.map((entry) => entry.data).join(''));
				tabs = tabs.map((item) =>
					item.id === tab.id
						? {
								...item,
								status: result.status,
								exit_code: result.exit_code,
								offset: result.next_offset,
								loaded: true,
								finished: result.status === 'done'
							}
						: item
				);
			}
		} catch (cause) {
			if (!disposed) error = String(cause);
		} finally {
			polling = false;
		}
	}

	function select(id: string) {
		expanded = true;
		activeId = id;
		if (id === 'shell') {
			shellOpened = true;
			shellDismissed = false;
		}
		tick().then(poll);
	}

	function dismiss(id: string) {
		dismissed.add(id);
		tabs = tabs.filter((tab) => tab.id !== id);
		delete panes[id];
		if (activeId === id) activeId = shellOpened ? 'shell' : (tabs[0]?.id ?? '');
		if (!activeId) expanded = false;
	}

	function closeShell() {
		shellOpened = false;
		shellDismissed = true;
		connected = false;
		connecting = false;
		activeId = tabs[0]?.id ?? '';
		if (!activeId) expanded = false;
	}

	function navigate(event: KeyboardEvent) {
		const ids = [...(!shellDismissed ? ['shell'] : []), ...tabs.map((tab) => tab.id)];
		const index = ids.indexOf(activeId);
		let next: string | undefined;
		if (event.key === 'ArrowRight') next = ids[(index + 1) % ids.length];
		if (event.key === 'ArrowLeft') next = ids[(index - 1 + ids.length) % ids.length];
		if (event.key === 'Home') next = ids[0];
		if (event.key === 'End') next = ids.at(-1);
		if (next) {
			event.preventDefault();
			select(next);
			(event.currentTarget as HTMLElement)
				.querySelector<HTMLButtonElement>(`[data-tab="${next}"]`)
				?.focus();
		}
	}

	onMount(() => {
		connection = resolveTerminalConnection(
			$selectedTerminalId,
			$terminalServers ?? [],
			($settings as { terminalServers?: { url: string; key?: string }[] })?.terminalServers ?? [],
			localStorage.getItem('token') ?? ''
		);
		poll();
		const interval = setInterval(poll, 1000);
		document.addEventListener('visibilitychange', poll);
		return () => {
			disposed = true;
			controller.abort();
			clearInterval(interval);
			document.removeEventListener('visibilitychange', poll);
		};
	});
</script>

<div class="terminal-dock min-h-0">
	<div
		class="flex h-7 min-w-0 items-center border-b border-black/5 text-[11px] text-gray-500 dark:border-white/5 dark:text-gray-400"
	>
		{#if !expanded}
			<button
				on:click={() => select(activeId || 'shell')}
				class="flex h-full min-w-0 flex-1 items-center gap-1.5 px-2 text-left hover:text-gray-900 dark:hover:text-gray-100"
			>
				<Icon name="terminal" size={13} />
				<span>{$i18n.t('Terminal')}</span>
				{#if running}<span class="tabular-nums text-gray-400">{running}</span>{/if}
			</button>
		{:else}
			<div
				role="tablist"
				tabindex="-1"
				aria-label={$i18n.t('Terminal')}
				on:keydown={navigate}
				class="terminal-tabs flex h-full min-w-0 flex-1 items-stretch overflow-x-auto"
			>
				{#if !shellDismissed}
					<div
						class="terminal-tab group flex shrink-0 items-center border-b"
						class:selected={activeId === 'shell'}
					>
						<button
							role="tab"
							data-tab="shell"
							aria-selected={activeId === 'shell'}
							tabindex={activeId === 'shell' ? 0 : -1}
							on:click={() => select('shell')}
							class="tab-button flex h-full items-center gap-1.5 pl-2 pr-1"
							title={$i18n.t('Shell')}
						>
							<Icon name="terminal" size={12} /><span>{$i18n.t('Shell')}</span>
						</button>
						{#if shellOpened}<button
								on:click={closeShell}
								class="tab-close mr-1 flex h-5 w-4 items-center justify-center"
								title={$i18n.t('Close terminal')}
								aria-label={$i18n.t('Close terminal')}><Icon name="xmark" size={10} /></button
							>{/if}
					</div>
				{:else}
					<button
						class="tab-button flex w-7 shrink-0 items-center justify-center"
						on:click={() => select('shell')}
						title={$i18n.t('Open terminal')}
						aria-label={$i18n.t('Open terminal')}><Icon name="plus" size={12} /></button
					>
				{/if}
				{#each tabs as tab (tab.id)}
					<div
						class="terminal-tab group flex shrink-0 items-center border-b"
						class:selected={activeId === tab.id}
					>
						<button
							role="tab"
							data-tab={tab.id}
							aria-selected={activeId === tab.id}
							tabindex={activeId === tab.id ? 0 : -1}
							on:click={() => select(tab.id)}
							class="tab-button flex h-full items-center gap-1.5 px-2"
							title={`${tab.command} (${!tab.available ? 'Unavailable' : tab.status === 'running' ? 'Running' : `Exit ${tab.exit_code ?? tab.status}`})`}
						>
							<span
								aria-hidden="true"
								class="h-[5px] w-[5px] shrink-0 rounded-full border {tab.available &&
								tab.status === 'running'
									? 'border-emerald-500 bg-emerald-500'
									: 'border-gray-400'}"
							></span>
							<span class="max-w-28 truncate">{tab.command}</span>
						</button>
						{#if tab.status !== 'running' || !tab.available}<button
								on:click={() => dismiss(tab.id)}
								class="tab-close mr-1 flex h-5 w-4 items-center justify-center"
								title={$i18n.t('Dismiss')}
								aria-label={`${$i18n.t('Dismiss')} ${tab.command}`}
								><Icon name="xmark" size={10} /></button
							>{/if}
					</div>
				{/each}
			</div>
		{/if}
		<button
			on:click={() => (expanded ? (expanded = false) : select(activeId || 'shell'))}
			class="tab-button flex h-7 w-7 shrink-0 items-center justify-center"
			aria-expanded={expanded}
			title={$i18n.t(expanded ? 'Collapse terminal' : 'Expand terminal')}
			aria-label={$i18n.t(expanded ? 'Collapse terminal' : 'Expand terminal')}
		>
			<Icon name={expanded ? 'chevron-down' : 'chevron-up'} size={12} />
		</button>
	</div>
	<div style:height={`${height}px`} class="flex min-h-0 flex-col bg-black" class:hidden={!expanded}>
		{#if error}<div class="shrink-0 truncate px-2 text-xs text-red-400" title={error}>
				{error}
			</div>{/if}
		<div class="relative min-h-0 flex-1">
			{#if connection && shellOpened}
				<div class="absolute inset-0" class:hidden={activeId !== 'shell'}>
					<XTerminal
						{connection}
						{chatId}
						{overlay}
						active={expanded && activeId === 'shell'}
						bind:connected
						bind:connecting
					/>
				</div>
			{/if}
			{#if connection}
				{#each tabs as tab (tab.id)}
					{#if tab.loaded || activeId === tab.id}
						<div class="absolute inset-0" class:hidden={activeId !== tab.id}>
							<XTerminal
								bind:this={panes[tab.id]}
								{connection}
								{chatId}
								{overlay}
								readOnly
								active={expanded && activeId === tab.id}
							/>
						</div>
					{/if}
				{/each}
			{/if}
		</div>
	</div>
</div>

<style>
	.terminal-tabs {
		scrollbar-width: none;
	}
	.terminal-tabs::-webkit-scrollbar {
		display: none;
	}
	.terminal-tab {
		border-color: transparent;
	}
	.terminal-tab.selected {
		border-color: currentColor;
		color: var(--color-gray-900, #171717);
	}
	:global(.dark) .terminal-tab.selected {
		color: #e5e5e5;
	}
	.tab-button,
	.tab-close {
		outline: none;
	}
	.terminal-dock .tab-button:focus-visible,
	.terminal-dock .tab-close:focus-visible {
		outline: 1px solid currentColor;
		outline-offset: -3px;
	}
	.tab-button:hover,
	.tab-close:hover {
		color: var(--color-gray-900, #171717);
	}
	:global(.dark) .tab-button:hover,
	:global(.dark) .tab-close:hover {
		color: #f5f5f5;
	}
	.tab-close {
		opacity: 0;
	}
	.terminal-tab:hover .tab-close,
	.terminal-tab:focus-within .tab-close {
		opacity: 1;
	}
	@media (hover: none) {
		.tab-close {
			opacity: 1;
		}
	}
</style>
