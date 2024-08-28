import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8080, log_level="debug")