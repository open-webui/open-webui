# Set default port if not provided
if (-not $env:PORT) {
    $Port = 8080
} else {
    $Port = $env:PORT
}

# Execute uvicorn command
uvicorn main:app --port $Port --host 0.0.0.0 --forwarded-allow-ips '*' --reload