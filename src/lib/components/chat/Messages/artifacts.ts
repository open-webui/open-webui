import { marked } from 'marked';

type ArtifactCodeToken = {
	type?: string;
	lang?: string | null;
	text?: string | null;
	raw?: string | null;
};

export const isArtifactCodeToken = (token: ArtifactCodeToken) => {
	const lang = (token.lang ?? '').trim().toLowerCase();
	const text = token.text ?? '';

	return lang === 'html' || lang === 'svg' || (lang === 'xml' && text.includes('svg'));
};

const findArtifactCodeToken = (value: unknown): ArtifactCodeToken | null => {
	if (Array.isArray(value)) {
		for (const item of value) {
			const token = findArtifactCodeToken(item);
			if (token) {
				return token;
			}
		}

		return null;
	}

	if (!value || typeof value !== 'object') {
		return null;
	}

	const token = value as ArtifactCodeToken & Record<string, unknown>;

	if (token.type === 'code' && (token.raw ?? '').includes('```') && isArtifactCodeToken(token)) {
		return token;
	}

	for (const child of Object.values(token)) {
		if (Array.isArray(child)) {
			const nestedToken = findArtifactCodeToken(child);
			if (nestedToken) {
				return nestedToken;
			}
		}
	}

	return null;
};

export const getArtifactCodeBlockSignature = (content = '') => {
	if (!content.includes('```')) {
		return null;
	}

	const token = findArtifactCodeToken(marked.lexer(content));

	if (!token) {
		return null;
	}

	return `${(token.lang ?? '').trim().toLowerCase()}\n${token.text ?? ''}`;
};
