// Kept apart from $lib/utils so the YAML parser only loads with the editors that need it.
import { parse as parseYaml } from 'yaml';

export const parseFrontmatter = (content: string): Record<string, unknown> => {
	const match = content.match(/^\uFEFF?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/);
	if (!match) return {};
	try {
		const fields = parseYaml(match[1]);
		return fields && typeof fields === 'object' && !Array.isArray(fields) ? fields : {};
	} catch {
		// Incomplete frontmatter is normal while typing.
		return {};
	}
};
