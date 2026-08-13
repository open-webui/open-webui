/**
 * Lightweight PPTX → Image renderer.
 *
 * Extracts text and images from each slide and renders them
 * directly to canvas, returning PNG data URLs.
 *
 * Uses jszip (dynamically imported) and the browser Canvas 2D API.
 * No theme resolution, charts, SmartArt, or animations — preview only.
 */

const EMU_PER_PX = 9525;
const emuToPx = (emu: number) => Math.round(emu / EMU_PER_PX);

const parseEmu = (val: string | null | undefined): number => (val ? parseInt(val, 10) || 0 : 0);

type ZipLike = {
	file: (path: string) => { async: (type: 'text' | 'base64') => Promise<string> } | null;
	files: Record<string, unknown>;
};

type Relationship = {
	type: string;
	target: string;
};

type Rect = {
	x: number;
	y: number;
	w: number;
	h: number;
};

type Placeholder = {
	type: string;
	idx: string;
	rect: Rect;
};

type TextToken = {
	text: string;
	fontFace: string;
	fontPt: number;
	bold: boolean;
	italic: boolean;
	color: string;
	width: number;
};

type TextStyle = Omit<TextToken, 'text' | 'width'>;

const getTag = (el: Element) => el.tagName.split(':').pop();

const normalizePath = (path: string) => {
	const parts: string[] = [];
	for (const part of path.split('/')) {
		if (!part || part === '.') continue;
		if (part === '..') parts.pop();
		else parts.push(part);
	}
	return parts.join('/');
};

const dirname = (path: string) => path.slice(0, path.lastIndexOf('/'));
const basename = (path: string) => path.slice(path.lastIndexOf('/') + 1);

const resolveTarget = (sourcePath: string, target: string) => {
	const cleanTarget = target.split('#')[0];
	if (cleanTarget.startsWith('/')) return normalizePath(cleanTarget.slice(1));
	return normalizePath(`${dirname(sourcePath)}/${cleanTarget}`);
};

const readXml = async (zip: ZipLike, path: string): Promise<Document | null> => {
	const file = zip.file(path);
	if (!file) return null;
	const text = await file.async('text');
	return new DOMParser().parseFromString(text, 'application/xml');
};

const readRels = async (
	zip: ZipLike,
	sourcePath: string
): Promise<Record<string, Relationship>> => {
	const relsPath = `${dirname(sourcePath)}/_rels/${basename(sourcePath)}.rels`;
	const relsDoc = await readXml(zip, relsPath);
	const rels: Record<string, Relationship> = {};
	if (!relsDoc) return rels;

	for (const rel of Array.from(relsDoc.getElementsByTagName('Relationship'))) {
		const id = rel.getAttribute('Id') ?? '';
		const target = rel.getAttribute('Target') ?? '';
		if (!id || !target || rel.getAttribute('TargetMode') === 'External') continue;

		rels[id] = {
			type: rel.getAttribute('Type') ?? '',
			target: resolveTarget(sourcePath, target)
		};
	}

	return rels;
};

const getRelationshipTarget = (
	rels: Record<string, Relationship>,
	typeSuffix: string
): string | null => {
	const rel = Object.values(rels).find((entry) => entry.type.endsWith(typeSuffix));
	return rel?.target ?? null;
};

const parseXfrm = (shape: Element): Rect | null => {
	const xfrm = shape.getElementsByTagName('a:xfrm')[0] ?? shape.getElementsByTagName('p:xfrm')[0];
	if (!xfrm) return null;

	const off = xfrm.getElementsByTagName('a:off')[0];
	const ext = xfrm.getElementsByTagName('a:ext')[0];
	if (!off || !ext) return null;

	const rect = {
		x: emuToPx(parseEmu(off.getAttribute('x'))),
		y: emuToPx(parseEmu(off.getAttribute('y'))),
		w: emuToPx(parseEmu(ext.getAttribute('cx'))),
		h: emuToPx(parseEmu(ext.getAttribute('cy')))
	};

	return rect.w === 0 && rect.h === 0 ? null : rect;
};

const getPlaceholder = (shape: Element): { type: string; idx: string } | null => {
	const ph = shape.getElementsByTagName('p:ph')[0];
	if (!ph) return null;
	return {
		type: ph.getAttribute('type') ?? 'body',
		idx: ph.getAttribute('idx') ?? ''
	};
};

const normalizePlaceholderType = (type: string) => (type === 'ctrTitle' ? 'title' : type);

const placeholderKeys = ({ type, idx }: { type: string; idx: string }) => {
	const normalizedType = normalizePlaceholderType(type);
	return [
		idx ? `${type}:${idx}` : '',
		idx ? `${normalizedType}:${idx}` : '',
		type,
		normalizedType,
		idx ? `idx:${idx}` : ''
	].filter(Boolean);
};

const collectPlaceholders = (doc: Document | null): Record<string, Placeholder> => {
	const placeholders: Record<string, Placeholder> = {};
	if (!doc) return placeholders;

	for (const shape of Array.from(doc.getElementsByTagName('p:sp'))) {
		const ph = getPlaceholder(shape);
		const rect = parseXfrm(shape);
		if (!ph || !rect) continue;

		for (const key of placeholderKeys(ph)) {
			placeholders[key] ??= { ...ph, rect };
		}
	}

	return placeholders;
};

const findPlaceholder = (
	ph: { type: string; idx: string } | null,
	placeholderSources: Record<string, Placeholder>[]
): Placeholder | null => {
	if (!ph) return null;
	for (const key of placeholderKeys(ph)) {
		for (const placeholders of placeholderSources) {
			if (placeholders[key]) return placeholders[key];
		}
	}
	return null;
};

const fallbackPlaceholderRect = (
	ph: { type: string; idx: string } | null,
	slideW: number,
	slideH: number
): Rect | null => {
	if (!ph) return null;
	const type = normalizePlaceholderType(ph.type);
	if (type === 'title') {
		return { x: slideW * 0.06, y: slideH * 0.08, w: slideW * 0.88, h: slideH * 0.18 };
	}
	if (type === 'subTitle') {
		return { x: slideW * 0.15, y: slideH * 0.58, w: slideW * 0.7, h: slideH * 0.2 };
	}
	if (['body', 'obj', 'content'].includes(type)) {
		return { x: slideW * 0.07, y: slideH * 0.26, w: slideW * 0.86, h: slideH * 0.6 };
	}
	return null;
};

const placeholderFontSize = (ph: { type: string; idx: string } | null) => {
	const type = normalizePlaceholderType(ph?.type ?? '');
	if (type === 'title') return 34;
	if (type === 'subTitle') return 22;
	return 16;
};

const paragraphAlign = (
	para: Element,
	ph: { type: string; idx: string } | null
): CanvasTextAlign => {
	const align = para.getElementsByTagName('a:pPr')[0]?.getAttribute('algn');
	if (align === 'ctr') return 'center';
	if (align === 'r') return 'right';

	const type = normalizePlaceholderType(ph?.type ?? '');
	if (type === 'title' || type === 'subTitle') return 'center';
	return 'left';
};

const schemeColor = (val: string | null) => {
	switch (val) {
		case 'bg1':
		case 'lt1':
			return '#ffffff';
		case 'tx1':
		case 'dk1':
			return '#000000';
		case 'accent1':
			return '#4472c4';
		case 'accent2':
			return '#ed7d31';
		case 'accent3':
			return '#a5a5a5';
		case 'accent4':
			return '#ffc000';
		case 'accent5':
			return '#5b9bd5';
		case 'accent6':
			return '#70ad47';
		default:
			return null;
	}
};

const solidFillColor = (el: Element | Document | null): string | null => {
	if (!el) return null;
	const fill = el.getElementsByTagName('a:solidFill')[0];
	if (!fill) return null;

	const srgb = fill.getElementsByTagName('a:srgbClr')[0];
	const srgbVal = srgb?.getAttribute('val');
	if (srgbVal) return `#${srgbVal}`;

	const scheme = fill.getElementsByTagName('a:schemeClr')[0];
	return schemeColor(scheme?.getAttribute('val') ?? null);
};

const renderBackground = (
	ctx: CanvasRenderingContext2D,
	doc: Document,
	slideW: number,
	slideH: number
) => {
	const bgColor = solidFillColor(doc.getElementsByTagName('p:bg')[0]);
	if (!bgColor) return;
	ctx.fillStyle = bgColor;
	ctx.fillRect(0, 0, slideW, slideH);
};

const directChild = (el: Element, tag: string) =>
	Array.from(el.children).find((child) => getTag(child) === tag);

const defaultTextStyle = (fontPt: number): TextStyle => ({
	fontFace: 'Calibri',
	fontPt,
	bold: false,
	italic: false,
	color: '#000000'
});

const fontString = ({ italic, bold, fontPt, fontFace }: TextStyle) => {
	const family = fontFace.includes(' ') ? `"${fontFace}"` : fontFace;
	return `${italic ? 'italic ' : ''}${bold ? 'bold ' : ''}${fontPt}pt ${family}, Calibri, Arial, sans-serif`;
};

const readTextStyle = (rPr: Element | undefined, base: TextStyle): TextStyle => {
	if (!rPr) return base;

	const latin = rPr.getElementsByTagName('a:latin')[0];
	const typeface = latin?.getAttribute('typeface');
	const sz = rPr.getAttribute('sz');

	return {
		fontFace: typeface && !typeface.startsWith('+') ? typeface : base.fontFace,
		fontPt: sz ? parseInt(sz, 10) / 100 : base.fontPt,
		bold: rPr.getAttribute('b') === '1' ? true : rPr.getAttribute('b') === '0' ? false : base.bold,
		italic:
			rPr.getAttribute('i') === '1' ? true : rPr.getAttribute('i') === '0' ? false : base.italic,
		color: solidFillColor(rPr) ?? base.color
	};
};

const readParagraphStyle = (para: Element, defaultFontSize: number) => {
	const pPr = directChild(para, 'pPr');
	const defRPr = pPr?.getElementsByTagName('a:defRPr')[0];
	const endParaRPr = para.getElementsByTagName('a:endParaRPr')[0];
	return readTextStyle(defRPr ?? endParaRPr, defaultTextStyle(defaultFontSize));
};

const readRunStyle = (run: Element, base: TextStyle) => {
	const rPr = directChild(run, 'rPr') as Element | undefined;
	return readTextStyle(rPr, base);
};

const textBodyInsets = (txBody: Element) => {
	const bodyPr = txBody.getElementsByTagName('a:bodyPr')[0];
	return {
		left: emuToPx(parseEmu(bodyPr?.getAttribute('lIns') ?? '91440')),
		right: emuToPx(parseEmu(bodyPr?.getAttribute('rIns') ?? '91440')),
		top: emuToPx(parseEmu(bodyPr?.getAttribute('tIns') ?? '45720')),
		bottom: emuToPx(parseEmu(bodyPr?.getAttribute('bIns') ?? '45720'))
	};
};

const paragraphBullet = (para: Element) => {
	const pPr = directChild(para, 'pPr');
	if (!pPr || pPr.getElementsByTagName('a:buNone')[0]) return '';

	const buChar = pPr.getElementsByTagName('a:buChar')[0]?.getAttribute('char');
	if (buChar) return `${buChar} `;

	if (pPr.getElementsByTagName('a:buAutoNum')[0]) return '1. ';
	return '';
};

const drawTextLine = (
	ctx: CanvasRenderingContext2D,
	line: TextToken[],
	align: CanvasTextAlign,
	x: number,
	y: number,
	w: number
) => {
	const lineWidth = line.reduce((sum, token) => sum + token.width, 0);
	let cursorX = x;
	if (align === 'center') cursorX = x + Math.max(0, (w - lineWidth) / 2);
	if (align === 'right') cursorX = x + w - lineWidth;

	for (const token of line) {
		ctx.font = fontString(token);
		ctx.fillStyle = token.color;
		ctx.fillText(token.text, cursorX, y);
		cursorX += token.width;
	}
};

/** Load a data URI into an Image element and wait for it. */
const loadImage = (src: string): Promise<HTMLImageElement> =>
	new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = () => reject(new Error('Failed to load image'));
		img.src = src;
	});

/**
 * Convert PPTX ArrayBuffer → array of PNG data URL strings, one per slide.
 */
export async function pptxToImages(
	buffer: ArrayBuffer
): Promise<{ images: string[]; width: number; height: number }> {
	const JSZip = (await import('jszip')).default;
	const zip = (await JSZip.loadAsync(buffer)) as ZipLike;

	// ── Read slide dimensions from presentation.xml ──────────────────
	let slideW = 960;
	let slideH = 540;
	const presXml = zip.file('ppt/presentation.xml');
	if (presXml) {
		const presText = await presXml.async('text');
		const presDoc = new DOMParser().parseFromString(presText, 'application/xml');
		const sldSz = presDoc.getElementsByTagName('p:sldSz')[0];
		if (sldSz) {
			slideW = emuToPx(parseEmu(sldSz.getAttribute('cx')));
			slideH = emuToPx(parseEmu(sldSz.getAttribute('cy')));
		}
	}

	// ── Collect media files (images) as base64 data URIs ─────────────
	const media: Record<string, string> = {};
	const mediaFiles = Object.keys(zip.files).filter((f) => f.startsWith('ppt/media/'));
	await Promise.all(
		mediaFiles.map(async (path) => {
			const file = zip.file(path);
			if (!file) return;
			const base64 = await file.async('base64');
			const ext = path.split('.').pop()?.toLowerCase() ?? '';
			const mime =
				ext === 'png'
					? 'image/png'
					: ext === 'gif'
						? 'image/gif'
						: ext === 'svg'
							? 'image/svg+xml'
							: ext === 'emf' || ext === 'wmf'
								? 'image/x-emf'
								: 'image/jpeg';
			media[path] = `data:${mime};base64,${base64}`;
		})
	);

	// ── Discover slide files ─────────────────────────────────────────
	const slideFiles = Object.keys(zip.files)
		.filter((f) => /^ppt\/slides\/slide\d+\.xml$/.test(f))
		.sort((a, b) => {
			const na = parseInt(a.match(/slide(\d+)/)?.[1] ?? '0');
			const nb = parseInt(b.match(/slide(\d+)/)?.[1] ?? '0');
			return na - nb;
		});

	const images: string[] = [];

	for (const slidePath of slideFiles) {
		const slideText = await zip.file(slidePath)!.async('text');
		const slideDoc = new DOMParser().parseFromString(slideText, 'application/xml');

		const rels = await readRels(zip, slidePath);
		const layoutPath = getRelationshipTarget(rels, '/slideLayout');
		const layoutDoc = layoutPath ? await readXml(zip, layoutPath) : null;
		const layoutRels = layoutPath ? await readRels(zip, layoutPath) : {};
		const masterPath = getRelationshipTarget(layoutRels, '/slideMaster');
		const masterDoc = masterPath ? await readXml(zip, masterPath) : null;
		const placeholderSources = [collectPlaceholders(layoutDoc), collectPlaceholders(masterDoc)];

		// ── Create canvas and render slide ───────────────────────────
		const canvas = document.createElement('canvas');
		canvas.width = slideW;
		canvas.height = slideH;
		const ctx = canvas.getContext('2d')!;

		ctx.fillStyle = '#ffffff';
		ctx.fillRect(0, 0, slideW, slideH);
		if (masterDoc) renderBackground(ctx, masterDoc, slideW, slideH);
		if (layoutDoc) renderBackground(ctx, layoutDoc, slideW, slideH);
		renderBackground(ctx, slideDoc, slideW, slideH);

		const spTree = slideDoc.getElementsByTagName('p:spTree')[0];
		if (!spTree) {
			images.push(canvas.toDataURL('image/png'));
			continue;
		}

		const shapes = Array.from(spTree.children).filter((el) =>
			['sp', 'pic'].includes(getTag(el) ?? '')
		);

		for (const shape of shapes) {
			const ph = getPlaceholder(shape);
			const placeholder = findPlaceholder(ph, placeholderSources);
			const rect =
				parseXfrm(shape) ?? placeholder?.rect ?? fallbackPlaceholderRect(ph, slideW, slideH);
			if (!rect) continue;

			const { x, y, w, h } = rect;
			if (w === 0 && h === 0) continue;

			if (getTag(shape) === 'sp') {
				const shapeFill = solidFillColor(shape.getElementsByTagName('p:spPr')[0]);
				if (shapeFill) {
					ctx.fillStyle = shapeFill;
					ctx.fillRect(x, y, w, h);
				}
			}

			// ── Picture ──────────────────────────────────────────────
			const blipFill = shape.getElementsByTagName('p:blipFill')[0];
			if (blipFill) {
				const blip = blipFill.getElementsByTagName('a:blip')[0];
				if (blip) {
					const rEmbed = blip.getAttribute('r:embed') ?? '';
					const mediaPath = rels[rEmbed]?.target;
					const dataUri = mediaPath ? media[mediaPath] : '';
					if (dataUri && !dataUri.includes('image/x-emf')) {
						try {
							const img = await loadImage(dataUri);
							ctx.drawImage(img, x, y, w, h);
						} catch {
							// Skip images that fail to load
						}
					}
				}
				continue;
			}

			// ── Text shape ───────────────────────────────────────────
			const txBody = shape.getElementsByTagName('p:txBody')[0];
			if (!txBody) continue;

			ctx.save();
			ctx.rect(x, y, w, h);
			ctx.clip();

			const paragraphs = txBody.getElementsByTagName('a:p');
			const insets = textBodyInsets(txBody);
			const textX = x + insets.left;
			const textY = y + insets.top;
			const textW = Math.max(1, w - insets.left - insets.right);
			const textBottom = y + h - insets.bottom;
			let cursorY = textY;
			const defaultFontSize = placeholderFontSize(ph ?? placeholder ?? null);

			for (let pi = 0; pi < paragraphs.length; pi++) {
				const para = paragraphs[pi];
				const align = paragraphAlign(para, ph ?? placeholder ?? null);
				const paragraphStyle = readParagraphStyle(para, defaultFontSize);
				const textParts: Array<{ text: string; style: TextStyle } | { newline: true }> = [];
				const bullet = paragraphBullet(para);

				for (const child of Array.from(para.children)) {
					const tag = getTag(child);
					if (tag === 'br') {
						textParts.push({ newline: true });
						continue;
					}
					if (tag !== 'r' && tag !== 'fld') continue;

					const style = tag === 'r' ? readRunStyle(child, paragraphStyle) : paragraphStyle;
					const text = child.getElementsByTagName('a:t')[0]?.textContent ?? '';
					if (text) textParts.push({ text, style });
				}

				if (bullet && textParts.some((part) => 'text' in part && part.text.trim())) {
					textParts.unshift({ text: bullet, style: paragraphStyle });
				}

				const maxFontPt = textParts.reduce(
					(max, part) => ('text' in part ? Math.max(max, part.style.fontPt) : max),
					paragraphStyle.fontPt
				);
				const lineHeight = maxFontPt * 1.4;
				cursorY += maxFontPt; // baseline offset

				let line: TextToken[] = [];
				let lineWidth = 0;
				const flushLine = () => {
					if (line.length === 0) return;
					if (cursorY <= textBottom) {
						drawTextLine(ctx, line, align, textX, cursorY, textW);
					}
					line = [];
					lineWidth = 0;
					cursorY += lineHeight;
				};

				if (textParts.length === 0) {
					cursorY += lineHeight;
					continue;
				}

				for (const part of textParts) {
					if ('newline' in part) {
						if (line.length > 0) flushLine();
						else cursorY += lineHeight;
						continue;
					}
					const { text, style } = part;
					ctx.font = fontString(style);
					ctx.textBaseline = 'alphabetic';

					// Simple word-wrap within the shape bounds
					const words = text.split(/(\n|[^\S\n]+)/);
					for (const word of words) {
						if (word === '') continue;
						if (word === '\n') {
							flushLine();
							continue;
						}
						if (cursorY > textBottom) break;

						const width = ctx.measureText(word).width;
						if (lineWidth + width > textW && line.length > 0) {
							flushLine();
							if (word.trim() === '') continue;
						}
						if (line.length === 0 && word.trim() === '') continue;

						line.push({ ...style, text: word, width });
						lineWidth += width;
					}
				}

				flushLine();
				cursorY -= lineHeight * 0.6; // paragraph spacing
			}

			ctx.restore();
		}

		images.push(canvas.toDataURL('image/png'));
	}

	return { images, width: slideW, height: slideH };
}
