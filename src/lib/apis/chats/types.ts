// Derived from /api/v1/chats/?page=1

export type ChatId = string;
export type UnixTimestamp = number;

export type Chat = {
    id: ChatId;
	title: string;
	updated_at: UnixTimestamp;
	created_at: UnixTimestamp;
};
