while true; do
  rm -rf /shared/uploads/* && cp -r /app/backend/data/uploads /shared/
  rm -rf /shared/webui.db && cp /app/backend/data/webui.db /shared/webui.db
  sleep 1
done
