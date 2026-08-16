<?php
/**
 * LLM Proxy: forwards chat completions to OpenAI-compatible or Ollama API
 * Keeps the API key server-side (secure).
 */
require_once __DIR__ . '/config.php';

$u = require_auth();
$body = get_body();

$provider = $body['provider'] ?? 'openai';
$model    = trim($body['model'] ?? '');
$messages = $body['messages'] ?? [];

if ($model === '' || !is_array($messages) || count($messages) === 0) {
    json_out(['error' => 'model و messages الزامی است'], 400);
}

// OpenAI-compatible endpoint
if ($provider === 'openai') {
    $base = $u['openai_base'] !== '' ? $u['openai_base'] : DEFAULT_OPENAI_BASE;
    $key  = $u['api_key'] !== '' ? $u['api_key'] : DEFAULT_API_KEY;
    if ($key === '') json_out(['error' => 'API key تنظیم نشده است. از تنظیمات وارد کنید.'], 400);

    $ch = curl_init(rtrim($base, '/') . '/chat/completions');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_TIMEOUT        => 180,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $key
        ],
        CURLOPT_POSTFIELDS     => json_encode([
            'model'    => $model,
            'messages' => $messages,
            'stream'   => !empty($body['stream']),
        ], JSON_UNESCAPED_UNICODE),
    ]);
    $resp = curl_exec($ch);
    $err  = curl_error($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($err) json_out(['error' => 'Connection error: ' . $err], 502);
    if ($code >= 400) json_out(['error' => 'Upstream error (' . $code . '): ' . substr($resp, 0, 500)], 502);

    header('Content-Type: application/json; charset=utf-8');
    echo $resp;
    exit;
}

// Ollama (native format)
if ($provider === 'ollama') {
    $base = $u['ollama_base'] !== '' ? $u['ollama_base'] : DEFAULT_OLLAMA_BASE;
    // Convert OpenAI messages to Ollama format
    $ollamaMessages = array_map(fn($m) => ['role' => $m['role'] ?? 'user', 'content' => $m['content'] ?? ''], $messages);

    $ch = curl_init(rtrim($base, '/') . '/api/chat');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_TIMEOUT        => 180,
        CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
        CURLOPT_POSTFIELDS     => json_encode([
            'model' => $model,
            'messages' => $ollamaMessages,
            'stream' => false,
        ]),
    ]);
    $resp = curl_exec($ch);
    $err  = curl_error($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($err) json_out(['error' => 'Connection error: ' . $err], 502);
    if ($code >= 400) json_out(['error' => 'Ollama error (' . $code . '): ' . substr($resp, 0, 500)], 502);

    $data = json_decode($resp, true);
    $content = $data['message']['content'] ?? '';

    json_out([
        'id' => 'ollama-' . bin2hex(random_bytes(6)),
        'choices' => [[
            'message' => ['role' => 'assistant', 'content' => $content],
            'finish_reason' => 'stop'
        ]]
    ]);
    exit;
}

json_out(['error' => 'Unknown provider'], 400);
