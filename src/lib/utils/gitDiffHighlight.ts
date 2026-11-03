import type { BundledLanguage } from 'shiki';
import type { DiffSegment } from '../components/chat/Messages/diff';
import type { VersionDiffHunk, VersionDiffLine } from '../components/workspace/common/versionDiff';
import { languageForFilePath } from './codeHighlight';

export type HighlightSegment = DiffSegment & { light?: string; dark?: string };
type Token = {
	content: string;
	variants: { light?: { color?: string }; dark?: { color?: string } };
};

export function diffFilePath(content: string): string {
	for (const marker of ['+++', '---']) {
		const raw = content
			.split('\n')
			.find((line) => line.startsWith(`${marker} `))
			?.slice(4);
		if (!raw || raw === '/dev/null') continue;
		let path = raw;
		if (raw.startsWith('"')) {
			try {
				path = JSON.parse(raw);
			} catch {
				/* Keep an unfamiliar Git path readable. */
			}
		}
		return path.replace(/^[ab]\//, '');
	}
	return content.match(/^rename to (.+)$/m)?.[1] ?? '';
}

export function mergeSyntaxTokens(tokens: Token[], segments: DiffSegment[]): HighlightSegment[] {
	const result: HighlightSegment[] = [];
	let tokenOffset = 0;
	let segmentOffset = 0;
	let segmentIndex = 0;
	for (const token of tokens) {
		const tokenEnd = tokenOffset + token.content.length;
		while (segmentIndex < segments.length && segmentOffset < tokenEnd) {
			const segment = segments[segmentIndex];
			const segmentEnd = segmentOffset + segment.text.length;
			const start = Math.max(segmentOffset, tokenOffset);
			const end = Math.min(segmentEnd, tokenEnd);
			if (start < end)
				result.push({
					text: token.content.slice(start - tokenOffset, end - tokenOffset),
					changed: segment.changed,
					light: token.variants.light?.color,
					dark: token.variants.dark?.color
				});
			if (segmentEnd > tokenEnd) break;
			segmentOffset = segmentEnd;
			segmentIndex++;
		}
		tokenOffset = tokenEnd;
	}
	return result.length ? result : segments;
}

export async function highlightDiffFile(path: string, hunks: VersionDiffHunk[]) {
	const highlighted = new Map<VersionDiffLine, HighlightSegment[]>();
	const language = languageForFilePath(path);
	if (!language || !hunks.length) return highlighted;
	const { codeToTokensWithThemes, bundledLanguages } = await import('shiki');
	if (!(language in bundledLanguages)) return highlighted;
	for (const hunk of hunks) {
		// Tokenize each side separately so embedded languages and multiline strings retain context.
		for (const side of ['before', 'after'] as const) {
			const lines = hunk.rows
				.map((row) => row[side])
				.filter((line): line is VersionDiffLine => !!line);
			if (!lines.length) continue;
			const tokens = await codeToTokensWithThemes(lines.map((line) => line.content).join('\n'), {
				lang: language as BundledLanguage,
				themes: { light: 'github-light', dark: 'github-dark' }
			});
			lines.forEach((line, index) =>
				highlighted.set(line, mergeSyntaxTokens(tokens[index] ?? [], line.segments))
			);
		}
	}
	return highlighted;
}
