/**
 * Lightweight PPTX → Image renderer.
 *
 * Extracts text and images from each slide and renders them
 * directly to canvas, returning PNG data URLs.
 *
 * Uses jszip (dynamically imported) and the browser Canvas 2D API.
 * No full theme resolution, SmartArt, or animations — preview only.
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

type TextInsets = {
	left: number;
	right: number;
	top: number;
	bottom: number;
};

type ChartSeries = {
	name: string;
	categories: string[];
	values: number[];
	color: string;
};

type ThemeColors = Record<string, string>;

let activeThemeColors: ThemeColors = {};

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

const readThemeColors = async (zip: ZipLike): Promise<ThemeColors> => {
	const themePath =
		Object.keys(zip.files)
			.filter((path) => /^ppt\/theme\/theme\d+\.xml$/.test(path))
			.sort()[0] ?? '';
	const themeDoc = themePath ? await readXml(zip, themePath) : null;
	const clrScheme = themeDoc?.getElementsByTagName('a:clrScheme')[0];
	const colors: ThemeColors = {};
	if (!clrScheme) return colors;

	for (const child of Array.from(clrScheme.children)) {
		const key = getTag(child);
		if (!key) continue;

		const srgb = child.getElementsByTagName('a:srgbClr')[0]?.getAttribute('val');
		if (srgb) {
			colors[key] = `#${srgb}`;
			continue;
		}

		const sys = child.getElementsByTagName('a:sysClr')[0];
		const lastClr = sys?.getAttribute('lastClr');
		if (lastClr) colors[key] = `#${lastClr}`;
	}

	return colors;
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
	const themeKey =
		val === 'bg1'
			? 'lt1'
			: val === 'tx1'
				? 'dk1'
				: val === 'bg2'
					? 'lt2'
					: val === 'tx2'
						? 'dk2'
						: val;
	if (themeKey && activeThemeColors[themeKey]) return activeThemeColors[themeKey];

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

const clampByte = (value: number) => Math.max(0, Math.min(255, Math.round(value)));

const hexToRgb = (color: string) => {
	const hex = color.replace('#', '');
	if (!/^[\da-f]{6}$/i.test(hex)) return null;
	return {
		r: parseInt(hex.slice(0, 2), 16),
		g: parseInt(hex.slice(2, 4), 16),
		b: parseInt(hex.slice(4, 6), 16)
	};
};

const rgbToHex = ({ r, g, b }: { r: number; g: number; b: number }) =>
	`#${[r, g, b].map((value) => clampByte(value).toString(16).padStart(2, '0')).join('')}`;

const colorWithTransforms = (color: string | null, colorEl: Element | undefined) => {
	if (!color || !colorEl) return color;
	const rgb = hexToRgb(color);
	if (!rgb) return color;

	const lumMod = colorEl.getElementsByTagName('a:lumMod')[0]?.getAttribute('val');
	const lumOff = colorEl.getElementsByTagName('a:lumOff')[0]?.getAttribute('val');
	const alpha = colorEl.getElementsByTagName('a:alpha')[0]?.getAttribute('val');
	const mod = lumMod ? parseInt(lumMod, 10) / 100000 : 1;
	const off = lumOff ? (parseInt(lumOff, 10) / 100000) * 255 : 0;
	const transformed = {
		r: rgb.r * mod + off,
		g: rgb.g * mod + off,
		b: rgb.b * mod + off
	};

	if (alpha) {
		const opacity = Math.max(0, Math.min(1, parseInt(alpha, 10) / 100000));
		return `rgba(${clampByte(transformed.r)}, ${clampByte(transformed.g)}, ${clampByte(
			transformed.b
		)}, ${opacity})`;
	}

	return rgbToHex(transformed);
};

const prstColor = (val: string | null) => {
	switch (val) {
		case 'black':
			return '#000000';
		case 'white':
			return '#ffffff';
		case 'gray':
		case 'grey':
			return '#808080';
		default:
			return null;
	}
};

const colorFromElement = (el: Element | undefined): string | null => {
	const srgb = el?.getElementsByTagName('a:srgbClr')[0];
	const srgbVal = srgb?.getAttribute('val');
	if (srgbVal) return colorWithTransforms(`#${srgbVal}`, srgb);

	const prst = el?.getElementsByTagName('a:prstClr')[0];
	const prstVal = prst?.getAttribute('val');
	if (prstVal) return colorWithTransforms(prstColor(prstVal), prst);

	const scheme = el?.getElementsByTagName('a:schemeClr')[0];
	return colorWithTransforms(schemeColor(scheme?.getAttribute('val') ?? null), scheme);
};

const solidFillColor = (el: Element | Document | null): string | null => {
	if (!el) return null;
	const fill = el.getElementsByTagName('a:solidFill')[0];
	if (!fill) return null;

	return colorFromElement(fill);
};

const renderFill = (ctx: CanvasRenderingContext2D, el: Element | Document | null, rect: Rect) => {
	if (!el) return false;

	const gradFill = el.getElementsByTagName('a:gradFill')[0];
	if (gradFill) {
		const stops = Array.from(gradFill.getElementsByTagName('a:gs'))
			.map((stop) => ({
				pos: parseInt(stop.getAttribute('pos') ?? '0', 10) / 100000,
				color: colorFromElement(stop)
			}))
			.filter((stop): stop is { pos: number; color: string } => Boolean(stop.color));

		if (stops.length > 0) {
			const lin = gradFill.getElementsByTagName('a:lin')[0];
			const angle =
				(((parseInt(lin?.getAttribute('ang') ?? '0', 10) / 60000) % 360) * Math.PI) / 180;
			const dx = Math.cos(angle) * rect.w;
			const dy = Math.sin(angle) * rect.h;
			const gradient = ctx.createLinearGradient(
				rect.x + rect.w / 2 - dx / 2,
				rect.y + rect.h / 2 - dy / 2,
				rect.x + rect.w / 2 + dx / 2,
				rect.y + rect.h / 2 + dy / 2
			);
			for (const stop of stops)
				gradient.addColorStop(Math.max(0, Math.min(1, stop.pos)), stop.color);
			ctx.fillStyle = gradient;
			ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
			return true;
		}
	}

	const fill = solidFillColor(el);
	if (!fill) return false;
	ctx.fillStyle = fill;
	ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
	return true;
};

const renderBackground = (
	ctx: CanvasRenderingContext2D,
	doc: Document,
	slideW: number,
	slideH: number
) => {
	renderFill(ctx, doc.getElementsByTagName('p:bg')[0], { x: 0, y: 0, w: slideW, h: slideH });
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

const textBodyInsets = (
	txBody: Element,
	fallback: TextInsets = { left: 10, right: 10, top: 5, bottom: 5 }
) => {
	const bodyPr = txBody.getElementsByTagName('a:bodyPr')[0];
	return {
		left: bodyPr?.hasAttribute('lIns')
			? emuToPx(parseEmu(bodyPr.getAttribute('lIns')))
			: fallback.left,
		right: bodyPr?.hasAttribute('rIns')
			? emuToPx(parseEmu(bodyPr.getAttribute('rIns')))
			: fallback.right,
		top: bodyPr?.hasAttribute('tIns')
			? emuToPx(parseEmu(bodyPr.getAttribute('tIns')))
			: fallback.top,
		bottom: bodyPr?.hasAttribute('bIns')
			? emuToPx(parseEmu(bodyPr.getAttribute('bIns')))
			: fallback.bottom
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

const paragraphTextParts = (para: Element, defaultFontSize: number) => {
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

	return { paragraphStyle, textParts };
};

const estimateTextHeight = (
	ctx: CanvasRenderingContext2D,
	paragraphs: HTMLCollectionOf<Element>,
	defaultFontSize: number,
	textW: number
) => {
	let height = 0;
	for (let pi = 0; pi < paragraphs.length; pi++) {
		const { paragraphStyle, textParts } = paragraphTextParts(paragraphs[pi], defaultFontSize);
		const maxFontPt = textParts.reduce(
			(max, part) => ('text' in part ? Math.max(max, part.style.fontPt) : max),
			paragraphStyle.fontPt
		);
		const lineHeight = maxFontPt * 1.4;
		let lines = 1;
		let lineWidth = 0;

		for (const part of textParts) {
			if ('newline' in part) {
				lines++;
				lineWidth = 0;
				continue;
			}
			ctx.font = fontString(part.style);
			for (const word of part.text.split(/(\n|[^\S\n]+)/)) {
				if (word === '') continue;
				if (word === '\n') {
					lines++;
					lineWidth = 0;
					continue;
				}
				const width = ctx.measureText(word).width;
				if (lineWidth + width > textW && lineWidth > 0) {
					lines++;
					lineWidth = word.trim() ? width : 0;
				} else if (lineWidth > 0 || word.trim()) {
					lineWidth += width;
				}
			}
		}

		height += lines * lineHeight;
		if (pi < paragraphs.length - 1) height += lineHeight * 0.4;
	}
	return height;
};

const renderTextBody = (
	ctx: CanvasRenderingContext2D,
	txBody: Element,
	rect: Rect,
	defaultFontSize: number,
	ph: { type: string; idx: string } | Placeholder | null = null,
	fallbackInsets?: TextInsets
) => {
	const { x, y, w, h } = rect;
	ctx.save();
	ctx.rect(x, y, w, h);
	ctx.clip();

	const paragraphs = txBody.getElementsByTagName('a:p');
	const bodyPr = txBody.getElementsByTagName('a:bodyPr')[0];
	const insets = textBodyInsets(txBody, fallbackInsets);
	const textX = x + insets.left;
	const textW = Math.max(1, w - insets.left - insets.right);
	const textBottom = y + h - insets.bottom;
	const textH = Math.max(1, textBottom - (y + insets.top));
	const estimatedHeight = estimateTextHeight(ctx, paragraphs, defaultFontSize, textW);
	const anchor = bodyPr?.getAttribute('anchor');
	const anchorOffset =
		anchor === 'b'
			? Math.max(0, textH - estimatedHeight)
			: anchor === 'ctr'
				? Math.max(0, (textH - estimatedHeight) / 2)
				: 0;
	const textY = y + insets.top + anchorOffset;
	let cursorY = textY;

	for (let pi = 0; pi < paragraphs.length; pi++) {
		const para = paragraphs[pi];
		const align = paragraphAlign(para, ph);
		const { paragraphStyle, textParts } = paragraphTextParts(para, defaultFontSize);

		const maxFontPt = textParts.reduce(
			(max, part) => ('text' in part ? Math.max(max, part.style.fontPt) : max),
			paragraphStyle.fontPt
		);
		const lineHeight = maxFontPt * 1.4;
		cursorY += maxFontPt;

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
		cursorY -= lineHeight * 0.6;
	}

	ctx.restore();
};

const renderTable = (ctx: CanvasRenderingContext2D, frame: Element, rect: Rect) => {
	const table = frame.getElementsByTagName('a:tbl')[0];
	if (!table) return false;

	const grid = table.getElementsByTagName('a:tblGrid')[0];
	const colEmus = Array.from(grid?.getElementsByTagName('a:gridCol') ?? []).map((col) =>
		Math.max(1, parseEmu(col.getAttribute('w')))
	);
	const rows = Array.from(table.getElementsByTagName('a:tr'));
	if (colEmus.length === 0 || rows.length === 0) return true;

	const rowEmus = rows.map((row) => Math.max(1, parseEmu(row.getAttribute('h'))));
	const colTotal = colEmus.reduce((sum, val) => sum + val, 0);
	const rowTotal = rowEmus.reduce((sum, val) => sum + val, 0);
	const colWidths = colEmus.map((val) => (val / colTotal) * rect.w);
	const rowHeights = rowEmus.map((val) => (val / rowTotal) * rect.h);

	let cy = rect.y;
	for (let ri = 0; ri < rows.length; ri++) {
		const row = rows[ri];
		const cells = Array.from(row.children).filter((child) => getTag(child) === 'tc');
		let cx = rect.x;
		for (let ci = 0; ci < colWidths.length; ci++) {
			const cw = colWidths[ci];
			const ch = rowHeights[ri];
			const cell = cells[ci];
			if (cell) {
				const tcPr = cell.getElementsByTagName('a:tcPr')[0];
				const fill = solidFillColor(tcPr);
				if (fill) {
					ctx.fillStyle = fill;
					ctx.fillRect(cx, cy, cw, ch);
				}

				ctx.strokeStyle = 'rgba(17, 24, 39, 0.12)';
				ctx.lineWidth = 1;
				ctx.beginPath();
				ctx.moveTo(cx, cy + ch);
				ctx.lineTo(cx + cw, cy + ch);
				ctx.stroke();

				const txBody = cell.getElementsByTagName('a:txBody')[0];
				if (txBody) {
					const marL = tcPr?.hasAttribute('marL')
						? emuToPx(parseEmu(tcPr.getAttribute('marL')))
						: 4;
					const marR = tcPr?.hasAttribute('marR')
						? emuToPx(parseEmu(tcPr.getAttribute('marR')))
						: 4;
					const marT = tcPr?.hasAttribute('marT')
						? emuToPx(parseEmu(tcPr.getAttribute('marT')))
						: 2;
					const marB = tcPr?.hasAttribute('marB')
						? emuToPx(parseEmu(tcPr.getAttribute('marB')))
						: 2;
					renderTextBody(ctx, txBody, { x: cx, y: cy, w: cw, h: ch }, 10, null, {
						left: marL,
						right: marR,
						top: marT,
						bottom: marB
					});
				}
			}
			cx += cw;
		}
		cy += rowHeights[ri];
	}

	return true;
};

const chartPointValues = (parent: Element, tag: string) => {
	const container = parent.getElementsByTagName(tag)[0];
	const pts = Array.from(container?.getElementsByTagName('c:pt') ?? []);
	return pts
		.sort((a, b) => parseInt(a.getAttribute('idx') ?? '0') - parseInt(b.getAttribute('idx') ?? '0'))
		.map((pt) => pt.getElementsByTagName('c:v')[0]?.textContent ?? '');
};

const chartSeries = (chartDoc: Document, chartType: 'bar' | 'line'): ChartSeries[] => {
	const chartEl = chartDoc.getElementsByTagName(
		chartType === 'bar' ? 'c:barChart' : 'c:lineChart'
	)[0];
	if (!chartEl) return [];
	const colors = ['#4472c4', '#70ad47', '#5b9bd5', '#ed7d31', '#a5a5a5', '#ffc000'];

	return Array.from(chartEl.getElementsByTagName('c:ser')).map((ser, index) => {
		const name = chartPointValues(ser, 'c:tx')[0] || `Series ${index + 1}`;
		const categories = chartPointValues(ser, 'c:cat');
		const values = chartPointValues(ser, 'c:val').map((value) => Number(value) || 0);
		return {
			name,
			categories,
			values,
			color: solidFillColor(ser.getElementsByTagName('c:spPr')[0]) ?? colors[index % colors.length]
		};
	});
};

const renderChart = (ctx: CanvasRenderingContext2D, chartDoc: Document, rect: Rect) => {
	const type = chartDoc.getElementsByTagName('c:barChart')[0]
		? 'bar'
		: chartDoc.getElementsByTagName('c:lineChart')[0]
			? 'line'
			: null;
	if (!type) return false;

	const series = chartSeries(chartDoc, type);
	const categories = series[0]?.categories ?? [];
	if (series.length === 0 || categories.length === 0) return true;

	const values = series.flatMap((item) => item.values);
	const maxValue = Math.max(1, ...values) * 1.15;
	const left = rect.x + 42;
	const top = rect.y + 28;
	const right = rect.x + rect.w - 14;
	const bottom = rect.y + rect.h - 34;
	const plotW = Math.max(1, right - left);
	const plotH = Math.max(1, bottom - top);

	ctx.save();
	ctx.fillStyle = '#ffffff';
	ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
	ctx.strokeStyle = 'rgba(17, 24, 39, 0.16)';
	ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);

	ctx.font = '9px Arial, sans-serif';
	ctx.fillStyle = '#6b7280';
	ctx.textAlign = 'right';
	ctx.textBaseline = 'middle';
	for (let i = 0; i <= 4; i++) {
		const value = (maxValue / 4) * i;
		const y = bottom - (value / maxValue) * plotH;
		ctx.strokeStyle = i === 0 ? '#9ca3af' : 'rgba(17, 24, 39, 0.08)';
		ctx.beginPath();
		ctx.moveTo(left, y);
		ctx.lineTo(right, y);
		ctx.stroke();
		ctx.fillText(Math.round(value).toString(), left - 6, y);
	}

	ctx.textAlign = 'center';
	ctx.textBaseline = 'top';
	categories.forEach((category, index) => {
		const x = left + ((index + 0.5) / categories.length) * plotW;
		ctx.fillStyle = '#6b7280';
		ctx.fillText(category, x, bottom + 7);
	});

	if (type === 'bar') {
		const groupW = plotW / categories.length;
		const barW = (groupW * 0.7) / Math.max(1, series.length);
		series.forEach((item, si) => {
			ctx.fillStyle = item.color;
			item.values.forEach((value, vi) => {
				const x = left + vi * groupW + groupW * 0.15 + si * barW;
				const h = (value / maxValue) * plotH;
				const y = bottom - h;
				ctx.fillRect(x, y, Math.max(1, barW - 2), h);
				ctx.fillStyle = '#111827';
				ctx.fillText(String(value), x + barW / 2, y - 12);
				ctx.fillStyle = item.color;
			});
		});
	} else {
		series.forEach((item) => {
			ctx.strokeStyle = item.color;
			ctx.fillStyle = item.color;
			ctx.lineWidth = 2;
			ctx.beginPath();
			item.values.forEach((value, vi) => {
				const x = left + ((vi + 0.5) / categories.length) * plotW;
				const y = bottom - (value / maxValue) * plotH;
				if (vi === 0) ctx.moveTo(x, y);
				else ctx.lineTo(x, y);
			});
			ctx.stroke();
			item.values.forEach((value, vi) => {
				const x = left + ((vi + 0.5) / categories.length) * plotW;
				const y = bottom - (value / maxValue) * plotH;
				ctx.beginPath();
				ctx.arc(x, y, 2.5, 0, Math.PI * 2);
				ctx.fill();
				ctx.fillStyle = '#111827';
				ctx.fillText(String(value), x, y - 14);
				ctx.fillStyle = item.color;
			});
		});
	}

	ctx.textAlign = 'left';
	ctx.textBaseline = 'middle';
	let legendX = rect.x + rect.w * 0.48;
	const legendY = rect.y + 13;
	series.forEach((item) => {
		ctx.fillStyle = item.color;
		ctx.fillRect(legendX, legendY - 3, 6, 6);
		ctx.fillStyle = '#6b7280';
		ctx.fillText(item.name, legendX + 9, legendY);
		legendX += ctx.measureText(item.name).width + 24;
	});
	ctx.restore();

	return true;
};

const renderConnector = (ctx: CanvasRenderingContext2D, shape: Element, rect: Rect) => {
	const spPr = shape.getElementsByTagName('p:spPr')[0];
	const line = spPr?.getElementsByTagName('a:ln')[0];
	ctx.save();
	ctx.strokeStyle = solidFillColor(line) ?? '#9ca3af';
	ctx.lineWidth = Math.max(1, emuToPx(parseEmu(line?.getAttribute('w') ?? '9525')));
	ctx.beginPath();
	ctx.moveTo(rect.x, rect.y);
	ctx.lineTo(rect.x + rect.w, rect.y + rect.h);
	ctx.stroke();
	ctx.restore();
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
	activeThemeColors = await readThemeColors(zip);

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
			['sp', 'pic', 'graphicFrame', 'cxnSp'].includes(getTag(el) ?? '')
		);

		for (const shape of shapes) {
			const ph = getPlaceholder(shape);
			const placeholder = findPlaceholder(ph, placeholderSources);
			const rect =
				parseXfrm(shape) ?? placeholder?.rect ?? fallbackPlaceholderRect(ph, slideW, slideH);
			if (!rect) continue;

			const { x, y, w, h } = rect;
			if (w === 0 && h === 0) continue;
			const tag = getTag(shape);

			if (tag === 'cxnSp') {
				renderConnector(ctx, shape, rect);
				continue;
			}

			if (tag === 'graphicFrame') {
				if (renderTable(ctx, shape, rect)) continue;

				const chartRelId = shape.getElementsByTagName('c:chart')[0]?.getAttribute('r:id') ?? '';
				const chartPath = rels[chartRelId]?.target;
				const chartDoc = chartPath ? await readXml(zip, chartPath) : null;
				if (chartDoc && renderChart(ctx, chartDoc, rect)) continue;
			}

			if (tag === 'sp') {
				renderFill(ctx, shape.getElementsByTagName('p:spPr')[0], rect);
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

			const defaultFontSize = placeholderFontSize(ph ?? placeholder ?? null);
			renderTextBody(ctx, txBody, rect, defaultFontSize, ph ?? placeholder ?? null);
		}

		images.push(canvas.toDataURL('image/png'));
	}

	return { images, width: slideW, height: slideH };
}
