# Local Development — ClapNClaw Webui

## Método recomendado: Docker

El webui corre completo en Docker (frontend + backend en un container). Sin dependencias de sistema que instalar.

### Primera vez

```bash
cd clapnclaw-webui
cp .env.dev.example .env.dev
# edita .env.dev si necesitas cambiar algo
docker compose -f docker-compose.dev.yml up -d --build
```

La primera build tarda ~5 min. Las siguientes son más rápidas.

### Cada vez que arranques

```bash
cd clapnclaw-webui
docker compose -f docker-compose.dev.yml up -d
```

Accede en **http://localhost:3000** — entra directo sin login (`WEBUI_AUTH=False`).

### Cuando hagas cambios de código

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Rebuild completo. Tarda ~3 min.

### Parar

```bash
docker compose -f docker-compose.dev.yml down
```

---

## Variables de entorno (.env.dev)

Crea `.env.dev` en `clapnclaw-webui/` (está en `.gitignore`):

```bash
# Backend de ClapNClaw al que conecta el webui
# Por defecto apunta a staging — no necesitas cambiarlo para dev normal
CLAPNCLAW_API_URL=https://api-staging.clapnclaw.io

# Secret del workspace (solo necesario para probar billing/tokens)
# Lo encuentras en staging: tabla workspaces, columna tenant_report_secret
CLAPNCLAW_WORKSPACE_SECRET=
```

---

## Puertos

| Servicio | Puerto | URL |
|----------|--------|-----|
| Webui completo (Docker) | 3000 | http://localhost:3000 |
| Staging webui | — | https://staging-webui.clapnclaw.io |

---

## Arquitectura local

```
Browser → http://localhost:3000
            └── Docker container (puerto 8080 interno)
                  ├── SvelteKit (build estático servido por FastAPI)
                  └── FastAPI / Open WebUI
                        └── HTTP → CLAPNCLAW_API_URL (staging o local)
```

---

## Troubleshooting

**Container no arranca:**
```bash
docker compose -f docker-compose.dev.yml logs -f
```

**Puerto 3000 ocupado:**
```bash
lsof -ti :3000 | xargs kill -9 2>/dev/null
```

**Limpiar todo y empezar de cero:**
```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d --build
```

**Ver logs en vivo:**
```bash
docker compose -f docker-compose.dev.yml logs -f open-webui
```
