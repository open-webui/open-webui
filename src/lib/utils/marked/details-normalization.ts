const structuralDetailsPattern =
	/<details\b[^>]*\btype="(?:tool_calls|reasoning|code_interpreter)"[^>]*>/g;

const findDetailsBlockEnd = (value: string, startIndex: number) => {
	let depth = 1;
	let index = startIndex;

	while (depth > 0 && index < value.length) {
		const nextOpen = value.indexOf('<details', index);
		const nextClose = value.indexOf('</details>', index);

		if (nextClose === -1) return -1;

		if (nextOpen !== -1 && nextOpen < nextClose) {
			depth++;
			index = nextOpen + '<details'.length;
		} else {
			depth--;
			index = nextClose + '</details>'.length;
		}
	}

	return depth === 0 ? index : -1;
};

const appendBlockBoundary = (value: string) => {
	if (!value || value.endsWith('\n\n')) return value;
	return value.endsWith('\n') ? `${value}\n` : `${value}\n\n`;
};

const hasOnlyWhitespaceBetweenStructuralDetails = (result: string, gap: string) => {
	return gap.trim().length === 0 && result.trimEnd().endsWith('</details>');
};

export const normalizeStructuralDetailsBlocks = (value = '') => {
	let result = '';
	let cursor = 0;

	structuralDetailsPattern.lastIndex = 0;
	let match: RegExpExecArray | null;

	while ((match = structuralDetailsPattern.exec(value)) !== null) {
		const start = match.index;
		const end = findDetailsBlockEnd(value, start + match[0].length);
		if (end === -1) continue;

		const gap = value.slice(cursor, start);
		result += gap;
		if (!hasOnlyWhitespaceBetweenStructuralDetails(result, gap)) {
			result = appendBlockBoundary(result);
		}
		result += value.slice(start, end);

		cursor = end;
		structuralDetailsPattern.lastIndex = end;
	}

	return result + value.slice(cursor);
};
