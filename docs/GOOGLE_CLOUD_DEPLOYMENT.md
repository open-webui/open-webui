# Deploying Ceylon Ally to Google Cloud

This guide will help you deploy Ceylon Ally to Google Cloud Platform using Docker and Cloud Run.

## Prerequisites

1. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. Install [Docker](https://docs.docker.com/get-docker/)
3. A Google Cloud account with billing enabled

## Setup Google Cloud Project

1. Create a new project or select an existing one:
```bash
gcloud projects create [PROJECT_ID] --name="[PROJECT_NAME]"
gcloud config set project [PROJECT_ID]
```

2. Enable required APIs:
```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com
```

3. Create a Docker repository in Artifact Registry:
```bash
gcloud artifacts repositories create open-webui --repository-format=docker --location=[REGION] --description="Ceylon Ally Docker repository"
```

## Build and Push Docker Images

1. Configure Docker authentication:
```bash
gcloud auth configure-docker [REGION]-docker.pkg.dev
```

2. Build and tag the images:
```bash
# Build Ollama image
docker build -t [REGION]-docker.pkg.dev/[PROJECT_ID]/open-webui/ollama:latest .

# Build Ceylon Ally image
docker build -t [REGION]-docker.pkg.dev/[PROJECT_ID]/open-webui/open-webui:latest .
```

3. Push the images to Artifact Registry:
```bash
docker push [REGION]-docker.pkg.dev/[PROJECT_ID]/open-webui/ollama:latest
docker push [REGION]-docker.pkg.dev/[PROJECT_ID]/open-webui/open-webui:latest
```

## Deploy to Cloud Run

1. Deploy Ollama service:
```bash
gcloud run deploy ollama \
  --image=[REGION]-docker.pkg.dev/[PROJECT_ID]/open-webui/ollama:latest \
  --region=[REGION] \
  --platform=managed \
  --port=11434 \
  --memory=4Gi \
  --cpu=2 \
  --allow-unauthenticated
```

2. Deploy Ceylon Ally service:
```bash
gcloud run deploy open-webui \
  --image=[REGION]-docker.pkg.dev/[PROJECT_ID]/open-webui/open-webui:latest \
  --region=[REGION] \
  --platform=managed \
  --port=8080 \
  --memory=2Gi \
  --cpu=1 \
  --set-env-vars="OLLAMA_BASE_URL=[OLLAMA_SERVICE_URL]" \
  --allow-unauthenticated
```

Replace `[PROJECT_ID]`, `[REGION]`, and `[OLLAMA_SERVICE_URL]` with your specific values.

## Access Your Deployment

After deployment, you can access your Ceylon Ally instance at the URL provided by Cloud Run. You can find this URL in the Google Cloud Console or by running:

```bash
gcloud run services describe open-webui --region=[REGION] --format='value(status.url)'
```

## Important Notes

1. Ensure your Cloud Run service account has the necessary permissions.
2. Consider setting up a custom domain if needed.
3. Monitor your usage to control costs.
4. Set up appropriate security measures and environment variables.
5. Consider using Cloud Run jobs for background tasks if needed.

## Troubleshooting

1. Check service logs in Cloud Console
2. Verify environment variables are set correctly
3. Ensure services can communicate with each other
4. Check resource allocation if experiencing performance issues