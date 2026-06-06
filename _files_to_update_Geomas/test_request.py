"""
курлом вызови основную модель по урлу http://87.228.65.110:11436/v1 
айди модели codgician/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GPTQ-int4
вызов в стиле опенаи, всэ стандартно, если что
"""

from openai import OpenAI

DEFAULT_BASE_URL = "http://87.228.65.110:11435/v1"
DEFAULT_MODEL = "granite4:1b"
DEFAULT_API_KEY = "sk-no-key-needed"


def create_client(base_url: str = DEFAULT_BASE_URL, api_key: str = DEFAULT_API_KEY) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def request_model(
    prompt: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str = DEFAULT_API_KEY,
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> str:
    client = create_client(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def main() -> None:
    result = request_model("Напиши хайку про машины.")
    print(result)


if __name__ == "__main__":
    main()