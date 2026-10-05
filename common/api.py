from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from common.contracts import TripRequest, TripResponse


def create_app(*, execute=None, specialist=None, port=None):
    a2a_app = None
    if specialist:
        from a2a.types import AgentCard, AgentCapabilities, AgentSkill
        from google.adk.a2a.utils.agent_to_a2a import to_a2a
        from agents.adk_agents import build_specialist
        agent = build_specialist(specialist)
        card = AgentCard(name=agent.name, description=agent.description, version="1.0.0",
                         url=f"http://127.0.0.1:{port}/a2a/",
                         capabilities=AgentCapabilities(streaming=True),
                         default_input_modes=["text/plain"], default_output_modes=["text/plain"],
                         skills=[AgentSkill(id=specialist, name=agent.name, description=agent.description, tags=["travel", specialist])])
        a2a_app = to_a2a(agent, agent_card=card)

    @asynccontextmanager
    async def lifespan(app):
        if a2a_app:
            async with a2a_app.router.lifespan_context(a2a_app):
                yield
        else:
            yield

    app = FastAPI(title="VoyagePlus", lifespan=lifespan)

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": specialist or "coordinator"}

    if execute is not None:
        @app.post("/run", response_model=TripResponse)
        async def run_trip(payload: TripRequest):
            return await execute(payload.model_dump(mode="json"))

    if a2a_app:
        app.mount("/a2a", a2a_app)
    return app
