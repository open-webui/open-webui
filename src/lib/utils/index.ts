import { v4 as uuidv4 } from 'uuid';
import sha256 from 'js-sha256';
import { WEBUI_BASE_URL } from '$lib/constants';

import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import isToday from 'dayjs/plugin/isToday';
import isYesterday from 'dayjs/plugin/isYesterday';
import localizedFormat from 'dayjs/plugin/localizedFormat';

dayjs.extend(relativeTime);
dayjs.extend(isToday);
dayjs.extend(isYesterday);
dayjs.extend(localizedFormat);

import { TTS_RESPONSE_SPLIT } from '$lib/types';

import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';

import { marked } from 'marked';
import markedExtension from '$lib/utils/marked/extension';
import markedKatexExtension from '$lib/utils/marked/katex-extension';
import hljs from 'highlight.js';

//////////////////////////
// Helper functions
//////////////////////////

export const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const formatNumber = (num: number): string => {
	return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(
		num
	);
};

function escapeRegExp(string: string): string {
	return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Replace tokens outside code blocks only
export const replaceOutsideCode = (content: string, replacer: (str: string) => string) => {
	return content
		.split(/(```[\s\S]*?```|`[\s\S]*?`)/)
		.map((segment) => {
			return segment.startsWith('```') || segment.startsWith('`') ? segment : replacer(segment);
		})
		.join('');
};

export const replaceTokens = (content, char, user) => {
	const tokens = [
		{ regex: /{{char}}/gi, replacement: char },
		{ regex: /{{user}}/gi, replacement: user },
		{
			regex: /{{VIDEO_FILE_ID_([a-f0-9-]+)}}/gi,
			replacement: (_, fileId) =>
				`<video src="${WEBUI_BASE_URL}/api/v1/files/${fileId}/content" controls></video>`
		},
		{
			regex: /{{HTML_FILE_ID_([a-f0-9-]+)}}/gi,
			replacement: (_, fileId) => `<file type="html" id="${fileId}" />`
		}
	];

	// Apply replacements
	content = replaceOutsideCode(content, (segment) => {
		tokens.forEach(({ regex, replacement }) => {
			if (replacement !== undefined && replacement !== null) {
				segment = segment.replace(regex, replacement);
			}
		});

		return segment;
	});

	return content;
};

export const sanitizeResponseContent = (content: string) => {
	return content
		.replace(/<\|[a-z]*$/, '')
		.replace(/<\|[a-z]+\|$/, '')
		.replace(/<$/, '')
		.replaceAll('<', '&lt;')
		.replaceAll('>', '&gt;')
		.replaceAll(/<\|[a-z]+\|>/g, ' ')
		.trim();
};

export const processResponseContent = (content: string) => {
	content = processChineseContent(content);
	return content.trim();
};

function isChineseChar(char: string): boolean {
	return /\p{Script=Han}/u.test(char);
}

// Tackle "Model output issue not following the standard Markdown/LaTeX format" in Chinese.
function processChineseContent(content: string): string {
	// This function is used to process the response content before the response content is rendered.
	const lines = content.split('\n');
	const processedLines = lines.map((line) => {
		if (/[\u4e00-\u9fa5]/.test(line)) {
			// Problems caused by Chinese parentheses
			/* Discription:
			 *   When `*` has Chinese delimiters on the inside, markdown parser ignore bold or italic style.
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
				// Handle **bold** and *italic*
				// 1. With Chinese parentheses
				if (/（|）/.test(line)) {
					line = processChineseDelimiters(line, '**', '（', '）');
					line = processChineseDelimiters(line, '*', '（', '）');
				}
				// 2. With Chinese quotations
				if (/“|”/.test(line)) {
					line = processChineseDelimiters(line, '**', '“', '”');
					line = processChineseDelimiters(line, '*', '“', '”');
				}
			}
		}
		return line;
	});
	content = processedLines.join('\n');

	return content;
}

// Helper function for `processChineseContent`
function processChineseDelimiters(
	line: string,
	symbol: string,
	leftSymbol: string,
	rightSymbol: string
): string {
	// NOTE: If needed, with a little modification, this function can be applied to more cases.
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

export function unescapeHtml(html: string) {
	const doc = new DOMParser().parseFromString(html, 'text/html');
	return doc.documentElement.textContent;
}

export const capitalizeFirstLetter = (string) => {
	return string.charAt(0).toUpperCase() + string.slice(1);
};

export const splitStream = (splitOn) => {
	let buffer = '';
	return new TransformStream({
		transform(chunk, controller) {
			buffer += chunk;
			const parts = buffer.split(splitOn);
			parts.slice(0, -1).forEach((part) => controller.enqueue(part));
			buffer = parts[parts.length - 1];
		},
		flush(controller) {
			if (buffer) controller.enqueue(buffer);
		}
	});
};

export const convertMessagesToHistory = (messages) => {
	const history = {
		messages: {},
		currentId: null
	};

	let parentMessageId = null;
	let messageId = null;

	for (const message of messages) {
		messageId = uuidv4();

		if (parentMessageId !== null) {
			history.messages[parentMessageId].childrenIds = [
				...history.messages[parentMessageId].childrenIds,
				messageId
			];
		}

		history.messages[messageId] = {
			...message,
			id: messageId,
			parentId: parentMessageId,
			childrenIds: []
		};

		parentMessageId = messageId;
	}

	history.currentId = messageId;
	return history;
};

export const getGravatarURL = (email) => {
	// Trim leading and trailing whitespace from
	// an email address and force all characters
	// to lower case
	const address = String(email).trim().toLowerCase();

	// Create a SHA256 hash of the final string
	const hash = sha256(address);

	// Grab the actual image URL
	return `https://www.gravatar.com/avatar/${hash}`;
};

export const canvasPixelTest = () => {
	// Test a 1x1 pixel to potentially identify browser/plugin fingerprint blocking or spoofing
	// Inspiration: https://github.com/kkapsner/CanvasBlocker/blob/master/test/detectionTest.js
	const canvas = document.createElement('canvas');
	const ctx = canvas.getContext('2d');
	canvas.height = 1;
	canvas.width = 1;
	const imageData = new ImageData(canvas.width, canvas.height);
	const pixelValues = imageData.data;

	// Generate RGB test data
	for (let i = 0; i < imageData.data.length; i += 1) {
		if (i % 4 !== 3) {
			pixelValues[i] = Math.floor(256 * Math.random());
		} else {
			pixelValues[i] = 255;
		}
	}

	ctx.putImageData(imageData, 0, 0);
	const p = ctx.getImageData(0, 0, canvas.width, canvas.height).data;

	// Read RGB data and fail if unmatched
	for (let i = 0; i < p.length; i += 1) {
		if (p[i] !== pixelValues[i]) {
			console.log(
				'canvasPixelTest: Wrong canvas pixel RGB value detected:',
				p[i],
				'at:',
				i,
				'expected:',
				pixelValues[i]
			);
			console.log('canvasPixelTest: Canvas blocking or spoofing is likely');
			return false;
		}
	}

	return true;
};

export const compressImage = async (imageUrl, maxWidth, maxHeight) => {
	return new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => {
			const canvas = document.createElement('canvas');
			let width = img.width;
			let height = img.height;

			// Maintain aspect ratio while resizing

			if (maxWidth && maxHeight) {
				// Resize with both dimensions defined (preserves aspect ratio)

				if (width <= maxWidth && height <= maxHeight) {
					resolve(imageUrl);
					return;
				}

				if (width / height > maxWidth / maxHeight) {
					height = Math.round((maxWidth * height) / width);
					width = maxWidth;
				} else {
					width = Math.round((maxHeight * width) / height);
					height = maxHeight;
				}
			} else if (maxWidth) {
				// Only maxWidth defined

				if (width <= maxWidth) {
					resolve(imageUrl);
					return;
				}

				height = Math.round((maxWidth * height) / width);
				width = maxWidth;
			} else if (maxHeight) {
				// Only maxHeight defined

				if (height <= maxHeight) {
					resolve(imageUrl);
					return;
				}

				width = Math.round((maxHeight * width) / height);
				height = maxHeight;
			}

			canvas.width = width;
			canvas.height = height;

			const context = canvas.getContext('2d');
			context.drawImage(img, 0, 0, width, height);

			// Get compressed image URL
			const mimeType = imageUrl.match(/^data:([^;]+);/)?.[1];
			const compressedUrl = canvas.toDataURL(mimeType);
			resolve(compressedUrl);
		};
		img.onerror = (error) => reject(error);
		img.src = imageUrl;
	});
};
export const generateInitialsImage = (name) => {
	const canvas = document.createElement('canvas');
	const ctx = canvas.getContext('2d');
	canvas.width = 100;
	canvas.height = 100;

	if (!canvasPixelTest()) {
		console.log(
			'generateInitialsImage: failed pixel test, fingerprint evasion is likely. Using default image.'
		);
		return `${WEBUI_BASE_URL}/user.png`;
	}

	ctx.fillStyle = '#F39C12';
	ctx.fillRect(0, 0, canvas.width, canvas.height);

	ctx.fillStyle = '#FFFFFF';
	ctx.font = '40px Helvetica';
	ctx.textAlign = 'center';
	ctx.textBaseline = 'middle';

	const sanitizedName = name.trim();
	const initials =
		sanitizedName.length > 0
			? sanitizedName[0] +
				(sanitizedName.split(' ').length > 1
					? sanitizedName[sanitizedName.lastIndexOf(' ') + 1]
					: '')
			: '';

	ctx.fillText(initials.toUpperCase(), canvas.width / 2, canvas.height / 2);

	return canvas.toDataURL();
};

export const formatDate = (inputDate) => {
	const date = dayjs(inputDate);

	if (date.isToday()) {
		return `Today at {{LOCALIZED_TIME}}`;
	} else if (date.isYesterday()) {
		return `Yesterday at {{LOCALIZED_TIME}}`;
	} else {
		return `{{LOCALIZED_DATE}} at {{LOCALIZED_TIME}}`;
	}
};

export const copyToClipboard = async (text, html = null, formatted = false) => {
	if (formatted) {
		let styledHtml = '';
		if (!html) {
			const options = {
				throwOnError: false,
				highlight: function (code, lang) {
					const language = hljs.getLanguage(lang) ? lang : 'plaintext';
					return hljs.highlight(code, { language }).value;
				}
			};
			marked.use(markedKatexExtension(options));
			marked.use(markedExtension(options));
			// DEVELOPER NOTE: Go to `$lib/components/chat/Messages/Markdown.svelte` to add extra markdown extensions for rendering.

			const htmlContent = marked.parse(text);

			// Add basic styling to make the content look better when pasted
			styledHtml = `
			<div>
				<style>
					pre {
						background-color: #f6f8fa;
						border-radius: 6px;
						padding: 16px;
						overflow: auto;
					}
					code {
						font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
						font-size: 14px;
					}
					.hljs-keyword { color: #d73a49; }
					.hljs-string { color: #032f62; }
					.hljs-comment { color: #6a737d; }
					.hljs-function { color: #6f42c1; }
					.hljs-number { color: #005cc5; }
					.hljs-operator { color: #d73a49; }
					.hljs-class { color: #6f42c1; }
					.hljs-title { color: #6f42c1; }
					.hljs-params { color: #24292e; }
					.hljs-built_in { color: #005cc5; }
					blockquote {
						border-left: 4px solid #dfe2e5;
						padding-left: 16px;
						color: #6a737d;
						margin-left: 0;
						margin-right: 0;
					}
					table {
						border-collapse: collapse;
						width: 100%;
						margin-bottom: 16px;
					}
					table, th, td {
						border: 1px solid #dfe2e5;
					}
					th, td {
						padding: 8px 12px;
					}
					th {
						background-color: #f6f8fa;
					}
				</style>
				${htmlContent}
			</div>
		`;
		} else {
			// If HTML is provided, use it directly
			styledHtml = html;
		}

		// Create a blob with HTML content
		const blob = new Blob([styledHtml], { type: 'text/html' });

		try {
			// Create a ClipboardItem with HTML content
			const data = new ClipboardItem({
				'text/html': blob,
				'text/plain': new Blob([text], { type: 'text/plain' })
			});

			// Write to clipboard
			await navigator.clipboard.write([data]);
			return true;
		} catch (err) {
			console.error('Error copying formatted content:', err);
			// Fallback to plain text
			return await copyToClipboard(text);
		}
	} else {
		let result = false;
		if (!navigator.clipboard) {
			const textArea = document.createElement('textarea');
			textArea.value = text;

			// Avoid scrolling to bottom
			textArea.style.top = '0';
			textArea.style.left = '0';
			textArea.style.position = 'fixed';

			document.body.appendChild(textArea);
			textArea.focus();
			textArea.select();

			try {
				const successful = document.execCommand('copy');
				const msg = successful ? 'successful' : 'unsuccessful';
				console.log('Fallback: Copying text command was ' + msg);
				result = true;
			} catch (err) {
				console.error('Fallback: Oops, unable to copy', err);
			}

			document.body.removeChild(textArea);
			return result;
		}

		result = await navigator.clipboard
			.writeText(text)
			.then(() => {
				console.log('Async: Copying to clipboard was successful!');
				return true;
			})
			.catch((error) => {
				console.error('Async: Could not copy text: ', error);
				return false;
			});

		return result;
	}
};

export const compareVersion = (latest, current) => {
	return current === '0.0.0'
		? false
		: current.localeCompare(latest, undefined, {
				numeric: true,
				sensitivity: 'case',
				caseFirst: 'upper'
			}) < 0;
};

export const extractCurlyBraceWords = (text) => {
	const regex = /\{\{([^}]+)\}\}/g;
	const matches = [];
	let match;

	while ((match = regex.exec(text)) !== null) {
		matches.push({
			word: match[1].trim(),
			startIndex: match.index,
			endIndex: regex.lastIndex - 1
		});
	}

	return matches;
};

export const removeLastWordFromString = (inputString, wordString) => {
	console.log('inputString', inputString);
	// Split the string by newline characters to handle lines separately
	const lines = inputString.split('\n');

	// Take the last line to operate only on it
	const lastLine = lines.pop();

	// Split the last line into an array of words
	const words = lastLine.split(' ');

	// Conditional to check for the last word removal
	if (words.at(-1) === wordString || (wordString === '' && words.at(-1) === '\\#')) {
		words.pop(); // Remove last word if condition is satisfied
	}

	// Join the remaining words back into a string and handle space correctly
	let updatedLastLine = words.join(' ');

	// Add a trailing space to the updated last line if there are still words
	if (updatedLastLine !== '') {
		updatedLastLine += ' ';
	}

	// Combine the lines together again, placing the updated last line back in
	const resultString = [...lines, updatedLastLine].join('\n');

	// Return the final string
	console.log('resultString', resultString);

	return resultString;
};

export const removeFirstHashWord = (inputString) => {
	// Split the string into an array of words
	const words = inputString.split(' ');

	// Find the index of the first word that starts with #
	const index = words.findIndex((word) => word.startsWith('#'));

	// Remove the first word with #
	if (index !== -1) {
		words.splice(index, 1);
	}

	// Join the remaining words back into a string
	const resultString = words.join(' ');

	return resultString;
};

export const transformFileName = (fileName) => {
	// Convert to lowercase
	const lowerCaseFileName = fileName.toLowerCase();

	// Remove special characters using regular expression
	const sanitizedFileName = lowerCaseFileName.replace(/[^\w\s]/g, '');

	// Replace spaces with dashes
	const finalFileName = sanitizedFileName.replace(/\s+/g, '-');

	return finalFileName;
};

export const calculateSHA256 = async (file) => {
	// Create a FileReader to read the file asynchronously
	const reader = new FileReader();

	// Define a promise to handle the file reading
	const readFile = new Promise((resolve, reject) => {
		reader.onload = () => resolve(reader.result);
		reader.onerror = reject;
	});

	// Read the file as an ArrayBuffer
	reader.readAsArrayBuffer(file);

	try {
		// Wait for the FileReader to finish reading the file
		const buffer = await readFile;

		// Convert the ArrayBuffer to a Uint8Array
		const uint8Array = new Uint8Array(buffer);

		// Calculate the SHA-256 hash using Web Crypto API
		const hashBuffer = await crypto.subtle.digest('SHA-256', uint8Array);

		// Convert the hash to a hexadecimal string
		const hashArray = Array.from(new Uint8Array(hashBuffer));
		const hashHex = hashArray.map((byte) => byte.toString(16).padStart(2, '0')).join('');

		return `${hashHex}`;
	} catch (error) {
		console.error('Error calculating SHA-256 hash:', error);
		throw error;
	}
};

export const getImportOrigin = (_chats) => {
	// Check what external service chat imports are from
	if ('mapping' in _chats[0]) {
		return 'openai';
	}
	return 'webui';
};

export const getUserPosition = async (raw = false) => {
	// Get the user's location using the Geolocation API
	const position = await new Promise((resolve, reject) => {
		navigator.geolocation.getCurrentPosition(resolve, reject);
	}).catch((error) => {
		console.error('Error getting user location:', error);
		throw error;
	});

	if (!position) {
		return 'Location not available';
	}

	// Extract the latitude and longitude from the position
	const { latitude, longitude } = position.coords;

	if (raw) {
		return { latitude, longitude };
	} else {
		return `${latitude.toFixed(3)}, ${longitude.toFixed(3)} (lat, long)`;
	}
};

const convertOpenAIMessages = (convo) => {
	// Parse OpenAI chat messages and create chat dictionary for creating new chats
	const mapping = convo['mapping'];
	const messages = [];
	let currentId = '';
	let lastId = null;

	for (const message_id in mapping) {
		const message = mapping[message_id];
		currentId = message_id;
		try {
			if (
				messages.length == 0 &&
				(message['message'] == null ||
					(message['message']['content']['parts']?.[0] == '' &&
						message['message']['content']['text'] == null))
			) {
				// Skip chat messages with no content
				continue;
			} else {
				const new_chat = {
					id: message_id,
					parentId: lastId,
					childrenIds: message['children'] || [],
					role: message['message']?.['author']?.['role'] !== 'user' ? 'assistant' : 'user',
					content:
						message['message']?.['content']?.['parts']?.[0] ||
						message['message']?.['content']?.['text'] ||
						'',
					model: 'gpt-3.5-turbo',
					done: true,
					context: null
				};
				messages.push(new_chat);
				lastId = currentId;
			}
		} catch (error) {
			console.log('Error with', message, '\nError:', error);
		}
	}

	const history: Record<PropertyKey, (typeof messages)[number]> = {};
	messages.forEach((obj) => (history[obj.id] = obj));

	const chat = {
		history: {
			currentId: currentId,
			messages: history // Need to convert this to not a list and instead a json object
		},
		models: ['gpt-3.5-turbo'],
		messages: messages,
		options: {},
		timestamp: convo['create_time'],
		title: convo['title'] ?? 'New Chat'
	};
	return chat;
};

const validateChat = (chat) => {
	// Because ChatGPT sometimes has features we can't use like DALL-E or might have corrupted messages, need to validate
	const messages = chat.messages;

	// Check if messages array is empty
	if (messages.length === 0) {
		return false;
	}

	// Last message's children should be an empty array
	const lastMessage = messages[messages.length - 1];
	if (lastMessage.childrenIds.length !== 0) {
		return false;
	}

	// First message's parent should be null
	const firstMessage = messages[0];
	if (firstMessage.parentId !== null) {
		return false;
	}

	// Every message's content should be a string
	for (const message of messages) {
		if (typeof message.content !== 'string') {
			return false;
		}
	}

	return true;
};

export const convertOpenAIChats = (_chats) => {
	// Create a list of dictionaries with each conversation from import
	const chats = [];
	let failed = 0;
	for (const convo of _chats) {
		const chat = convertOpenAIMessages(convo);

		if (validateChat(chat)) {
			chats.push({
				id: convo['id'],
				user_id: '',
				title: convo['title'],
				chat: chat,
				timestamp: convo['create_time']
			});
		} else {
			failed++;
		}
	}
	console.log(failed, 'Conversations could not be imported');
	return chats;
};

export const isValidHttpUrl = (string: string) => {
	let url;

	try {
		url = new URL(string);
	} catch (_) {
		return false;
	}

	return url.protocol === 'http:' || url.protocol === 'https:';
};

export const isYoutubeUrl = (url: string) => {
	return (
		url.startsWith('https://www.youtube.com') ||
		url.startsWith('https://youtu.be') ||
		url.startsWith('https://youtube.com') ||
		url.startsWith('https://m.youtube.com')
	);
};

export const removeEmojis = (str: string) => {
	// Regular expression to match emojis
	const emojiRegex = /[\uD800-\uDBFF][\uDC00-\uDFFF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDE4F]/g;

	// Replace emojis with an empty string
	return str.replace(emojiRegex, '');
};

export const removeFormattings = (str: string) => {
	return (
		str
			// Block elements (remove completely)
			.replace(/(```[\s\S]*?```)/g, '') // Code blocks
			.replace(/^\|.*\|$/gm, '') // Tables
			// Inline elements (preserve content)
			.replace(/(?:\*\*|__)(.*?)(?:\*\*|__)/g, '$1') // Bold
			.replace(/(?:[*_])(.*?)(?:[*_])/g, '$1') // Italic
			.replace(/~~(.*?)~~/g, '$1') // Strikethrough
			.replace(/`([^`]+)`/g, '$1') // Inline code

			// Links and images
			.replace(/!?\[([^\]]*)\](?:\([^)]+\)|\[[^\]]*\])/g, '$1') // Links & images
			.replace(/^\[[^\]]+\]:\s*.*$/gm, '') // Reference definitions

			// Block formatting
			.replace(/^#{1,6}\s+/gm, '') // Headers
			.replace(/^\s*[-*+]\s+/gm, '') // Lists
			.replace(/^\s*(?:\d+\.)\s+/gm, '') // Numbered lists
			.replace(/^\s*>[> ]*/gm, '') // Blockquotes
			.replace(/^\s*:\s+/gm, '') // Definition lists

			// Cleanup
			.replace(/\[\^[^\]]*\]/g, '') // Footnotes
			.replace(/\n{2,}/g, '\n')
	); // Multiple newlines
};

export const cleanText = (content: string) => {
	return removeFormattings(removeEmojis(content.trim()));
};

export const removeDetails = (content, types) => {
	return replaceOutsideCode(content, (segment) => {
		for (const type of types) {
			segment = segment.replace(
				new RegExp(`<details\\s+type="${type}"[^>]*>.*?<\\/details>`, 'gis'),
				''
			);
		}
		return segment;
	});
};

export const removeAllDetails = (content) => {
	return replaceOutsideCode(content, (segment) => {
		return segment.replace(/<details[^>]*>.*?<\/details>/gis, '');
	});
};

export const processDetails = (content) => {
	content = removeDetails(content, ['reasoning', 'code_interpreter']);

	// This regex matches <details> tags with type="tool_calls" and captures their attributes to convert them to a string
	const detailsRegex = /<details\s+type="tool_calls"([^>]*)>([\s\S]*?)<\/details>/gis;
	const matches = content.match(detailsRegex);
	if (matches) {
		for (const match of matches) {
			const attributesRegex = /(\w+)="([^"]*)"/g;
			const attributes = {};
			let attributeMatch;
			while ((attributeMatch = attributesRegex.exec(match)) !== null) {
				attributes[attributeMatch[1]] = attributeMatch[2];
			}

			if (attributes.result) {
				content = content.replace(match, unescapeHtml(attributes.result));
			}
		}
	}

	return content;
};

// This regular expression matches code blocks marked by triple backticks
const codeBlockRegex = /```[\s\S]*?```/g;

export const extractSentences = (text: string) => {
	const codeBlocks: string[] = [];
	let index = 0;

	// Temporarily replace code blocks with placeholders and store the blocks separately
	text = text.replace(codeBlockRegex, (match) => {
		const placeholder = `\u0000${index}\u0000`; // Use a unique placeholder
		codeBlocks[index++] = match;
		return placeholder;
	});

	// Split the modified text into sentences based on common punctuation marks or newlines, avoiding these blocks
	let sentences = text.split(/(?<=[.!?])\s+|\n+/);

	// Restore code blocks and process sentences
	sentences = sentences.map((sentence) => {
		// Check if the sentence includes a placeholder for a code block
		return sentence.replace(/\u0000(\d+)\u0000/g, (_, idx) => codeBlocks[idx]);
	});

	return sentences.map(cleanText).filter(Boolean);
};

export const extractParagraphsForAudio = (text: string) => {
	const codeBlocks: string[] = [];
	let index = 0;

	// Temporarily replace code blocks with placeholders and store the blocks separately
	text = text.replace(codeBlockRegex, (match) => {
		const placeholder = `\u0000${index}\u0000`; // Use a unique placeholder
		codeBlocks[index++] = match;
		return placeholder;
	});

	// Split the modified text into paragraphs based on newlines, avoiding these blocks
	let paragraphs = text.split(/\n+/);

	// Restore code blocks and process paragraphs
	paragraphs = paragraphs.map((paragraph) => {
		// Check if the paragraph includes a placeholder for a code block
		return paragraph.replace(/\u0000(\d+)\u0000/g, (_, idx) => codeBlocks[idx]);
	});

	return paragraphs.map(cleanText).filter(Boolean);
};

export const extractSentencesForAudio = (text: string) => {
	return extractSentences(text).reduce((mergedTexts, currentText) => {
		const lastIndex = mergedTexts.length - 1;
		if (lastIndex >= 0) {
			const previousText = mergedTexts[lastIndex];
			const wordCount = previousText.split(/\s+/).length;
			const charCount = previousText.length;
			if (wordCount < 4 || charCount < 50) {
				mergedTexts[lastIndex] = previousText + ' ' + currentText;
			} else {
				mergedTexts.push(currentText);
			}
		} else {
			mergedTexts.push(currentText);
		}
		return mergedTexts;
	}, [] as string[]);
};

export const getMessageContentParts = (content: string, splitOn: string = 'punctuation') => {
	const messageContentParts: string[] = [];

	switch (splitOn) {
		default:
		case TTS_RESPONSE_SPLIT.PUNCTUATION:
			messageContentParts.push(...extractSentencesForAudio(content));
			break;
		case TTS_RESPONSE_SPLIT.PARAGRAPHS:
			messageContentParts.push(...extractParagraphsForAudio(content));
			break;
		case TTS_RESPONSE_SPLIT.NONE:
			messageContentParts.push(cleanText(content));
			break;
	}

	return messageContentParts;
};

export const blobToFile = (blob, fileName) => {
	// Create a new File object from the Blob
	const file = new File([blob], fileName, { type: blob.type });
	return file;
};

export const getPromptVariables = (user_name, user_location, user_email = '') => {
	return {
		'{{USER_NAME}}': user_name,
		'{{USER_EMAIL}}': user_email || 'Unknown',
		'{{USER_LOCATION}}': user_location || 'Unknown',
		'{{CURRENT_DATETIME}}': getCurrentDateTime(),
		'{{CURRENT_DATE}}': getFormattedDate(),
		'{{CURRENT_TIME}}': getFormattedTime(),
		'{{CURRENT_WEEKDAY}}': getWeekday(),
		'{{CURRENT_TIMEZONE}}': getUserTimezone(),
		'{{USER_LANGUAGE}}': localStorage.getItem('locale') || 'en-US'
	};
};

/**
 * This function is used to replace placeholders in a template string with the provided prompt.
 * The placeholders can be in the following formats:
 * - `{{prompt}}`: This will be replaced with the entire prompt.
 * - `{{prompt:start:<length>}}`: This will be replaced with the first <length> characters of the prompt.
 * - `{{prompt:end:<length>}}`: This will be replaced with the last <length> characters of the prompt.
 * - `{{prompt:middletruncate:<length>}}`: This will be replaced with the prompt truncated to <length> characters, with '...' in the middle.
 *
 * @param {string} template - The template string containing placeholders.
 * @param {string} prompt - The string to replace the placeholders with.
 * @returns {string} The template string with the placeholders replaced by the prompt.
 */
export const titleGenerationTemplate = (template: string, prompt: string): string => {
	template = template.replace(
		/{{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}/g,
		(match, startLength, endLength, middleLength) => {
			if (match === '{{prompt}}') {
				return prompt;
			} else if (match.startsWith('{{prompt:start:')) {
				return prompt.substring(0, startLength);
			} else if (match.startsWith('{{prompt:end:')) {
				return prompt.slice(-endLength);
			} else if (match.startsWith('{{prompt:middletruncate:')) {
				if (prompt.length <= middleLength) {
					return prompt;
				}
				const start = prompt.slice(0, Math.ceil(middleLength / 2));
				const end = prompt.slice(-Math.floor(middleLength / 2));
				return `${start}...${end}`;
			}
			return '';
		}
	);

	return template;
};

export const approximateToHumanReadable = (nanoseconds: number) => {
	const seconds = Math.floor((nanoseconds / 1e9) % 60);
	const minutes = Math.floor((nanoseconds / 6e10) % 60);
	const hours = Math.floor((nanoseconds / 3.6e12) % 24);

	const results: string[] = [];

	if (seconds >= 0) {
		results.push(`${seconds}s`);
	}

	if (minutes > 0) {
		results.push(`${minutes}m`);
	}

	if (hours > 0) {
		results.push(`${hours}h`);
	}

	return results.reverse().join(' ');
};

export const getTimeRange = (timestamp) => {
	const now = new Date();
	const date = new Date(timestamp * 1000); // Convert Unix timestamp to milliseconds

	// Calculate the difference in milliseconds
	const diffTime = now.getTime() - date.getTime();
	const diffDays = diffTime / (1000 * 3600 * 24);

	const nowDate = now.getDate();
	const nowMonth = now.getMonth();
	const nowYear = now.getFullYear();

	const dateDate = date.getDate();
	const dateMonth = date.getMonth();
	const dateYear = date.getFullYear();

	if (nowYear === dateYear && nowMonth === dateMonth && nowDate === dateDate) {
		return 'Today';
	} else if (nowYear === dateYear && nowMonth === dateMonth && nowDate - dateDate === 1) {
		return 'Yesterday';
	} else if (diffDays <= 7) {
		return 'Previous 7 days';
	} else if (diffDays <= 30) {
		return 'Previous 30 days';
	} else if (nowYear === dateYear) {
		return date.toLocaleString('default', { month: 'long' });
	} else {
		return date.getFullYear().toString();
	}
};

/**
 * Extract frontmatter as a dictionary from the specified content string.
 * @param content {string} - The content string with potential frontmatter.
 * @returns {Object} - The extracted frontmatter as a dictionary.
 */
export const extractFrontmatter = (content) => {
	const frontmatter = {};
	let frontmatterStarted = false;
	let frontmatterEnded = false;
	const frontmatterPattern = /^\s*([a-z_]+):\s*(.*)\s*$/i;

	// Split content into lines
	const lines = content.split('\n');

	// Check if the content starts with triple quotes
	if (lines[0].trim() !== '"""') {
		return {};
	}

	frontmatterStarted = true;

	for (let i = 1; i < lines.length; i++) {
		const line = lines[i];

		if (line.includes('"""')) {
			if (frontmatterStarted) {
				frontmatterEnded = true;
				break;
			}
		}

		if (frontmatterStarted && !frontmatterEnded) {
			const match = frontmatterPattern.exec(line);
			if (match) {
				const [, key, value] = match;
				frontmatter[key.trim()] = value.trim();
			}
		}
	}

	return frontmatter;
};

// Function to determine the best matching language
export const bestMatchingLanguage = (supportedLanguages, preferredLanguages, defaultLocale) => {
	const languages = supportedLanguages.map((lang) => lang.code);

	const match = preferredLanguages
		.map((prefLang) => languages.find((lang) => lang.startsWith(prefLang)))
		.find(Boolean);

	return match || defaultLocale;
};

// Get the date in the format YYYY-MM-DD
export const getFormattedDate = () => {
	const date = new Date();
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
};

// Get the time in the format HH:MM:SS
export const getFormattedTime = () => {
	const date = new Date();
	return date.toTimeString().split(' ')[0];
};

// Get the current date and time in the format YYYY-MM-DD HH:MM:SS
export const getCurrentDateTime = () => {
	return `${getFormattedDate()} ${getFormattedTime()}`;
};

// Get the user's timezone
export const getUserTimezone = () => {
	return Intl.DateTimeFormat().resolvedOptions().timeZone;
};

// Get the weekday
export const getWeekday = () => {
	const date = new Date();
	const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
	return weekdays[date.getDay()];
};

export const createMessagesList = (history, messageId) => {
	if (messageId === null) {
		return [];
	}

	const message = history.messages[messageId];
	if (message === undefined) {
		return [];
	}
	if (message?.parentId) {
		return [...createMessagesList(history, message.parentId), message];
	} else {
		return [message];
	}
};

export const formatFileSize = (size) => {
	if (size == null) return 'Unknown size';
	if (typeof size !== 'number' || size < 0) return 'Invalid size';
	if (size === 0) return '0 B';
	const units = ['B', 'KB', 'MB', 'GB', 'TB'];
	let unitIndex = 0;

	while (size >= 1024 && unitIndex < units.length - 1) {
		size /= 1024;
		unitIndex++;
	}
	return `${size.toFixed(1)} ${units[unitIndex]}`;
};

export const getLineCount = (text) => {
	console.log(typeof text);
	return text ? text.split('\n').length : 0;
};

// Helper function to recursively resolve OpenAPI schema into JSON schema format
function resolveSchema(schemaRef, components, resolvedSchemas = new Set()) {
	if (!schemaRef) return {};

	if (schemaRef['$ref']) {
		const refPath = schemaRef['$ref'];
		const schemaName = refPath.split('/').pop();

		if (resolvedSchemas.has(schemaName)) {
			// Avoid infinite recursion on circular references
			return {};
		}
		resolvedSchemas.add(schemaName);
		const referencedSchema = components.schemas[schemaName];
		return resolveSchema(referencedSchema, components, resolvedSchemas);
	}

	if (schemaRef.type) {
		const schemaObj = { type: schemaRef.type };

		if (schemaRef.description) {
			schemaObj.description = schemaRef.description;
		}

		switch (schemaRef.type) {
			case 'object':
				schemaObj.properties = {};
				schemaObj.required = schemaRef.required || [];
				for (const [propName, propSchema] of Object.entries(schemaRef.properties || {})) {
					schemaObj.properties[propName] = resolveSchema(propSchema, components);
				}
				break;

			case 'array':
				schemaObj.items = resolveSchema(schemaRef.items, components);
				break;

			default:
				// for primitive types (string, integer, etc.), just use as is
				break;
		}
		return schemaObj;
	}

	// fallback for schemas without explicit type
	return {};
}

// Main conversion function
export const convertOpenApiToToolPayload = (openApiSpec) => {
	const toolPayload = [];

	// Guard against invalid or non-OpenAPI specs (e.g., MCP-style configs)
	if (!openApiSpec || !openApiSpec.paths) {
		return toolPayload;
	}

	for (const [path, methods] of Object.entries(openApiSpec.paths)) {
		for (const [method, operation] of Object.entries(methods)) {
			if (operation?.operationId) {
				const tool = {
					name: operation.operationId,
					description: operation.description || operation.summary || 'No description available.',
					parameters: {
						type: 'object',
						properties: {},
						required: []
					}
				};

				// Extract path and query parameters
				if (operation.parameters) {
					operation.parameters.forEach((param) => {
						const paramName = param?.name;
						if (!paramName) return;
						const paramSchema = param?.schema ?? {};
						let description = paramSchema.description || param.description || '';
						if (paramSchema.enum && Array.isArray(paramSchema.enum)) {
							description += `. Possible values: ${paramSchema.enum.join(', ')}`;
						}
						tool.parameters.properties[paramName] = {
							type: paramSchema.type,
							description: description
						};

						if (param.required) {
							tool.parameters.required.push(paramName);
						}
					});
				}

				// Extract and recursively resolve requestBody if available
				if (operation.requestBody) {
					const content = operation.requestBody.content;
					if (content && content['application/json']) {
						const requestSchema = content['application/json'].schema;
						const resolvedRequestSchema = resolveSchema(requestSchema, openApiSpec.components);

						if (resolvedRequestSchema.properties) {
							tool.parameters.properties = {
								...tool.parameters.properties,
								...resolvedRequestSchema.properties
							};

							if (resolvedRequestSchema.required) {
								tool.parameters.required = [
									...new Set([...tool.parameters.required, ...resolvedRequestSchema.required])
								];
							}
						} else if (resolvedRequestSchema.type === 'array') {
							tool.parameters = resolvedRequestSchema; // special case when root schema is an array
						}
					}
				}

				toolPayload.push(tool);
			}
		}
	}

	return toolPayload;
};

export const slugify = (str: string): string => {
	return (
		str
			// 1. Normalize: separate accented letters into base + combining marks
			.normalize('NFD')
			// 2. Remove all combining marks (the accents)
			.replace(/[\u0300-\u036f]/g, '')
			// 3. Replace any sequence of whitespace with a single hyphen
			.replace(/\s+/g, '-')
			// 4. Remove all characters except alphanumeric characters, hyphens, and underscores
			.replace(/[^a-zA-Z0-9-_]/g, '')
			// 5. Convert to lowercase
			.toLowerCase()
	);
};

export const extractInputVariables = (text: string): Record<string, any> => {
	const regex = /{{\s*([^|}\s]+)\s*\|\s*([^}]+)\s*}}/g;
	const regularRegex = /{{\s*([^|}\s]+)\s*}}/g;
	const variables: Record<string, any> = {};
	let match;
	// Use exec() loop instead of matchAll() for better compatibility
	while ((match = regex.exec(text)) !== null) {
		const varName = match[1].trim();
		const definition = match[2].trim();
		variables[varName] = parseVariableDefinition(definition);
	}
	// Then, extract regular variables (without pipe) - only if not already processed
	while ((match = regularRegex.exec(text)) !== null) {
		const varName = match[1].trim();
		// Only add if not already processed as custom variable
		if (!variables.hasOwnProperty(varName)) {
			variables[varName] = { type: 'text' }; // Default type for regular variables
		}
	}
	return variables;
};

export const splitProperties = (str: string, delimiter: string): string[] => {
	const result: string[] = [];
	let current = '';
	let depth = 0;
	let inString = false;
	let escapeNext = false;

	for (let i = 0; i < str.length; i++) {
		const char = str[i];

		if (escapeNext) {
			current += char;
			escapeNext = false;
			continue;
		}

		if (char === '\\') {
			current += char;
			escapeNext = true;
			continue;
		}

		if (char === '"' && !escapeNext) {
			inString = !inString;
			current += char;
			continue;
		}

		if (!inString) {
			if (char === '{' || char === '[') {
				depth++;
			} else if (char === '}' || char === ']') {
				depth--;
			}

			if (char === delimiter && depth === 0) {
				result.push(current.trim());
				current = '';
				continue;
			}
		}

		current += char;
	}

	if (current.trim()) {
		result.push(current.trim());
	}

	return result;
};

export const parseVariableDefinition = (definition: string): Record<string, any> => {
	// Use splitProperties for the main colon delimiter to handle quoted strings
	const parts = splitProperties(definition, ':');
	const [firstPart, ...propertyParts] = parts;

	// Parse type (explicit or implied)
	const type = firstPart.startsWith('type=') ? firstPart.slice(5) : firstPart;

	// Parse properties; support both key=value and bare flags (e.g., ":required")
	const properties = propertyParts.reduce(
		(props, part) => {
			const trimmed = part.trim();
			if (!trimmed) return props;

			// Use splitProperties for the equals sign as well, in case there are nested quotes
			const equalsParts = splitProperties(trimmed, '=');

			if (equalsParts.length === 1) {
				// It's a flag with no value, e.g. "required" -> true
				const flagName = equalsParts[0].trim();
				if (flagName.length > 0) {
					return { ...props, [flagName]: true };
				}
				return props;
			}

			const [propertyName, ...valueParts] = equalsParts;
			const propertyValueRaw = valueParts.join('='); // Handle values with extra '='

			if (!propertyName || propertyValueRaw == null) return props;

			return {
				...props,
				[propertyName.trim()]: parseJsonValue(propertyValueRaw.trim())
			};
		},
		{} as Record<string, any>
	);

	return { type, ...properties };
};
export const parseJsonValue = (value: string): any => {
	// Remove surrounding quotes if present (for string values)
	if (value.startsWith('"') && value.endsWith('"')) {
		return value.slice(1, -1);
	}

	// Check if it starts with square or curly brackets (JSON)
	if (/^[\[{]/.test(value)) {
		try {
			return JSON.parse(value);
		} catch {
			return value; // Return as string if JSON parsing fails
		}
	}

	return value;
};

async function ensurePDFjsLoaded() {
	if (!window.pdfjsLib) {
		const pdfjs = await import('pdfjs-dist');
		pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;
		if (!window.pdfjsLib) {
			throw new Error('pdfjsLib is required for PDF extraction');
		}
	}
	return window.pdfjsLib;
}

export const extractContentFromFile = async (file: File) => {
	// Known text file extensions for extra fallback
	const textExtensions = [
		'.txt',
		'.md',
		'.csv',
		'.json',
		'.js',
		'.ts',
		'.css',
		'.html',
		'.xml',
		'.yaml',
		'.yml',
		'.rtf'
	];

	function getExtension(filename: string) {
		const dot = filename.lastIndexOf('.');
		return dot === -1 ? '' : filename.substr(dot).toLowerCase();
	}

	// Uses pdfjs to extract text from PDF
	async function extractPdfText(file: File) {
		const pdfjsLib = await ensurePDFjsLoaded();
		const arrayBuffer = await file.arrayBuffer();
		const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
		let allText = '';
		for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
			const page = await pdf.getPage(pageNum);
			const content = await page.getTextContent();
			const strings = content.items.map((item: any) => item.str);
			allText += strings.join(' ') + '\n';
		}
		return allText;
	}

	// Reads file as text using FileReader
	function readAsText(file: File) {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(reader.result);
			reader.onerror = reject;
			reader.readAsText(file);
		});
	}

	async function extractDocxText(file: File) {
		const [arrayBuffer, { default: mammoth }] = await Promise.all([
			file.arrayBuffer(),
			import('mammoth')
		]);
		const result = await mammoth.extractRawText({ arrayBuffer });
		return result.value; // plain text
	}

	const type = file.type || '';
	const ext = getExtension(file.name);

	// PDF check
	if (type === 'application/pdf' || ext === '.pdf') {
		return await extractPdfText(file);
	}

	// DOCX check
	if (
		type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
		ext === '.docx'
	) {
		return await extractDocxText(file);
	}

	// Text check (plain or common text-based)
	if (type.startsWith('text/') || textExtensions.includes(ext)) {
		return await readAsText(file);
	}

	// Fallback: try to read as text, if decodable
	try {
		return await readAsText(file);
	} catch (err) {
		throw new Error('Unsupported or non-text file type: ' + (file.name || type));
	}
};

export const getAge = (birthDate) => {
	const today = new Date();
	const bDate = new Date(birthDate);
	let age = today.getFullYear() - bDate.getFullYear();
	const m = today.getMonth() - bDate.getMonth();

	if (m < 0 || (m === 0 && today.getDate() < bDate.getDate())) {
		age--;
	}
	return age.toString();
};

export const convertHeicToJpeg = async (file: File) => {
	const { default: heic2any } = await import('heic2any');
	try {
		return await heic2any({ blob: file, toType: 'image/jpeg' });
	} catch (err: any) {
		if (err?.message?.includes('already browser readable')) {
			return file;
		}
		throw err;
	}
};

export const decodeString = (str: string) => {
	try {
		return decodeURIComponent(str);
	} catch (e) {
		return str;
	}
};

export const initMermaid = async () => {
	const { default: mermaid } = await import('mermaid');
	mermaid.initialize({
		startOnLoad: false, // Should be false when using render API
		theme: document.documentElement.classList.contains('dark') ? 'dark' : 'default',
		securityLevel: 'loose'
	});
	return mermaid;
};

export const renderMermaidDiagram = async (mermaid, code: string) => {
	const parseResult = await mermaid.parse(code, { suppressErrors: false });
	if (parseResult) {
		const { svg } = await mermaid.render(`mermaid-${uuidv4()}`, code);
		return svg;
	}
	return '';
};

export const renderVegaVisualization = async (spec: string, i18n?: any) => {
	const vega = await import('vega');
	const parsedSpec = JSON.parse(spec);
	let vegaSpec = parsedSpec;
	if (parsedSpec.$schema && parsedSpec.$schema.includes('vega-lite')) {
		const vegaLite = await import('vega-lite');
		vegaSpec = vegaLite.compile(parsedSpec).spec;
	}
	const view = new vega.View(vega.parse(vegaSpec), { renderer: 'none' });
	const svg = await view.toSVG();
	return svg;
};

export const getCodeBlockContents = (content: string): object => {
	const codeBlockContents = content.match(/```[\s\S]*?```/g);

	let codeBlocks = [];

	let htmlContent = '';
	let cssContent = '';
	let jsContent = '';

	if (codeBlockContents) {
		codeBlockContents.forEach((block) => {
			const lang = block.split('\n')[0].replace('```', '').trim().toLowerCase();
			const code = block.replace(/```[\s\S]*?\n/, '').replace(/```$/, '');
			codeBlocks.push({ lang, code });
		});

		codeBlocks.forEach((block) => {
			const { lang, code } = block;

			if (lang === 'html') {
				htmlContent += code + '\n';
			} else if (lang === 'css') {
				cssContent += code + '\n';
			} else if (lang === 'javascript' || lang === 'js') {
				jsContent += code + '\n';
			}
		});
	} else {
		// Remove details tags from the content to check if there are any code blocks
		// hidden in the details tags (e.g. reasoning, etc.)
		content = removeAllDetails(content);

		const inlineHtml = content.match(/<html>[\s\S]*?<\/html>/gi);
		const inlineCss = content.match(/<style>[\s\S]*?<\/style>/gi);
		const inlineJs = content.match(/<script>[\s\S]*?<\/script>/gi);

		if (inlineHtml) {
			inlineHtml.forEach((block) => {
				const content = block.replace(/<\/?html>/gi, ''); // Remove <html> tags
				htmlContent += content + '\n';
			});
		}
		if (inlineCss) {
			inlineCss.forEach((block) => {
				const content = block.replace(/<\/?style>/gi, ''); // Remove <style> tags
				cssContent += content + '\n';
			});
		}
		if (inlineJs) {
			inlineJs.forEach((block) => {
				const content = block.replace(/<\/?script>/gi, ''); // Remove <script> tags
				jsContent += content + '\n';
			});
		}
	}

	return {
		codeBlocks: codeBlocks,
		html: htmlContent.trim(),
		css: cssContent.trim(),
		js: jsContent.trim()
	};
};
export const parseFrontmatter = (content) => {
	const match = content.match(/^---\s*\n([\s\S]*?)\n---/);
	if (match) {
		const frontmatter = {};
		match[1].split('\n').forEach((line) => {
			const [key, ...value] = line.split(':');
			if (key && value) {
				frontmatter[key.trim()] = value
					.join(':')
					.trim()
					.replace(/^["']|["']$/g, '');
			}
		});
		return frontmatter;
	}
	return {};
};

export const formatSkillName = (name) => {
	return name.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};
