# AccelBrain Model Chatbot (Based on open-webui)

This project is forked from [open-webui/open-webui](https://github.com/open-webui/open-webui?tab=readme-ov-file),  
and is customized to build a Dockerized chatbot for use in the AccelBrain system.

---

## 🛠️ Build Workflow

1. **Update versioning information**:
   - Edit `CHANGELOG.md`
   - Modify `package.json` with the new version info

2. **Trigger the GitHub Actions `build-release` workflow**:
   - Push a tag (e.g., `v1.2.3`) to start the workflow
   - Multi-architecture Docker images will be built and published automatically

---

## 📦 Docker Images

- Once built, images will be published to [Docker Hub](https://hub.docker.com/r/innodiskorg/open-webui):
  ```bash
  docker pull innodiskorg/open-webui:<version>