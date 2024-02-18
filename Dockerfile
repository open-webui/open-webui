# syntax=docker/dockerfile:1

FROM node:alpine as build

WORKDIR /app

# wget embedding model weight from alpine (does not exist from slim-buster)
RUN wget "https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz" -O - | \
    tar -xzf - -C /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM python:3.11-slim-bookworm as base

ENV ENV=prod
ENV PORT ""

ENV OLLAMA_API_BASE_URL "/ollama/api"

ENV OPENAI_API_BASE_URL ""
ENV OPENAI_API_KEY ""

ENV WEBUI_SECRET_KEY ""

ENV SCARF_NO_ANALYTICS true
ENV DO_NOT_TRACK true

# whisper TTS Settings
ENV WHISPER_MODEL="base"
ENV WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

# any sentence transformer model; models to use can be found at https://huggingface.co/models?library=sentence-transformers
# Leaderboard: https://huggingface.co/spaces/mteb/leaderboard 
# for better persormance and multilangauge support use "intfloat/multilingual-e5-large"
# IMPORTANT: If you change the default model (all-MiniLM-L6-v2) and vice versa, you aren't able to use RAG Chat with your previous documents loaded in the WebUI! You need to re-embed them.
ENV RAG_EMBEDDING_MODEL="all-MiniLM-L6-v2"

WORKDIR /app/backend

# install python dependencies
COPY ./backend/requirements.txt ./requirements.txt

RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --no-cache-dir
RUN pip3 install -r requirements.txt --no-cache-dir

# Install pandoc and netcat
# RUN python -c "import pypandoc; pypandoc.download_pandoc()"
RUN apt-get update \
    && apt-get install -y pandoc netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# preload embedding model
RUN python -c "import os; from chromadb.utils import embedding_functions; sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=os.environ['RAG_EMBEDDING_MODEL'])"
# preload tts model
RUN python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"


# copy embedding weight from build
RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2
COPY --from=build /app/onnx /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx

# copy built frontend files
COPY --from=build /app/build /app/build

# copy backend files
COPY ./backend .

CMD [ "bash", "start.sh"]