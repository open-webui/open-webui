### Download container
```bash
docker pull ghcr.io/sunkendreams/voltron-webui:main
```

### Run Voltron container
```bash
docker run -d -p 3300:8080 --gpus=all -v ollama:/root/.ollama -v voltron:/app/backend/data --name voltron --restart always ghcr.io/sunkendreams/voltron-webui:ollama
```
