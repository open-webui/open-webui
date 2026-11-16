import type { Writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { updateChatById } from '$lib/apis/chats';
import { isSavedChatId } from '$lib/utils/chatId';

export function terminalIconName(process: string, title = ''): string {
	const command =
		(process || title)
			.trim()
			.split(/[\\/]/)
			.pop()
			?.toLowerCase()
			.replace(/\.exe$/, '') ?? '';
	if (!process || ['node', 'nodejs', 'bun', 'deno'].includes(command)) {
		const agent = title
			.replace(/^[^\p{L}\p{N}]+/u, '')
			.match(/^(claude(?: code)?|codex)(?=$|[\s:])/i);
		if (agent) return agent[1].toLowerCase().startsWith('claude') ? 'claude' : 'openai';
	}
	if (/^(?:pythonw?|ipython|pypy)\d*(?:\.\d+)*$/.test(command)) return 'python';
	const icons: Record<string, string> = {
		claude: 'claude',
		'claude-code': 'claude',
		codex: 'openai',
		node: 'nodejs',
		nodejs: 'nodejs',
		npm: 'npm',
		npx: 'npm',
		pnpm: 'npm',
		yarn: 'npm',
		git: 'git-branch',
		docker: 'docker',
		ruby: 'ruby-logo',
		go: 'go-logo',
		rustc: 'rust',
		cargo: 'rust',
		java: 'java-logo',
		php: 'php-logo',
		sqlite3: 'database-script'
	};
	return icons[command] ?? 'terminal';
}

// Select a chat's terminal at once, saving it to the chat in the background.
export const selectTerminal = (
	selectedTerminalId: Pick<Writable<string | null>, 'set'>,
	id: string | null,
	chatId: string | null
) => {
	selectedTerminalId.set(id);
	if (isSavedChatId(chatId))
		updateChatById(localStorage.token, chatId!, { terminal_id: id, working_directory: '' }).catch(
			(error) => toast.error(String(error))
		);
};
