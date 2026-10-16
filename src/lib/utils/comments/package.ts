import JSZip from 'jszip';

export const elements = (node: Document | Element, name: string): Element[] =>
	Array.from(node.getElementsByTagNameNS('*', name));
export const children = (node: Node): Element[] =>
	Array.from(node.childNodes).filter((n) => n.nodeType === 1) as Element[];
export const attr = (node: Element, name: string) =>
	Array.from(node.attributes).find((a) => a.localName === name)?.value ?? '';
export const text = (node: Element, paragraph = 'p') => {
	const paragraphs = elements(node, paragraph);
	return (paragraphs.length ? paragraphs : [node])
		.map((p) =>
			elements(p, 't')
				.map((t) => t.textContent ?? '')
				.join('')
		)
		.join('\n');
};
export function resolvePart(source: string, target: string) {
	const parts: string[] = [];
	for (const part of (target.startsWith('/')
		? target
		: `${source.slice(0, source.lastIndexOf('/') + 1)}${target}`
	).split('/')) {
		if (part === '..') {
			if (!parts.length) throw new Error('Invalid package relationship');
			parts.pop();
		} else if (part && part !== '.') parts.push(part);
	}
	return parts.join('/');
}
export interface Relationship {
	id: string;
	type: string;
	path: string;
}
export class OfficePackage {
	warnings: string[] = [];
	private cache = new Map<string, Promise<Document | null>>();
	constructor(readonly zip: JSZip) {}
	static async open(data: ArrayBuffer) {
		return new OfficePackage(await JSZip.loadAsync(data));
	}
	async xml(path: string): Promise<Document | null> {
		if (!this.cache.has(path)) this.cache.set(path, this.read(path));
		return this.cache.get(path)!;
	}
	private async read(path: string) {
		const file = this.zip.file(path);
		if (!file) {
			this.warnings.push(`Missing document part: ${path}`);
			return null;
		}
		try {
			// XML metadata should not be allowed to expand without a bound in the browser.
			const size = (file as unknown as { _data?: { uncompressedSize?: number } })._data
				?.uncompressedSize;
			if (size && size > 32 * 1024 * 1024) throw new Error('XML part exceeds 32 MB');
			const xml = await file.async('string');
			if (xml.length > 32 * 1024 * 1024 || /<!DOCTYPE/i.test(xml))
				throw new Error('Unsupported XML content');
			const doc = new DOMParser().parseFromString(xml, 'application/xml');
			if (elements(doc, 'parsererror').length) throw new Error('Malformed XML');
			return doc;
		} catch {
			this.warnings.push(`Could not read document part: ${path}`);
			return null;
		}
	}
	async relationships(source: string): Promise<Relationship[]> {
		const slash = source.lastIndexOf('/');
		const path = source
			? `${source.slice(0, slash + 1)}_rels/${source.slice(slash + 1)}.rels`
			: '_rels/.rels';
		if (!this.zip.file(path)) return [];
		const doc = await this.xml(path);
		return doc
			? elements(doc, 'Relationship').flatMap((r) => {
					if (attr(r, 'TargetMode') === 'External') return [];
					try {
						return [
							{
								id: attr(r, 'Id'),
								type: attr(r, 'Type'),
								path: resolvePart(source, attr(r, 'Target'))
							}
						];
					} catch {
						this.warnings.push(`Invalid relationship in ${path}`);
						return [];
					}
				})
			: [];
	}
	async main() {
		const main = (await this.relationships('')).find((r) => r.type.endsWith('/officeDocument'));
		if (!main) throw new Error('Missing Office document relationship');
		return main.path;
	}
	checkContent(node: Element) {
		if (
			elements(node, 'drawing').length ||
			elements(node, 'pic').length ||
			elements(node, 'altChunk').length
		)
			this.warnings.push(
				'Some embedded comment content cannot be displayed. Download the original file to view it.'
			);
	}
}

export async function presentationSlides(pkg: OfficePackage) {
	const main = await pkg.main();
	const doc = await pkg.xml(main);
	if (!doc) throw new Error('Could not read presentation');
	const rels = await pkg.relationships(main);
	return elements(doc, 'sldId').map((slide) => {
		const id = Array.from(slide.attributes).find(
			(a) => a.localName === 'id' && a.namespaceURI
		)?.value;
		const rel = rels.find((r) => r.id === id);
		if (!rel) throw new Error('Missing slide relationship');
		return rel.path;
	});
}
