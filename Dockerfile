# Initialize basic args

ARG BUILD_HASH=dev-build
# Override at your own risk - non-root configurations are untested
ARG UID=0
ARG GID=0

######## WebUI frontend ########
FROM --platform=$BUILDPLATFORM node:22-alpine3.20 AS build
ARG BUILD_HASH

WORKDIR /app

# to store git revision in build
RUN apk add --no-cache git

COPY package.json yarn.lock ./
RUN yarn config set network-timeout 300000 && \
    yarn install --frozen-lockfile --ignore-scripts || yarn install --ignore-scripts

COPY . .
ENV APP_BUILD_HASH=${BUILD_HASH}
ENV CHOKIDAR_USEPOLLING=true
ENV CHOKIDAR_INTERVAL=1000
RUN NODE_OPTIONS="--max-old-space-size=4096" yarn build

######## WebUI backend ########
FROM python:3.11-slim-bookworm AS base

# Use args
ARG UID
ARG GID

## Basis ##
ENV ENV=prod \
    PORT=8080

## API Config ##
ENV OPENAI_API_BASE_URL=""

## API Key and Security Config ##
ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false


WORKDIR /app/backend

ENV HOME=/root
# Create user and group if not root
RUN if [ $UID -ne 0 ]; then \
    if [ $GID -ne 0 ]; then \
    addgroup --gid $GID app; \
    fi; \
    adduser --uid $UID --gid $GID --home $HOME --disabled-password --no-create-home app; \
    fi


# Make sure the user has access to the app and root directory
RUN chown -R $UID:$GID /app $HOME

RUN apt-get update && \
    # Install basic dependencies
    apt-get install -y --no-install-recommends git build-essential pandoc gcc netcat-openbsd curl jq && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    # cleanup
    rm -rf /var/lib/apt/lists/*

# install python dependencies
COPY --chown=$UID:$GID ./backend/requirements.txt ./requirements.txt

# Create necessary directories first
RUN mkdir -p /app/backend/data/

# Install uv package manager
RUN pip3 install --no-cache-dir --retries 10 --timeout 600 uv

# Install minimal requirements without ML dependencies
RUN grep -v "sentence-transformers\|transformers\|torch\|accelerate\|datasets\|faster-whisper\|opencv-python\|rapidocr-onnxruntime\|onnxruntime" requirements.txt > requirements-minimal.txt && \
    UV_HTTP_TIMEOUT=600 UV_HTTP_RETRIES=10 uv pip install --system -r requirements-minimal.txt --no-cache-dir


# Set ownership
RUN chown -R $UID:$GID /app/backend/data/



# copy embedding weight from build
# RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2
# COPY --from=build /app/onnx /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx

# copy built frontend files
COPY --chown=$UID:$GID --from=build /app/build /app/build
COPY --chown=$UID:$GID --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --chown=$UID:$GID --from=build /app/package.json /app/package.json

# copy backend files
COPY --chown=$UID:$GID ./backend .

EXPOSE 8080

HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

USER $UID:$GID

ARG BUILD_HASH
ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

CMD [ "bash", "start.sh"]
