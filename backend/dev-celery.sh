#!/bin/bash

# Determine o diretório do script atual
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# CONFIG_FILE="$SCRIPT_DIR/common-vars.sh"
# chmod +x $CONFIG_FILE

# # Verifique se o arquivo de configuração existe e carregue-o
# if [ -f "$CONFIG_FILE" ]; then
#     echo "A carregar variáveis de configuração de: $CONFIG_FILE"
#     . "$CONFIG_FILE"
# else
#     echo "Erro: Arquivo de configuração $CONFIG_FILE não encontrado."
#     exit 1
# fi

if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs) # Método simples, mas com limitações para valores com espaços/caracteres especiais
fi

# Now you can use the variables loaded from config.env
echo "VECTOR_DB is set to: $VECTOR_DB" # For verification
echo "S3_ENDPOINT_URL is set to: $S3_ENDPOINT_URL"

# Verifique se as variáveis não estão vazias (opcional, mas recomendado)
if [ -z "$VECTOR_DB" ] || [ -z "$S3_ENDPOINT_URL" ]; then
    echo "Erro: Uma ou mais variáveis de configuração não foram definidas corretamente."
    echo "Por favor, verifique o arquivo $CONFIG_FILE."
    # exit 1 # Pode decidir sair se as variáveis forem cruciais
fi



# PORT="${PORT:-3030}"
# uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --log-level=info --forwarded-allow-ips '*' --reload  &
# FASTAPI_PID=$!

# sleep 10
export DATA_DIR="$SCRIPT_DIR/data"


echo "Iniciando o Celery worker..."
celery -A open_webui.celery_worker worker --loglevel=INFO --concurrency=10 &
CELERY_PID=$!

trap "kill $CELERY_PID" SIGINT SIGTERM
wait
