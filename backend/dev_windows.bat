$env:FORWARDED_ALLOW_IPS='*'
$env:CORS_ALLOW_ORIGIN='*'
uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload
