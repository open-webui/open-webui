import { v4 as uuidv4 } from 'uuid';
import sha256 from 'js-sha256';

import { WEBUI_BASE_URL } from '$lib/constants';
import { TTS_RESPONSE_SPLIT } from '$lib/types';

//////////////////////////
// Helper functions
//////////////////////////

export const replaceTokens = (content, char, user) => {
	const charToken = /{{char}}/gi;
	const userToken = /{{user}}/gi;
	const videoIdToken = /{{VIDEO_FILE_ID_([a-f0-9-]+)}}/gi; // Regex to capture the video ID
	const htmlIdToken = /{{HTML_FILE_ID_([a-f0-9-]+)}}/gi; // Regex to capture the HTML ID

	// Replace {{char}} if char is provided
	if (char !== undefined && char !== null) {
		content = content.replace(charToken, char);
	}

	// Replace {{user}} if user is provided
	if (user !== undefined && user !== null) {
		content = content.replace(userToken, user);
	}

	// Replace video ID tags with corresponding <video> elements
	content = content.replace(videoIdToken, (match, fileId) => {
		const videoUrl = `${WEBUI_BASE_URL}/api/v1/files/${fileId}/content`;
		return `<video src="${videoUrl}" controls></video>`;
	});

	// Replace HTML ID tags with corresponding HTML content
	content = content.replace(htmlIdToken, (match, fileId) => {
		const htmlUrl = `${WEBUI_BASE_URL}/api/v1/files/${fileId}/content/html`;
		return `<iframe src="${htmlUrl}" width="100%" frameborder="0" onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"></iframe>`;
	});

	return content;
};

export const sanitizeResponseContent = (content: string) => {
	return content
		.replace(/<\|[a-z]*$/, '')
		.replace(/<\|[a-z]+\|$/, '')
		.replace(/<$/, '')
		.replaceAll(/<\|[a-z]+\|>/g, ' ')
		.replaceAll('<', '&lt;')
		.replaceAll('>', '&gt;')
		.trim();
};

export const processResponseContent = (content: string) => {
	return content.trim();
};

export const revertSanitizedResponseContent = (content: string) => {
	return content.replaceAll('&lt;', '<').replaceAll('&gt;', '>');
};

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

export const generateInitialsImage = (name) => {
	const canvas = document.createElement('canvas');
	const ctx = canvas.getContext('2d');
	canvas.width = 100;
	canvas.height = 100;

	if (!canvasPixelTest()) {
		console.log(
			'generateInitialsImage: failed pixel test, fingerprint evasion is likely. Using default image.'
		);
		return '/user.png';
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

export const copyToClipboard = async (text) => {
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

export const findWordIndices = (text) => {
	const regex = /\[([^\]]+)\]/g;
	const matches = [];
	let match;

	while ((match = regex.exec(text)) !== null) {
		matches.push({
			word: match[1],
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
				timestamp: convo['timestamp']
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

export const removeEmojis = (str: string) => {
	// Regular expression to match emojis
	const emojiRegex = /[\uD800-\uDBFF][\uDC00-\uDFFF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDE4F]/g;

	// Replace emojis with an empty string
	return str.replace(emojiRegex, '');
};

export const removeFormattings = (str: string) => {
	return str.replace(/(\*)(.*?)\1/g, '').replace(/(```)(.*?)\1/gs, '');
};

export const cleanText = (content: string) => {
	return removeFormattings(removeEmojis(content.trim()));
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

	// Split the modified text into sentences based on common punctuation marks, avoiding these blocks
	let sentences = text.split(/(?<=[.!?])\s+/);

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

export const getMessageContentParts = (content: string, split_on: string = 'punctuation') => {
	const messageContentParts: string[] = [];

	switch (split_on) {
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

/**
 * @param {string} template - The template string containing placeholders.
 * @returns {string} The template string with the placeholders replaced by the prompt.
 */
export const promptTemplate = (
	template: string,
	user_name?: string,
	user_location?: string
): string => {
	// Get the current date
	const currentDate = new Date();

	// Format the date to YYYY-MM-DD
	const formattedDate =
		currentDate.getFullYear() +
		'-' +
		String(currentDate.getMonth() + 1).padStart(2, '0') +
		'-' +
		String(currentDate.getDate()).padStart(2, '0');

	// Format the time to HH:MM:SS AM/PM
	const currentTime = currentDate.toLocaleTimeString('en-US', {
		hour: 'numeric',
		minute: 'numeric',
		second: 'numeric',
		hour12: true
	});

	// Get the current weekday
	const currentWeekday = getWeekday();

	// Get the user's timezone
	const currentTimezone = getUserTimezone();

	// Get the user's language
	const userLanguage = localStorage.getItem('locale') || 'en-US';

	// Replace {{CURRENT_DATETIME}} in the template with the formatted datetime
	template = template.replace('{{CURRENT_DATETIME}}', `${formattedDate} ${currentTime}`);

	// Replace {{CURRENT_DATE}} in the template with the formatted date
	template = template.replace('{{CURRENT_DATE}}', formattedDate);

	// Replace {{CURRENT_TIME}} in the template with the formatted time
	template = template.replace('{{CURRENT_TIME}}', currentTime);

	// Replace {{CURRENT_WEEKDAY}} in the template with the current weekday
	template = template.replace('{{CURRENT_WEEKDAY}}', currentWeekday);

	// Replace {{CURRENT_TIMEZONE}} in the template with the user's timezone
	template = template.replace('{{CURRENT_TIMEZONE}}', currentTimezone);

	// Replace {{USER_LANGUAGE}} in the template with the user's language
	template = template.replace('{{USER_LANGUAGE}}', userLanguage);

	if (user_name) {
		// Replace {{USER_NAME}} in the template with the user's name
		template = template.replace('{{USER_NAME}}', user_name);
	}

	if (user_location) {
		// Replace {{USER_LOCATION}} in the template with the current location
		template = template.replace('{{USER_LOCATION}}', user_location);
	}

	return template;
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

	template = promptTemplate(template);

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
	return date.toISOString().split('T')[0];
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
