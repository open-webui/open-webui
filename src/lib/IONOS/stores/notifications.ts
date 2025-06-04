import { type Writable, writable } from 'svelte/store';

export enum NotificationType {
	INFO = 'bg-blue-100 text-blue-800',
	SUCCESS = 'success',
	ERROR = 'bg-red-100 text-blue-800',
	WARNING = 'warning',
	FEEDBACK = NotificationType.INFO,
}

export type NotificationActionBase = {
	label: string;
};

/**
 * Handle notification action clicks as click event handler
 */
export type NotificationActionClickHandler = NotificationActionBase & {
	handler: (e: Event) => void;
};

/**
 * Handle notification action clicks as href
 */
export type NotificationActionHref = NotificationActionBase & {
	href: string;
};

export type NotificationAction = NotificationActionHandler | NotificationActionHref;

export type Notification = {
	type: NotificationType;
	title: string;
	message: string;
	actions: NotificationAction[];
	dismissible?: boolean;
};

export const notifications: Writable<Notification[]> = writable([]);

export const addNotification = (notification: Notification): void => {
	notifications.update((currentNotifications: Notification[]) => {
		if (currentNotifications.some(n => n.title === notification.title)) {
			return currentNotifications;
		}
	 return [...currentNotifications, notification]
	});
};

export const removeNotification = (notification: Notification): void => {
	notifications.update((currentNotifications: Notification[]) =>
		currentNotifications.filter(n => n !== notification)
	);
};
