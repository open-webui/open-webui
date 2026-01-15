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

## Scripts Disponibles

| Script            | Propósito                                |
| ----------------- | ---------------------------------------- |
| `./start-dev.sh`  | Desarrollo local (frontend + backend)    |
| `./build-push.sh` | Build y push a GitHub Container Registry |

### Comandos de start-dev.sh

```bash
./start-dev.sh dev       # Frontend (recomendado)
./start-dev.sh backend   # Backend con Docker
./start-dev.sh start     # Ambos
./start-dev.sh stop      # Detener backend
./start-dev.sh restart   # Reiniciar backend
./start-dev.sh status    # Ver estado
./start-dev.sh logs      # Ver logs
./start-dev.sh help      # Ayuda
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
├── start-dev.sh           # Script desarrollo local
└── build-push.sh          # Script build para VPS
```

## Personalización

### Variables de Entorno (.env)

Las personalizaciones se configuran en `.env`:

```bash
WEBUI_NAME="Open WebUi"
WEBUI_FAVICON_URL="https://webui.codingsoft.org/favicon.png"
WEBUI_ADMIN_EMAIL="team@codingsoft.org"
```

### Personalizaciones Aplicadas

| Campo         | Valor                            |
| ------------- | -------------------------------- |
| **Nombre**    | Open WebUi                       |
| **Repo**      | github.com/CodingSoft/open-webui |
| **Container** | ghcr.io/codingsoft/open-webui    |
| **Docs**      | docs.webui.codingsoft.org        |
| **Web**       | codingsoft.org                   |
| **Email**     | team@codingsoft.org              |
| **Discord**   | Eliminado                        |

## Build y Deploy en VPS

### 1. Preparar el VPS

```bash
# Conectar al VPS
ssh usuario@vps-ip

# Clonar el fork
git clone https://github.com/CodingSoft/open-webui.git
cd open-webui

# Hacer pull de los últimos cambios
git pull origin dev
```

### 2. Build y Push a GHCR (GitHub Container Registry)

```bash
# Configurar GitHub Token
export GITHUB_TOKEN="ghp_tu_token_aqui"

# Ejecutar build y push
./build-push.sh

# O paso a paso:
./build-push.sh build   # Solo build
./build-push.sh push    # Solo push
./build-push.sh deploy  # Build + push completo
```

### 3. Deploy en Producción

```bash
# Actualizar imagen en docker-compose
docker-compose pull

# Reiniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f
```

### 4. Variables de Entorno en VPS

Crear `.env` en el VPS:

```bash
WEBUI_NAME="Open WebUi"
WEBUI_FAVICON_URL="https://webui.codingsoft.org/favicon.png"
WEBUI_ADMIN_EMAIL="team@codingsoft.org"
OLLAMA_BASE_URL=http://ollama:11434
WEBUI_SECRET_KEY=tu_secret_key_aqui
```

## Links Útiles

- **Frontend Dev**: http://localhost:5173
- **Repo Fork**: https://github.com/CodingSoft/open-webui
- **Container Registry**: https://github.com/CodingSoft/open-webui/pkgs/container/open-webui
- **Docs**: https://docs.webui.codingsoft.org
- **Web**: https://codingsoft.org

## Solución de Problemas

### El backend no inicia

```bash
# Ver logs
./start-dev.sh logs

# Verificar Docker
docker ps

# Reiniciar
./start-dev.sh restart
```

### Error de memoria en build

```bash
# Aumentar memoria de Docker Desktop a 8GB+
# O ejecutar build en VPS con más recursos
```
