import uvicorn
from common.api import create_app

app = create_app(specialist="stay", port=8002)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
