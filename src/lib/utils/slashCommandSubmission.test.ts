import { describe, expect, it } from 'vitest';
import {
	resolveSlashCommandSubmission,
	shouldPassThroughSlashCommands
} from './slashCommandSubmission';

const model = (id: string, ownedBy: string, capabilities: Record<string, boolean> = {}) => ({
	id,
	owned_by: ownedBy,
	info: { meta: { capabilities } }
});

describe('shouldPassThroughSlashCommands', () => {
	it('enables passthrough for models advertised by Hermes', () => {
		expect(shouldPassThroughSlashCommands([model('agent', 'hermes')], ['agent'])).toBe(true);
	});

	it('allows other agent backends to opt in with model metadata', () => {
		expect(
			shouldPassThroughSlashCommands(
				[model('agent', 'openai', { native_slash_commands: true })],
				['agent']
			)
		).toBe(true);
	});

	it('keeps Open WebUI commands for ordinary and mixed model selections', () => {
		const models = [model('agent', 'hermes'), model('chat', 'openai')];
		expect(shouldPassThroughSlashCommands(models, ['chat'])).toBe(false);
		expect(shouldPassThroughSlashCommands(models, ['agent', 'chat'])).toBe(false);
		expect(shouldPassThroughSlashCommands(models, ['missing'])).toBe(false);
	});
});

describe('resolveSlashCommandSubmission', () => {
	it.each(['/help', '/status', '/model', '/new', '/agents', '/custom-command argument1'])(
		'preserves %s byte-for-byte for a native slash-command model',
		(input) => {
			expect(resolveSlashCommandSubmission(input, true)).toEqual({
				type: 'message',
				content: input
			});
		}
	);

	it('preserves whitespace, URLs, paths, multiple slashes and code blocks', () => {
		const inputs = [
			'  /model  openrouter:foo/bar  ',
			'Bonjour /help',
			'https://example.com/test',
			'/custom a/b/c',
			'```sh\nprintf "/status"\n```'
		];

		for (const input of inputs) {
			expect(resolveSlashCommandSubmission(input, true)).toEqual({
				type: 'message',
				content: input
			});
		}
	});

	it('retains existing Open WebUI command behavior for ordinary models', () => {
		expect(resolveSlashCommandSubmission('/compact', false)).toEqual({ type: 'compact' });
		expect(resolveSlashCommandSubmission('/status', false)).toEqual({ type: 'status' });
		expect(resolveSlashCommandSubmission('/fork', false)).toEqual({ type: 'fork' });
		expect(resolveSlashCommandSubmission('/model', false)).toEqual({ type: 'model', modelId: '' });
		expect(resolveSlashCommandSubmission('/model llama3.2', false)).toEqual({
			type: 'model',
			modelId: 'llama3.2'
		});
	});

	it('submits unknown slash commands and ordinary messages unchanged for ordinary models', () => {
		for (const input of ['/new', '/custom-command argument1', 'ordinary message']) {
			expect(resolveSlashCommandSubmission(input, false)).toEqual({
				type: 'message',
				content: input
			});
		}
	});
});
