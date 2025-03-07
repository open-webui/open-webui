PORT="${PORT:-8080}"

# if custom_resource_loader script exists, run it
if [ -f "custom_resource_loader.py" ]; then
  echo "Running maintenance script"
  python custom_resource_loader.py
else
  echo "custom_resource_loader not found"
fi

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload