import { CONTROL_LABELS, isControlVisible, type ControlId } from './ui-visibility';
import type { SettingsAccessContext } from './settings-search';

export const canEditSystemPrompt = ({ user }: SettingsAccessContext) =>
	user?.role === 'admin' ||
	((user?.permissions?.chat?.controls ?? true) && (user?.permissions?.chat?.system_prompt ?? true));
export const canEditParameters = ({ user }: SettingsAccessContext) =>
	user?.role === 'admin' ||
	((user?.permissions?.chat?.controls ?? true) && (user?.permissions?.chat?.params ?? true));
export const canManageChats = (
	{ user }: SettingsAccessContext,
	action: 'import' | 'export' | 'delete'
) => user?.role === 'admin' || (user?.permissions?.chat?.[action] ?? true);
export const canUseApiKeys = ({ user, config }: SettingsAccessContext) =>
	(config?.features?.enable_api_keys ?? true) &&
	(user?.role === 'admin' || (user?.permissions?.features?.api_keys ?? false));
export const canUseNotificationTargets = ({ user, config }: SettingsAccessContext) =>
	config?.features?.enable_user_webhooks &&
	(user?.role === 'admin' || (user?.permissions?.features?.webhooks ?? false));
export const canUseTemporaryChats = ({ user }: SettingsAccessContext) =>
	user?.role === 'admin' || user?.permissions?.chat?.temporary;
export const canUseChannels = ({ user, config }: SettingsAccessContext) =>
	config?.features?.enable_channels &&
	(user?.role === 'admin' || (user?.permissions?.features?.channels ?? true));
export const canUseCalls = ({ user }: SettingsAccessContext) =>
	user?.role === 'admin' || (user?.permissions?.chat?.call ?? true);
export const canUseWebSearch = ({ user, config }: SettingsAccessContext) =>
	config?.features?.enable_web_search &&
	(user?.role === 'admin' || user?.permissions?.features?.web_search);
export const canRegenerateResponses = ({ user }: SettingsAccessContext) =>
	user?.role === 'admin' || (user?.permissions?.chat?.regenerate_response ?? true);
export const isSettingsAdmin = ({ user }: SettingsAccessContext) => user?.role === 'admin';

/** Search follows the same permissions and visibility as the rendered controls. */
export function canSearchSetting(
	key: string,
	tabId: string,
	context: SettingsAccessContext
): boolean {
	const stem = key.replace(/\.(label|description|title)$/, '');
	if (
		/^settings\.personal\.(dataControls\.archiveAll(Chats)?|archivedChats\.unarchiveAll)$/.test(
			stem
		)
	)
		return isControlVisible('chat.archive', context);
	if (key.startsWith('settings.personal.')) {
		const control = (Object.keys(CONTROL_LABELS) as ControlId[]).find(
			(id) => CONTROL_LABELS[id].replace(/\.(label|title)$/, '') === stem
		);
		if (control && !isControlVisible(control, context)) return false;
	}
	if (stem === 'settings.personal.general.sections.systemPrompt')
		return canEditSystemPrompt(context);
	if (
		stem === 'settings.personal.general.sections.advancedParameters' ||
		stem === 'settings.personal.general.modelParameters' ||
		(key.startsWith('settings.personal.general.parameters.') && tabId === 'general')
	) {
		if (!canEditParameters(context)) return false;
	}
	if (
		key.startsWith('settings.personal.general.parameters.') &&
		/\.(streamDeltaChunkSize|contextCompactionThreshold|numThread|numGpu|useMmap|useMlock|keepAlive)\./.test(
			key
		)
	)
		return isSettingsAdmin(context);
	if (key.startsWith('settings.personal.dataControls.')) {
		if (stem.endsWith('.importChats')) return canManageChats(context, 'import');
		if (stem.endsWith('.exportChats')) return canManageChats(context, 'export');
		if (/\.(deleteAllChats|deleteAll)$/.test(stem)) return canManageChats(context, 'delete');
	}
	if (
		key.startsWith('settings.personal.notifications.') &&
		/\.(notificationTargets|addNotificationTarget)\./.test(key)
	)
		return !!canUseNotificationTargets(context);
	if (
		key.startsWith('settings.personal.account.') &&
		/\.(apiKeys|secrets|jwtToken|copyToken|apiKey|copyApiKey|createNewSecretKey)\./.test(key)
	) {
		return (
			canUseApiKeys(context) && (!/\.(jwtToken|copyToken)\./.test(key) || isSettingsAdmin(context))
		);
	}
	if (stem === 'settings.personal.interface.toastNotificationsForNewUpdates')
		return isSettingsAdmin(context);
	if (stem === 'settings.personal.interface.temporaryChatByDefault')
		return !!canUseTemporaryChats(context);
	if (stem === 'settings.personal.interface.compressImagesInChannels')
		return !!canUseChannels(context);
	if (
		key.startsWith('settings.personal.interface.') &&
		/\.(sections\.voice|allowVoiceInterruptionInCall|displayEmojiInCall)\./.test(key)
	)
		return canUseCalls(context);
	if (stem === 'settings.personal.interface.webSearchInChat') return !!canUseWebSearch(context);
	if (stem === 'settings.personal.shortcuts.newTemporaryChat')
		return !!canUseTemporaryChats(context);
	if (stem === 'settings.personal.shortcuts.deleteChat') return canManageChats(context, 'delete');
	if (stem === 'settings.personal.interface.regenerateMenu') return canRegenerateResponses(context);
	return true;
}
