<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import {
		createEventWebhook,
		deleteEventWebhook,
		getEventWebhooks,
		getEvents,
		updateEventWebhook,
		type EventCatalogItem,
		type EventWebhook,
		type EventWebhookTarget
	} from '$lib/apis';
	import Modal from '$lib/components/common/Modal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { getGroups, getGroupInfoById } from '$lib/apis/groups';
	import { getUserInfoById, searchUsers } from '$lib/apis/users';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { settings } from '$lib/stores';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let webhooks: EventWebhook[] = [];
	let eventItems: EventCatalogItem[] = [];
	let pattern = '';
	let showWebhookModal = false;
	let showDeleteConfirmDialog = false;
	let editing: EventWebhook | null = null;
	let targetMode: 'all' | 'system' | 'selected' = 'all';
	let targetUserIds: string[] = [];
	let targetGroupIds: string[] = [];
	let targetQuery = '';
	let targetUserResults: any[] = [];
	let targetGroupResults: any[] = [];
	let groups: any[] = [];
	let selectedUsers: Record<string, any> = {};
	let selectedGroups: Record<string, any> = {};
	let targetSearchTimer: ReturnType<typeof setTimeout>;
	let form = {
		id: '',
		name: '',
		url: '',
		enabled: true,
		events: ['*'] as string[]
	};

	$: events = eventItems.map((item) => item.event);
	$: eventDetails = Object.fromEntries(eventItems.map((item) => [item.event, item]));
	$: eventFilter = pattern.trim().toLowerCase().replace(/\*$/, '');
	$: filteredEvents = events.filter((event) => !eventFilter || event.includes(eventFilter));
	$: allEvents = form.events.includes('*');
	$: selectedExactEvents = form.events.filter((event) => event !== '*' && !event.endsWith('.*'));

	const sortWebhooks = (items: EventWebhook[]) =>
		[...items].sort((a, b) => {
			if (a.id === 'default') {
				return -1;
			}
			if (b.id === 'default') {
				return 1;
			}
			return (a.name || '').localeCompare(b.name || '');
		});

	const load = async () => {
		const [catalog, webhookList, groupList] = await Promise.all([
			getEvents(localStorage.token),
			getEventWebhooks(localStorage.token),
			getGroups(localStorage.token, true).catch(() => [])
		]);
		eventItems = [...(catalog?.events ?? [])].sort((a, b) => a.event.localeCompare(b.event));
		webhooks = sortWebhooks(webhookList ?? []);
		groups = groupList ?? [];
	};

	const resetTargets = () => {
		targetMode = 'all';
		targetUserIds = [];
		targetGroupIds = [];
		targetQuery = '';
		targetUserResults = [];
		targetGroupResults = [];
		selectedUsers = {};
		selectedGroups = {};
	};

	const resetForm = () => {
		editing = null;
		showWebhookModal = false;
		form = {
			id: '',
			name: '',
			url: '',
			enabled: true,
			events: ['*']
		};
		pattern = '';
		resetTargets();
	};

	const newWebhook = () => {
		resetForm();
		showWebhookModal = true;
	};

	const editWebhook = async (webhook: EventWebhook) => {
		editing = webhook;
		showWebhookModal = true;
		form = {
			id: webhook.id,
			name: webhook.name,
			url: webhook.url,
			enabled: webhook.enabled,
			events: webhook.events?.length ? [...webhook.events] : ['*']
		};
		pattern = '';

		if (webhook.targets === null || webhook.targets === undefined) {
			resetTargets();
			return;
		}

		targetMode = webhook.targets.length > 0 ? 'selected' : 'system';
		targetUserIds = webhook.targets
			.filter((target) => target.type === 'user')
			.map((target) => target.id);
		targetGroupIds = webhook.targets
			.filter((target) => target.type === 'group')
			.map((target) => target.id);
		await hydrateSelectedTargets();
	};

	const eventSummary = (webhook: EventWebhook) => {
		const filters = webhook.events?.length ? webhook.events : ['*'];
		if (filters.includes('*')) {
			return $i18n.t('All events');
		}
		if (filters.length <= 2) {
			return filters.join(' + ');
		}
		return $i18n.t('{{count}} filters', { count: filters.length });
	};

	const targetSummary = (webhook: EventWebhook) => {
		const targets = webhook.targets;
		if (targets === null || targets === undefined) {
			return $i18n.t('All users and system events');
		}
		if (targets.length === 0) {
			return $i18n.t('System events only');
		}

		const userCount = targets.filter((target) => target.type === 'user').length;
		const groupCount = targets.filter((target) => target.type === 'group').length;
		const parts = [];
		if (userCount > 0) {
			parts.push(
				userCount === 1 ? $i18n.t('1 user') : $i18n.t('{{count}} users', { count: userCount })
			);
		}
		if (groupCount > 0) {
			parts.push(
				groupCount === 1 ? $i18n.t('1 group') : $i18n.t('{{count}} groups', { count: groupCount })
			);
		}
		return parts.join(' + ');
	};

	const urlHost = (url: string) => {
		try {
			return new URL(url).host;
		} catch {
			return url || $i18n.t('Not configured');
		}
	};

	const setAllEvents = (enabled: boolean) => {
		form.events = enabled ? ['*'] : [];
	};

	const toggleEvent = (event: string) => {
		const selected = new Set(form.events.filter((value) => value !== '*'));
		if (selected.has(event)) {
			selected.delete(event);
		} else {
			selected.add(event);
		}
		form.events = [...selected].sort();
	};

	const removeFilter = (event: string) => {
		form.events = form.events.filter((value) => value !== event);
		if (form.events.length === 0) {
			form.events = ['*'];
		}
	};

	const isValidPattern = (value: string) => {
		if (value === '*') {
			return true;
		}
		if (events.includes(value)) {
			return true;
		}
		if (!value.endsWith('.*')) {
			return false;
		}
		return events.some((event) => event.startsWith(value.slice(0, -1)));
	};

	const addPattern = () => {
		const value = pattern.trim();
		if (!value) {
			return;
		}
		if (!isValidPattern(value)) {
			toast.error($i18n.t('Use a valid event name or pattern like user.*'));
			return;
		}

		form.events =
			value === '*'
				? ['*']
				: [...new Set(form.events.filter((event) => event !== '*').concat(value))];
		pattern = '';
	};

	const selectedTargets = (): EventWebhookTarget[] | null => {
		if (targetMode === 'all') {
			return null;
		}
		if (targetMode === 'system') {
			return [];
		}

		return [
			...targetUserIds.map((id) => ({ type: 'user' as const, id })),
			...targetGroupIds.map((id) => ({ type: 'group' as const, id }))
		];
	};

	const hydrateSelectedTargets = async () => {
		selectedUsers = {};
		selectedGroups = {};

		await Promise.all(
			targetUserIds.map(async (id) => {
				const user = await getUserInfoById(localStorage.token, id).catch(() => null);
				if (user) {
					selectedUsers = { ...selectedUsers, [id]: user };
				}
			})
		);

		await Promise.all(
			targetGroupIds.map(async (id) => {
				const group =
					groups.find((group) => group.id === id) ??
					(await getGroupInfoById(localStorage.token, id).catch(() => null));
				if (group) {
					selectedGroups = { ...selectedGroups, [id]: group };
				}
			})
		);
	};

	const searchTargets = async () => {
		const query = targetQuery.trim().toLowerCase();
		if (!query) {
			targetUserResults = [];
			targetGroupResults = [];
			return;
		}

		targetGroupResults = groups
			.filter((group: any) => group.name?.toLowerCase().includes(query))
			.filter((group: any) => !targetGroupIds.includes(group.id))
			.slice(0, 5);

		const res = await searchUsers(localStorage.token, targetQuery, 'name', 'asc', 1).catch(
			() => null
		);
		targetUserResults = (res?.users ?? [])
			.filter((user: any) => !targetUserIds.includes(user.id))
			.slice(0, 5);
	};

	const handleTargetSearch = () => {
		clearTimeout(targetSearchTimer);
		targetSearchTimer = setTimeout(searchTargets, 250);
	};

	const addTargetUser = (user: any) => {
		if (!targetUserIds.includes(user.id)) {
			targetUserIds = [...targetUserIds, user.id];
			selectedUsers = { ...selectedUsers, [user.id]: user };
		}
		targetQuery = '';
		targetUserResults = [];
		targetGroupResults = [];
	};

	const addTargetGroup = (group: any) => {
		if (!targetGroupIds.includes(group.id)) {
			targetGroupIds = [...targetGroupIds, group.id];
			selectedGroups = { ...selectedGroups, [group.id]: group };
		}
		targetQuery = '';
		targetUserResults = [];
		targetGroupResults = [];
	};

	const removeTargetUser = (id: string) => {
		targetUserIds = targetUserIds.filter((userId) => userId !== id);
		const next = { ...selectedUsers };
		delete next[id];
		selectedUsers = next;
	};

	const removeTargetGroup = (id: string) => {
		targetGroupIds = targetGroupIds.filter((groupId) => groupId !== id);
		const next = { ...selectedGroups };
		delete next[id];
		selectedGroups = next;
	};

	const saveWebhook = async () => {
		const payload = {
			name: form.name || (form.id === 'default' ? 'Default webhook' : 'Webhook'),
			url: form.url,
			enabled: form.enabled,
			events: form.events.length ? form.events : ['*'],
			targets: selectedTargets()
		};

		try {
			if (editing) {
				await updateEventWebhook(localStorage.token, form.id, payload);
			} else {
				await createEventWebhook(localStorage.token, payload);
			}
			await load();
			resetForm();
			toast.success($i18n.t('Webhook saved'));
		} catch (error) {
			toast.error(typeof error === 'string' ? error : $i18n.t('Failed to save webhook'));
		}
	};

	const deleteWebhook = async (webhook: EventWebhook | null = editing) => {
		if (!webhook) {
			return;
		}

		try {
			await deleteEventWebhook(localStorage.token, webhook.id);
			await load();
			resetForm();
			toast.success($i18n.t('Webhook deleted'));
		} catch (error) {
			toast.error(typeof error === 'string' ? error : $i18n.t('Failed to delete webhook'));
		}
	};

	const toggleWebhook = async (webhook: EventWebhook, enabled: boolean) => {
		const previous = webhook.enabled;
		webhooks = webhooks.map((item) => (item.id === webhook.id ? { ...item, enabled } : item));

		try {
			await updateEventWebhook(localStorage.token, webhook.id, { enabled });
		} catch (error) {
			webhooks = webhooks.map((item) =>
				item.id === webhook.id ? { ...item, enabled: previous } : item
			);
			toast.error(typeof error === 'string' ? error : $i18n.t('Failed to update webhook'));
		}
	};

	onMount(load);
	onDestroy(() => {
		clearTimeout(targetSearchTimer);
	});
</script>

<Modal bind:show={showWebhookModal} size="sm">
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<h1 class="text-lg font-medium self-center font-primary">
				{editing ? $i18n.t('Edit webhook') : $i18n.t('Add webhook')}
			</h1>

			<button class="self-center" aria-label={$i18n.t('Close')} type="button" on:click={resetForm}>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="flex flex-col w-full px-5 pb-4 dark:text-gray-200">
			<form class="flex flex-col w-full" on:submit|preventDefault={saveWebhook}>
				<div class="flex gap-3">
					<div class="flex flex-col w-full">
						<label
							for="event-webhook-name"
							class={`text-xs mb-0.5 ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
							>{$i18n.t('Name')}</label
						>
						<input
							id="event-webhook-name"
							class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
							type="text"
							placeholder={$i18n.t('Identity audit')}
							autocomplete="off"
							bind:value={form.name}
						/>
					</div>
				</div>

				<div class="flex gap-3 mt-2">
					<div class="flex flex-col w-full">
						<label
							for="event-webhook-url"
							class={`text-xs mb-0.5 ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
							>{$i18n.t('URL')}</label
						>
						<div class="flex items-center gap-2">
							<input
								id="event-webhook-url"
								class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
								type="url"
								placeholder="https://example.com/events"
								autocomplete="off"
								required
								bind:value={form.url}
							/>
							<Tooltip content={form.enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
								<Switch bind:state={form.enabled} />
							</Tooltip>
						</div>
					</div>
				</div>

				<div class="mt-3">
					<div class="flex justify-between items-center gap-3">
						<div
							class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
						>
							{$i18n.t('Send events for')}
						</div>
						<select
							class="text-xs bg-transparent outline-hidden text-gray-700 dark:text-gray-300"
							bind:value={targetMode}
						>
							<option value="all">{$i18n.t('All users and system events')}</option>
							<option value="system">{$i18n.t('System events only')}</option>
							<option value="selected">{$i18n.t('Specific users or groups')}</option>
						</select>
					</div>

					<div class="mt-1 text-xs text-gray-500">
						{#if targetMode === 'all'}
							{$i18n.t(
								'Receives matching events across the instance, including system/config events and events associated with any user.'
							)}
						{:else if targetMode === 'system'}
							{$i18n.t('Receives matching events that are not associated with a user.')}
						{:else}
							{$i18n.t(
								'Receives matching user-associated events only when the actor, user subject, or user data matches these users or current group members. System/config events are not sent.'
							)}
						{/if}
					</div>

					{#if targetMode === 'selected'}
						<div class="mt-2">
							{#if targetUserIds.length > 0 || targetGroupIds.length > 0}
								<div class="flex flex-wrap gap-1 mb-2">
									{#each targetGroupIds as id}
										<div
											class="flex items-center gap-1 rounded-full bg-gray-100 dark:bg-gray-850 px-2 py-1 text-xs"
										>
											<span class="truncate max-w-36">{selectedGroups[id]?.name ?? id}</span>
											<span class="text-gray-500">{$i18n.t('group')}</span>
											<button
												type="button"
												aria-label={$i18n.t('Remove')}
												on:click={() => removeTargetGroup(id)}
											>
												<XMark className="size-3" strokeWidth="2" />
											</button>
										</div>
									{/each}

									{#each targetUserIds as id}
										<div
											class="flex items-center gap-1 rounded-full bg-gray-100 dark:bg-gray-850 px-2 py-1 text-xs"
										>
											<span class="truncate max-w-36">{selectedUsers[id]?.name ?? id}</span>
											<span class="text-gray-500">{$i18n.t('user')}</span>
											<button
												type="button"
												aria-label={$i18n.t('Remove')}
												on:click={() => removeTargetUser(id)}
											>
												<XMark className="size-3" strokeWidth="2" />
											</button>
										</div>
									{/each}
								</div>
							{/if}

							<div class="relative">
								<input
									class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
									type="text"
									placeholder={$i18n.t('Search users or groups')}
									autocomplete="off"
									bind:value={targetQuery}
									on:input={handleTargetSearch}
								/>

								{#if targetQuery.trim() && (targetGroupResults.length > 0 || targetUserResults.length > 0)}
									<div
										class="absolute z-10 mt-1 w-full rounded-lg bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-850 shadow-lg py-1 max-h-48 overflow-y-auto"
									>
										{#each targetGroupResults as group}
											<button
												type="button"
												class="w-full flex items-center justify-between gap-2 px-3 py-1.5 text-xs text-left hover:bg-gray-50 dark:hover:bg-gray-850"
												on:click={() => addTargetGroup(group)}
											>
												<span class="truncate">{group.name}</span>
												<span class="text-gray-500">{$i18n.t('Group')}</span>
											</button>
										{/each}

										{#each targetUserResults as user}
											<button
												type="button"
												class="w-full flex items-center justify-between gap-2 px-3 py-1.5 text-xs text-left hover:bg-gray-50 dark:hover:bg-gray-850"
												on:click={() => addTargetUser(user)}
											>
												<span class="truncate">
													{user.name}
													{#if user.email}
														<span class="text-gray-500">({user.email})</span>
													{/if}
												</span>
												<span class="text-gray-500">{$i18n.t('User')}</span>
											</button>
										{/each}
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<div class="mt-3">
					<div class="flex justify-between items-center">
						<label
							for="event-webhook-all-events"
							class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
							>{$i18n.t('Events')}</label
						>
						<label class="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300">
							<input
								id="event-webhook-all-events"
								type="checkbox"
								checked={allEvents}
								on:change={(event) => setAllEvents(event.currentTarget.checked)}
							/>
							<span>{$i18n.t('All events')}</span>
						</label>
					</div>

					{#if !allEvents}
						<div class="flex flex-col gap-2 mt-2">
							{#if form.events.length > 0}
								<div class="flex flex-wrap gap-1">
									{#each form.events as event}
										<div
											class="flex items-center gap-1 rounded-full bg-gray-100 dark:bg-gray-850 px-2 py-1 text-xs"
										>
											<span class="font-mono break-all">{event}</span>
											<button
												type="button"
												aria-label={$i18n.t('Remove')}
												on:click={() => removeFilter(event)}
											>
												<XMark className="size-3" strokeWidth="2" />
											</button>
										</div>
									{/each}
								</div>
							{/if}

							<div class="flex gap-2">
								<input
									class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
									type="text"
									placeholder={$i18n.t('Search or add pattern')}
									autocomplete="off"
									bind:value={pattern}
									on:keydown={(event) => {
										if (event.key === 'Enter') {
											event.preventDefault();
											addPattern();
										}
									}}
								/>
								<button
									type="button"
									class="text-xs text-gray-700 dark:text-gray-300 hover:underline"
									on:click={addPattern}
								>
									{$i18n.t('Add')}
								</button>
							</div>

							<div class="max-h-36 overflow-y-auto pb-0.5">
								{#each filteredEvents as event}
									<label
										class="flex items-start gap-2 py-0.5 text-xs text-gray-700 dark:text-gray-300"
									>
										<input
											class="mt-0.5"
											type="checkbox"
											checked={selectedExactEvents.includes(event)}
											on:change={() => toggleEvent(event)}
										/>
										<span class="min-w-0">
											<span class="font-mono break-all">{event}</span>
											<span class="ml-1 text-gray-500">{eventDetails[event]?.message}</span>
										</span>
									</label>
								{/each}
							</div>

							<div class="text-xs text-gray-500">
								{$i18n.t(
									'Event names may change as Open WebUI evolves. Use broad patterns like user.* for integrations that should continue across new related events.'
								)}
							</div>
						</div>
					{/if}
				</div>

				<div class="flex justify-between items-center pt-4 text-sm font-medium">
					<div>
						{#if editing}
							<button
								class="px-1 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:underline transition"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}
					</div>

					<button
						type="submit"
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t('Are you sure you want to delete this webhook? This action cannot be undone.')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		deleteWebhook();
	}}
/>

<div class="mb-3">
	<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Events')}</div>
	<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

	<div class="mb-2.5 flex flex-col w-full justify-between">
		<div class="flex justify-between items-center mb-1">
			<div class="font-medium text-xs">{$i18n.t('Webhooks')}</div>

			<Tooltip content={$i18n.t('Add webhook')}>
				<button class="px-1" on:click={newWebhook} type="button">
					<Plus />
				</button>
			</Tooltip>
		</div>

		<div class="flex flex-col gap-1">
			{#each webhooks as webhook}
				<div class="flex w-full gap-2 items-center">
					<div
						class="flex-1 min-w-0 flex gap-1.5 items-center {webhook.enabled ? '' : 'opacity-50'}"
					>
						<div class="outline-hidden w-full bg-transparent text-sm truncate">
							<span class="font-medium">
								{webhook.id === 'default' ? $i18n.t('Default webhook') : webhook.name}
							</span>
							<span class="text-xs text-gray-500">
								- {urlHost(webhook.url)} - {eventSummary(webhook)} - {targetSummary(webhook)}
							</span>
						</div>
					</div>

					<div class="flex gap-1 items-center">
						<Tooltip content={$i18n.t('Configure')}>
							<button
								class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
								on:click={() => editWebhook(webhook)}
								type="button"
							>
								<Cog6 />
							</button>
						</Tooltip>

						<Tooltip content={webhook.enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
							<Switch
								state={webhook.enabled}
								on:change={(event) => {
									toggleWebhook(webhook, event.detail);
								}}
							/>
						</Tooltip>
					</div>
				</div>
			{/each}
		</div>

		{#if webhooks.length === 0}
			<div class="text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('No event webhooks configured.')}
			</div>
		{/if}

		<div class="mt-1.5">
			<div class="text-xs text-gray-500">
				{$i18n.t(
					'Send product events as JSON to external services. Chat destinations receive readable messages.'
				)}
			</div>
		</div>
	</div>
</div>
