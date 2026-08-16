<?php
/** Auth API: register / login / logout / profile */
require_once __DIR__ . '/config.php';

$action = $_GET['action'] ?? ($_POST['action'] ?? '');

switch ($action) {
    case 'register': {
        $body = get_body();
        $name  = trim($body['name'] ?? '');
        $email = strtolower(trim($body['email'] ?? ''));
        $pass  = $body['password'] ?? '';

        if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($pass) < 6) {
            json_out(['error' => 'نام، ایمیل معتبر و رمز حداقل ۶ کاراکتر الزامی است'], 400);
        }

        $st = db()->prepare('SELECT id FROM users WHERE email = ?');
        $st->execute([$email]);
        if ($st->fetch()) json_out(['error' => 'این ایمیل قبلاً ثبت شده است'], 409);

        $st = db()->prepare('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)');
        $st->execute([$name, $email, password_hash($pass, PASSWORD_DEFAULT)]);
        $_SESSION['user_id'] = (int)db()->lastInsertId();

        json_out(['ok' => true, 'user' => ['id' => $_SESSION['user_id'], 'name' => $name, 'email' => $email]]);
        break;
    }

    case 'login': {
        $body = get_body();
        $email = strtolower(trim($body['email'] ?? ''));
        $pass  = $body['password'] ?? '';

        $st = db()->prepare('SELECT * FROM users WHERE email = ?');
        $st->execute([$email]);
        $u = $st->fetch();
        if (!$u || !password_verify($pass, $u['password_hash'])) {
            json_out(['error' => 'ایمیل یا رمز عبور اشتباه است'], 401);
        }
        $_SESSION['user_id'] = (int)$u['id'];
        json_out(['ok' => true, 'user' => ['id' => (int)$u['id'], 'name' => $u['name'], 'email' => $u['email']]]);
        break;
    }

    case 'logout': {
        session_destroy();
        json_out(['ok' => true]);
        break;
    }

    case 'me': {
        $u = current_user();
        if (!$u) json_out(['error' => 'Not authenticated'], 401);
        json_out(['user' => ['id' => (int)$u['id'], 'name' => $u['name'], 'email' => $u['email']]]);
        break;
    }

    case 'update': {
        $u = require_auth();
        $body = get_body();
        $name = trim($body['name'] ?? $u['name']);
        $apiKey = trim($body['api_key'] ?? $u['api_key']);
        $openaiBase = rtrim(trim($body['openai_base'] ?? $u['openai_base']), '/');
        $ollamaBase = rtrim(trim($body['ollama_base'] ?? $u['ollama_base']), '/');

        $st = db()->prepare('UPDATE users SET name=?, api_key=?, openai_base=?, ollama_base=? WHERE id=?');
        $st->execute([$name, $apiKey, $openaiBase, $ollamaBase, $u['id']]);
        json_out(['ok' => true]);
        break;
    }

    default:
        json_out(['error' => 'Unknown action'], 400);
}
