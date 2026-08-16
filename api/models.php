<?php
/** Models API: list known models + Ollama local models */
require_once __DIR__ . '/config.php';

$u = require_auth();

$common = [
    ['id' => 'gpt-4o',              'name' => 'GPT-4o',             'provider' => 'openai', 'group' => 'OpenAI'],
    ['id' => 'gpt-4o-mini',         'name' => 'GPT-4o mini',        'provider' => 'openai', 'group' => 'OpenAI'],
    ['id' => 'gpt-4.1',             'name' => 'GPT-4.1',            'provider' => 'openai', 'group' => 'OpenAI'],
    ['id' => 'gpt-4.1-mini',        'name' => 'GPT-4.1 mini',       'provider' => 'openai', 'group' => 'OpenAI'],
    ['id' => 'gpt-4-turbo',         'name' => 'GPT-4 Turbo',        'provider' => 'openai', 'group' => 'OpenAI'],
    ['id' => 'gpt-3.5-turbo',       'name' => 'GPT-3.5 Turbo',      'provider' => 'openai', 'group' => 'OpenAI'],
    ['id' => 'claude-3-5-sonnet',   'name' => 'Claude 3.5 Sonnet',  'provider' => 'openai', 'group' => 'Anthropic (via compatible API)'],
    ['id' => 'gemini-2.0-flash',    'name' => 'Gemini 2.0 Flash',   'provider' => 'openai', 'group' => 'Google (via compatible API)'],
    ['id' => 'deepseek-chat',       'name' => 'DeepSeek Chat',      'provider' => 'openai', 'group' => 'DeepSeek'],
    ['id' => 'deepseek-reasoner',   'name' => 'DeepSeek Reasoner',  'provider' => 'openai', 'group' => 'DeepSeek'],
    ['id' => 'llama3.2',            'name' => 'Llama 3.2',          'provider' => 'ollama', 'group' => 'Ollama (local)'],
    ['id' => 'llama3.1',            'name' => 'Llama 3.1',          'provider' => 'ollama', 'group' => 'Ollama (local)'],
    ['id' => 'qwen2.5',             'name' => 'Qwen 2.5',           'provider' => 'ollama', 'group' => 'Ollama (local)'],
    ['id' => 'mistral',             'name' => 'Mistral',            'provider' => 'ollama', 'group' => 'Ollama (local)'],
    ['id' => 'gemma2',              'name' => 'Gemma 2',            'provider' => 'ollama', 'group' => 'Ollama (local)'],
];

// Try to fetch live Ollama models if reachable
$ollamaBase = $u['ollama_base'] !== '' ? $u['ollama_base'] : DEFAULT_OLLAMA_BASE;
$ch = curl_init(rtrim($ollamaBase, '/') . '/api/tags');
curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 3]);
$resp = curl_exec($ch);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($code === 200) {
    $data = json_decode($resp, true);
    foreach (($data['models'] ?? []) as $m) {
        $common[] = ['id' => $m['name'], 'name' => $m['name'], 'provider' => 'ollama', 'group' => 'Ollama (local)'];
    }
}

json_out(['models' => $common]);
