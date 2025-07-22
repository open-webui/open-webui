#!/bin/bash

# Determine o diretório do script atual
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Carrega variáveis do arquivo .env (se existir)
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Mostra algumas variáveis carregadas
echo "VECTOR_DB is set to: $VECTOR_DB"
echo "S3_ENDPOINT_URL is set to: $S3_ENDPOINT_URL"

# Validação opcional das variáveis
if [ -z "$VECTOR_DB" ] || [ -z "$S3_ENDPOINT_URL" ]; then
  echo "Erro: Uma ou mais variáveis de configuração não foram definidas corretamente."
  echo "Por favor, verifique o arquivo .env."
  # exit 1
fi
export NODE_OPTIONS="--max-old-space-size=8096"
export ENV="dev"
# Define porta com valor padrão
PORT="${PORT:-3030}"
# Inicia o FastAPI com Uvicorn em background
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --log-level=info  &
FASTAPI_PID=$!

# Define trap para matar o processo quando receber SIGINT ou SIGTERM (ex: CTRL+C)
trap "echo 'Encerrando FastAPI...'; kill $FASTAPI_PID; exit 0" SIGINT SIGTERM

# Aguarda o processo filho encerrar
wait $FASTAPI_PID
