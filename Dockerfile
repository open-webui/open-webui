# syntax=docker/dockerfile:1

######## WebUI frontend ########
FROM node:21-alpine3.19 as build

WORKDIR /app

#RUN apt-get update \ 
#    && apt-get install -y --no-install-recommends wget \ 
#    # cleanup
#    && rm -rf /var/lib/apt/lists/*

# wget embedding model weight from alpine (does not exist from slim-buster)
#RUN wget "https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz" -O - | \
#    tar -xzf - -C /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

######## WebUI backend ########
FROM python:3.11-slim-bookworm as base

## Basis ##
ENV ENV=prod \
    PORT=8080

## Basis URL Config ##
ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

## API Key and Security Config ##
ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true

#### Preloaded models #########################################################
## whisper TTS Settings ##
ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

## RAG Embedding Model Settings ##
# any sentence transformer model; models to use can be found at https://huggingface.co/models?library=sentence-transformers
# Leaderboard: https://huggingface.co/spaces/mteb/leaderboard 
# for better persormance and multilangauge support use "intfloat/multilingual-e5-large" (~2.5GB) or "intfloat/multilingual-e5-base" (~1.5GB)
# IMPORTANT: If you change the default model (all-MiniLM-L6-v2) and vice versa, you aren't able to use RAG Chat with your previous documents loaded in the WebUI! You need to re-embed them.
ENV RAG_EMBEDDING_MODEL="all-MiniLM-L6-v2" \
    RAG_EMBEDDING_MODEL_DIR="/app/backend/data/cache/embedding/models" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models" \
    # device type for whisper tts and embbeding models - "cpu" (default) or "mps" (apple silicon) - choosing this right can lead to better performance
    # Important:
    #  If you want to use CUDA you need to install the nvidia-container-toolkit (https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) 
    #  you can set this to "cuda" but its recomended to use --build-arg CUDA_ENABLED=true flag when building the image
    RAG_EMBEDDING_MODEL_DEVICE_TYPE="cuda"
# device type for whisper tts and embbeding models - "cpu" (default), "cuda" (nvidia gpu and CUDA required) or "mps" (apple silicon) - choosing this right can lead to better performance
#### Preloaded models ##########################################################

WORKDIR /app/backend
# install python dependencies
COPY ./backend/requirements.txt ./requirements.txt

RUN pip3 install -r requirements.txt --no-cache-dir

RUN if [ "$RAG_EMBEDDING_MODEL_DEVICE_TYPE" = "cuda" ]; then \
        echo "CUDA enabled" && \
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117 --no-cache-dir; \
    else \
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --no-cache-dir && \
        python -c "import os; from chromadb.utils import embedding_functions; sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=os.environ['RAG_EMBEDDING_MODEL'], device=os.environ['RAG_EMBEDDING_MODEL_DEVICE_TYPE'])"; \
    fi

# preload tts model
RUN python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='auto', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"

#  install required packages
RUN apt-get update \
    # Install pandoc and netcat
    && apt-get install -y --no-install-recommends pandoc netcat-openbsd \
    # for RAG OCR
    && apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6 \
    # cleanup
    && rm -rf /var/lib/apt/lists/*



# copy embedding weight from build
# RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2
# COPY --from=build /app/onnx /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx

# copy built frontend files
COPY --from=build /app/build /app/build
COPY --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --from=build /app/package.json /app/package.json

# copy backend files
COPY ./backend .

EXPOSE 8080

CMD [ "bash", "start.sh"]
