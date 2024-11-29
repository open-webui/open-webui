# Backend Service Debug Plan

## Current Issues

### 1. Missing CHANGELOG.md
```
FileNotFoundError: [Errno 2] No such file or directory: '/app/CHANGELOG.md'
FileNotFoundError: [Errno 2] No such file or directory: '/app/backend/open_webui/CHANGELOG.md'
```

The backend service is failing to start due to missing CHANGELOG.md file. The code tries two locations:
- `/app/CHANGELOG.md`
- `/app/backend/open_webui/CHANGELOG.md`

### 2. Missing ffmpeg
```
RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
```

## Docker Compose Solutions

### Solution 1: Mount CHANGELOG.md
Update backend service in docker-compose files to mount the CHANGELOG.md:

```yaml
backend:
  volumes:
    - whatever-backend-{env}:/app/data
    - ./CHANGELOG.md:/app/CHANGELOG.md:ro  # Add this line
```

### Solution 2: Install ffmpeg
Add ffmpeg to backend service:

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
    args:
      - INSTALL_FFMPEG=true  # Add build arg
  environment:
    - SKIP_FFMPEG_CHECK=true  # Optional: Skip ffmpeg check
```

### Solution 3: Environment Variable Override
Try bypassing changelog check with environment variables:

```yaml
backend:
  environment:
    - SKIP_CHANGELOG_CHECK=true  # Add this if supported
    - CHANGELOG_CONTENT=""       # Or this to provide empty content
```

## Implementation Plan

1. Try solutions in this order:
   a. Mount CHANGELOG.md (least intrusive)
   b. Environment variable override (if supported)
   c. Install ffmpeg (if audio features needed)

2. Test after each change:
   ```bash
   docker compose -f docker-compose.dev.yaml --env-file .env.dev up backend
   ```

3. Monitor logs:
   ```bash
   docker compose -f docker-compose.dev.yaml logs -f backend
   ```

## Notes
- All solutions maintain Docker-compose only approach
- No modifications to source code required
- Solutions can be applied to all environments (dev/prod/test)
