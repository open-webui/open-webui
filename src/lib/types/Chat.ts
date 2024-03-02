export type Chat = {
	history: History;
	models: string[];
	messages: Message[];
	options: ChatOptions;
	title: string;
};
export type ChatOptions = {
	//
};
export type ChatHistory = {
	currentId: string | null;
	messages: { [key: string]: Message };
};
export type Message = {
	id: string;
	parentId: string | null;
	childrenIds: string;
	role: string;
	content: string;
	user?: string;
	timestamp?: number;
	files: MessageFile[];
	model: string;
	done: boolean;
	context: null;
	info?: MessageInfo;
};

export type Conversation = {
	id: string;
	user_id: string;
	title: string;
	chat: Chat;
	timestamp: string | number | Date;
};

export type MessageFile = {
	type: MessageFileType;
	name: string;
	title?: string;
	url: string;
};

export const MessageFileTypes = {
	image: 'image',
	doc: 'doc',
	collection: 'collection'
};
export type MessageFileType = keyof typeof MessageFileTypes;

export type MessageInfo = {
	eval_duration: number;
	prompt_eval_duration: number;
	eval_count?: number;
	prompt_eval_count?: number;
	total_duration?: number;
	load_duration?: number;
};
