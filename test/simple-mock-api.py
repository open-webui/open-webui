#!/usr/bin/env python3
"""
Ultra Simple Mock API - No dependencies, just prints and echoes
"""

import json
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs


class MockHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Print the request
        print("\n" + "=" * 60)
        print("REQUEST RECEIVED:")
        print("=" * 60)
        print(f"Method: {self.command}")
        print(f"Path: {self.path}")
        print(f"Headers: {dict(self.headers)}")
        print("=" * 60)

        # Send response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        if self.path == "/health":
            response = {
                "status": "healthy",
                "message": "Mock API server is running",
                "timestamp": 1234567890,
            }
        elif self.path == "/v1/models" or self.path == "/models":
            response = {
                "object": "list",
                "data": [
                    {
                        "id": "mock 1",
                        "object": "model",
                        "created": 1234567890,
                        "owned_by": "nenna.ai",
                    },
                    {
                        "id": "mock 2",
                        "object": "model",
                        "created": 1234567890,
                        "owned_by": "nenna.ai",
                    },
                ],
            }
        else:
            response = {"message": "Mock API endpoint", "path": self.path}

        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        # Read the request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        # Print the request
        print("\n" + "=" * 60)
        print("REQUEST RECEIVED:")
        print("=" * 60)
        print(f"Method: {self.command}")
        print(f"Path: {self.path}")
        print(f"Headers: {dict(self.headers)}")
        print(
            f"Body: {json.dumps(json.loads(body), indent=2) if body else 'Empty body'}"
        )
        print("=" * 60)

        # Send response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        # Simple mock response
        response = {
            "id": "mock-response",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-3.5-turbo",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Request received: "
                        + (
                            json.dumps(json.loads(body), indent=2)
                            if body
                            else "Empty body"
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        self.wfile.write(json.dumps(response).encode())

    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


if __name__ == "__main__":
    PORT = 8001
    print(f"Simple Mock API Server")
    print(f"Server: http://localhost:{PORT}")
    print(f"Endpoint: http://localhost:{PORT}/v1/chat/completions")
    print("Press Ctrl+C to stop")

    with socketserver.TCPServer(("", PORT), MockHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
