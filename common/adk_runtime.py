"""ADK lifecycle shared by local agents and remote A2A agents."""
import asyncio
import json
import uuid
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


async def run_agent(agent, payload, timeout=100):
    sessions = InMemorySessionService()
    session_id = uuid.uuid4().hex
    app_name = "voyageplus"
    await sessions.create_session(app_name=app_name, user_id="traveler", session_id=session_id)
    runner = Runner(agent=agent, app_name=app_name, session_service=sessions)

    async def collect():
        final = ""
        async for event in runner.run_async(
            user_id="traveler", session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=json.dumps(payload, ensure_ascii=False))]),
        ):
            if event.is_final_response() and event.content:
                final = "".join(part.text or "" for part in event.content.parts or [])
        if not final:
            raise ValueError("L'agent n'a pas renvoyé de réponse finale.")
        return final

    try:
        return await asyncio.wait_for(collect(), timeout=timeout)
    finally:
        await runner.close()
        await sessions.delete_session(app_name=app_name, user_id="traveler", session_id=session_id)
