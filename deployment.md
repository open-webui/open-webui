## **🛠 Step 1: Install Required Tools**
Before starting, ensure you have the following installed:  
✅ **Docker** → [Install Docker](https://docs.docker.com/get-docker/)  
✅ **Google Cloud SDK** → [Install gcloud](https://cloud.google.com/sdk/docs/install)  
✅ **gcloud authenticated** → Run:  
```sh
gcloud auth login
gcloud config set project cogniforce  # Set your project
gcloud auth configure-docker  # Allow Docker to push to GCR
cd C:\Users\Zsombor\Development\open-webui # Navigate to directory
```

---

## **🐳 Step 2: Build a Docker Image Locally**
Navigate to your OpenWebUI project directory and **build the Docker image**:
```sh
docker build -t gcr.io/cogniforce/openwebui-service .
```
💡 If your **Dockerfile** is inside a subfolder, specify the path like:
```sh
docker build -t gcr.io/cogniforce/openwebui-service -f path/to/Dockerfile .
```

---

## **📤 Step 3: Push the Image to Google Container Registry (GCR)**
Once the image is built, push it to **Google Cloud Registry**:
```sh
docker push gcr.io/cogniforce/openwebui-service
```
✅ **Verify upload** by listing images:
```sh
gcloud container images list
```

---

## **🚀 Step 4: Deploy the Container on Google Cloud Run**
Deploy your image to **Google Cloud Run** with:
```sh
 
```

---

## **🔍 Step 5: Verify the Deployment**
Check **the status of the service**:
```sh
gcloud run services list
```
Retrieve the **service URL**:
```sh
gcloud run services describe openwebui-service --region europe-west4 --format="value(status.url)"
```
Visit this URL in your browser to see if your service is running!

---

## **🚀 Step 5.1: Verify Custom Domain**
Run this command to check your domain mapping:
```sh
gcloud beta run domain-mappings describe --domain chat.cogniforce.io
```

## **🚀 Step 5.2: List Custom Domains**
Run this command to check your domains mapping:
```sh
gcloud beta run domain-mappings list --region=europe-west4
```

## **♻️ Step 6: Updating the Service**
Anytime you update your project:  
1️⃣ **Rebuild the Docker Image**:
```sh
docker build -t gcr.io/cogniforce/openwebui-service .
```
2️⃣ **Push the New Image**:
```sh
docker push gcr.io/cogniforce/openwebui-service
```
3️⃣ **Redeploy to Cloud Run**:
```sh
gcloud run deploy openwebui-service --image gcr.io/cogniforce/openwebui-service --region europe-west4 --allow-unauthenticated
```
4️⃣ **Set the Database Connection (DATABASE_URL)**:

After deploying, set the environment variable for PostgreSQL:
```sh
gcloud run services update openwebui-service --region europe-west4 --set-env-vars DATABASE_URL="postgresql://<dbuser>:<dbpass>@34.91.14.23:5432/postgres"
```
Replace:

    <dbuser> → Your PostgreSQL username
    <dbpass> → Your PostgreSQL password