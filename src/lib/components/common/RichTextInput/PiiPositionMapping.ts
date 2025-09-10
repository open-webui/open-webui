/**
 * Position mapping utilities for PII processing
 * Maps between plain text positions and ProseMirror document positions
 */

import type { Node as ProseMirrorNode } from 'prosemirror-model';

export interface PositionMapping {
	plainTextToProseMirror: Map<number, number>;
	proseMirrorToPlainText: Map<number, number>;
	plainText: string;
}

/**
 * Build comprehensive position mapping between plain text and ProseMirror document
 * This function traverses the entire ProseMirror document and creates bidirectional
 * mapping for position conversion, handling block elements and special characters.
 */
export function buildPositionMapping(doc: ProseMirrorNode): PositionMapping {
	const plainTextToProseMirror = new Map<number, number>();
	const proseMirrorToPlainText = new Map<number, number>();
	let plainTextOffset = 0;
	let plainText = '';

	function addSyntheticChar(ch: string, pmPos: number) {
		const plainPos = plainTextOffset;
		plainTextToProseMirror.set(plainPos, pmPos);
		proseMirrorToPlainText.set(pmPos, plainPos);
		plainText += ch;
		plainTextOffset += ch.length;
	}

	let previousWasTableCell = false;

	doc.nodesBetween(0, doc.content.size, (node, pos, parent, index) => {
		if (node.isText && node.text) {
			for (let i = 0; i < node.text.length; i++) {
				const proseMirrorPos = pos + i;
				const plainTextPos = plainTextOffset + i;
				plainTextToProseMirror.set(plainTextPos, proseMirrorPos);
				proseMirrorToPlainText.set(proseMirrorPos, plainTextPos);
			}
			plainText += node.text;
			plainTextOffset += node.text.length;
			previousWasTableCell = false;
		} else {
			const typeName = node.type.name;

			// Insert block separators BEFORE starting a new block
			const needsLeadingNewline = () =>
				plainTextOffset > 0 && plainText.charAt(plainTextOffset - 1) !== '\n';

			if (typeName === 'tableRow') {
				if (needsLeadingNewline()) addSyntheticChar('\n', pos);
				previousWasTableCell = false;
			} else if (typeName === 'tableCell' || typeName === 'tableHeader') {
				if (previousWasTableCell) addSyntheticChar('\t', pos);
				previousWasTableCell = true;
			} else if (typeName === 'hardBreak') {
				addSyntheticChar('\n', pos);
				previousWasTableCell = false;
			} else if (
				typeName === 'paragraph' ||
				typeName === 'heading' ||
				typeName === 'blockquote' ||
				typeName === 'codeBlock' ||
				typeName === 'listItem' ||
				typeName === 'bulletList' ||
				typeName === 'orderedList' ||
				typeName === 'taskList'
			) {
				if (needsLeadingNewline()) addSyntheticChar('\n', pos);
				previousWasTableCell = false;
			} else {
				previousWasTableCell = false;
			}
		}
		return true;
	});

	return { plainTextToProseMirror, proseMirrorToPlainText, plainText };
}
