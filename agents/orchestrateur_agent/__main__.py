import uvicorn

from common.a2a_server import create_app
from .task_manager import run

app = create_app(run)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
