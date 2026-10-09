"""Minimal local Ollama HTTP stub. Not a real language model."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = {"name": "canchat-dev-stub:latest", "model": "canchat-dev-stub:latest", "modified_at": "2026-01-01T00:00:00Z", "size": 1, "digest": "dev-stub", "details": {"family": "mock", "format": "gguf", "parameter_size": "0", "quantization_level": "none"}}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, value, status=200):
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path in ('/', '/api/version'):
            return self.send_json({"version": "0.0.0-dev-stub"})
        if self.path == '/api/tags':
            return self.send_json({"models": [MODEL]})
        if self.path == '/api/ps':
            return self.send_json({"models": []})
        self.send_json({"error": "unsupported mock endpoint"}, 404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        data = json.loads(self.rfile.read(length) or '{}')
        if self.path == '/api/show':
            return self.send_json({"modelfile": "FROM scratch", "parameters": "", "template": "{{ .Prompt }}", "details": MODEL['details'], "model_info": {}})
        if self.path == '/api/chat':
            return self.send_json({"model": MODEL['name'], "created_at": "2026-01-01T00:00:00Z", "message": {"role": "assistant", "content": "CANChat development stub response."}, "done": True, "done_reason": "stop"})
        if self.path == '/api/generate':
            return self.send_json({"model": MODEL['name'], "response": "CANChat development stub response.", "done": True})
        self.send_json({"error": "unsupported mock endpoint"}, 404)

ThreadingHTTPServer(('0.0.0.0', 11434), Handler).serve_forever()
