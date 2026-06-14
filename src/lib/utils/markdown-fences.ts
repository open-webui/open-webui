/**
 * Normalize nested triple-backtick fences inside a language-tagged code block.
 *
 * LLMs frequently emit a language-tagged block (e.g. ```python) opened with only
 * three backticks whose body itself contains ``` fences — a prompt string, a
 * markdown example, etc. Per CommonMark (which `marked` implements) the 3-backtick
 * outer fence is closed by the FIRST inner ```, so the block breaks apart and the
 * remainder spills into alternating prose/code tokens. The model should have used
 * 4+ backticks on the outer fence; this rewrites the outer fence pair to use one
 * more backtick than the longest nested fence so the inner fences become content.
 *
 * Heuristic: a language-tagged opener owns everything up to the LAST fence before
 * the next language-tagged opener, EOF, or a markdown section heading — whichever
 * comes first. We trust the *last* close (not the first), but never extend across a
 * prose boundary. This matches LLM conventions: outer blocks are language-tagged,
 * nested example fences are bare and embedded in code, and distinct top-level blocks
 * are separated by prose (headings).
 *
 * The "prose boundary" is an ATX heading of level >= 2 (`## ` … `###### `). Level is
 * capped at 2+ on purpose so a single-`#` code comment (`# Configuration`) is NOT
 * mistaken for a heading. Stopping at a heading prevents a tagged block from swallowing
 * a later, unrelated bare code block (and the prose between them) into itself.
 *
 * Streaming-safe: a no-op until 2+ fences are present and a nested fence would
 * actually close the block. Idempotent: already-wide outer fences are skipped.
 *
 * Known limitations: tilde (~~~) fences are not handled (a ~ fence cannot close a
 * backtick fence in marked, so there is nothing to corrupt); two code blocks separated
 * only by a plain sentence (no heading) where the second is bare can still over-merge.
 * The bias is toward UNDER-merging (leaving a block unfixed, i.e. no worse than today)
 * rather than over-merging (hiding prose inside a code block).
 *
 * NOTE: `replaceOutsideCode` in ./index.ts shares the same naive ```...``` pairing
 * blind spot, but it only drives token substitution (low blast radius) and is left
 * untouched here.
 */
export const normalizeNestedFences = (content: string): string => {
	if (!content || !content.includes('```')) return content;

	const lines = content.split('\n');
	// Whole-line fence: ≤3 leading spaces, 3+ backticks, optional info string (no backticks).
	const fenceRe = /^( {0,3})(`{3,})[ \t]*([^`]*?)[ \t]*$/;

	type Fence = { lineIdx: number; indent: number; ticks: number; info: string; tagged: boolean };
	const fences: Fence[] = [];
	for (let i = 0; i < lines.length; i++) {
		const m = fenceRe.exec(lines[i]);
		if (m) {
			fences.push({
				lineIdx: i,
				indent: m[1].length,
				ticks: m[2].length,
				info: m[3],
				tagged: m[3] !== ''
			});
		}
	}
	if (fences.length < 2) return content;

	// ATX heading, level >= 2 — a prose boundary a tagged block must not extend across.
	const headingRe = /^ {0,3}#{2,6}\s/;

	const edits: { openIdx: number; closeIdx: number; ticks: number; indent: number; info: string }[] =
		[];
	let k = 0;
	while (k < fences.length) {
		const open = fences[k];
		if (!open.tagged) {
			// Leave orphan bare top-level fences alone — we can't tell open from close.
			k++;
			continue;
		}

		// The next language-tagged opener begins a sibling block; the current opener
		// cannot extend past it.
		let nextTagged = k + 1;
		while (nextTagged < fences.length && !fences[nextTagged].tagged) {
			nextTagged++;
		}

		// A markdown heading after the opener also bounds the block: nested example
		// fences live in code (no headings between them), so the first heading marks
		// where this code block must already have ended.
		const regionEnd = nextTagged < fences.length ? fences[nextTagged].lineIdx : lines.length;
		let proseLine = regionEnd;
		for (let li = open.lineIdx + 1; li < regionEnd; li++) {
			if (headingRe.test(lines[li])) {
				proseLine = li;
				break;
			}
		}

		// True close = last fence before the next tagged opener AND before any heading.
		let closePos = -1;
		for (let j = k + 1; j < nextTagged; j++) {
			if (fences[j].lineIdx < proseLine) closePos = j;
			else break;
		}

		if (closePos <= k) {
			// No nested fence before the boundary → ordinary, well-formed block.
			k = nextTagged;
			continue;
		}

		// Widest nested fence strictly between the opener and its true close.
		let maxInner = 0;
		for (let j = k + 1; j < closePos; j++) {
			if (fences[j].ticks > maxInner) maxInner = fences[j].ticks;
		}

		// Only rewrite when a nested fence would actually close the block
		// (maxInner >= open.ticks). This guard also makes the transform idempotent.
		if (closePos - k - 1 >= 1 && maxInner >= open.ticks) {
			edits.push({
				openIdx: open.lineIdx,
				closeIdx: fences[closePos].lineIdx,
				ticks: maxInner + 1,
				indent: open.indent,
				info: open.info
			});
		}

		k = nextTagged;
	}

	if (edits.length === 0) return content;

	for (const e of edits) {
		const fence = '`'.repeat(e.ticks);
		const pad = ' '.repeat(e.indent);
		lines[e.openIdx] = `${pad}${fence}${e.info}`;
		lines[e.closeIdx] = `${pad}${fence}`;
	}
	return lines.join('\n');
};
