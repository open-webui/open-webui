<?php
/**
 * Open WebUI — PHP Edition for cPanel
 * Configuration, SQLite connection, session handling
 * 
 * Auth modes: 'session' (default PHP sessions) or 'api_key' (single-user, sessionless)
 * Override in .htaccess: SetEnv AUTH_MODE api_key
 */

declare(strict_types=1);

session_start();

// ─── App Config ───────────────────────────────────────────────
define('APP_NAME', 'Open WebUI');
define('APP_VERSION', '0.1.0-php');
define('BASE_URL', rtrim(dirname(dirname($_SERVER['SCRIPT_NAME'] ?? '/')), '/'));

// ─── Database ────────────────────────────────────────────────
define('DB_FILE', __DIR__ . '/../data/openwebui.db');

// ─── Auth Mode ───────────────────────────────────────────────
$aMode = getenv('AUTH_MODE');
$aMode = ($aMode === false || $aMode === null) ? 'session' : $aMode;
define('AUTH_MODE', strtolower(trim($aMode)) === 'api_key' ? 'api_key' : 'session');

// ─── Default settings ─────────────────────────────────────────
define('DEFAULT_OPENAI_BASE', 'https://api.openai.com/v1');
define('DEFAULT_OLLAMA_BASE', 'http://localhost:11434');

// ─── Helpers ─────────────────────────────────────────────────
function db(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        $dir = dirname(DB_FILE);
        if (!is_dir($dir)) { mkdir($dir, 0775, true); }
        try {
            $pdo = new PDO('sqlite:' . DB_FILE);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
            $pdo->exec('PRAGMA journal_mode = WAL;');
        } catch (PDOException $e) {
            http_response_code(500);
            echo json_encode(['error' => 'Database error: ' . $e->getMessage()]);
            exit;
        }
    }
    return $pdo;
}

function init_db(): void {
    $pdo = db();
    $pdo->exec("CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        api_key TEXT DEFAULT '',
        openai_base TEXT DEFAULT '',
        ollama_base TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )");
    $pdo->exec("CREATE TABLE IF NOT EXISTS chats (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title TEXT DEFAULT 'New Chat',
        messages TEXT DEFAULT '[]',
        model TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )");
}

function json_out(array $data, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

// ─── Simple key-based auth (for API_KEY mode) ────────────────
function api_key_auth(): ?array {
    if (defined('AUTH_MODE') && AUTH_MODE === 'api_key') {
        // Look for API key in header or as query param
        $key = $_SERVER['HTTP_X_API_KEY'] ?? '';
        if (empty($key)) $key = $_GET['api_key'] ?? '';
        
        // First try: check if any user has this key
        if ($key) {
            $st = db()->prepare('SELECT * FROM users WHERE api_key = ? LIMIT 1');
            $st->execute([$key]);
            $u = $st->fetch();
            if ($u) {
                return $u;
            }
        }
        // Fallback: return first user (for dev/test)
        if (!isset($_SESSION['user_first_init'])) {
            $st = db()->prepare('SELECT * FROM users LIMIT 1');
            $st->execute();
            $u = $st->fetch();
            if ($u) {
                $_SESSION['user_first_init'] = true;
                return $u;
            }
        }
        return null;
    }
    // Session mode: use existing session logic
    if (empty($_SESSION['user_id'])) return null;
    $st = db()->prepare('SELECT * FROM users WHERE id = ?');
    $st->execute([$_SESSION['user_id']]);
    return $st->fetch() ?: null;
}

function current_user(): ?array {
    return api_key_auth();
}

function require_auth(): array {
    $u = current_user();
    if (!$u) {
        // In API_KEY mode, respond with challenge; in session mode redirect to login
        if (defined('AUTH_MODE') && AUTH_MODE === 'api_key') {
            http_response_code(401);
            json_out(['error' => 'API key missing or invalid'], 401);
        } else {
            json_out(['error' => 'Not authenticated'], 401);
        }
        exit;
    }
    return $u;
}

function e(?string $s): string {
    return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8');
}

function get_body(): array {
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);
    return is_array($data) ? $data : [];
}

init_db();
