<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';

	import { config, settings, user } from '$lib/stores';
	import Modal from '$lib/components/common/Modal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import {
		createNotificationTarget,
		deleteNotificationTarget,
		getNotificationEvents,
		getNotificationTargets,
		setDefaultNotificationTarget,
		testNotificationTarget,
		updateNotificationTarget,
		type NotificationTarget
	} from '$lib/apis/notifications';

	const i18n: Writable<any> = getContext('i18n');

	export let saveSettings: Function;

	let notificationEnabled = false;
	let notificationSound = true;
	let targets: NotificationTarget[] = [];
	let events: { event: string; label: string; description?: string }[] = [
		{
			event: 'chat.finished',
			label: 'Chat finished',
			description: 'A chat run finished successfully.'
		},
		{ event: 'chat.failed', label: 'Chat failed', description: 'A chat run failed.' }
	];
	let loadingTargets = false;
	let savingTarget = false;
	let editingId: string | null = null;
	let formOpen = false;
	let form = {
		id: '',
		url: '',
		enabled: true,
		events: [] as string[],
		delivery: 'away' as 'away' | 'always'
	};
	let loadedTargets = false;

	$: canUseWebhooks =
		($config?.features as any)?.enable_user_webhooks &&
		($user?.role === 'admin' || ($user?.permissions?.features?.webhooks ?? false));

	$: if (canUseWebhooks && !loadedTargets) {
		void loadTargets();
	}

	const toggleNotifications = async () => {
		if (!notificationEnabled) {
			const permission =
				'Notification' in window ? await Notification.requestPermission() : 'denied';
			if (permission === 'granted') {
				notificationEnabled = true;
				saveSettings({ notificationEnabled });
			} else {
				toast.error(
					$i18n.t(
						'Response notifications cannot be activated as the website permissions have been denied. Please visit your browser settings to grant the necessary access.'
					)
				);
			}
		} else {
			notificationEnabled = false;
			saveSettings({ notificationEnabled });
		}
	};

	const loadTargets = async () => {
		if (!canUseWebhooks) {
			return;
		}

		loadingTargets = true;
		loadedTargets = true;
		try {
			const [eventResult, targetResult] = await Promise.allSettled([
				getNotificationEvents(localStorage.token),
				getNotificationTargets(localStorage.token)
			]);

			if (eventResult.status === 'fulfilled' && eventResult.value?.length) {
				events = eventResult.value;
			}
			if (targetResult.status === 'fulfilled') {
				targets = targetResult.value.targets ?? [];
			} else {
				toast.error(`${targetResult.reason}`);
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loadingTargets = false;
		}
	};

	const openNewTarget = () => {
		editingId = null;
		formOpen = true;
		form = {
			id: '',
			url: '',
			enabled: true,
			events: [],
			delivery: 'away'
		};
	};

	const openEditTarget = (target: NotificationTarget) => {
		editingId = target.id;
		formOpen = true;
		form = {
			id: target.id,
			url: '',
			enabled: target.enabled,
			events: [...target.events],
			delivery: target.delivery
		};
	};

	const toggleFormEvent = (event: string) => {
		form.events = form.events.includes(event)
			? form.events.filter((item) => item !== event)
			: [...form.events, event];
	};

	const saveTarget = async () => {
		savingTarget = true;
		try {
			const id = form.id.trim();
			const payload: Partial<NotificationTarget> = {
				...(id ? { id } : {}),
				type: 'webhook',
				enabled: form.enabled,
				events: form.events,
				delivery: form.delivery,
				...(form.url.trim() ? { config: { url: form.url.trim() } } : {})
			};

			if (editingId) {
				await updateNotificationTarget(localStorage.token, editingId, payload);
			} else {
				await createNotificationTarget(localStorage.token, payload);
			}

			await loadTargets();
			formOpen = false;
			toast.success($i18n.t('Settings saved successfully!'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			savingTarget = false;
		}
	};

	const patchTarget = async (target: NotificationTarget, patch: Partial<NotificationTarget>) => {
		try {
			await updateNotificationTarget(localStorage.token, target.id, patch);
			await loadTargets();
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	const sendTest = async (target: NotificationTarget) => {
		try {
			await testNotificationTarget(localStorage.token, target.id);
			toast.success($i18n.t('Test notification sent.'));
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	onMount(async () => {
		notificationEnabled = $settings.notificationEnabled ?? false;
		notificationSound = $settings?.notificationSound ?? true;
	});
</script>

<div id="tab-notifications" class="flex h-full flex-col text-sm">
	<div class="flex-1 min-h-0 w-full overflow-y-auto scrollbar-hover pr-1.5">
		<h2 class="mb-4 text-sm font-medium text-gray-900 dark:text-white">
			{$i18n.t('Notifications')}
		</h2>

		<div class="flex flex-col gap-2.5">
			<label class="flex cursor-pointer items-center justify-between">
				<span class="text-xs text-gray-600 dark:text-gray-400">
					{$i18n.t('Browser Notifications')}
				</span>
				<Switch
					state={notificationEnabled}
					ariaLabel={$i18n.t('Browser Notifications')}
					on:change={toggleNotifications}
				/>
			</label>
			<p class="-mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
				{$i18n.t('Allow browser notifications for completed responses.')}
			</p>

			<label class="flex cursor-pointer items-center justify-between">
				<span class="text-xs text-gray-600 dark:text-gray-400">
					{$i18n.t('Notification Sound')}
				</span>
				<Switch
					bind:state={notificationSound}
					ariaLabel={$i18n.t('Notification Sound')}
					on:change={() => {
						saveSettings({ notificationSound });
					}}
				/>
			</label>

			{#if canUseWebhooks}
				<div class="mt-3 flex items-center justify-between">
					<span class="text-xs font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Notification Targets')}
					</span>
					<button
						class="flex h-6 w-6 items-center justify-center rounded-lg text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
						type="button"
						on:click={openNewTarget}
						title={$i18n.t('Add Notification Target')}
						aria-label={$i18n.t('Add Notification Target')}
					>
						<Plus className="size-3.5" strokeWidth="2" />
					</button>
				</div>

				{#if loadingTargets}
					<p class="text-[0.6875rem] text-gray-400 dark:text-gray-600">{$i18n.t('Loading...')}</p>
				{:else if !targets.length}
					<p class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
						{$i18n.t('No notification targets configured.')}
					</p>
				{:else}
					<div class="flex flex-col">
						{#each targets as target}
							{@const alertLabels = events
								.filter((event) => target.events.includes(event.event))
								.map((event) => event.label)
								.join(', ')}
							<div
								class="flex items-center gap-3 border-b border-gray-100/50 px-1 py-1.5 last:border-b-0 dark:border-white/[0.03]"
							>
								<div class="min-w-0 flex-1">
									<div class="flex min-w-0 items-center gap-2">
										<span class="truncate text-[0.71875rem] text-gray-700 dark:text-gray-300">
											{target.id}
										</span>
										<span class="shrink-0 text-[0.625rem] text-gray-400 dark:text-gray-600">
											{$i18n.t('Webhook')}
										</span>
										{#if target.is_default}
											<span class="shrink-0 text-[0.625rem] text-gray-400 dark:text-gray-600">
												{$i18n.t('Default')}
											</span>
										{/if}
									</div>
									<div
										class="truncate text-[0.625rem] leading-tight text-gray-400 dark:text-gray-600"
									>
										{target.config?.url_masked}
									</div>
									<div
										class="truncate text-[0.625rem] leading-tight text-gray-400 dark:text-gray-600"
									>
										{alertLabels || $i18n.t('No chat alerts')}
										{#if target.events.length}
											&middot; {target.delivery === 'away'
												? $i18n.t('Only when away')
												: $i18n.t('Always')}
										{/if}
									</div>
								</div>

								<div class="flex shrink-0 items-center gap-2">
									<button
										class="text-[0.625rem] text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:hover:text-gray-300"
										type="button"
										on:click={() => sendTest(target)}
									>
										{$i18n.t('Send Test')}
									</button>
									{#if !target.is_default}
										<button
											class="text-[0.625rem] text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:hover:text-gray-300"
											type="button"
											on:click={async () => {
												await setDefaultNotificationTarget(localStorage.token, target.id);
												await loadTargets();
											}}
										>
											{$i18n.t('Make Default')}
										</button>
									{/if}
									<button
										class="text-[0.625rem] text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:hover:text-gray-300"
										type="button"
										on:click={() => openEditTarget(target)}
									>
										{$i18n.t('Edit')}
									</button>
									<button
										class="text-[0.625rem] text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:hover:text-gray-300"
										type="button"
										on:click={async () => {
											await deleteNotificationTarget(localStorage.token, target.id);
											await loadTargets();
										}}
									>
										{$i18n.t('Remove')}
									</button>
								</div>

								<div class="flex w-9 shrink-0 justify-end">
									<Switch
										state={target.enabled}
										ariaLabel={$i18n.t('Enabled')}
										on:change={(event) => patchTarget(target, { enabled: event.detail })}
									/>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>

<Modal size="sm" bind:show={formOpen}>
	<div class="p-4">
		<h2 class="mb-3 text-sm font-medium text-gray-900 dark:text-white">
			{editingId ? $i18n.t('Edit') : $i18n.t('Add Notification Target')}
		</h2>

		<div class="text-[0.625rem] text-gray-400 dark:text-gray-600">
			{$i18n.t('Target ID for notify')}
		</div>
		<input
			bind:value={form.id}
			placeholder={$i18n.t('Target ID')}
			autocomplete="off"
			spellcheck="false"
			class="block w-full bg-transparent py-0.5 font-mono text-[0.8125rem] text-gray-700 outline-none placeholder:text-gray-300 dark:text-gray-300 dark:placeholder:text-gray-700"
		/>

		<div class="mt-2 text-[0.625rem] text-gray-400 dark:text-gray-600">
			{$i18n.t('Webhook')}
		</div>
		<input
			type="url"
			bind:value={form.url}
			placeholder={editingId
				? $i18n.t('Keep current webhook URL')
				: 'https://hooks.slack.com/services/...'}
			autocomplete="off"
			spellcheck="false"
			class="block w-full bg-transparent py-0.5 font-mono text-[0.8125rem] text-gray-700 outline-none placeholder:text-gray-300 dark:text-gray-300 dark:placeholder:text-gray-700"
		/>

		<div class="mt-3 mb-1 text-[0.625rem] text-gray-400 dark:text-gray-600">
			{$i18n.t('Automatic Events')}
		</div>
		<div class="flex flex-wrap gap-1">
			{#each events as event}
				<button
					class="h-6 rounded-md px-2 text-[0.6875rem] transition-colors {form.events.includes(
						event.event
					)
						? 'bg-gray-200/60 text-gray-900 dark:bg-white/10 dark:text-white'
						: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'}"
					type="button"
					on:click={() => toggleFormEvent(event.event)}
				>
					{event.label}
				</button>
			{/each}
		</div>

		{#if form.events.length}
			<div class="mt-3 mb-1 text-[0.625rem] text-gray-400 dark:text-gray-600">
				{$i18n.t('Automatic Delivery')}
			</div>
			<div class="flex gap-1">
				{#each ['away', 'always'] as mode}
					<button
						class="h-6 rounded-md px-2 text-[0.6875rem] transition-colors {form.delivery === mode
							? 'bg-gray-200/60 text-gray-900 dark:bg-white/10 dark:text-white'
							: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'}"
						type="button"
						on:click={() => (form.delivery = mode as 'away' | 'always')}
					>
						{mode === 'away' ? $i18n.t('Only when away') : $i18n.t('Always')}
					</button>
				{/each}
			</div>
		{/if}

		<p class="mt-3 text-[0.625rem] text-gray-400 dark:text-gray-600">
			{$i18n.t(
				'The notify tool always sends to an enabled target, regardless of automatic event settings.'
			)}
		</p>

		<div class="mt-4 flex justify-end gap-3">
			<button
				class="text-[0.8125rem] text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:hover:text-gray-300"
				type="button"
				on:click={() => (formOpen = false)}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				class="text-[0.8125rem] text-gray-700 transition-colors duration-100 hover:text-gray-900 disabled:opacity-30 dark:text-gray-300 dark:hover:text-white"
				type="button"
				on:click={saveTarget}
				disabled={savingTarget || (!editingId && !form.url.trim())}
			>
				{savingTarget ? $i18n.t('Saving...') : $i18n.t('Save')}
			</button>
		</div>
	</div>
</Modal>
