import uvicorn
from common.api import create_app

app = create_app(specialist="flight", port=8001)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
