#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/../"

mkdir -p src/routes/version/

cat <<EOF > src/routes/version/+page.svelte
<html>
<head>
    <style>
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>

<body>
    <ul>
        <li>branch: <a href="https://github.com/etalab-ia/albert-conversation/tree/$(git rev-parse --abbrev-ref HEAD)/">"$(git rev-parse --abbrev-ref HEAD)"</a></li>
        <li>gitDate": $(git show -s --format=%ci | sed "s/ /_/g")</li>
        <li>buildStamp: $(env TZ=Europe/Paris date '+%Y-%m-%d_%H:%M:%S-%Z')</li>
        <li>gitHash: <a href="https://github.com/etalab-ia/albert-conversation/tree/$(git rev-parse HEAD)">$(git rev-parse HEAD)</li>
    </ul>
</body>
</html>
EOF
