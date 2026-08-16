<?php
/** Chat API: list / create / get / save / delete chats */
require_once __DIR__ . '/config.php';

$u = require_auth();
$action = $_GET['action'] ?? 'list';

switch ($action) {
    case 'list': {
        $st = db()->prepare('SELECT id, title, model, updated_at FROM chats WHERE user_id = ? ORDER BY updated_at DESC');
        $st->execute([$u['id']]);
        json_out(['chats' => $st->fetchAll()]);
        break;
    }

    case 'create': {
        $body = get_body();
        $id = $body['id'] ?? ('chat_' . bin2hex(random_bytes(8)));
        $title = trim($body['title'] ?? 'New Chat');
        $model = trim($body['model'] ?? '');
        $st = db()->prepare('INSERT INTO chats (id, user_id, title, model, messages) VALUES (?, ?, ?, ?, ?)');
        $st->execute([$id, $u['id'], $title, $model, '[]']);
        json_out(['chat' => ['id' => $id, 'title' => $title, 'model' => $model]]);
        break;
    }

    case 'get': {
        $id = $_GET['id'] ?? '';
        $st = db()->prepare('SELECT * FROM chats WHERE id = ? AND user_id = ?');
        $st->execute([$id, $u['id']]);
        $c = $st->fetch();
        if (!$c) json_out(['error' => 'Chat not found'], 404);
        $c['messages'] = json_decode($c['messages'], true) ?: [];
        json_out(['chat' => $c]);
        break;
    }

    case 'save': {
        $body = get_body();
        $id = $body['id'] ?? '';
        $messages = $body['messages'] ?? null;
        $title = trim($body['title'] ?? '');

        $st = db()->prepare('SELECT id FROM chats WHERE id = ? AND user_id = ?');
        $st->execute([$id, $u['id']]);
        if (!$st->fetch()) json_out(['error' => 'Chat not found'], 404);

        if ($messages !== null) {
            $st = db()->prepare("UPDATE chats SET messages = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?");
            $st->execute([json_encode($messages, JSON_UNESCAPED_UNICODE), $id, $u['id']]);
        }
        if ($title !== '') {
            $st = db()->prepare('UPDATE chats SET title = ? WHERE id = ? AND user_id = ?');
            $st->execute([$title, $id, $u['id']]);
        }
        json_out(['ok' => true]);
        break;
    }

    case 'delete': {
        $id = $_GET['id'] ?? ($_POST['id'] ?? '');
        $st = db()->prepare('DELETE FROM chats WHERE id = ? AND user_id = ?');
        $st->execute([$id, $u['id']]);
        json_out(['ok' => true]);
        break;
    }

    default:
        json_out(['error' => 'Unknown action'], 400);
}
