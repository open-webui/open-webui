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
