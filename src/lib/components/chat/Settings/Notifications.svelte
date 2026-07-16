<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';

	import { config, settings, user } from '$lib/stores';
	import Switch from '$lib/components/common/Switch.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import UserSettingField from './UserSettingField.svelte';
	import UserSettingRow from './UserSettingRow.svelte';
	import UserSettingSection from './UserSettingSection.svelte';
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
	let notificationSoundAlways = false;
	let targets: NotificationTarget[] = [];
	let defaultTargetId: string | null = null;
	let events: { event: string; label: string }[] = [];
	let loading = false;
	let editingTarget: NotificationTarget | null = null;
	let targetName = 'Webhook';
	let targetUrl = '';
	let targetEnabled = true;
	let targetDelivery: 'away' | 'always' = 'away';
	let targetEvents = ['chat.finished', 'chat.failed'];

	const inputClass =
		'h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const actionButtonClass =
		'text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white disabled:cursor-not-allowed disabled:opacity-50';

	$: canUseWebhooks =
		($config?.features as any)?.enable_user_webhooks &&
		($user?.role === 'admin' || ($user?.permissions?.features?.webhooks ?? false));

	const setNotificationEnabled = async (enabled: boolean) => {
		const permission = enabled ? await Notification.requestPermission() : 'granted';

		if (permission === 'granted') {
			notificationEnabled = enabled;
			saveSettings({ notificationEnabled });
		} else {
			notificationEnabled = false;
			toast.error(
				$i18n.t(
					'Response notifications cannot be activated as the website permissions have been denied. Please visit your browser settings to grant the necessary access.'
				)
			);
		}
	};

	const loadTargets = async () => {
		if (!canUseWebhooks) {
			return;
		}

		loading = true;
		try {
			events = await getNotificationEvents(localStorage.token);
			const response = await getNotificationTargets(localStorage.token);
			targets = response.targets ?? [];
			defaultTargetId = response.default_target_id ?? null;
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	const resetForm = () => {
		editingTarget = null;
		targetName = 'Webhook';
		targetUrl = '';
		targetEnabled = true;
		targetDelivery = 'away';
		targetEvents = ['chat.finished', 'chat.failed'];
	};

	const editTarget = (target: NotificationTarget) => {
		editingTarget = target;
		targetName = target.name;
		targetUrl = '';
		targetEnabled = target.enabled;
		targetDelivery = target.delivery;
		targetEvents = [...target.events];
	};

	const saveTarget = async () => {
		try {
			const payload: Partial<NotificationTarget> = {
				type: 'webhook',
				name: targetName,
				enabled: targetEnabled,
				events: targetEvents,
				delivery: targetDelivery,
				config: targetUrl ? { url: targetUrl } : {}
			};

			if (editingTarget) {
				await updateNotificationTarget(localStorage.token, editingTarget.id, payload);
			} else {
				await createNotificationTarget(localStorage.token, payload);
			}

			toast.success($i18n.t('Settings saved successfully!'));
			resetForm();
			await loadTargets();
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	const toggleEvent = (event: string) => {
		if (targetEvents.includes(event)) {
			targetEvents = targetEvents.filter((item) => item !== event);
		} else {
			targetEvents = [...targetEvents, event];
		}
	};

	onMount(async () => {
		notificationEnabled = $settings.notificationEnabled ?? false;
		notificationSound = $settings?.notificationSound ?? true;
		notificationSoundAlways = $settings?.notificationSoundAlways ?? false;
		await loadTargets();
	});
</script>

<div id="tab-notifications" class="flex h-full flex-col text-sm">
	<div class="flex-1 min-h-0 w-full overflow-y-auto scrollbar-hover pr-1.5">
		<h2 class="mb-4 text-sm font-medium text-gray-900 dark:text-white">
			{$i18n.t('Notifications')}
		</h2>

		<UserSettingSection title={$i18n.t('Local Notifications')} first>
			<UserSettingRow
				label={$i18n.t('Browser Notifications')}
				description={$i18n.t('Allow browser notifications for completed responses.')}
			>
				<Switch
					state={notificationEnabled}
					ariaLabel={$i18n.t('Browser Notifications')}
					on:change={(event) => {
						setNotificationEnabled(event.detail);
					}}
				/>
			</UserSettingRow>

			<UserSettingRow
				label={$i18n.t('Notification Sound')}
				description={$i18n.t('Play a sound when new chat activity arrives.')}
			>
				<Switch
					bind:state={notificationSound}
					ariaLabel={$i18n.t('Notification Sound')}
					on:change={() => {
						saveSettings({ notificationSound });
					}}
				/>
			</UserSettingRow>

			{#if notificationSound}
				<UserSettingRow
					label={$i18n.t('Always Play Notification Sound')}
					description={$i18n.t('Play notification sounds even when the app is focused.')}
				>
					<Switch
						bind:state={notificationSoundAlways}
						ariaLabel={$i18n.t('Always Play Notification Sound')}
						on:change={() => {
							saveSettings({ notificationSoundAlways });
						}}
					/>
				</UserSettingRow>
			{/if}
		</UserSettingSection>

		{#if canUseWebhooks}
			<UserSettingSection title={$i18n.t('Webhook Targets')}>
				{#if loading}
					<div class="text-xs text-gray-400 dark:text-gray-600">{$i18n.t('Loading...')}</div>
				{:else if targets.length === 0}
					<div class="text-xs text-gray-400 dark:text-gray-600">
						{$i18n.t('No notification targets configured.')}
					</div>
				{:else}
					<div class="flex flex-col gap-2">
						{#each targets as target}
							<div
								class="rounded-lg border border-gray-100/70 p-2.5 text-xs dark:border-white/[0.06]"
							>
								<div class="flex items-center justify-between gap-3">
									<div class="min-w-0">
										<div class="truncate font-medium text-gray-700 dark:text-gray-300">
											{target.name}
											{#if target.id === defaultTargetId}
												<span class="ml-1 text-gray-400 dark:text-gray-600"
													>{$i18n.t('Default')}</span
												>
											{/if}
										</div>
										<div class="truncate text-gray-400 dark:text-gray-600">
											{target.config?.url}
										</div>
									</div>

									<Switch
										state={target.enabled}
										ariaLabel={$i18n.t('Enabled')}
										on:change={async (event) => {
											await updateNotificationTarget(localStorage.token, target.id, {
												enabled: event.detail
											});
											await loadTargets();
										}}
									/>
								</div>

								<div class="mt-2 flex flex-wrap gap-2 text-gray-400 dark:text-gray-600">
									<span
										>{target.delivery === 'always'
											? $i18n.t('Always')
											: $i18n.t('Only when away')}</span
									>
									<span>{target.events.join(', ')}</span>
								</div>

								<div class="mt-2 flex flex-wrap gap-3">
									<button
										class={actionButtonClass}
										type="button"
										on:click={async () => {
											await testNotificationTarget(localStorage.token, target.id);
											toast.success($i18n.t('Test notification sent.'));
										}}>{$i18n.t('Test')}</button
									>
									<button
										class={actionButtonClass}
										type="button"
										on:click={() => editTarget(target)}>{$i18n.t('Edit')}</button
									>
									<button
										class={actionButtonClass}
										type="button"
										disabled={target.id === defaultTargetId}
										on:click={async () => {
											await setDefaultNotificationTarget(localStorage.token, target.id);
											await loadTargets();
										}}>{$i18n.t('Make Default')}</button
									>
									<button
										class={actionButtonClass}
										type="button"
										on:click={async () => {
											await deleteNotificationTarget(localStorage.token, target.id);
											await loadTargets();
										}}>{$i18n.t('Remove')}</button
									>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</UserSettingSection>

			<UserSettingSection title={editingTarget ? $i18n.t('Edit Target') : $i18n.t('Add Target')}>
				<UserSettingField label={$i18n.t('Name')}>
					<input class={inputClass} type="text" bind:value={targetName} />
				</UserSettingField>

				<UserSettingField
					label={$i18n.t('Webhook URL')}
					description={editingTarget
						? $i18n.t('Leave blank to keep the current webhook URL.')
						: $i18n.t('Send chat notifications to this webhook URL.')}
				>
					<input
						class={inputClass}
						type="url"
						bind:value={targetUrl}
						placeholder={editingTarget
							? editingTarget.config?.url
							: $i18n.t('Enter your webhook URL')}
					/>
				</UserSettingField>

				<UserSettingRow label={$i18n.t('Enabled')}>
					<Switch bind:state={targetEnabled} ariaLabel={$i18n.t('Enabled')} />
				</UserSettingRow>

				<UserSettingField label={$i18n.t('Delivery')}>
					<SettingsSelect bind:value={targetDelivery} ariaLabel={$i18n.t('Delivery')}>
						<option value="away">{$i18n.t('Only when away')}</option>
						<option value="always">{$i18n.t('Always')}</option>
					</SettingsSelect>
				</UserSettingField>

				<UserSettingField label={$i18n.t('Events')}>
					<div class="flex flex-col gap-1.5">
						{#each events as item}
							<label class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
								<input
									type="checkbox"
									checked={targetEvents.includes(item.event)}
									on:change={() => toggleEvent(item.event)}
								/>
								<span>{$i18n.t(item.label)}</span>
							</label>
						{/each}
					</div>
				</UserSettingField>

				<div class="flex justify-end gap-3">
					{#if editingTarget}
						<button class={actionButtonClass} type="button" on:click={resetForm}
							>{$i18n.t('Cancel')}</button
						>
					{/if}
					<button
						class="rounded-full bg-black px-3.5 py-1.5 text-sm font-normal text-white transition hover:bg-gray-900 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-gray-100"
						type="button"
						disabled={!editingTarget && !targetUrl}
						on:click={saveTarget}
					>
						{editingTarget ? $i18n.t('Save') : $i18n.t('Add')}
					</button>
				</div>
			</UserSettingSection>
		{/if}
	</div>
</div>
