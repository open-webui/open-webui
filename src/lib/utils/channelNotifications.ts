export const shouldNotifyChannelMessage = (
	isMuted: boolean,
	content: string,
	userId: string
): boolean =>
	!isMuted ||
	Array.from(content.matchAll(/<@U:([^|>]+)(?:\|[^>]+)?>/g)).some((match) => match[1] === userId);
