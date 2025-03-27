import requests

api_key: str | None = None
host: str | None = "http://localhost:8080"
chat_completion_api_endpoint: str | None = '/api/chat/completions'

class ChatCompletion:
    def create(
        model: str,
        messages: list,
        max_completion_tokens: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        num_ctx: int | None = None
        ):
        request_data = {}
        request_data['messages'] = messages
        request_data['model'] = model
        request_data['stream'] = False

        params = {}
        if max_tokens is not None:
            params['max_tokens'] = max_tokens
        if max_completion_tokens is not None:
            params['max_tokens'] = max_completion_tokens
        if temperature is not None:
            params['temperature'] = temperature
        if num_ctx is not None:
            params['num_ctx'] = num_ctx
        request_data['params'] = params

        print(params)

        request_header = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + api_key
        }

        url = host + chat_completion_api_endpoint
        response = requests.post(url, headers=request_header, json=request_data)
        return response
    
if __name__ == '__main__':
    api_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjFmOGViY2VjLTFjZGUtNGM1ZS04Y2YyLTBhNjFiMTBlNjJlZCJ9.Jx-727-o-dl9-PFq6KkkVEuAR7OhVG8AB9agkjggMso'
    message = [
        {
            'content': "Tell me the brief summary for the project",
            'role': 'user'
        }
    ]
    model = 'nadia'
    response = ChatCompletion.create(model, message, max_completion_tokens=1024, temperature=0.1, num_ctx=65565)
    print(response.json())
