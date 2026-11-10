<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Users from '$lib/components/icons/Users.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import ArrowUturnLeft from '$lib/components/icons/ArrowUturnLeft.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import { templatesApi, getTerminalServers } from '$lib/apis/terminal';
	import { terminalServers } from '$lib/stores';

	export let show = true;
	export let chatId: string | null = null;
	export let modelId: string | null = null;
	export let selected: string | null = null;
	export let onSelect: (id: string) => Promise<void>;
	const i18n = getContext<any>('i18n');
	let rows: any[] = [];
	let connections: any[] = [];
	let current: any = null;
	let editing: any = selected ? null : { id: null };
	let sharing: any = null;
	let accessGrants: any[] = [];
	let connectionId = '';
	let name = '';
	let image = '';
	let scope = 'none';
	let cpu = '';
	let memory = '';
	let advanced = '{}';
	let showAdvanced = false;
	let busy = false;
	let error = '';
	let confirmation: { title: string; message: string; run: () => Promise<void> } | null = null;
	let showConfirm = false;
	const button =
		'flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 disabled:opacity-50 dark:text-gray-400 dark:hover:bg-gray-850 dark:hover:text-white';
	const input =
		'w-full min-w-0 bg-transparent py-0.5 text-sm text-gray-900 outline-hidden placeholder:text-gray-300 dark:text-gray-100 dark:placeholder:text-gray-700';
	const select =
		'min-w-0 bg-transparent pr-5 text-sm text-gray-900 outline-hidden dark:text-gray-100';
	const path = (id: string) => `/${encodeURIComponent(id)}`;
	const context = () => ({ chat_id: chatId, model_id: modelId });

	async function run(work: () => Promise<void>) {
		busy = true;
		error = '';
		try {
			await work();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	async function load() {
		const [servers, allowed] = await Promise.all([
			getTerminalServers(localStorage.token),
			templatesApi('/connections')
		]);
		terminalServers.set(servers);
		rows = servers.filter((row) => row.template_id);
		connections = allowed;
		if (!connections.some((c) => c.id === connectionId)) connectionId = connections[0]?.id ?? '';
		current = null;
		if (selected && rows.some((r) => r.id === selected)) {
			const query = new URLSearchParams();
			if (chatId) query.set('chat_id', chatId);
			if (modelId) query.set('model_id', modelId);
			try {
				current = await templatesApi(`${path(selected)}/instance?${query}`);
			} catch (e) {
				current = { status: 'unavailable', detail: String(e) };
			}
		}
	}
	async function edit(row: any = null) {
		await run(async () => {
			const data = row ? (await templatesApi(path(row.id))).data : {};
			editing = row ?? { id: null };
			sharing = null;
			name = data.name ?? row?.name ?? '';
			image = data.image ?? '';
			scope = data.scope ?? 'none';
			cpu = data.cpu_limit ?? '';
			memory = data.memory_limit ?? '';
			const { name: _name, image: _image, scope: _scope, cpu_limit, memory_limit, ...rest } = data;
			advanced = JSON.stringify(rest, null, 2);
			showAdvanced = false;
		});
	}
	async function save() {
		await run(async () => {
			const extra = JSON.parse(advanced);
			if (!extra || Array.isArray(extra) || typeof extra !== 'object')
				throw new Error('Configuration must be an object');
			const data = {
				...extra,
				name: name.trim(),
				image: image.trim() || null,
				scope: scope === 'none' ? null : scope,
				cpu_limit: cpu || null,
				memory_limit: memory || null
			};
			if (!data.name) throw new Error('Name is required');
			if (editing.id) await templatesApi(path(editing.id), 'PATCH', data);
			else {
				const row = await templatesApi('', 'POST', {
					id: uuidv4(),
					connection_id: connectionId,
					data
				});
				await load();
				await onSelect(row.terminal_id);
				selected = row.terminal_id;
			}
			editing = null;
			await load();
		});
	}
	async function share(row: any) {
		await run(async () => {
			accessGrants = await templatesApi(`${path(row.id)}/access`);
			sharing = row;
			editing = null;
		});
	}
	async function saveShares() {
		await run(async () => {
			await templatesApi(`${path(sharing.id)}/access`, 'POST', { access_grants: accessGrants });
			sharing = null;
			await load();
		});
	}
	async function removeTemplate(row: any) {
		await run(async () => {
			const instances = await templatesApi(`${path(row.id)}/instances`);
			confirmation = {
				title: `Delete ${row.name}?`,
				message: `This deletes the terminal and ${instances.length} instances, including their files.`,
				run: async () => {
					await templatesApi(path(row.id), 'DELETE');
					await load();
				}
			};
			showConfirm = true;
		});
	}
	function action(kind: 'restart' | 'reset' | 'delete') {
		if (!selected) return;
		const target = selected;
		const pinned = context();
		confirmation = {
			title:
				kind === 'delete'
					? 'Delete this instance?'
					: `${kind === 'restart' ? 'Restart' : 'Reset'} terminal?`,
			message:
				kind === 'restart'
					? 'Running work stops. Files are kept.'
					: 'Files and running work are removed for everyone using this instance.',
			run: async () => {
				await templatesApi(
					`${path(target)}/${kind === 'delete' ? 'instance' : kind}`,
					kind === 'delete' ? 'DELETE' : 'POST',
					pinned
				);
				await load();
			}
		};
		showConfirm = true;
	}
	onMount(() => run(load));
</script>

<Modal
	bind:show
	size="sm"
	ariaLabel={$i18n.t(
		editing
			? editing.id
				? 'Configure terminal'
				: 'New terminal'
			: sharing
				? 'Share terminal'
				: 'Terminals'
	)}
>
	<div class="text-gray-900 dark:text-gray-100">
		<div class="flex items-center justify-between gap-2 px-4 pb-1 pt-3 dark:text-gray-300">
			<h2 class="min-w-0 self-center truncate text-sm font-medium">
				{editing
					? $i18n.t(editing.id ? 'Configure terminal' : 'New terminal')
					: sharing
						? `${$i18n.t('Share')} ${sharing.name}`
						: $i18n.t('Terminals')}
			</h2>
			<button
				type="button"
				class="self-center shrink-0 rounded-lg px-0 py-1 text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				on:click={() => (show = false)}
				aria-label={$i18n.t('Close')}><XMark className="size-4" /></button
			>
		</div>
		<div
			class="max-h-[min(36rem,75dvh)] overflow-y-auto pb-4 {editing || sharing ? 'px-5' : 'px-3'}"
			aria-busy={busy}
		>
			{#if error}<p role="alert" class="mb-3 text-xs text-gray-700 dark:text-gray-300">
					{error}
				</p>{/if}
			{#if editing}
				<form class="space-y-2" on:submit|preventDefault={save}>
					<div>
						<label for="terminal-name" class="mb-0.5 block text-xs text-gray-500"
							>{$i18n.t('Name')}</label
						>
						<input
							id="terminal-name"
							list="terminal-name-suggestions"
							class={input}
							bind:value={name}
							placeholder={$i18n.t('My Terminal')}
							required
						/>
						<datalist id="terminal-name-suggestions">
							{#each [$i18n.t('My Terminal'), $i18n.t('Development'), $i18n.t('Sandbox')] as value}
								<option {value}></option>
							{/each}
						</datalist>
					</div>
					{#if !editing.id}
						<div>
							<label for="terminal-connection" class="mb-0.5 block text-xs text-gray-500"
								>{$i18n.t('Connection')}</label
							>
							<select
								id="terminal-connection"
								class="{select} w-full"
								bind:value={connectionId}
								required
								disabled={busy}
							>
								{#each connections as c}<option value={c.id}>{c.name}</option>{/each}
							</select>
							<p class="mt-1 text-xs text-gray-500">
								{$i18n.t('Choose the connection that will run this terminal.')}
							</p>
						</div>
					{/if}
					<div>
						<label for="terminal-scope" class="mb-0.5 block text-xs text-gray-500"
							>{$i18n.t('Scope')}</label
						>
						<select id="terminal-scope" class="{select} w-full" bind:value={scope} disabled={busy}>
							<option value="none">{$i18n.t('None')}</option>
							<option value="user">{$i18n.t('User')}</option>
							<option value="chat">{$i18n.t('Chat')}</option>
							<option value="model">{$i18n.t('Model')}</option>
						</select>
						<p class="mt-1 text-xs text-gray-500">
							{$i18n.t(
								scope === 'none'
									? 'Everyone with access shares this terminal.'
									: scope === 'user'
										? 'Each user gets their own terminal.'
										: scope === 'chat'
											? 'Each chat gets a terminal shared by its participants.'
											: 'Each model gets a terminal shared across authorized users and chats.'
							)}
						</p>
					</div>
					<div>
						<label for="terminal-image" class="mb-0.5 block text-xs text-gray-500"
							>{$i18n.t('Image')}</label
						>
						<input
							id="terminal-image"
							list="terminal-image-suggestions"
							class={input}
							bind:value={image}
							placeholder={$i18n.t('Server default')}
						/>
						<datalist id="terminal-image-suggestions">
							{#each ['latest', 'agents', 'cuda', 'slim', 'alpine', 'openshift'] as tag}
								<option value={`ghcr.io/open-webui/open-terminal:${tag}`}></option>
							{/each}
						</datalist>
						<p class="mt-1 text-xs text-gray-500">
							{$i18n.t('Container image used to run the terminal.')}
						</p>
					</div>
					<div class="grid grid-cols-2 gap-2">
						<div class="min-w-0">
							<label for="terminal-cpu" class="mb-0.5 block text-xs text-gray-500">CPU</label>
							<input
								id="terminal-cpu"
								list="terminal-cpu-suggestions"
								class={input}
								bind:value={cpu}
								placeholder={$i18n.t('Server default')}
							/>
							<datalist id="terminal-cpu-suggestions">
								{#each ['0.5', '1', '2', '4', '8'] as value}
									<option {value}></option>
								{/each}
							</datalist>
							<p class="mt-1 text-xs text-gray-500">
								{$i18n.t('CPU limit, for example 1 or 0.5.')}
							</p>
						</div>
						<div class="min-w-0">
							<label for="terminal-memory" class="mb-0.5 block text-xs text-gray-500"
								>{$i18n.t('Memory')}</label
							>
							<input
								id="terminal-memory"
								list="terminal-memory-suggestions"
								class={input}
								bind:value={memory}
								placeholder={$i18n.t('Server default')}
							/>
							<datalist id="terminal-memory-suggestions">
								{#each ['512Mi', '1Gi', '2Gi', '4Gi', '8Gi', '16Gi'] as value}
									<option {value}></option>
								{/each}
							</datalist>
							<p class="mt-1 text-xs text-gray-500">{$i18n.t('Memory limit, for example 2Gi.')}</p>
						</div>
					</div>
					<Collapsible
						title={$i18n.t('Advanced')}
						bind:open={showAdvanced}
						buttonClassName="flex w-full py-1 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
						chevronClassName="size-3.5"
						chevronStrokeWidth="2"
					>
						<div slot="content" class="mt-2">
							<p class="mb-2 text-xs text-gray-500">
								{$i18n.t('Environment variables, storage, networking, and security settings.')}
							</p>
							<textarea
								class="w-full resize-y rounded-lg bg-gray-50/60 p-2.5 font-mono text-xs leading-relaxed outline-hidden focus:ring-1 focus:ring-gray-200 dark:bg-gray-850/50 dark:focus:ring-gray-700"
								rows="7"
								bind:value={advanced}
								aria-label={$i18n.t('Template configuration')}
								spellcheck="false"
							/>
						</div>
					</Collapsible>
					<div class="flex items-center justify-between pt-3">
						<button
							type="button"
							class="px-1 py-1.5 text-sm font-medium text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
							disabled={busy}
							on:click={() => (editing = null)}>{$i18n.t('Cancel')}</button
						>
						<button
							type="submit"
							class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-50 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
							disabled={busy || (!editing.id && !connectionId)}
						>
							{$i18n.t(editing.id ? 'Save' : 'Create')}
							{#if busy}<Spinner className="size-3" />{/if}
						</button>
					</div>
				</form>
			{:else if sharing}
				<p class="mb-3 pt-1 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
					{$i18n.t(
						'Use allows commands and file access. Manage also allows configuration, sharing, and instance management.'
					)}
				</p>
				<AccessControl
					bind:accessGrants
					accessRoles={['read']}
					labels={{ read: $i18n.t('Use') }}
					sharePublic={false}
					shareOpen={false}
					shareUsers={true}
					allowGroups={true}
					onChange={() => {}}
				/>
				<div class="mt-4 flex justify-end gap-1.5">
					<button class={button} disabled={busy} on:click={() => (sharing = null)}
						>{$i18n.t('Cancel')}</button
					><button
						class="flex h-7 items-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black disabled:opacity-50 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
						disabled={busy}
						on:click={saveShares}
						>{#if busy}<Spinner className="size-3" />{/if}{$i18n.t('Save')}</button
					>
				</div>
			{:else}
				<div class="space-y-0.5">
					{#each rows as row (row.id)}
						{@const connection = connections.find(
							(c) => c.id === row.id.slice('template:'.length, row.id.lastIndexOf(':'))
						)}
						<div
							class="flex items-center gap-1 rounded-lg pr-1 hover:bg-gray-50/60 dark:hover:bg-gray-850/60"
						>
							<button
								class="flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-left disabled:opacity-50"
								aria-pressed={row.id === selected}
								disabled={busy}
								on:click={() =>
									run(async () => {
										await onSelect(row.id);
										selected = row.id;
										await load();
									})}
							>
								<Cloud
									className="size-3.5 shrink-0 text-gray-500 dark:text-gray-400"
									strokeWidth="1.5"
								/>
								<span class="min-w-0 flex-1"
									><span class="block truncate text-sm font-normal text-gray-800 dark:text-gray-100"
										>{row.name}</span
									><span class="flex flex-wrap items-center gap-1.5 text-xs text-gray-500"
										>{$i18n.t('Scope')}: {$i18n.t(
											row.scope ? row.scope[0].toUpperCase() + row.scope.slice(1) : 'None'
										)}{#if row.id === selected && current}<span aria-hidden="true">·</span><span
												class="flex items-center gap-1"
												>{#if current.status === 'running'}<span
														class="size-1 rounded-full bg-emerald-500"
													/>{/if}{$i18n.t(
													current.status === 'not_created'
														? 'Not started'
														: current.status[0].toUpperCase() + current.status.slice(1)
												)}</span
											>{/if}</span
									></span
								>
								{#if row.id === selected}<Check
										className="size-3.5 shrink-0 text-gray-500 dark:text-gray-400"
									/>{/if}
							</button>
							{#if connection}
								<Dropdown align="end" closeOnSelect>
									<button
										class="flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-400 transition hover:text-gray-700 disabled:opacity-50 dark:text-gray-500 dark:hover:text-gray-200"
										aria-label={$i18n.t('Actions for {{name}}', { name: row.name })}
										disabled={busy}><EllipsisHorizontal className="size-4" /></button
									>
									<div slot="content">
										<DropdownMenu className="min-w-[10.625rem]">
											<button disabled={busy} on:click={() => edit(row)}
												><Pencil />{$i18n.t('Configure')}</button
											>
											<button disabled={busy} on:click={() => share(row)}
												><Users />{$i18n.t('Share')}</button
											>
											{#if row.id === selected && current && !['not_created', 'unavailable'].includes(current.status)}
												<hr class="border-gray-50 dark:border-gray-850/30" />
												<button disabled={busy} on:click={() => action('restart')}
													><ArrowPath />{$i18n.t('Restart')}</button
												>
												<button disabled={busy} on:click={() => action('reset')}
													><ArrowUturnLeft />{$i18n.t('Reset')}</button
												>
												<button disabled={busy} on:click={() => action('delete')}
													><XMark />{$i18n.t('Delete instance')}</button
												>
											{/if}
											<hr class="border-gray-50 dark:border-gray-850/30" />
											<button disabled={busy} on:click={() => removeTemplate(row)}
												><GarbageBin />{$i18n.t('Delete terminal')}</button
											>
										</DropdownMenu>
									</div>
								</Dropdown>
							{/if}
						</div>
					{:else}<div class="flex items-center justify-center gap-2 py-8 text-xs text-gray-500">
							{#if busy}<Spinner className="size-3.5" />{$i18n.t('Loading...')}{:else}{$i18n.t(
									'No terminals available'
								)}{/if}
						</div>{/each}
				</div>
				{#if current?.detail}<p class="mt-2 text-xs text-gray-500" role="status">
						{current.detail}
					</p>{/if}
				{#if connections.length}<div class="mt-2 flex justify-end px-1">
						<button
							class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-100 px-2.5 text-xs font-normal text-gray-800 transition hover:bg-gray-100/70 disabled:opacity-60 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-850/60"
							disabled={busy}
							on:click={() => edit()}><Plus className="size-3.5" />{$i18n.t('New terminal')}</button
						>
					</div>{/if}
			{/if}
		</div>
	</div>
</Modal>
<ConfirmDialog
	bind:show={showConfirm}
	title={confirmation?.title ?? ''}
	message={confirmation?.message ?? ''}
	onConfirm={() =>
		run(async () => {
			await confirmation?.run();
			showConfirm = false;
		})}
/>
