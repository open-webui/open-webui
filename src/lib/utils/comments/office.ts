import type { WorkBook } from 'xlsx';
import type { CommentResult, FileComment } from './types';
import { OfficePackage, elements, attr, text, presentationSlides, children } from './package';

const status = (value: string): FileComment['status'] =>
	['1', 'true', 'resolved', 'closed'].includes(value)
		? 'resolved'
		: ['0', 'false', 'active', 'open'].includes(value)
			? 'open'
			: undefined;
const result = (pkg: OfficePackage, comments: FileComment[]): CommentResult => ({
	comments,
	warnings: [...new Set(pkg.warnings)]
});

async function word(pkg: OfficePackage): Promise<CommentResult> {
	const main = await pkg.main();
	const rels = await pkg.relationships(main);
	const document = await pkg.xml(main);
	if (!document) throw new Error('Could not read Word document');
	const comments: FileComment[] = [];
	const paragraphIds = new Map<string, string>();
	const durableIds = new Map<string, string>();
	const metadata: Array<{ para: string; parent: string; done: string }> = [];
	for (const rel of rels.filter((r) =>
		/\/(comments|commentsExtended|commentsIds|commentsExtensible)$/.test(r.type)
	)) {
		const doc = await pkg.xml(rel.path);
		if (!doc) continue;
		if (rel.type.endsWith('/comments')) {
			for (const c of elements(doc, 'comment')) {
				const id = attr(c, 'id');
				const paragraphs = elements(c, 'p');
				const paraId = attr(paragraphs[paragraphs.length - 1] ?? c, 'paraId');
				if (paraId) paragraphIds.set(paraId, `word:${id}`);
				pkg.checkContent(c);
				const start = elements(document, 'commentRangeStart').find((e) => attr(e, 'id') === id);
				const reference = elements(document, 'commentReference').find((e) => attr(e, 'id') === id);
				let quote = '';
				if (start) {
					const nodes = elements(document, '*');
					for (const e of nodes.slice(nodes.indexOf(start) + 1)) {
						if (e.localName === 'commentRangeEnd' && attr(e, 'id') === id) break;
						if (e.localName === 't') quote += e.textContent ?? '';
					}
				}
				comments.push({
					id: `word:${id}`,
					text: text(c),
					author: attr(c, 'author'),
					date: attr(c, 'date'),
					location: start || reference ? { kind: 'word', anchor: id, quote } : undefined
				});
			}
		} else if (rel.type.endsWith('/commentsExtended')) {
			for (const c of elements(doc, 'commentEx'))
				metadata.push({
					para: attr(c, 'paraId'),
					parent: attr(c, 'paraIdParent'),
					done: attr(c, 'done')
				});
		} else if (rel.type.endsWith('/commentsIds')) {
			for (const c of elements(doc, 'commentId'))
				durableIds.set(attr(c, 'durableId'), attr(c, 'paraId'));
		}
	}
	for (const m of metadata) {
		const c = comments.find((c) => c.id === paragraphIds.get(m.para));
		if (c) {
			c.parentId = m.parent ? paragraphIds.get(m.parent) : undefined;
			c.status = status(m.done);
		}
	}
	for (const rel of rels.filter((r) => r.type.endsWith('/commentsExtensible'))) {
		const doc = await pkg.xml(rel.path);
		if (!doc) continue;
		for (const m of elements(doc, 'commentExtensible')) {
			const c = comments.find(
				(c) => c.id === paragraphIds.get(durableIds.get(attr(m, 'durableId')) ?? '')
			);
			if (c && attr(m, 'dateUtc')) c.date = attr(m, 'dateUtc');
		}
	}
	for (const rel of rels.filter(
		(r) =>
			/comment/i.test(r.type) &&
			!/\/(comments|commentsExtended|commentsIds|commentsExtensible)$/.test(r.type)
	))
		pkg.warnings.push(`Unsupported Word comment metadata: ${rel.type}`);
	return result(pkg, comments);
}

export function workbookNotes(workbook: WorkBook): FileComment[] {
	return workbook.SheetNames.flatMap((sheet) =>
		Object.entries(workbook.Sheets[sheet]).flatMap(([cell, value]) => {
			if (cell.startsWith('!') || !value?.c) return [];
			return value.c.map((c: { t?: string; a?: string; T?: boolean }, index: number) => ({
				id: `cell:${sheet}:${cell}:${index}`,
				text: c.t ?? '',
				author: c.a,
				parentId: c.T && index ? `cell:${sheet}:${cell}:0` : undefined,
				location: { kind: 'cell' as const, sheet, cell }
			}));
		})
	);
}

async function spreadsheet(pkg: OfficePackage, workbook: WorkBook): Promise<CommentResult> {
	const comments = workbookNotes(workbook);
	const main = await pkg.main();
	const doc = await pkg.xml(main);
	if (!doc) throw new Error('Could not read workbook');
	const rels = await pkg.relationships(main);
	const people = new Map<string, string>();
	for (const rel of rels.filter((r) => /\/(person|persons)$/.test(r.type))) {
		const peopleDoc = await pkg.xml(rel.path);
		if (peopleDoc)
			for (const p of elements(peopleDoc, 'person'))
				people.set(attr(p, 'id'), attr(p, 'displayName'));
	}
	for (const sheet of elements(doc, 'sheet')) {
		const name = attr(sheet, 'name');
		const sheetRel = rels.find((r) => r.id === attr(sheet, 'id'));
		if (!sheetRel) {
			pkg.warnings.push(`Missing worksheet relationship: ${name}`);
			continue;
		}
		for (const rel of (await pkg.relationships(sheetRel.path)).filter((r) =>
			/comment/i.test(r.type)
		)) {
			const commentDoc = await pkg.xml(rel.path);
			if (!commentDoc) continue;
			if (rel.type.endsWith('/threadedComment')) {
				const threaded = elements(commentDoc, 'threadedComment');
				const cells = new Set(threaded.map((c) => attr(c, 'ref')).filter(Boolean));
				for (let i = comments.length - 1; i >= 0; i--) {
					const loc = comments[i].location;
					if (loc?.kind === 'cell' && loc.sheet === name && cells.has(loc.cell))
						comments.splice(i, 1);
				}
				for (const c of threaded)
					comments.push({
						id: `thread:${attr(c, 'id')}`,
						parentId: attr(c, 'parentId') ? `thread:${attr(c, 'parentId')}` : undefined,
						text: elements(c, 'text')[0]?.textContent ?? '',
						author: people.get(attr(c, 'personId')),
						date: attr(c, 'dT'),
						status: status(attr(c, 'done')),
						location: attr(c, 'ref')
							? { kind: 'cell', sheet: name, cell: attr(c, 'ref') }
							: undefined
					});
			} else if (!rel.type.endsWith('/comments'))
				pkg.warnings.push(`Unsupported spreadsheet comment metadata: ${rel.type}`);
		}
	}
	return result(pkg, comments);
}

async function presentation(pkg: OfficePackage): Promise<CommentResult> {
	const main = await pkg.main();
	const authors = new Map<string, string>();
	const mainRels = await pkg.relationships(main);
	for (const rel of mainRels.filter((r) => /\/(commentAuthors|authors)$/.test(r.type))) {
		const doc = await pkg.xml(rel.path);
		if (doc)
			for (const p of [...elements(doc, 'cmAuthor'), ...elements(doc, 'author')])
				authors.set(attr(p, 'id'), attr(p, 'name'));
	}
	const presentationDoc = await pkg.xml(main);
	const size = presentationDoc ? elements(presentationDoc, 'sldSz')[0] : null;
	const width = size ? Number(attr(size, 'cx')) / 9525 : undefined;
	const height = size ? Number(attr(size, 'cy')) / 9525 : undefined;
	const paths = await presentationSlides(pkg);
	let pdfPage = 0;
	const comments: FileComment[] = [];
	for (let i = 0; i < paths.length; i++) {
		const slide = await pkg.xml(paths[i]);
		if (!slide) continue;
		const hidden = ['0', 'false'].includes(attr(slide.documentElement, 'show'));
		if (!hidden) pdfPage++;
		const rels = (await pkg.relationships(paths[i])).filter((r) => /comment/i.test(r.type));
		// Modern threads supersede legacy compatibility comments for this slide.
		const modern = rels.filter((r) => /2018|2020/.test(r.type));
		for (const rel of modern.length ? modern : rels) {
			const doc = await pkg.xml(rel.path);
			if (!doc) continue;
			const roots = elements(doc, 'cm');
			if (!roots.length && children(doc.documentElement).length)
				pkg.warnings.push(`Unsupported presentation comment structure: ${rel.path}`);
			for (const c of roots) {
				const isModern = /powerpoint\/2018/.test(c.namespaceURI ?? '');
				const id = isModern ? attr(c, 'id') : `${attr(c, 'authorId')}:${attr(c, 'idx')}`;
				const key = `slide:${i + 1}:${id}`;
				const position = elements(c, 'pos')[0];
				// Classic positions use 1/8 point units; modern positions are object-relative EMUs.
				const x = position && !isModern ? Number(attr(position, 'x')) / 6 : undefined;
				const y = position && !isModern ? Number(attr(position, 'y')) / 6 : undefined;
				const body = isModern ? children(c).find((e) => e.localName === 'txBody') : null;
				comments.push({
					id: key,
					text: isModern ? (body ? text(body) : '') : (elements(c, 'text')[0]?.textContent ?? ''),
					author: authors.get(attr(c, 'authorId')),
					date: attr(c, isModern ? 'created' : 'dt'),
					status: status(attr(c, 'status')),
					location: {
						kind: 'slide',
						slide: i + 1,
						hidden,
						pdfPage: hidden ? undefined : pdfPage,
						width,
						height,
						x,
						y
					}
				});
				for (const reply of elements(c, 'reply'))
					comments.push({
						id: `slide:${i + 1}:${attr(reply, 'id')}`,
						parentId: key,
						text: text(reply),
						author: authors.get(attr(reply, 'authorId')),
						date: attr(reply, 'created'),
						status: status(attr(reply, 'status'))
					});
				pkg.checkContent(c);
			}
		}
	}
	return result(pkg, comments);
}

export async function readOfficeComments(
	data: ArrayBuffer,
	ext: string,
	workbook?: WorkBook
): Promise<CommentResult> {
	if (ext === 'xls') return { comments: workbook ? workbookNotes(workbook) : [], warnings: [] };
	const pkg = await OfficePackage.open(data);
	if (ext === 'docx') return word(pkg);
	if (ext === 'pptx') return presentation(pkg);
	if (ext === 'xlsx' && workbook) return spreadsheet(pkg, workbook);
	throw new Error('Unsupported document format');
}
