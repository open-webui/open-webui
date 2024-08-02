# Google Could Guide

## Build and Install Locally

Linux/MacOS:
```
./location/setup/script/start.sh
```

Windows use 
```
copy .env.example .env

npm install
npm run build

cd .\backend

# Optional: To install using Conda as your development environment, follow these instructions:
# Create and activate a Conda environment
conda create --name open-webui-env python=3.11
conda activate open-webui-env

pip install -r requirements.txt -U

start.bat
```

page should be up at http://localhost:8080

## Monitoring Usage Locally



## Deployment

1. Follow [Create Your Project](https://cloud.google.com/appengine/docs/standard/python3/building-app/creating-gcp-project) till Step 5
2. Run the following in your terminal

    ```bash
    gcloud config configurations create [CONFIG_NAME] --activate
    gcloud config configurations list # check if its created
    gcloud config set project [PROJECT_ID]
    gcloud config set account [YOUR_ACCOUNT]
    gcloud auth login
    gcloud config configurations list # check if the setting is correct
    gcloud app create
    ```
