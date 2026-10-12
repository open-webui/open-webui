const DOCX_STYLE_MAP = [
	"p[style-name='Title'] => h1.docx-title:fresh",
	"p[style-name='Subtitle'] => p.docx-subtitle:fresh",
	"p[style-name='Caption'] => p.docx-caption:fresh",
	"p[style-name='Quote'] => blockquote:fresh",
	"p[style-name='Intense Quote'] => blockquote:fresh",
	'r[style-name="Strong"] => strong',
	'r[style-name="Emphasis"] => em',
	'u => u',
	'strike => s'
];

export async function docxToHtml(arrayBuffer: ArrayBuffer): Promise<string> {
	const mammoth = await import('mammoth');
	const convertImage = mammoth.images.imgElement(async (image) => ({
		src: `data:${image.contentType};base64,${await image.readAsBase64String()}`
	}));

	const result = await mammoth.convertToHtml(
		{ arrayBuffer },
		{
			convertImage,
			ignoreEmptyParagraphs: false,
			includeDefaultStyleMap: true,
			styleMap: DOCX_STYLE_MAP
		}
	);

	return result.value;
}
