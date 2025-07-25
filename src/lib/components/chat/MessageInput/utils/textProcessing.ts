import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { 
	extractCurlyBraceWords,
	extractInputVariables,
	getCurrentDateTime,
	getFormattedDate,
	getFormattedTime,
	getUserPosition,
	getUserTimezone,
	getWeekday
} from '$lib/utils';
import type { InputVariable, TextProcessingOptions } from '../types';

export function processInputText(text: string, options: TextProcessingOptions = {}): string {
	const { variables = {}, extractVariables = true, processMarkdown = false } = options;
	
	let processedText = text;
	
	// Replace variables
	if (extractVariables) {
		processedText = replaceVariables(processedText, variables);
	}
	
	// Process markdown if needed
	if (processMarkdown) {
		processedText = processMarkdownText(processedText);
	}
	
	return processedText;
}

export function replaceVariables(text: string, variables: Record<string, string>): string {
	let processedText = text;
	
	// Replace user-defined variables
	Object.entries(variables).forEach(([key, value]) => {
		const regex = new RegExp(`{{${key}}}`, 'g');
		processedText = processedText.replace(regex, value);
	});
	
	// Replace system variables
	processedText = replaceSystemVariables(processedText);
	
	return processedText;
}

export function replaceSystemVariables(text: string): string {
	const systemVars: Record<string, () => string> = {
		'{{DATE}}': getFormattedDate,
		'{{TIME}}': getFormattedTime,
		'{{DATETIME}}': getCurrentDateTime,
		'{{WEEKDAY}}': getWeekday,
		'{{TIMEZONE}}': getUserTimezone,
		'{{USER}}': () => localStorage.getItem('username') || 'User'
	};
	
	let processedText = text;
	
	for (const [variable, getValue] of Object.entries(systemVars)) {
		if (processedText.includes(variable)) {
			processedText = processedText.replace(new RegExp(variable, 'g'), getValue());
		}
	}
	
	// Handle location variable asynchronously
	if (processedText.includes('{{LOCATION}}')) {
		getUserPosition().then(location => {
			if (location) {
				processedText = processedText.replace(
					/{{LOCATION}}/g,
					`${location.latitude}, ${location.longitude}`
				);
			}
		});
	}
	
	return processedText;
}

export function extractVariablesFromText(text: string): InputVariable[] {
	const curlyBraceWords = extractCurlyBraceWords(text);
	const inputVariables = extractInputVariables(text);
	
	const variables: InputVariable[] = [];
	
	// Extract simple variables
	curlyBraceWords.forEach(word => {
		if (!isSystemVariable(word)) {
			variables.push({
				id: word,
				name: word,
				type: 'text',
				label: word.charAt(0).toUpperCase() + word.slice(1),
				required: true
			});
		}
	});
	
	// Extract input variables with types
	inputVariables.forEach(variable => {
		const existing = variables.find(v => v.name === variable.name);
		if (!existing) {
			variables.push({
				id: variable.name,
				name: variable.name,
				type: variable.type || 'text',
				label: variable.label || variable.name,
				options: variable.options,
				required: variable.required !== false
			});
		}
	});
	
	return variables;
}

export function isSystemVariable(variable: string): boolean {
	const systemVars = [
		'DATE', 'TIME', 'DATETIME', 'WEEKDAY', 
		'TIMEZONE', 'LOCATION', 'USER'
	];
	
	return systemVars.includes(variable.toUpperCase());
}

export function processMarkdownText(text: string): string {
	try {
		const html = marked(text);
		return DOMPurify.sanitize(html);
	} catch (error) {
		console.error('Markdown processing error:', error);
		return text;
	}
}

export function extractCommandFromText(text: string): { command: string; args: string[] } | null {
	const commandMatch = text.match(/^\/(\w+)(?:\s+(.*))?$/);
	
	if (!commandMatch) {
		return null;
	}
	
	const [, command, argsString] = commandMatch;
	const args = argsString ? argsString.split(/\s+/) : [];
	
	return { command, args };
}

export function formatPastedText(text: string, maxLength?: number): string {
	// Remove excessive whitespace
	let formatted = text.replace(/\s+/g, ' ').trim();
	
	// Truncate if needed
	if (maxLength && formatted.length > maxLength) {
		formatted = formatted.substring(0, maxLength) + '...';
	}
	
	return formatted;
}

export function countTokens(text: string): number {
	// Simple token estimation (1 token ≈ 4 characters)
	return Math.ceil(text.length / 4);
}

export function splitTextIntoChunks(text: string, maxChunkSize: number): string[] {
	const chunks: string[] = [];
	const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
	
	let currentChunk = '';
	
	for (const sentence of sentences) {
		if ((currentChunk + sentence).length <= maxChunkSize) {
			currentChunk += sentence;
		} else {
			if (currentChunk) {
				chunks.push(currentChunk.trim());
			}
			currentChunk = sentence;
		}
	}
	
	if (currentChunk) {
		chunks.push(currentChunk.trim());
	}
	
	return chunks;
}