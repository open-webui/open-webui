import { describe, it, expect } from 'vitest';

// Import the function we want to test
// Since it's not exported, we'll need to extract it or test it indirectly
// For now, let's create a copy of the function for testing
function cleanMarkdownFormatting(text: string): string {
	if (!text) return text;

	// Replace markdown formatting characters with spaces of equivalent length
	// This prevents formatting from interfering with PII tokenization while preserving exact offsets
	let cleaned = text
		// Handle bold formatting: **text** -> replace ** with spaces (preserve exact length)
		.replace(/\*\*([^*]+)\*\*/g, (match, content) => {
			// Replace ** with spaces, keep content unchanged
			// **text** (8 chars) -> '  text  ' (8 chars)
			return '  ' + content + '  ';
		})
		// Handle italic formatting: *text* -> replace * with spaces (preserve exact length)
		.replace(/\*([^*]+)\*/g, (match, content) => {
			// Replace * with spaces, keep content unchanged
			// *text* (6 chars) -> ' text ' (6 chars)
			return ' ' + content + ' ';
		})
		// Handle underline formatting: _text_ -> replace _ with spaces (preserve exact length)
		.replace(/_([^_]+)_/g, (match, content) => {
			// Replace _ with spaces, keep content unchanged
			// _text_ (6 chars) -> ' text ' (6 chars)
			return ' ' + content + ' ';
		})
		// Handle standalone formatting characters that might be adjacent to words
		.replace(/(\w)\*(\w)/g, '$1 $2') // word*word -> word word (preserves length)
		.replace(/(\w)_(\w)/g, '$1 $2') // word_word -> word word (preserves length)
		.replace(/\*(\w)/g, ' $1') // *word -> space + word (preserves length)
		.replace(/_(\w)/g, ' $1') // _word -> space + word (preserves length)
		.replace(/(\w)\*/g, '$1 ') // word* -> word + space (preserves length)
		.replace(/(\w)_/g, '$1 ') // word_ -> word + space (preserves length)
		// Handle multiple consecutive asterisks/underscores
		.replace(/\*+/g, (match) => ' '.repeat(match.length)) // *** -> spaces
		.replace(/_+/g, (match) => ' '.repeat(match.length)) // ___ -> spaces
		// Replace newlines with spaces to prevent interference with PII tokenization
		.replace(/\r\n/g, '  ') // \r\n -> two spaces (preserve length)
		.replace(/\n/g, ' '); // \n -> space (preserve length)

	return cleaned;
}

describe('cleanMarkdownFormatting', () => {
	describe('Length Preservation', () => {
		it('should preserve exact text length for all formatting types', () => {
			const testCases = [
				{ input: 'Hello **John Doe** how are you?', expectedLength: 31 },
				{ input: 'My email is *john@example.com* please contact me', expectedLength: 48 },
				{ input: 'Visit _123 Main Street_ for more info', expectedLength: 37 },
				{ input: '**Bold text** and *italic text* and _underlined text_', expectedLength: 53 },
				{ input: 'word*word and word_word and *word and word*', expectedLength: 43 },
				{ input: '***bold***', expectedLength: 10 },
				{ input: '___italic___', expectedLength: 12 },
				{ input: '**nested*bold**', expectedLength: 15 },
				{ input: 'No formatting here', expectedLength: 18 },
				{ input: '', expectedLength: 0 },
				{ input: '***', expectedLength: 3 },
				{ input: '___', expectedLength: 3 },
				{ input: 'Line 1\nLine 2', expectedLength: 13 },
				{ input: 'Line 1\r\nLine 2', expectedLength: 14 },
				{ input: '**Bold**\n*Italic*', expectedLength: 17 },
				{ input: 'Text\nwith\nnewlines', expectedLength: 18 }
			];

			testCases.forEach(({ input, expectedLength }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result.length).toBe(expectedLength);
			});
		});

		it('should handle edge cases without changing length', () => {
			const edgeCases = [
				'', // Empty string
				'   ', // Only spaces
				'***', // Only asterisks
				'___', // Only underscores
				'**', // Incomplete bold
				'*', // Single asterisk
				'_', // Single underscore
				'No formatting here', // No formatting
				'***bold***', // Triple asterisks
				'___italic___', // Triple underscores
				'*word*word*', // Multiple adjacent formatting
				'**nested*bold**', // Nested formatting
				'\n', // Single newline
				'\r\n', // Windows newline
				'\n\n', // Multiple newlines
				'\r\n\r\n' // Multiple Windows newlines
			];

			edgeCases.forEach((input) => {
				const result = cleanMarkdownFormatting(input);
				expect(result.length).toBe(input.length);
			});
		});
	});

	describe('Bold Formatting', () => {
		it('should replace **text** with spaces while preserving content', () => {
			const testCases = [
				{ input: '**John Doe**', expected: '  John Doe  ' },
				{ input: 'Hello **John Doe** how are you?', expected: 'Hello   John Doe   how are you?' },
				{ input: '**Bold text** and normal text', expected: '  Bold text   and normal text' },
				{ input: 'Multiple **bold** **words** here', expected: 'Multiple   bold     words   here' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});

		it('should handle triple asterisks correctly', () => {
			const testCases = [
				{ input: '***bold***', expected: '   bold   ' },
				{ input: '****extra****', expected: '    extra    ' },
				{ input: '***', expected: '   ' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});
	});

	describe('Italic Formatting', () => {
		it('should replace *text* with spaces while preserving content', () => {
			const testCases = [
				{ input: '*John Doe*', expected: ' John Doe ' },
				{
					input: 'My email is *john@example.com* please contact me',
					expected: 'My email is  john@example.com  please contact me'
				},
				{ input: '*Italic text* and normal text', expected: ' Italic text  and normal text' },
				{ input: 'Multiple *italic* *words* here', expected: 'Multiple  italic   words  here' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});
	});

	describe('Underline Formatting', () => {
		it('should replace _text_ with spaces while preserving content', () => {
			const testCases = [
				{ input: '_John Doe_', expected: ' John Doe ' },
				{
					input: 'Visit _123 Main Street_ for more info',
					expected: 'Visit  123 Main Street  for more info'
				},
				{
					input: '_Underlined text_ and normal text',
					expected: ' Underlined text  and normal text'
				},
				{
					input: 'Multiple _underlined_ _words_ here',
					expected: 'Multiple  underlined   words  here'
				}
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});

		it('should handle triple underscores correctly', () => {
			const testCases = [
				{ input: '___italic___', expected: '   italic   ' },
				{ input: '____extra____', expected: '    extra    ' },
				{ input: '___', expected: '   ' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});
	});

	describe('Adjacent Formatting Characters', () => {
		it('should handle formatting characters adjacent to words', () => {
			const testCases = [
				{ input: 'word*word', expected: 'word word' },
				{ input: 'word_word', expected: 'word word' },
				{ input: '*word', expected: ' word' },
				{ input: '_word', expected: ' word' },
				{ input: 'word*', expected: 'word ' },
				{ input: 'word_', expected: 'word ' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});
	});

	describe('Newline Handling', () => {
		it('should replace Unix newlines with spaces while preserving length', () => {
			const testCases = [
				{ input: 'Line 1\nLine 2', expected: 'Line 1 Line 2' },
				{ input: 'Text\nwith\nmultiple\nnewlines', expected: 'Text with multiple newlines' },
				{ input: 'Multiple\n\n\nnewlines', expected: 'Multiple   newlines' },
				{ input: 'No newlines here', expected: 'No newlines here' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
				expect(result.length).toBe(input.length);
			});
		});

		it('should replace Windows newlines with two spaces while preserving length', () => {
			const testCases = [
				{ input: 'Line 1\r\nLine 2', expected: 'Line 1  Line 2' },
				{
					input: 'Text\r\nwith\r\nmultiple\r\nnewlines',
					expected: 'Text  with  multiple  newlines'
				},
				{ input: 'Multiple\r\n\r\n\r\nnewlines', expected: 'Multiple      newlines' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
				expect(result.length).toBe(input.length);
			});
		});

		it('should handle mixed Unix and Windows newlines', () => {
			const testCases = [
				{ input: 'Mixed\r\nand\nnewlines', expected: 'Mixed  and newlines' },
				{ input: 'Unix\nWindows\r\nUnix\n', expected: 'Unix Windows  Unix ' },
				{ input: 'Start\r\nMiddle\nEnd', expected: 'Start  Middle End' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
				expect(result.length).toBe(input.length);
			});
		});

		it('should handle newlines with formatting', () => {
			const testCases = [
				{ input: '**Bold text**\n*Italic text*', expected: '  Bold text    Italic text ' },
				{
					input: 'Text with\nnewlines and **formatting**',
					expected: 'Text with newlines and   formatting  '
				},
				{ input: '_Underlined_\r\n**Bold**', expected: ' Underlined     Bold  ' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
				expect(result.length).toBe(input.length);
			});
		});

		it('should handle edge cases with newlines', () => {
			const testCases = [
				{ input: '\n', expected: ' ' },
				{ input: '\r\n', expected: '  ' },
				{ input: '\n\n', expected: '  ' },
				{ input: '\r\n\r\n', expected: '    ' },
				{ input: 'Start\n', expected: 'Start ' },
				{ input: '\nEnd', expected: ' End' },
				{ input: '\r\nStart', expected: '  Start' },
				{ input: 'End\r\n', expected: 'End  ' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
				expect(result.length).toBe(input.length);
			});
		});
	});

	describe('Mixed Formatting', () => {
		it('should handle multiple types of formatting in the same text', () => {
			const testCases = [
				{
					input: '**Bold text** and *italic text* and _underlined text_',
					expected: '  Bold text   and  italic text  and  underlined text '
				},
				{
					input: 'word*word and word_word and *word and word*',
					expected: 'word word and word word and  word and word '
				},
				{
					input: '**nested*bold**',
					expected: '  nested bold  '
				}
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});
	});

	describe('Content Preservation', () => {
		it('should preserve all actual text content', () => {
			const testCases = [
				'Hello **John Doe** how are you?',
				'My email is *john@example.com* please contact me',
				'Visit _123 Main Street_ for more info',
				'**Bold text** and *italic text* and _underlined text_',
				'word*word and word_word and *word and word*',
				'***bold***',
				'___italic___',
				'**nested*bold**',
				'No formatting here'
			];

			testCases.forEach((input) => {
				const result = cleanMarkdownFormatting(input);

				// Extract all non-formatting characters from both input and result
				// Remove formatting characters (* and _) and spaces from input
				const inputContent = input.replace(/[*_\s]/g, '');
				// Remove only spaces from result (formatting chars already replaced)
				const resultContent = result.replace(/\s/g, '');

				expect(resultContent).toBe(inputContent);
			});
		});

		it('should not modify text without formatting', () => {
			const testCases = [
				'No formatting here',
				'Regular text with numbers 123 and symbols @#$',
				'Multiple   spaces   and		tabs'
			];

			testCases.forEach((input) => {
				const result = cleanMarkdownFormatting(input);
				// For text without markdown formatting, result should be the same
				expect(result).toBe(input);
			});
		});

		it('should handle special characters that might be confused with formatting', () => {
			const testCases = [
				{
					input: 'Special characters: !@#$%^&*()_+-=[]{}|;:,.<>?',
					expected: 'Special characters: !@#$%^& () +-=[]{}|;:,.<>?'
				},
				{ input: 'Math: 2*3 = 6 and 4_5 = 20', expected: 'Math: 2 3 = 6 and 4 5 = 20' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});
	});

	describe('Tokenizer Interference Prevention', () => {
		it('should remove formatting characters that could interfere with PII tokenization', () => {
			const testCases = [
				{ input: '**John Doe**', expected: '  John Doe  ' },
				{ input: '*john@example.com*', expected: ' john@example.com ' },
				{ input: '_123 Main Street_', expected: ' 123 Main Street ' },
				{ input: 'word*word', expected: 'word word' },
				{ input: 'word_word', expected: 'word word' }
			];

			testCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);

				// Check that no asterisks or underscores remain (except in content)
				const hasFormattingChars = /[*_](?![^*_]*[*_])/.test(result);
				expect(hasFormattingChars).toBe(false);

				expect(result).toBe(expected);
			});
		});

		it('should ensure PII entities can be properly tokenized', () => {
			// Test cases that represent common PII patterns with formatting
			const piiTestCases = [
				{ input: '**John Doe**', description: 'Person name in bold' },
				{ input: '*john@example.com*', description: 'Email in italic' },
				{ input: '_555-123-4567_', description: 'Phone number underlined' },
				{ input: '**123 Main St**', description: 'Address in bold' },
				{ input: '*SSN: 123-45-6789*', description: 'SSN in italic' }
			];

			piiTestCases.forEach(({ input, description }) => {
				const result = cleanMarkdownFormatting(input);

				// The result should have spaces instead of formatting characters
				// This allows the PII tokenizer to properly identify entities
				expect(result).not.toMatch(/^[*_]+|[*_]+$/); // No leading/trailing formatting chars
				expect(result.length).toBe(input.length); // Length preserved

				// Content should be preserved (remove formatting chars and spaces from both)
				const inputContent = input.replace(/[*_\s]/g, '');
				const resultContent = result.replace(/\s/g, '');
				expect(resultContent).toBe(inputContent);
			});
		});
	});

	describe('Edge Cases and Error Handling', () => {
		it('should handle empty and null inputs', () => {
			expect(cleanMarkdownFormatting('')).toBe('');
			expect(cleanMarkdownFormatting(null as any)).toBe(null);
			expect(cleanMarkdownFormatting(undefined as any)).toBe(undefined);
		});

		it('should handle malformed markdown', () => {
			const malformedCases = [
				{ input: '**unclosed bold', expected: '  unclosed bold' },
				{ input: '*unclosed italic', expected: ' unclosed italic' },
				{ input: '_unclosed underline', expected: ' unclosed underline' },
				{ input: '**', expected: '  ' },
				{ input: '*', expected: ' ' },
				{ input: '_', expected: ' ' }
			];

			malformedCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});

		it('should handle nested and complex formatting', () => {
			const complexCases = [
				{ input: '**bold *italic* bold**', expected: '  bold  italic  bold  ' },
				{ input: '*italic **bold** italic*', expected: ' italic   bold   italic ' },
				{ input: '_underline *italic* underline_', expected: ' underline  italic  underline ' }
			];

			complexCases.forEach(({ input, expected }) => {
				const result = cleanMarkdownFormatting(input);
				expect(result).toBe(expected);
			});
		});

		it('should handle very long text', () => {
			const longText =
				'**Bold** '.repeat(1000) + '*italic* '.repeat(1000) + '_underline_ '.repeat(1000);
			const result = cleanMarkdownFormatting(longText);

			expect(result.length).toBe(longText.length);
			expect(result).not.toMatch(/^[*_]+|[*_]+$/);
		});
	});

	describe('Performance and Consistency', () => {
		it('should produce consistent results for the same input', () => {
			const testInput = '**Bold text** and *italic text* and _underlined text_';

			const result1 = cleanMarkdownFormatting(testInput);
			const result2 = cleanMarkdownFormatting(testInput);
			const result3 = cleanMarkdownFormatting(testInput);

			expect(result1).toBe(result2);
			expect(result2).toBe(result3);
		});

		it('should handle rapid successive calls', () => {
			const testInputs = [
				'**Bold**',
				'*italic*',
				'_underline_',
				'**Bold** and *italic*',
				'Mixed **formatting** *here*'
			];

			// Call the function multiple times rapidly
			for (let i = 0; i < 100; i++) {
				testInputs.forEach((input) => {
					const result = cleanMarkdownFormatting(input);
					expect(result.length).toBe(input.length);
				});
			}
		});
	});
});
