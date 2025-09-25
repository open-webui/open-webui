# ComfyUI Microservice

A microservice for AI image generation that integrates with CerebraUI platform. Built with FastAPI and supports multiple image generation workflows including text-to-image, image-to-image, and advanced multimodal generation.

## Features

- **Text-to-Image Generation**: Create images from text descriptions
- **Image-to-Image Transformation**: Transform existing images with text prompts
- **Multimodal Generation**: Combine multiple images and text for complex compositions
- **Fashion Transfer**: Specialized clothing and style transfer functionality
- **File Upload Support**: Handle multiple image formats (JPEG, PNG, WebP, BMP, TIFF, GIF)
- **Rate Limiting**: Built-in protection against overload
- **Error Handling**: Comprehensive error management and logging
- **Docker Support**: Containerized deployment ready

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed service status
- `POST /api/v1/generate/text-to-image` - Text to image generation
- `POST /api/v1/generate/image-to-image` - Image transformation
- `POST /api/v1/generate/multimodal` - Basic multimodal generation
- `POST /api/v1/generate/multimodal-advanced` - Advanced 3-image multimodal
- `POST /api/v1/generate/fashion-transfer` - Specialized fashion transfer
- `GET /api/v1/models` - List available models

## Quick Start

### Prerequisites

- Python 3.11+
- Hugging Face account and API token

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd comfyui-service
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export HUGGINGFACE_API_TOKEN="hf_your_token_here"
```

4. Run the service:
```bash
python main.py
```

The service will be available at http://localhost:8001

### API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Docker Deployment

### Build and run with Docker:
```bash
docker build -t comfyui-service .
docker run -p 8001:8001 -e HUGGINGFACE_API_TOKEN="hf_your_token" comfyui-service
```

### Or use docker-compose:
```bash
docker-compose up
```

## Configuration

### Environment Variables

- `HUGGINGFACE_API_TOKEN` - Required for Hugging Face API access
- `LOG_LEVEL` - Logging level (default: INFO)

### Rate Limits

- 15 requests per minute per IP
- Maximum 5 concurrent requests
- File upload limit: 10MB per file

## Development

### Project Structure
```
comfyui-service/
├── api/
│   ├── __init__.py
│   └── routes.py
├── models/          # Data models (if needed)
├── utils/           # Utility functions (if needed)
├── tests/           # Test files (if needed)
├── main.py          # Application entry point
├── requirements.txt # Python dependencies
├── Dockerfile       # Docker configuration
└── README.md        # This file
```

### Testing

The service includes simulation mode for testing without API costs. If no API token is provided, it will use mock responses.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions, please open an issue on the project repository.