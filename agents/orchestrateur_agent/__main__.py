import uvicorn
from common.api import create_app
from .adk_coordinator import plan_trip

app = create_app(execute=plan_trip)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
