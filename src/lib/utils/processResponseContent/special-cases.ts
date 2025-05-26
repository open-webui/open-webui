/* Expliantion:
 *   This file handles special cases of LLM output not following markdown syntax.
 *   It obeys the rule of modifying original text as **LITTLE** as possible.
 *   Detailed documentation of rendering problems is provided in comments.
 *   More special cases can be added in future.
 * Note:
 *   It should NOT handle the case unless there is clear evidence that it occurs.
 *   It only deals with special cases, especially with non-English characters, not general ones.
 *   Other general issues found, new files shall be added to folder `'$lib/utils/processResponseContent/`,
 *   and function `processResponseContent` in `$lib/utils/index.ts` should be updated accordingly.
 */

export const specialCases = (src: string): string => {
	const lines = src.split('\n'); // Process from line to line.
	const processedLines = lines.map((line) => {
		// 1. 中文 (Chinese, CN)
		if (/[\u4e00-\u9fa5]/.test(line)) {
			// 1.1. Problems caused by Chinese parentheses
			/* Discription:
			 *   When `*` has Chinese parentheses on the inside, markdown parser ignore bold or italic style.
			 *   - e.g. `**中文名（English）**中文内容` will be parsed directly,
			 *          instead of `<strong>中文名（English）</strong>中文内容`.
			 * Solution:
			 *   Adding a `space` before and after the bold/italic part can solve the problem.
			 *   - e.g. `**中文名（English）**中文内容` -> ` **中文名（English）** 中文内容`
			 * Note:
			 *   Similar problem was found with English parentheses and other full delimiters,
			 *   but they are not handled here because they are less likely to appear in LLM output.
			 *   Change the behavior in future if needed.
			 */

			if (line.includes('*')) {
				// 1.1.1. Handle **bold** with Chinese parentheses
				line = processCN_01(line, '**', '（', '）');
				// 1.1.2. Handle *italic* with Chinese parentheses
				line = processCN_01(line, '*', '（', '）');
			}
		}
		return line;
	});
	const result = processedLines.join('\n');
	return result;
};

//////////////////////////
// Helper functions
//////////////////////////

function isChineseChar(char: string): boolean {
	return /\p{Script=Han}/u.test(char);
}

function escapeRegExp(string: string): string {
	return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
}

//////////////////////////
// Main functions
//////////////////////////

// Handle case `1.1.1` and `1.1.2`
function processCN_01(
	line: string,
	symbol: string,
	leftSymbol: string,
	rightSymbol: string
): string {
	const escapedSymbol = escapeRegExp(symbol);
	const regex = new RegExp(
		`(.?)(?<!${escapedSymbol})(${escapedSymbol})([^${escapedSymbol}]+)(${escapedSymbol})(?!${escapedSymbol})(.)`,
		'g'
	);
	return line.replace(regex, (match, l, left, content, right, r) => {
		const result =
			(content.startsWith(leftSymbol) && l && l.length > 0 && isChineseChar(l[l.length - 1])) ||
			(content.endsWith(rightSymbol) && r && r.length > 0 && isChineseChar(r[0]));

		if (result) {
			return `${l} ${left}${content}${right} ${r}`;
		} else {
			return match;
		}
	});
}
