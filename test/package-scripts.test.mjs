import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const packageJson = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));
const { scripts } = packageJson;

test('lint scripts keep checks and autofix separate', () => {
	assert.ok(scripts['lint:frontend'], 'lint:frontend script should exist');
	assert.ok(!scripts['lint:frontend'].includes('--fix'), 'lint:frontend should not modify files');
	assert.equal(scripts['lint:fix'], 'eslint . --fix');
});
