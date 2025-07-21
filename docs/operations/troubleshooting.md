# mAI Troubleshooting Guide

## Understanding the mAI Architecture

The mAI system is designed to streamline interactions between the client (your browser) and the Ollama API. At the heart of this design is a backend reverse proxy, enhancing security and resolving CORS issues.

- **How it Works**: mAI is designed to interact with the Ollama API through a specific route. When a request is made from the WebUI to Ollama, it is not directly sent to the Ollama API. Initially, the request is sent to the mAI backend via `/ollama` route. From there, the backend is responsible for forwarding the request to the Ollama API. This forwarding is accomplished by using the route specified in the `OLLAMA_BASE_URL` environment variable. Therefore, a request made to `/ollama` in the WebUI is effectively the same as making a request to `OLLAMA_BASE_URL` in the backend. For instance, a request to `/ollama/api/tags` in the WebUI is equivalent to `OLLAMA_BASE_URL/api/tags` in the backend.

- **Security Benefits**: This design prevents direct exposure of the Ollama API to the frontend, safeguarding against potential CORS (Cross-Origin Resource Sharing) issues and unauthorized access. Requiring authentication to access the Ollama API further enhances this security layer.

## Common Issues and Solutions

### Server Connection Error

If you're experiencing connection issues, it's often due to the mAI docker container not being able to reach the Ollama server at 127.0.0.1:11434 (host.docker.internal:11434) inside the container.

**Solutions**:

1. **Use Host Network** (Linux only):
   ```bash
   docker run -d --network=host -v mai_open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main
   ```
   Note: Port changes from 3000 to 8080 with host network.

2. **Connect to Host Ollama** (Recommended for Mac/Windows):
   ```bash
   docker run -d -p 3000:8080 -v mai_open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://host.docker.internal:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main
   ```

### Error on Slow Responses for Ollama

mAI has a default timeout of 5 minutes for Ollama to finish generating the response. If needed, this can be adjusted via the environment variable `AIOHTTP_CLIENT_TIMEOUT`, which sets the timeout in seconds.

```bash
docker run -d -p 3000:8080 -e AIOHTTP_CLIENT_TIMEOUT=600 ... # 10 minutes timeout
```

### Docker-Specific Issues

#### 1. Favicon Not Displaying
**Problem**: Favicon doesn't show in production after updates.

**Solution**:
- Clear browser cache (Cmd+Shift+Delete on Mac, Ctrl+Shift+Delete on Windows)
- Force refresh (Cmd+Shift+R on Mac, Ctrl+F5 on Windows)
- Test in incognito/private mode
- Verify files exist: `docker exec open-webui ls -la /app/backend/static/favicon.*`

#### 2. Lost Data After Container Rebuild
**Problem**: User accounts and chat history disappear after rebuilding container.

**Solution**:
- Always use named volumes with `external: true` in docker-compose
- Check existing volumes: `docker volume ls | grep mai`
- Use the correct volume name in your docker-compose.yaml:
  ```yaml
  volumes:
    open-webui:
      external: true
      name: mai_open-webui  # Your existing volume name
  ```

#### 3. Ollama Models Not Showing
**Problem**: No models appear in mAI despite having models on the host.

**Solution**:
- Docker Ollama is isolated from host Ollama
- Option 1: Connect to host Ollama using `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- Option 2: Mount host Ollama directory: `-v ~/.ollama:/root/.ollama`
- Option 3: Pull models inside container: `docker exec ollama ollama pull llama3.1:8b`

#### 4. Port Already in Use
**Problem**: Error "port is already allocated" when starting container.

**Solution**:
- Check what's using the port: `lsof -i :3000` (Mac/Linux) or `netstat -ano | findstr :3000` (Windows)
- Stop conflicting container: `docker stop <container_name>`
- Use a different port: `-p 3001:8080`

### General Connection Errors

**Ensure Ollama Version is Up-to-Date**: Always start by checking that you have the latest version of Ollama. Visit [Ollama's official site](https://ollama.com/) for the latest updates.

**Troubleshooting Steps**:

1. **Verify Ollama URL Format**:
   - When running the mAI container, ensure the `OLLAMA_BASE_URL` is correctly set
   - Common formats:
     - Docker Ollama: `http://ollama:11434`
     - Host Ollama: `http://host.docker.internal:11434`
     - Network Ollama: `http://192.168.1.100:11434`

2. **Check Container Logs**:
   ```bash
   docker logs open-webui
   docker logs ollama
   ```

3. **Test Ollama Connection**:
   ```bash
   # From host
   curl http://localhost:11434/api/tags
   
   # From mAI container
   docker exec open-webui curl http://ollama:11434/api/tags
   ```

4. **Verify Network Connectivity**:
   ```bash
   # Check if containers can communicate
   docker exec open-webui ping ollama
   ```

### Browser-Specific Issues

#### Cache Problems
- **Chrome/Edge**: Cmd/Ctrl + Shift + R for hard refresh
- **Firefox**: Cmd/Ctrl + Shift + R
- **Safari**: Cmd + Option + R
- Clear all browser data if issues persist

#### PWA Installation Issues
- Ensure HTTPS is enabled for production deployments
- Check manifest.json is properly configured
- Verify service worker registration in DevTools

### Database Issues

#### Backup and Restore
```bash
# Backup database
docker exec open-webui sqlite3 /app/backend/data/webui.db ".backup /app/backend/data/backup.db"

# Restore database
docker exec open-webui sqlite3 /app/backend/data/webui.db ".restore /app/backend/data/backup.db"
```

#### Migration Errors
If you encounter database migration errors:
1. Check migration status: `docker exec open-webui alembic current`
2. Apply pending migrations: `docker exec open-webui alembic upgrade head`

### Performance Issues

#### Slow Response Times
1. Check container resources: `docker stats`
2. Increase memory allocation if needed
3. Enable GPU support for Ollama if available
4. Adjust worker count: `-e WORKERS=4`

#### High Memory Usage
1. Limit container memory: `--memory=4g`
2. Monitor with: `docker stats --no-stream`
3. Check for memory leaks in logs

### Development Environment Issues

#### Frontend Not Updating
1. Clear Vite cache: `rm -rf node_modules/.vite`
2. Restart dev server
3. Check for TypeScript errors: `npm run check`

#### Backend Not Reloading
1. Ensure `watchfiles` is installed
2. Check file permissions
3. Restart with: `sh dev.sh`

## Getting Help

If you continue to experience issues:

1. **Check Logs**: Always start by checking container logs
2. **GitHub Issues**: Search existing issues at the mAI repository
3. **Community Support**: Join our Discord community
4. **Documentation**: Review the complete documentation in `/docs`

Remember to include:
- Your Docker version
- Operating system
- Complete error messages
- Steps to reproduce the issue