# Desarrollo Local - Open WebUi (Fork CodingSoft)

## Inicio Rápido

### Opción 1: Solo Frontend (Recomendado para desarrollo UI)

```bash
npm run dev
# http://localhost:5173
```

### Opción 2: Frontend + Backend (Requiere Docker para backend)

```bash
# Terminal 1: Backend con Docker
./start-dev.sh backend

# Terminal 2: Frontend
npm run dev
```

### Opción 3: Usar script combinado

```bash
./start-dev.sh all  # Inicia ambos
./start-dev.sh stop # Detiene el backend
```

## Estructura del Proyecto

```
open-webui/
├── src/                    # Frontend (Svelte/SvelteKit)
│   ├── lib/
│   │   ├── components/     # Componentes UI
│   │   └── stores/         # Stores de Svelte
│   └── routes/             # Rutas de la aplicación
├── backend/                # Backend (Python/FastAPI)
│   ├── open_webui/         # Código principal
│   │   ├── routers/        # API endpoints
│   │   ├── utils/          # Utilidades
│   │   └── config.py       # Configuración
│   └── requirements.txt    # Dependencias Python
├── docker-compose.yaml     # Producción
└── start-dev.sh           # Script desarrollo local
```

## Personalización

### Variables de Entorno (.env)

Las personalizaciones se configuran en `.env`:

```bash
WEBUI_NAME="Open WebUi"
WEBUI_FAVICON_URL="https://webui.codingsoft.org/favicon.png"
WEBUI_ADMIN_EMAIL="team@codingsoft.org"
```

### Archivos Modificados

Ver commit de personalización:

```
feat: CodingSoft branding customization
```

## Construir para Producción

### Build Docker

```bash
# En un servidor con más recursos
docker build -t ghcr.io/codingsoft/open-webui:latest .
docker push ghcr.io/codingsoft/open-webui:latest
```

### Deploy en VPS

```bash
# En el VPS
docker-compose pull
docker-compose up -d
```

## Links Útiles

- **Frontend Dev**: http://localhost:5173
- **Repo Fork**: https://github.com/CodingSoft/open-webui
- **Docs**: https://docs.webui.codingsoft.org
- **Web**: https://codingsoft.org
