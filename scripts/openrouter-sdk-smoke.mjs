import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

import { OpenRouter } from '@openrouter/sdk';

const root = process.cwd();
const envPath = path.join(root, '.env');

const parseEnvLine = (line) => {
	const trimmed = line.trim();
	if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) {
		return null;
	}

	const idx = trimmed.indexOf('=');
	const key = trimmed.slice(0, idx).trim();
	const value = trimmed.slice(idx + 1).trim();
	return { key, value };
};

const loadEnvFile = () => {
	if (!fs.existsSync(envPath)) {
		return;
	}

	const content = fs.readFileSync(envPath, 'utf8');
	for (const line of content.split(/\r?\n/)) {
		const parsed = parseEnvLine(line);
		if (!parsed) {
			continue;
		}

		if (!process.env[parsed.key]) {
			process.env[parsed.key] = parsed.value;
		}
	}
};

const main = async () => {
	loadEnvFile();

	const apiKey = process.env.OPENROUTER_API_KEY || process.env.OPENAI_API_KEY;
	const model = process.env.OPENROUTER_SDK_SMOKE_MODEL || 'google/gemini-3-flash-preview';
	const prompt = process.env.OPENROUTER_SDK_SMOKE_PROMPT || 'Return JSON with key status="ok"';
	const dryRun = `${process.env.OPENROUTER_SDK_DRY_RUN || ''}`.toLowerCase() === 'true';

	if (!apiKey || apiKey.includes('REPLACE_WITH_YOUR_REAL_KEY')) {
		console.error(
			'[openrouter-sdk-smoke] Missing a real API key. Set OPENROUTER_API_KEY (or OPENAI_API_KEY) in .env.'
		);
		process.exit(1);
	}

	const client = new OpenRouter({
		apiKey,
		defaultHeaders: {
			'HTTP-Referer': process.env.OPENROUTER_HTTP_REFERER || 'https://openwebui.com/',
			'X-Title': process.env.OPENROUTER_X_TITLE || 'Open WebUI'
		}
	});

	if (dryRun) {
		console.log('[openrouter-sdk-smoke] Dry run OK. SDK client initialized successfully.');
		console.log(`[openrouter-sdk-smoke] model=${model}`);
		return;
	}

	const completion = await client.chat.send({
		chatGenerationParams: {
			model,
			messages: [{ role: 'user', content: prompt }],
			stream: false
		}
	});

	const completionData = completion?.value ?? completion;
	const content = completionData?.choices?.[0]?.message?.content;
	console.log('[openrouter-sdk-smoke] Success. First response chunk:');
	console.log(typeof content === 'string' ? content : JSON.stringify(content, null, 2));
};

main().catch((err) => {
	console.error('[openrouter-sdk-smoke] Failed:', err?.message || err);
	process.exit(1);
});
