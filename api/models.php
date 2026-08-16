<?php
/** Models API: fetch live model list from the configured endpoint */
require_once __DIR__ . '/config.php';

$u = require_auth();

$base = $u['openai_base'] !== '' ? $u['openai_base'] : DEFAULT_OPENAI_BASE;
$key  = $u['api_key'] !== '' ? $u['api_key'] : DEFAULT_API_KEY;

$models = [];

// Try to fetch live model list from the OpenAI-compatible endpoint
$ch = curl_init(rtrim($base, '/') . '/models');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 10,
    CURLOPT_HTTPHEADER     => ['Authorization: Bearer ' . $key],
]);
$resp = curl_exec($ch);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($code === 200) {
    $data = json_decode($resp, true);
    foreach (($data['data'] ?? []) as $m) {
        $id = $m['id'] ?? '';
        if ($id === '') continue;
        $isCombo = ($m['owned_by'] ?? '') === 'combo';
        $models[] = [
            'id'       => $id,
            'name'     => $id,
            'provider' => 'openai',
            'group'    => $isCombo ? 'Combo' : (str_contains($id, '/') ? explode('/', $id)[0] : 'Other'),
        ];
    }
}

// Fallback list when endpoint is unreachable
if (empty($models)) {
    $models = [
        ['id' => 'ChatRayovin',           'name' => 'ChatRayovin',            'provider' => 'openai', 'group' => 'Combo'],
        ['id' => 'oc/deepseek-v4-flash-free', 'name' => 'DeepSeek V4 Flash',  'provider' => 'openai', 'group' => 'Oc (free)'],
        ['id' => 'oc/mimo-v2.5-free',     'name' => 'MiMo V2.5',              'provider' => 'openai', 'group' => 'Oc (free)'],
        ['id' => 'gpt-4o-mini',           'name' => 'GPT-4o mini',            'provider' => 'openai', 'group' => 'OpenAI'],
        ['id' => 'gpt-4o',                'name' => 'GPT-4o',                 'provider' => 'openai', 'group' => 'OpenAI'],
        ['id' => 'llama3.2',              'name' => 'Llama 3.2',              'provider' => 'ollama', 'group' => 'Ollama (local)'],
    ];
}

// Ensure ChatRayovin is always first
usort($models, fn($a) => $a['id'] === 'ChatRayovin' ? -1 : 0);

json_out(['models' => $models]);
