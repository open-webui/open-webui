docker run -d \
      --name open-webui-test \
      -p 8080:8080 \
      -e GOOGLE_CLIENT_ID=1063776054060-2fa0vn14b7ahi1tmfk49cuio44goosc1.apps.googleusercontent.com \
      -e GOOGLE_CLIENT_SECRET=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 \
      -e GOOGLE_REDIRECT_URI=http://127.0.0.1:8080/oauth/google/callback \
      -e ENABLE_OAUTH_SIGNUP=true \
      -e OAUTH_ALLOWED_DOMAINS=martins.net \
      -e OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration \
      -e WEBUI_NAME="QuantaBase" \
      -v $(pwd)/assets/logos:/app/backend/open_webui/static \
      -v open-webui:/app/backend/data \
      ghcr.io/open-webui/open-webui:main