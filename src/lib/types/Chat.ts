export type Chat = {
	history: History;
	models: string[];
	messages: Message[];
	options: ChatOptions;
	timestamp: string | number | Date;
	title: string;
};
export type ChatOptions = {
	//
};
export type ChatHistory = {
	currrentId: string;
	messages: Message;
};
export type Message = {
	id: string;
	parentId: string | null;
	childrenIds: string;
	role: string;
	// TODO figure out the content type
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	content: any;
	model: string;
	done: boolean;
	context: null;
};
export type Conversation = {
	id: string;
	user_id: string;
	title: string;
	chat: Chat;
	timestamp: string | number | Date;
};
