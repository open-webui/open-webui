#!/bin/bash
source .env

# Se já existe um container rabbitmq-local, remove ele
if [ "$(docker ps -a -q -f name=rabbitmq-local)" ]; then
    echo "Container rabbitmq-local já existe."
else
    echo "Container rabbitmq-local não existe."
    echo "Subindo o RabbitMQ..."
    docker run -d \
      --name rabbitmq-local \
      -p 5672:5672 \
      -p 15672:15672 \
      -e RABBITMQ_DEFAULT_USER=guest \
      -e RABBITMQ_DEFAULT_PASS=guest \
      rabbitmq:3-management

    echo "Aguardando o RabbitMQ iniciar..."
    sleep 10
fi

echo "RabbitMQ está pronto!"


PORT="${PORT:-3030}"
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --log-level=info --forwarded-allow-ips '*' --reload  &
FASTAPI_PID=$!

sleep 10
export CELERY_BROKER_URL="amqp://guest:guest@localhost:5672//"
echo "Iniciando o Celery worker..."
celery -A open_webui.celery_worker worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

trap "kill $FASTAPI_PID $CELERY_PID" SIGINT SIGTERM
wait
