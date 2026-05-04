# Public Release Checklist

Use this checklist before pushing this repository to a public GitHub repo.

## License

- Keep the upstream `LICENSE` and copyright notices intact.
- Review the Open WebUI branding restriction before publishing a fork or derivative.
- Do not remove or replace branding unless your distribution qualifies under the license terms.

## Secrets and Local Data

- Do not commit `.env`, `.env.*`, secret key files, or runtime databases.
- Keep `open-webui-data/`, cache directories, and model caches out of the public repo.
- Verify no API keys, tokens, private keys, or session cookies appear in tracked files.

## Network Details

- Remove hardcoded LAN IPs, hostnames, Docker service names, and internal URLs.
- Prefer placeholders such as `http://<OLLAMA_HOST>:11434` in docs and examples.

## Quick Checks

```bash
git ls-files | rg '(^|/)(\\.env(\\.|$)|webui\\.db|ollama\\.db|.*secret.*|.*token.*|.*key.*)$'
git ls-files -z | xargs -0 rg -n '(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36,}|xox[baprs]-[A-Za-z0-9-]+|-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----|sk-[A-Za-z0-9]{20,})'
git ls-files -z | xargs -0 rg -n '(192\\.168\\.|10\\.|172\\.(1[6-9]|2[0-9]|3[0-1])\\.|localhost:11434|ollama-dify)'
```

## Before Push

- Run the quick checks above.
- Review `git status` for any runtime or data files.
- Push only the sanitized source tree.
