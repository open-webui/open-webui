<?php
require_once __DIR__ . '/api/config.php';
$user = current_user();
?><!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= e(APP_NAME) ?> — رابط هوش مصنوعی</title>
<link rel="stylesheet" href="assets/css/app.css?v=<?= APP_VERSION ?>">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>">
</head>
<body class="app-body" data-user="<?= $user ? e($user['name']) : '' ?>">
<div id="app"></div>
<script src="assets/js/app.js?v=<?= APP_VERSION ?>"></script>
</body>
</html>
