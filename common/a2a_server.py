from fastapi import FastAPI
from fastapi.responses import RedirectResponse


def create_app(execute):
    app = FastAPI()

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    @app.post("/run")
    async def run(payload: dict):
        return await execute(payload)

    return app
