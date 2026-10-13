import type { Embed } from '$lib/apis/apps';

export const getAppMessageText = (message?: {
	content?: string;
	data?: { app?: { embeds?: Embed[] } };
}) =>
	[
		message?.content,
		...(message?.data?.app?.embeds ?? []).map((embed) =>
			[
				embed.author?.name,
				embed.title,
				embed.description,
				...(embed.fields ?? []).map((field) => `${field.name}: ${field.value}`),
				embed.footer?.text,
				embed.url
			]
				.filter(Boolean)
				.join('\n')
		)
	]
		.filter(Boolean)
		.join('\n\n');
