## **1. Pull the Latest Changes from GitHub**

First, ensure your local repository is up to date.

```sh
# Navigate to your project directory
cd C:\Users\Zsombor\Development\open-webui

# Fetch the latest changes from GitHub
git pull origin main
```

If you have a forked repository and need to sync with the upstream repo:

```sh
# Add the original OpenWebUI repository as upstream (if not already added)
git remote add upstream https://github.com/open-webui/open-webui.git

# Fetch the latest updates
git fetch upstream

# Merge the latest upstream changes into your branch
git merge upstream/main
```

If conflicts arise, resolve them manually before proceeding.

---

## **2. Build the Updated Docker Image**

Once your local code is updated, build a new Docker image:

```sh
# Build the Docker image
docker build -t gcr.io/cogniforce/openwebui-service:latest .
```

Verify the built image:

```sh
docker images | grep openwebui-service
```

---

## **3. Push the Image to Google Container Registry (GCR)**

Authenticate Docker with Google Cloud:

```sh
gcloud auth configure-docker
```

Tag the image for Google Cloud:

```sh
docker tag gcr.io/cogniforce/openwebui-service:latest gcr.io/cogniforce/openwebui-service:v1
```

Push the image to **Google Container Registry (GCR)**:

```sh
docker push gcr.io/cogniforce/openwebui-service:latest
```

Confirm that the image is successfully pushed:

```sh
gcloud container images list
```

---

## **4. Deploy the Updated Frontend to Google Cloud Run**

Now, deploy the updated image to **Google Cloud Run**:

```sh
gcloud run deploy openwebui-service \
  --image gcr.io/cogniforce/openwebui-service:latest \
  --region europe-west4 \
  --allow-unauthenticated
```

After deployment, verify the service URL:

```sh
gcloud run services describe openwebui-service --format 'value(status.url)'
```

---

## **5. Verify Deployment**

Once deployed, check if the frontend is working:

- Open the provided URL in a browser.
- Check logs for errors:

```sh
gcloud run logs read openwebui-service
```

If anything breaks, rollback to the previous version:

```sh
gcloud run services update-traffic openwebui-service --to-latest
```

---

## **6. Automate Updates (Optional)**

To automate this process, set up a **GitHub Action** or **Cloud Build** to rebuild and deploy your frontend whenever you push new code.

Would you like a GitHub Action workflow for automated deployment? 🚀

