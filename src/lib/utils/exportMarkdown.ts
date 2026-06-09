type ChatMessage = {
	parentId?: string | null;
	role?: string | null;
	content?: unknown;
};

type ChatMessages = Record<string, ChatMessage | undefined>;

type ChatMetadata = {
	title?: unknown;
	created_at?: unknown;
	models?: unknown;
};

const yamlQuote = (value: string) =>
	JSON.stringify(value.replace(/\r\n/g, '\n').replace(/\r/g, '\n'));

const getDate = (createdAt: unknown) => {
	const timestamp =
		typeof createdAt === 'number' && Number.isFinite(createdAt)
			? createdAt * 1000
			: typeof createdAt === 'string' && Number.isFinite(Number(createdAt))
				? Number(createdAt) * 1000
				: Date.now();

	return new Date(timestamp).toISOString().split('T')[0];
};

const getTitle = (title: unknown) => {
	return typeof title === 'string' && title.trim() ? title.trim() : 'Open WebUI Conversation';
};

const getModel = (models: unknown) => {
	if (Array.isArray(models)) {
		const model = models.find((item) => typeof item === 'string' && item.trim());
		return model ?? 'Unknown Model';
	}

	return typeof models === 'string' && models.trim() ? models.trim() : 'Unknown Model';
};

const formatContent = (content: unknown) => {
	if (typeof content === 'string') {
		return content.trim() ? content : '_No content_';
	}

	if (content === null || content === undefined) {
		return '_No content_';
	}

	return String(content);
};

/**
 * Traverses the chat history tree, formats it as Markdown with YAML frontmatter,
 * and triggers a browser download.
 */
export const exportChatToMarkdown = (
	chat: ChatMetadata | null | undefined,
	messages: ChatMessages | null | undefined,
	currentId: string | null | undefined
) => {
	if (!messages || !currentId) {
		console.error('No message history available to export.');
		return false;
	}

	// 1. Traverse the tree from leaf to root
	const thread: ChatMessage[] = [];
	const visited = new Set<string>();
	let currId: string | null | undefined = currentId;

	while (currId && messages[currId]) {
		if (visited.has(currId)) {
			break;
		}

		visited.add(currId);
		const message: ChatMessage | undefined = messages[currId];
		if (!message) {
			break;
		}

		thread.push(message);
		// Move up to the parent message
		currId = message.parentId;
	}

	// 2. Reverse the array so the conversation is chronological
	thread.reverse();

	// 3. Generate YAML Frontmatter
	const date = getDate(chat?.created_at);
	const title = getTitle(chat?.title);
	const model = getModel(chat?.models);

	let markdown = `---\n`;
	markdown += `title: ${yamlQuote(title)}\n`;
	markdown += `date: ${date}\n`;
	markdown += `model: ${yamlQuote(model)}\n`;
	markdown += `tags: [open-webui, pkm-export]\n`;
	markdown += `---\n\n`;
	markdown += `# ${title}\n\n`;

	// 4. Format the conversation thread
	thread.forEach((msg) => {
		// Skip system prompts if desired, or include them based on preference
		if (msg.role === 'system') return;

		const roleHeader = msg.role === 'user' ? '### User' : '### Assistant';
		markdown += `${roleHeader}\n\n${formatContent(msg.content)}\n\n---\n\n`;
	});

	// 5. Create the Blob and trigger the download
	const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8;' });
	const url = URL.createObjectURL(blob);

	// Sanitize the filename
	const safeTitle = title.replace(/[^a-z0-9]/gi, '_').toLowerCase();

	const link = document.createElement('a');
	link.href = url;
	link.download = `${safeTitle}_${date}.md`;
	link.style.display = 'none';

	document.body.appendChild(link);
	link.click();

	// Cleanup
	document.body.removeChild(link);
	URL.revokeObjectURL(url);

	return true;
};
