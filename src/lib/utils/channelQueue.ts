import { get } from 'svelte/store';
import { sendMessage } from '$lib/apis/channels';
import { channelRequestQueues, user } from '$lib/stores';

export const processingQueueChannels = new Set<string>();

export const processNextInQueue = async (key: string, messageId?: string) => {
	if (processingQueueChannels.has(key)) return;
	processingQueueChannels.add(key);
	try {
		while (get(channelRequestQueues)[key]?.length) {
			const queue = get(channelRequestQueues)[key] ?? [];
			const item = messageId ? queue.find((m) => m.id === messageId) : queue[0];
			if (
				!item ||
				item.user_id !== get(user)?.id ||
				(item.error && !messageId) ||
				item.files.some((file) => ['uploading', 'error'].includes(file.status))
			)
				return;

			messageId = undefined;
			item.sending = true;
			item.error = undefined;
			channelRequestQueues.update((q) => q);
			try {
				const result = await sendMessage(localStorage.token, item.channel_id, {
					temp_id: item.id,
					parent_id: item.parent_id ?? undefined,
					reply_to_id: item.reply_to_message?.id ?? null,
					content: item.prompt,
					data: { files: item.files }
				});
				if (!result) throw new Error('Failed to send message');
				channelRequestQueues.update((q) => {
					if (q[key]) q[key] = q[key].filter((m) => m.id !== item.id);
					return q;
				});
			} catch (error) {
				// Logout can clear this entry while the request is pending.
				if (!get(channelRequestQueues)[key]?.includes(item)) continue;
				item.sending = false;
				item.error = String(error);
				channelRequestQueues.update((q) => q);
				return;
			}
		}
	} finally {
		processingQueueChannels.delete(key);
	}
};
