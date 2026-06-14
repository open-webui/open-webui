import { describe, it, expect } from 'vitest';
import { Marked } from 'marked';
import { normalizeNestedFences } from './markdown-fences';

// Triple backtick, kept in a constant so the source itself stays readable.
const F = '```';

const lex = (s: string) => new Marked().lexer(s);
const codeTokens = (tokens: any[]) => tokens.filter((t) => t.type === 'code');
const hasType = (tokens: any[], type: string) => tokens.some((t) => t.type === type);

// The shape that broke in the "Automated ModSecurity Log Analyzer" chat: a language-tagged
// block whose body (a prompt string) embeds ``` fences. The visible break happened right
// after the colon-terminated lines, because those are the last code lines before a nested ```.
const pythonExample = [
	F + 'python',
	'    prompt = f"""You are a security expert.',
	'',
	'Provide ModSec rules in proper syntax:',
	'   ' + F,
	'   SecRule VARIABLES "OPERATOR" \\',
	'       "id:900000,phase:2,deny"',
	'   ' + F,
	'',
	'LOG CONTENT:',
	F,
	'{log_content}',
	F,
	'"""',
	'    return prompt',
	F
].join('\n');

describe('normalizeNestedFences', () => {
	it('keeps a python block with nested ``` fences as a single code token', () => {
		const tokens = lex(normalizeNestedFences(pythonExample));
		const codes = codeTokens(tokens);

		expect(codes).toHaveLength(1);
		expect(codes[0].lang).toBe('python');
		expect(codes[0].text).toContain('SecRule');
		expect(codes[0].text).toContain('{log_content}');
		expect(codes[0].text).toContain(F); // inner fences preserved as content
		expect(hasType(tokens, 'paragraph')).toBe(false); // nothing spilled out
	});

	it('(control) reproduces the bug on un-normalized input', () => {
		const tokens = lex(pythonExample);
		// The block splits at the first inner ```; prose (e.g. "SecRule ...") spills out.
		expect(codeTokens(tokens).length).toBeGreaterThan(1);
		expect(hasType(tokens, 'paragraph')).toBe(true);
	});

	it('preserves the language tag for a csharp block', () => {
		const csharp = [
			F + 'csharp',
			'var msg = $@"prompt with a fenced example:',
			F,
			'SecRule ...',
			F,
			'";'
		].join('\n');
		const codes = codeTokens(lex(normalizeNestedFences(csharp)));
		expect(codes).toHaveLength(1);
		expect(codes[0].lang).toBe('csharp');
	});

	it('promotes a nested block without swallowing a following tagged block', () => {
		const s = [
			F + 'python',
			'p = """',
			'in proper syntax:',
			F,
			'SecRule',
			F,
			'end',
			'"""',
			F, // true close of the python block
			'',
			'More text.',
			'',
			F + 'bash',
			'echo hi',
			F
		].join('\n');
		const tokens = lex(normalizeNestedFences(s));
		const codes = codeTokens(tokens);

		expect(codes).toHaveLength(2);
		expect(codes[0].lang).toBe('python');
		expect(codes[0].text).toContain('SecRule');
		expect(codes[0].text).toContain(F);
		expect(codes[1].lang).toBe('bash');
		expect(hasType(tokens, 'paragraph')).toBe(true); // "More text." between the blocks
	});

	it('is a no-op for content without code fences', () => {
		const s = 'Just some **markdown** text, with a $cost of 5 and no code.';
		expect(normalizeNestedFences(s)).toBe(s);
	});

	it('leaves a well-formed single code block unchanged', () => {
		const s = [F + 'js', 'const x = 1;', F].join('\n');
		expect(normalizeNestedFences(s)).toBe(s);
		const codes = codeTokens(lex(s));
		expect(codes).toHaveLength(1);
		expect(codes[0].lang).toBe('js');
	});

	it('is idempotent and skips already-wide outer fences', () => {
		// Outer already 4 backticks, inner 3 -> already safe, must not change.
		const safe = ['````python', 'x = """', F, 'inner', F, '"""', '````'].join('\n');
		expect(normalizeNestedFences(safe)).toBe(safe);

		// Re-running on already-normalized content is stable.
		const once = normalizeNestedFences(pythonExample);
		expect(normalizeNestedFences(once)).toBe(once);
	});

	it('is stable on a streaming prefix (block not yet closed)', () => {
		const prefix = [
			F + 'python',
			'p = """',
			'in proper syntax:',
			F,
			'SecRule',
			F,
			'still streaming...'
		].join('\n');
		const once = normalizeNestedFences(prefix);
		expect(normalizeNestedFences(once)).toBe(once);
		expect(() => lex(once)).not.toThrow();
	});
});
