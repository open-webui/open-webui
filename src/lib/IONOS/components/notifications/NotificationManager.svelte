<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import type { Chat } from '$lib/apis/chats/types.ts';
	import NotificationBanner from "$lib/IONOS/components/notifications/NotificationBanner.svelte";
	import { chats, config, user } from '$lib/stores';
	import { updateSettings } from '$lib/IONOS/services/settings';
	import { notifications, addNotification, removeNotification, type Notification, NotificationType } from "$lib/IONOS/stores/notifications";
	import { getContext, onDestroy } from 'svelte';
	import { getUserSettings } from '$lib/apis/users';

	const i18n = getContext<Readable<I18Next>>('i18n');

	const DAYS = 24 * 60 * 60 * 1000;

	const surveyUrl = $config?.features?.ionos_survey_new_users_url ?? null;

	// Check if the user should be prompted for feedback
	const unsubscribeChats = chats.subscribe(async (chats: Chat[]) => {
		const userSettings = await getUserSettings(localStorage.token);
		const userCreatedAt = new Date($user!.created_at * 1000);
		if (chats.length >= 2 || (new Date().getTime() - userCreatedAt.getTime()) < (14 * DAYS)) {
			if (!userSettings.ui?.ionosProvidedFeedback) {
				addSurveyNotification();
			}
		}
	});

	const addSurveyNotification = () => {
		if (surveyUrl === null) {
			return;
		}

		const url = new URL(surveyUrl);
		url.searchParams.append('urlVar01', 'DE'); // Country code
		url.searchParams.append('urlVar02', $user.pseudonymized_user_id);
		url.searchParams.append('urlVar03', 'Product'); // Channels
		const surveyNotification: Notification = {
			type: NotificationType.FEEDBACK,
			title: $i18n.t('Love our product?', { ns: 'ionos' }),
			message: $i18n.t('Help us improve', { ns: 'ionos' }),
			actions: [{
				label: $i18n.t('Take Our Quick Survey', { ns: 'ionos' }),
				handler: () => {
					window.open(url.toString(), '_blank', "noopener=yes,noreferrer=yes");
					updateSettings({
						ionosProvidedFeedback: true
					});
				}
			}],
		}
		addNotification(surveyNotification);
	};

	const dismissHandler = (event: CustomEvent) => {
		removeNotification(event.detail.notification);
	};

	onDestroy(() => {
		unsubscribeChats();
	});
</script>

<div class="sticky top-0 flex flex-col w-full z-50">
	{#each $notifications as notification }
		<NotificationBanner {notification} on:dismiss={dismissHandler} />
	{/each}
</div>
